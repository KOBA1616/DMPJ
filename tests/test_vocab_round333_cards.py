"""再変換ラウンド333（第298弾 same_name_cast）の記録テスト。

- 新規登録1件: dm26ex4-cho010 邪眼皇アレクサンドルIII世（最新版）。
  partial（abilities 無し）に第298弾の誘発（choose の reveal: true →
  見つけた場合の if 内で shuffle → may play_free）を1つ足して登録。
  登録形は abilities == [CHO010_FORM]・keywords == [double_breaker] で、
  partial の連結残り・テキスト由来の追加が無いことを固定する。
- alias 畳み込み1件: c48-sec001（旧印刷）は submit の原文コーパスに
  無いため直接は提出できず、cho010 の登録時に validate の
  aliases_for で source.aliases に畳み込まれた（reject 行は reopen で
  除去済み。converted の独立エントリではない）。
- converted 是正3件（件数不変）: 29-sec001 / dm29-s03 / dmc48-001 は
  独立エントリとして本誘発を欠いた形（キーワードのみ）で登録されて
  いた既存の欠落。各エントリの本文は旧印刷形（選んで唱え、その後
  シャッフル）のため、第282弾の詠唱形 CAST_FORM を abilities に追加
  して是正した。
- 差し戻し0件。converted 10,223→10,224 / rejects 2,107→2,099、
  重なり0・漏れ0。same_name_cast は rejects に残らない。

プロトテスト（test_vocab_pilot298.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが
汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402
from test_vocab_pilot282_cards import CAST_FORM  # noqa: E402
from test_vocab_pilot298_cards import CHO010_FORM  # noqa: E402


def setup(rules, p0, p1=None, filler="T002", seed=1, deck_size=20):
    """conftest の setup と同じ薄い包み（tests.conftest は import しない）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

CORRECTED = ["29-sec001", "dm29-s03", "dmc48-001"]


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round333_disposition():
    rej = _reject_rows()
    assert len(rej) == 2096
    # 新規登録: cho010（登録形は提出形と完全一致、連結残り・追加なし）
    c = _conv("dm26ex4-cho010")
    assert c is not None
    assert "dm26ex4-cho010" not in rej
    assert not (c.get("source") or {}).get("unsupported")
    assert c["abilities"] == [CHO010_FORM]
    assert c["keywords"] == ["double_breaker"]
    parse_card(c, TABLES)
    # alias 畳み込み: c48-sec001 は独立エントリではなく cho010 の alias
    assert _conv("c48-sec001") is None
    assert "c48-sec001" not in rej
    assert "c48-sec001" in c["source"]["aliases"]
    assert sorted(c["source"]["aliases"]) == sorted(
        ["29-sec001", "c48-sec001", "dm29-s03", "dmc48-001"])
    # 是正3件: 旧印刷形 CAST_FORM を持ち、キーワードは不変
    for cid in CORRECTED:
        e = _conv(cid)
        assert e is not None, cid
        assert e["abilities"] == [CAST_FORM], cid
        assert e["keywords"] == ["double_breaker"], cid
        assert "ラウンド333で是正" in e["source"]["notes"], cid
        parse_card(e, TABLES)
    # same_name_cast は解消、converted と rejects の重なり0
    assert not [r for r in rej.values()
                if "same_name_cast" in (r.get("gaps") or [])]
    ids = {x["id"] for x in _conv_cache.all_cards(CONVERTED)}
    assert len(ids) == 10227
    assert not (ids & set(rej))


# ---------- 実挙動ドライバ（第298弾のものと同形） ----------

def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _count(e, zone, p, defn):
    return _defns(e, zone, p).count(defn)


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _pub(e, n0, kind, defn=None, zone=None):
    out = []
    for r in e.s.pub:
        if r["n"] < n0 or r.get("kind") != kind:
            continue
        if defn is not None and r.get("defn") != defn:
            continue
        if zone is not None and r.get("zone") != zone:
            continue
        out.append(r)
    return out


class _Driver:
    def __init__(self, play=None, choose=None, may=True):
        self.play = play
        self.choose = choose
        self.may = may
        self.seen = []

    def run(self, e, stop, limit=800):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen.append(kind)
            if kind == "choose_cards" and self.choose is not None:
                ans = self.choose(e, d)
                if ans is not None:
                    e.answer(ans)
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
            if kind == "declare_strigger":
                e.answer([])
            elif kind == "declare_sback":
                e.answer([])
            elif kind == "choose_breaker":
                e.answer([max(range(len(keys)),
                              key=lambda i: int(keys[i].split(":")[1]))])
            elif kind == "choose_shields":
                e.answer(list(range(d.get("min", 0))))
            elif kind == "pay_mana":
                e.answer([0])
            elif kind == "yes_no":
                e.answer([keys.index("yes" if self.may else "no")])
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
    state = {"done": False}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not state["done"]:
            state["done"] = True
            return [keys.index(key)]
        return None

    return play


def _choose_defn(defn):
    def choose(e, d):
        for i, o in enumerate(d["options"]):
            if defn in o["key"]:
                return [i]
        return None

    return choose


def test_registered_cho010_reveals_shuffles_then_casts(rules):
    """dm26ex4-cho010（登録形・最新版形）: 手札から水の呪文 T800 を
    唱えると、山札の同名呪文が表向きにされ、シャッフルされてから
    無償で唱えられる（公開記録の順序 reveal < shuffle、墓地の
    T800 が2枚）。"""
    e = setup(rules, {"bz": ["dm26ex4-cho010", "T799"], "hand": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T800", "T800"]},
              {"bz": ["T001"]})
    n0 = len(e.s.pub)
    drv = _Driver(play=_play_once("play:T800"), choose=_choose_defn("T800"))
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 2
            and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 2
    assert "yes_no" in drv.seen
    reveals = _pub(e, n0, "reveal", defn="T800", zone="deck")
    shuffles = _pub(e, n0, "shuffle")
    assert reveals and shuffles
    assert reveals[0]["n"] < shuffles[0]["n"]


def test_corrected_dm29s03_casts_then_shuffles(rules):
    """dm29-s03（是正形・旧印刷形）: 手札から T800 を唱えると、山札の
    同名呪文を選んで無償で唱え、その後で山札をシャッフルする。
    旧印刷形には「表向きにする」が無いため reveal 記録は出ない。"""
    e = setup(rules, {"bz": ["dm29-s03", "T799"], "hand": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T800", "T800"]},
              {"bz": ["T001"]})
    n0 = len(e.s.pub)
    drv = _Driver(play=_play_once("play:T800"), choose=_choose_defn("T800"))
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 2
            and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 2
    assert "yes_no" in drv.seen
    assert _pub(e, n0, "shuffle")
    assert not _pub(e, n0, "reveal", defn="T800", zone="deck")
