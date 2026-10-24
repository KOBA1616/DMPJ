"""開発者モード: ブラウザでカードの効果を1手ずつ動かして確かめる（標準ライブラリだけで動く）。

    python -m dmsim.devserver            # http://127.0.0.1:8765/ を開く
    python -m dmsim.devserver --port 9000 --host 0.0.0.0

- 「カード」タブ: 公式テキスト・効果データ・変換メモを並べて見る。「試す」でそのカードの局面を作る。
  動きを確かめたら approved / rejected を付ける（data/cards/real.yaml の source.review を書き換える）。
- 「対戦」タブ: シナリオ（各ゾーンの配置）かデッキ＋シードから始め、Decision に答えて進める。
  1手ごとに動いたカードを表示する。1手戻す、記録（シード＋選択ログ）の保存・読み込みができる。
エンジンは DMSIM_CHECK と同じ形の検査を有効にして動かす。
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

from . import scenario as sc
from .defs import DATA, load_rules
from .engine import Engine, IllegalAnswer
from .play import deck_lists, make_record, passive_policy, replay
from .verify import verify_all

WEB = Path(__file__).resolve().parent / "web"
REAL = DATA / "cards" / "real.yaml"
REVIEW_STATES = ("pending", "approved", "rejected")


# ---- カード一覧とレビュー ----------------------------------------------------------------------

def _card_blocks(path: Path) -> dict[str, str]:
    """YAML ファイルの各カードの記述（書かれたままのテキスト）。"""
    text = path.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^ *- id: (\S+)\n.*?(?=^ *- id: |\Z)", text, re.S | re.M):
        out[m.group(1)] = m.group(0).rstrip() + "\n"
    return out


def _official_texts() -> dict[str, dict]:
    out = {}
    for f in sorted((DATA / "cards" / "raw").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                out[row["id"]] = row
    return out


def card_list(rules) -> list[dict]:
    blocks = {}
    for f in sorted((DATA / "cards").glob("*.yaml")):
        blocks.update({k: (f.name, v) for k, v in _card_blocks(f).items()})
    official = _official_texts()
    out = []
    for cid, d in sorted(rules.cards.items(), key=lambda kv: (not kv[1].source, kv[0])):   # 実カードを先に
        src = d.source or {}
        fname, block = blocks.get(cid, ("", ""))
        out.append({"id": cid, "name": d.name, "file": fname, "types": d.types, "civs": d.civs, "cost": d.cost,
                    "text": d.text, "official": official.get(src.get("official", cid)),
                    "review": src.get("review"), "notes": src.get("notes", ""),
                    "review_note": src.get("review_note", ""), "yaml": block,
                    "unsupported": list(src.get("unsupported") or [])})
    return out


def locate_card(card_id: str, root: Path | None = None) -> Path:
    """カード定義が書かれている YAML（real.yaml / converted.yaml など）を探す。"""
    root = root or DATA / "cards"
    for f in sorted(root.glob("*.yaml")):
        if card_id in _card_blocks(f):
            return f
    raise KeyError(f"{card_id} is not in any card file")


def set_review(card_id: str, status: str, note: str = "", path: Path | None = None):
    """カードの source.review を書き換える（コメントや書式はそのまま残す）。
    path を省くと、そのカードが書かれているファイル（real.yaml, converted.yaml など）を探す。"""
    if status not in REVIEW_STATES:
        raise ValueError(f"status must be one of {REVIEW_STATES}")
    path = path or locate_card(card_id)
    text = path.read_text(encoding="utf-8")
    m = re.search(rf"^ *- id: {re.escape(card_id)}\n.*?(?=^ *- id: |\Z)", text, re.S | re.M)
    if not m:
        raise KeyError(f"{card_id} is not in {path.name}")
    block = re.sub(r",? *review_note: \"(?:[^\"\\]|\\.)*\"|\n *review_note: \"(?:[^\"\\]|\\.)*\"", "", m.group(0))
    q = json.dumps(note, ensure_ascii=False)
    inline = re.search(r"(source: \{[^\n]*?review: )\w+", block)
    if inline:
        block = block[:inline.start()] + inline.group(1) + status + (f", review_note: {q}" if note else "") \
            + block[inline.end():]
    else:
        mm = re.search(r"^( +)review: \w+", block, re.M)
        if not mm:
            raise KeyError(f"{card_id} has no source.review")
        block = block[:mm.start()] + f"{mm.group(1)}review: {status}" \
            + (f"\n{mm.group(1)}review_note: {q}" if note else "") + block[mm.end():]
    new = text[:m.start()] + block + text[m.end():]
    yaml.safe_load(new)            # 壊していないことを確かめてから書く
    path.write_text(new, encoding="utf-8")


# ---- 対戦セッション ---------------------------------------------------------------------------

def _label(eng, o: dict) -> str:
    s = eng.s
    parts = [o["key"]]
    if "name" in o:
        parts.append(o["name"])
    for c in o.get("cids", []):
        parts.append(eng.cdef(c).name)
    return " / ".join(dict.fromkeys(parts))


def _card_view(eng, cid: int) -> dict:
    s = eng.s
    c = s.cards[cid]
    v = {"cid": cid, "id": c.defn, "name": eng.fdef(cid).name, "tapped": c.tapped, "owner": c.owner,
         "cost": eng.cdef(cid).cost, "civs": eng.cdef(cid).civs}
    if c.zone == "bz":
        ch = eng.chars(cid)
        v.update(power=ch["power"], keywords=ch["keywords"], controller=c.controller,
                 sick=c.entered_turn == s.turn, under=[eng.cdef(u).name for u in c.under])
    return v


def _opt_view(eng, o: dict) -> dict:
    """選択肢を前端が使いやすい形にする。どのカード・どの攻撃先かを構造で持たせる。"""
    v = {"key": o["key"], "label": _label(eng, o)}
    for k in ("cid", "face", "cids"):
        if k in o:
            v[k] = o[k]
    if "target" in o:
        v["target"] = "player" if o["target"] == "player" else o["target"][0]
    return v


def _hand_hints(eng, p: int) -> dict[str, str]:
    """メインでプレイできない手札の理由（カードID → 理由）。スペースはプレイ可。"""
    out = {}
    for cid in eng.zlist("hand", p):
        d = eng.cdef(cid)
        faces = [(None, d)] if not d.faces else list(enumerate(d.faces))
        for fi, f in faces:
            if eng._can_play_face(cid, p, fi):
                out[d.id] = ""
                break
            if not eng.permits(cid, "summon" if f.is_creature() else "cast", face=fi):
                reason = "効果により実行できない"
            elif "evolution" in f.types:
                reason = "進化元のクリーチャーがいない"
            else:
                reason = "マナが足りない（枚数・文明が合っていない）"
            out[d.id] = reason
    return out


def _attack_hints(eng, a: int) -> dict[int, str]:
    """攻撃ステップで攻撃できないクリーチャーの理由（cid → 理由）。"""
    out = {}
    for cid in eng.bz_tops(a):
        if eng._can_attack(cid):
            continue
        c = eng.s.cards[cid]
        if c.tapped:
            out[cid] = "タップ中（攻撃に使えるのはアンタップ状態）"
        elif c.entered_turn == eng.s.turn:
            out[cid] = "召喚酔い（このターンに出したので攻撃できない）"
        elif not eng.permits(cid, "attack_player") and not eng.permits(cid, "attack_creature"):
            out[cid] = "効果により攻撃できない"
        else:
            out[cid] = "攻撃できる先がいない"
    return out


def _snapshot(eng) -> dict[int, tuple]:
    return {c.cid: (c.zone, c.controller, c.tapped, c.gen) for c in eng.s.cards}


def _diff(eng, before, after) -> list[str]:
    out = []
    for cid, (z0, p0, t0, g0) in before.items():
        z1, p1, t1, g1 = after[cid]
        name = eng.cdef(cid).name
        if z0 != z1:
            out.append(f"P{eng.s.cards[cid].owner} {name}: {z0} → {z1}")
        elif g0 != g1:
            out.append(f"P{eng.s.cards[cid].owner} {name}: {z0} を出入り")
        elif t0 != t1:
            out.append(f"P{eng.s.cards[cid].owner} {name}: {'タップ' if t1 else 'アンタップ'}")
    return out


class Session:
    def __init__(self, rules, start: dict):
        self.rules = rules
        self.start = start            # {"scenario": spec} か {"decks": [...], "seed": n, "first": p}
        self.auto = [False, True]     # 自動で答えるプレイヤー（既定: 相手は何もしない方策）
        self.eng = self._new()
        self.history: list[dict] = []
        self._settle()

    def _new(self) -> Engine:
        if "scenario" in self.start:
            return sc.build(self.rules, self.start["scenario"], check=True)
        return Engine.new_game(self.rules, self.start["decks"], self.start.get("seed", 1),
                               self.start.get("first", 0), check=True)

    def _step(self, choice, auto=False):
        d = self.eng.s.waiting
        before, turn = _snapshot(self.eng), self.eng.s.turn
        self.eng.answer(choice)
        self.eng.advance()
        self.history.append({"p": d["player"], "kind": d["kind"], "auto": auto, "turn": turn,
                             "chosen": [_label(self.eng, d["options"][i]) for i in self.eng.log[-1]["choice"]],
                             "changes": _diff(self.eng, before, _snapshot(self.eng))})

    def _settle(self, limit=500):
        before = _snapshot(self.eng)
        d = self.eng.advance()
        if not self.history and d is not None:
            ch = _diff(self.eng, before, _snapshot(self.eng))
            if ch:
                self.history.append({"p": None, "kind": "start", "auto": True, "turn": 1, "chosen": [],
                                     "changes": ch})
        for _ in range(limit):
            d = self.eng.s.waiting
            if d is None or not self.auto[d["player"]]:
                return
            self._step(passive_policy(self.eng, d), auto=True)

    def answer(self, choice):
        self._step(choice)
        self._settle()

    def undo(self):
        """自分（自動でない）の直前の選択まで戻す。シード＋ログからの再生で戻すので状態は必ず一致する。"""
        keep = len(self.eng.log)
        while keep and self.history and self.history[-1]["auto"] and self.history[-1]["kind"] != "start":
            self.history.pop()
            keep -= 1
        if keep and self.history and self.history[-1]["kind"] != "start":
            self.history.pop()
            keep -= 1
        log = self.eng.log[:keep]
        eng = self._new()
        for e in log:
            eng.advance()
            eng.answer(e["choice"])
        eng.advance()
        self.eng = eng

    def record(self) -> dict:
        spec = self.start.get("scenario")
        return make_record(self.eng, deck_lists(self.eng), (spec or self.start).get("seed", 1),
                           self.start.get("first", 0), scenario=spec)

    @classmethod
    def from_record(cls, rules, rec: dict) -> "Session":
        start = {"scenario": rec["scenario"]} if rec.get("scenario") else \
            {"decks": rec["decks"], "seed": rec["seed"], "first": rec.get("first_player", 0)}
        self = cls.__new__(cls)
        self.rules, self.start, self.auto, self.history = rules, start, [False, False], []
        self.eng = replay(rules, rec["decks"], rec["seed"], [], rec.get("first_player", 0), rec.get("scenario"))
        for e in rec["log"]:
            self.eng.advance()
            self._step(e["choice"])
        self.eng.advance()
        self.auto = [False, True]
        return self

    def view(self) -> dict:
        eng, s = self.eng, self.eng.s
        zones = {}
        for p in (0, 1):
            zs = {}
            for z in eng.rules.zones:
                if z == "bz":
                    cids = eng.bz_tops(p)
                else:
                    cids = eng.zlist(z, p)
                if z == "deck":
                    zs[z] = {"count": len(cids), "top": [_card_view(eng, c) for c in cids[:5]]}
                elif cids or z in ("hand", "bz", "mana", "shield", "graveyard"):
                    zs[z] = [_card_view(eng, c) for c in cids]
            zones[p] = zs
        d = s.waiting
        dec = None
        hints = None
        if d is not None:
            dec = {"player": d["player"], "kind": d["kind"], "min": d["min"], "max": d["max"],
                   "prompt": d.get("prompt", ""),
                   "options": [_opt_view(eng, o) for o in d["options"]]}
            if d["kind"] == "attack":
                for o in dec["options"]:          # プレイヤー攻撃: ブレイク枚数を表示用に出しておく
                    if o.get("target") == "player":
                        counts = sorted(set(eng.chars(o["cid"])["break_opts"])) or [1]
                        o["breaks"] = max(counts)
                hints = {"bz": _attack_hints(eng, s.active)}
            elif d["kind"] == "main":
                hints = {"hand": _hand_hints(eng, s.active)}
        return {"turn": s.turn, "active": s.active, "step": s.step, "result": s.result, "decision": dec,
                "hints": hints,
                "zones": zones, "hold": [_card_view(eng, c) for c in s.hold],
                "continuous": [{"mod": c["mod"], "duration": c["duration"]} for c in s.continuous],
                "delayed": [{"when": x["when"], "duration": x["duration"]} for x in s.delayed],
                "step_mods": s.step_mods, "history": self.history[-60:], "auto": self.auto,
                "log_len": len(eng.log), "digest": s.digest()}


# ---- HTTP ------------------------------------------------------------------------------------

class App:
    def __init__(self):
        self.lock = threading.Lock()
        self.rules = load_rules()
        self.sessions: dict[int, Session] = {}
        self.next_id = 1
        self.playbacks: dict[int, object] = {}

    def _add(self, sess) -> dict:
        gid = self.next_id
        self.next_id += 1
        self.sessions[gid] = sess
        return {"gid": gid, **sess.view()}

    def _pb_open(self, body: dict) -> dict:
        """再生を開く。body は {record} / {record, cert, at, laps}（証明書の周回を記録につなげる）/
        {deck, seed, first, turns, budget, opp_deck}（1局を回して記録にする。探索結果の勝ち筋を見る用）。"""
        from .playback import Playback, cert_from_dict, record_with_cert
        rec = body.get("record")
        if rec is not None and body.get("cert"):
            rec = record_with_cert(self.rules, rec, int(body["at"]), cert_from_dict(body["cert"]), int(body.get("laps", 1)))
        elif rec is None:
            from .solitaire import play_game
            fp = int(body.get("first", 0))
            deck = list(body["deck"])
            opp = list(body.get("opp_deck") or ["T001"] * len(deck))
            res, eng = play_game(self.rules, deck, opp, int(body.get("seed", 1)), first_player=fp,
                                 max_turn=int(body.get("turns", 4)), budget=int(body.get("budget", 200)))
            rec = make_record(eng, [deck, opp], int(body.get("seed", 1)), fp, note=json.dumps(asdict(res), ensure_ascii=False))
        pid = self.next_id
        self.next_id += 1
        pb = self.playbacks[pid] = Playback(self.rules, rec)
        return {"pid": pid, "record": rec, **pb.info}

    def handle(self, path: str, body: dict):
        if path == "/api/cards":
            return {"cards": card_list(self.rules), "zones": list(self.rules.zones)}
        if path == "/api/try":
            return {"scenario": sc.try_card(self.rules, body["id"])}
        if path == "/api/new":
            start = {"scenario": body["scenario"]} if body.get("scenario") else \
                {"decks": body["decks"], "seed": int(body.get("seed", 1)), "first": int(body.get("first", 0))}
            return self._add(Session(self.rules, start))
        if path == "/api/load":
            return self._add(Session.from_record(self.rules, body["record"]))
        if path == "/api/pb_open":
            return self._pb_open(body)
        if path == "/api/pb_frame":
            return self.playbacks[int(body["pid"])].view_at(int(body["i"]))
        if path == "/api/review":
            set_review(body["id"], body["status"], body.get("note", ""))
            self.rules = load_rules()
            return {"ok": True}
        if path == "/api/review_bulk":
            for cid in body["ids"]:
                set_review(cid, body["status"], body.get("note", ""))
            self.rules = load_rules()
            return {"ok": True, "n": len(body["ids"])}
        if path == "/api/verify_all":
            # 一括検証: 「試す」シナリオを自動回しして、動かないカードを見つける
            res = verify_all(self.rules, body.get("ids"))
            return {"results": res, "ok": sum(1 for r in res if r["status"] == "ok"),
                    "total": len(res)}
        sess = self.sessions[int(body["gid"])]
        if path == "/api/answer":
            sess.answer(body["choice"])
        elif path == "/api/undo":
            sess.undo()
        elif path == "/api/auto":
            sess.auto = [bool(x) for x in body["auto"]]
            sess._settle()
        elif path == "/api/record":
            return sess.record()
        elif path != "/api/view":
            raise KeyError(path)
        return {"gid": int(body["gid"]), **sess.view()}


def make_handler(app: App):
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code, data: bytes, ctype="application/json; charset=utf-8", extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8",
                           extra={"Cache-Control": "no-store"})
            elif self.path.startswith("/api/"):
                self._api(self.path, {})
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            self._api(self.path, body)

        def _api(self, path, body):
            try:
                with app.lock:
                    out = app.handle(path, body)
                self._send(200, json.dumps(out, ensure_ascii=False, default=list).encode())
            except (IllegalAnswer, KeyError, ValueError, StopIteration, RuntimeError) as e:
                self._send(400, json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False).encode())
    return H


def serve(host="127.0.0.1", port=8765):
    srv = ThreadingHTTPServer((host, port), make_handler(App()))
    print(f"dmsim 開発者モード: http://{host}:{port}/")
    srv.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    serve(a.host, a.port)
