"""語彙パイロット第276弾のカード適用テスト（登録形）。

ラウンド311で grant_duration の純粋4件をすべて新規登録、差し戻しなし。
- dmex18-s11 地龍神バラフィオル（自然・コスト10・パワー22000・ファイブ・
  オリジン・ドラゴン）: partial の abilities はマッハファイター展開形のみ
  だったため、攻撃誘発（自分のドラゴンが相手プレイヤーを攻撃する時、上から
  3枚を表向きにしてドラゴンを1体出してもよい、残りは好きな順序で底へ）と
  破壊時誘発（次の自分のターンの終わりまで world_breaker 付与、
  until_next_own_turn_end）を公式全文から組んだ。
- dmr05-078 ビックリ・ガード（光・呪文・コスト1・S・トリガー）: 呪文面は
  partial が空。ブロッカー付与を until_next_own_turn_start で組んだ。
- dmr22-006 ジャッジメント・タイム（光/水・呪文・コスト5）: partial は
  abilities 空・text 切り詰め。ロック（deny [attack_player, attack_creature,
  block, untap_at_start]、until_next_opp_turn_end）＋光のコスト4以下の呪文の
  無償詠唱（may+play_free）＋唱えた後の山札下行き（zone: hold の自己置換、
  reason: resolve）を公式全文から組んだ。マナゾーンに置く時タップして置くは
  多色カードの一般則のため面項目なし。
- dmrp19-032 †正義†と「正義」（光・呪文・コスト6）: partial のシンパシー
  常在型は完全なためそのまま。呪文面は「次の相手のターン中のみ」の
  delayed_trigger イディオム（第276弾）。
- converted 10,135 / rejects 2,198、重複0・漏れ0。grant_duration ギャップは
  残り0件でファミリー解消。

プロトテスト（test_vocab_pilot276.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
IDS = ["dmex18-s11", "dmr05-078", "dmr22-006", "dmrp19-032"]


def _setup(rules, p0, p1=None, **kw):
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001",
                         "seed": 1, "deck_size": 20, **kw})


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if r["id"] == cid:
                return r
    raise KeyError(cid)


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, zone, p, defn):
    cids = e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)
    return next(c for c in cids if e.cdef(c).id == defn)


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _keywords(e, cid):
    return e.chars_ro(cid)["keywords"]


class _Driver:
    """汎用ドライバ（第276弾プロトテストのもの）。

    play: main 決定で (e, d) -> 答えのリストか None を返すフック。
    choose_defn: choose_cards ではその defn のカードを選ぶ。
    attacks: {(turn, player): 攻撃キー}。その攻撃決定で一度だけそのキーを選ぶ。
    attack_log: (turn, player, keys) を全攻撃決定について記録する。
    block_defn: block 決定でその defn のブロッカーを選ぶ。
    """

    def __init__(self, play=None, choose_defn=None, attacks=None, block_defn=None):
        self.play = play
        self.choose_defn = choose_defn
        self.attacks = dict(attacks or {})
        self.block_defn = block_defn
        self.attack_log = []

    def run(self, e, stop, limit=1200):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            if kind == "choose_cards" and self.choose_defn is not None:
                hit = [i for i, o in enumerate(d["options"])
                       if e.cdef(o["cid"]).id == self.choose_defn]
                if hit:
                    e.answer(hit[:1])
                    if stop(e):
                        return
                    continue
            if kind == "main" and self.play is not None:
                ans = self.play(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "attack":
                self.attack_log.append((e.s.turn, d["player"], list(keys)))
                key = self.attacks.get((e.s.turn, d["player"]))
                if key is not None and key in keys:
                    del self.attacks[(e.s.turn, d["player"])]
                    e.answer([keys.index(key)])
                    if stop(e):
                        return
                    continue
            if kind == "block" and self.block_defn is not None:
                hit = [i for i, o in enumerate(d["options"])
                       if o["key"].startswith(f"bz:{self.block_defn}")]
                if hit:
                    e.answer(hit[:1])
                    if stop(e):
                        return
                    continue
            if kind == "declare_strigger":
                e.answer([])
            elif kind == "declare_sback":
                e.answer([])
            elif kind == "choose_breaker":
                e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
            elif kind == "choose_shields":
                e.answer(list(range(d.get("min", 0))))
            elif kind == "pay_mana":
                e.answer([0])
            elif kind == "yes_no":
                e.answer([keys.index("yes")])
            elif kind == "order_pending":
                e.answer([0])
            elif kind == "block":
                if "no_block" in keys:
                    e.answer([keys.index("no_block")])
                else:
                    e.answer(list(range(d.get("min", 0))))
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            if stop(e):
                return
        raise AssertionError("limit reached")


def _play_once(key):
    seen = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None

    return play


# ---------- 登録形 ----------

def test_registered_forms():
    for cid in IDS:
        c = _converted(cid)
        parse_card(copy.deepcopy(c), TABLES)
        assert "unsupported" not in (c.get("source") or {}), cid
        try:
            _reject(cid)
            raise AssertionError(f"{cid} が rejects に残っている")
        except KeyError:
            pass

    c = _converted("dmex18-s11")
    assert c["name"] == "地龍神バラフィオル"
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 10 and c["power"] == 22000
    assert c["races"] == ["ファイブ・オリジン・ドラゴン"]
    assert c["keywords"] == ["quad_breaker"]
    assert c["text"] == (
        "マッハファイター\nQ・ブレイカー\n"
        "自分のドラゴンが相手プレイヤーを攻撃する時、自分の山札の上から３枚を表向きにする。"
        "その中からドラゴンを１体出してもよい。その後、残りを好きな順序で山札の下に置く。\n"
        "このクリーチャーが破壊された時、次の自分のターンの終わりまで、"
        "自分のクリーチャーすべてに「ワールド・ブレイカー」を与える。")
    mach, atk, des = c["abilities"]
    # マッハファイターは展開形（キーワードパターンの展開と同形）
    assert mach == {"kind": "trigger",
                    "when": {"event": "move", "to": "bz", "subject": "self"},
                    "effect": [{"op": "modify", "select": {"ref": "self"},
                                "mod": {"allow": [{"action": "attack_creature",
                                                   "other": {"tapped": False}}]},
                                "duration": "end_of_turn"}]}
    assert atk["kind"] == "trigger"
    assert atk["when"] == {"event": "attack", "target": "player",
                           "subject": {"owner": "you",
                                       "filter": {"types": ["creature"],
                                                  "race_has": "ドラゴン"}}}
    ch, may, mv = atk["effect"]
    assert ch["op"] == "choose" and ch["reveal"] is True and ch["as"] == "pile"
    assert ch["select"] == {"zone": "deck", "owner": "you", "from_top": 3,
                            "look": True, "count": "all"}
    assert may["op"] == "may"
    assert may["body"] == [{"op": "play_free",
                            "select": {"ref": "pile",
                                       "filter": {"types": ["creature"],
                                                  "race_has": "ドラゴン"},
                                       "count": 1}}]
    assert mv == {"op": "move", "select": {"ref": "pile", "count": "all"},
                  "to": "deck", "position": "bottom", "order": "choose",
                  "reason": "put"}
    assert des["kind"] == "trigger"
    assert des["when"] == {"event": "move", "from": "bz", "to": "graveyard",
                           "reason": "destroy", "subject": "self"}
    assert des["effect"] == [{"op": "modify",
                              "select": {"zone": "bz", "owner": "you",
                                         "filter": {"types": ["creature"]},
                                         "count": "all"},
                              "mod": {"grant": ["world_breaker"]},
                              "duration": "until_next_own_turn_end"}]

    c = _converted("dmr05-078")
    assert c["name"] == "ビックリ・ガード"
    assert c["types"] == ["spell"] and c["civs"] == ["light"]
    assert c["cost"] == 1 and c["keywords"] == ["s_trigger"]
    assert c["spell"] == [{"op": "modify",
                           "select": {"zone": "bz", "owner": "you",
                                      "filter": {"types": ["creature"]},
                                      "count": "all"},
                           "mod": {"grant": ["blocker"]},
                           "duration": "until_next_own_turn_start"}]

    c = _converted("dmr22-006")
    assert c["name"] == "ジャッジメント・タイム"
    assert c["types"] == ["spell"] and c["civs"] == ["light", "water"]
    assert c["cost"] == 5
    assert c["text"] == (
        "マナゾーンに置く時、このカードはタップして置く。"
        "次の相手のターンの終わりまで、相手のクリーチャーは攻撃もブロックもできず、アンタップしない。"
        "光のコスト４以下の呪文を１枚、コストを支払わずに自分の手札から唱えてもよい。"
        "この呪文を唱えた後、自分の墓地に置くかわりに山札の一番下に置く。")
    lock, free = c["spell"]
    assert lock == {"op": "modify",
                    "select": {"zone": "bz", "owner": "opp",
                               "filter": {"types": ["creature"]}, "count": "all"},
                    "mod": {"deny": ["attack_player", "attack_creature",
                                     "block", "untap_at_start"]},
                    "duration": "until_next_opp_turn_end"}
    assert free == {"op": "may", "body": [
        {"op": "play_free",
         "select": {"zone": "hand", "owner": "you",
                    "filter": {"types": ["spell"], "civs": ["light"],
                               "cost_le": 4},
                    "count": 1}}]}
    (rep,) = c["abilities"]
    assert rep == {"kind": "replace", "zone": "hold",
                   "when": {"event": "move", "to": "graveyard",
                            "reason": "resolve", "subject": "self"},
                   "instead": [{"op": "move", "select": {"ref": "self"},
                                "to": "deck", "position": "bottom",
                                "reason": "return"}]}

    c = _converted("dmrp19-032")
    assert c["name"] == "†正義†と「正義」"
    assert c["types"] == ["spell"] and c["civs"] == ["light"]
    assert c["cost"] == 6
    (sym,) = c["abilities"]
    assert sym["kind"] == "static" and sym["zone"] == "hand"
    assert sym["mod"]["cost"]["amount"] == -1
    assert c["spell"] == [{"op": "delayed_trigger",
                           "when": {"event": "turn_start", "player": "opp"},
                           "duration": "permanent",
                           "effect": [{"op": "modify",
                                       "select": {"zone": "bz", "owner": "you",
                                                  "filter": {"types": ["creature"]},
                                                  "count": "all"},
                                       "mod": {"no_leave": True},
                                       "duration": "end_of_turn"}]}]


# ---------- 実挙動 ----------

def test_registered_s11_attack_trigger_puts_dragon():
    """dmex18-s11: 自分のドラゴン（自身）が相手プレイヤーを攻撃する時、
    上から3枚を表向きにし、その中のドラゴンを1体出し、残りは底へ戻る。"""
    e = _setup(load_rules(),
               {"bz": ["dmex18-s11"], "deck": ["T063"] * 8},
               {"deck": ["T002"] * 8}, deck_size=8)
    drv = _Driver(choose_defn="T063",
                  attacks={(1, 0): "attack:dmex18-s11:player"})
    drv.run(e, lambda ev: "T063" in _defns(ev, "bz", 0) and _quiet(ev))
    assert "T063" in _defns(e, "bz", 0)          # 見たドラゴンを出した
    rest = _defns(e, "deck", 0) + _defns(e, "hand", 0)
    assert rest.count("T063") == 7               # 残りは山札に戻った（底）


def test_registered_s11_destroy_grants_world_breaker():
    """dmex18-s11: 相手のターンに破壊されても、付与は次の自分のターンの
    終わりまで続く（生成ターンは解決済み duration の生成ターン欄で証明）。"""
    e = _setup(load_rules(),
               {"bz": ["dmex18-s11", "T001"]},
               {"hand": ["T056"], "mana": ["T008", "T008", "T008"]})
    t001 = _cid(e, "bz", 0, "T001")
    drv = _Driver(play=_play_once("play:T056"), choose_defn="dmex18-s11")
    drv.run(e, lambda ev: "dmex18-s11" in _defns(ev, "graveyard", 0) and _quiet(ev))
    ce = next(c for c in e.s.continuous if c["duration"].startswith("until_turn_end:"))
    assert ce["duration"] == "until_turn_end:0:2"   # 自分・生成ターン2（相手のターン）
    assert "world_breaker" in _keywords(e, t001)
    drv.run(e, lambda ev: ev.s.turn >= 3 and _quiet(ev))
    assert "world_breaker" in _keywords(e, t001)    # 次の自分のターンいっぱい
    drv.run(e, lambda ev: ev.s.turn >= 4 and _quiet(ev))
    assert "world_breaker" not in _keywords(e, t001)  # ターン3終了で失効


def test_registered_078_grants_blocker_until_next_own_turn_start():
    """dmr05-078: 次の自分のターンのはじめまでブロッカー付与。"""
    e = _setup(load_rules(),
               {"hand": ["dmr05-078"], "mana": ["T030"], "bz": ["T001"]},
               {"bz": ["T001"]})
    t001 = _cid(e, "bz", 0, "T001")
    drv = _Driver(play=_play_once("play:dmr05-078"))
    drv.run(e, lambda ev: any(c["duration"] == "until_turn_start:0"
                              for c in ev.s.continuous) and _quiet(ev))
    assert "blocker" in _keywords(e, t001)
    drv.run(e, lambda ev: ev.s.turn == 2 and _quiet(ev))
    assert "blocker" in _keywords(e, t001)          # 相手のターンいっぱい
    drv.run(e, lambda ev: ev.s.turn == 3 and _quiet(ev))
    assert "blocker" not in _keywords(e, t001)      # 自分のターンのはじめに失効


def test_registered_006_lock_free_cast_and_bottom():
    """dmr22-006: ロック＋手札の光呪文の無償詠唱＋自身は山札の一番下へ。
    ロックは次の相手のターンの終わりまで（ターン2は攻撃決定自体が出ず、
    ターン4には戻る）。"""
    e = _setup(load_rules(),
               {"hand": ["dmr22-006", "dmr05-078"], "mana": ["T030"] * 5,
                "bz": ["T001"]},
               {"bz": ["T004", "T001"]})
    t001 = _cid(e, "bz", 0, "T001")
    drv = _Driver(play=_play_once("play:dmr22-006"), choose_defn="dmr05-078")
    drv.run(e, lambda ev: "dmr22-006" in _defns(ev, "deck", 0) and _quiet(ev))
    assert "dmr22-006" not in _defns(e, "graveyard", 0)   # 墓地ではなく山札へ
    assert "dmr05-078" in _defns(e, "graveyard", 0)       # 無料で唱えた呪文は墓地へ
    assert "blocker" in _keywords(e, t001)                # 唱えた 078 の付与
    ce = next(c for c in e.s.continuous
              if c["duration"].startswith("until_turn_end:"))
    assert ce["duration"] == "until_turn_end:1:1"         # 相手・生成ターン1
    assert ce["mod"]["deny"] == ["attack_player", "attack_creature",
                                  "block", "untap_at_start"]
    # ターン2（相手）: ロック中は攻撃決定に相手の攻撃キーが現れない
    drv.run(e, lambda ev: ev.s.turn >= 3 and _quiet(ev))
    assert not any(t == 2 and p == 1 and any(k.startswith("attack:")
                                             for k in keys)
                   for t, p, keys in drv.attack_log)
    # ターン4（相手）: ターン2終了で失効し、攻撃が戻る
    drv.run(e, lambda ev: any(t == 4 and p == 1 for t, p, _ in drv.attack_log))
    keys4 = next(k for t, p, k in drv.attack_log if t == 4 and p == 1)
    assert any(k.startswith("attack:") for k in keys4)


def test_registered_p19_idiom_window():
    """dmrp19-032: 次の相手のターン中のみ離れない。自分のターン（1）では
    効かず、相手のターン（2）のバトルでは離れず、失効後のターン4で破壊。"""
    e = _setup(load_rules(),
               {"hand": ["dmrp19-032"], "mana": ["T030"] * 6, "bz": ["T001"]},
               {"bz": ["T779"]})
    t001 = _cid(e, "bz", 0, "T001")
    drv = _Driver(play=_play_once("play:dmrp19-032"),
                  attacks={(1, 0): "attack:T001:player",
                           (2, 1): "attack:T779:T001",
                           (3, 0): "attack:T001:player",
                           (4, 1): "attack:T779:T001"})
    drv.run(e, lambda ev: any(d["when"].get("event") == "turn_start"
                              for d in ev.s.delayed) and _quiet(ev))
    assert e.s.turn == 1
    assert e.chars_ro(t001)["no_leave"] == []          # 自分のターン中は効かない
    drv.run(e, lambda ev: ev.s.turn >= 3 and _quiet(ev))
    assert "T001" in _defns(e, "bz", 0)                # ターン2のバトルで離れなかった
    assert "T001" not in _defns(e, "graveyard", 0)
    assert e.s.cards[_cid(e, "bz", 1, "T779")].tapped  # T779 は確かに攻撃した
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert any(t == 4 and p == 1 and "attack:T779:T001" in keys
               for t, p, keys in drv.attack_log)       # 失効後のターン4で破壊
