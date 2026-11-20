"""再変換ラウンド329（第294弾「下にあったカード」）の記録テスト。

- 新規登録4件: dm25rp2-033（形A）/ dmex12-004（形B）/ dmex12-037（形C）/
  dm24bd5-012（形D）。差し戻し0件、alias 畳み込み0件（alias は各カードの
  source.aliases として登録時に併記）。
- dm24bd5-012 はラウンド328で was_under_cards_return に差し戻された行で、
  第294弾の was_under で再変換された。
- ラウンド直後: converted 10,211 / rejects 2,115、重なり0・漏れ0。
  was_under_cards_return は rejects に残らない（ファミリー解消）。
- submit 時の lint 警告2件（dmex12-004 / dmex12-037 の play_free）は
  助言であり、「出す」は召喚意味論（第288弾: play_free の場への移動は
  reason: summon）のため第294弾の登録形が正。

プロトテスト（test_vocab_pilot294.py）とは別プロセスで実行すること
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


def setup(rules, p0, p1=None, filler="T002", seed=1, deck_size=20):
    """conftest の setup と同じ薄い包み（tests.conftest は import しない）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

NEW = ["dm25rp2-033", "dmex12-004", "dmex12-037", "dm24bd5-012"]


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round329_disposition():
    rej = _reject_rows()
    for cid in NEW:
        c = _conv(cid)
        assert c is not None, cid                      # 新規登録された
        assert cid not in rej, cid                     # rejects に残らない
        assert "unsupported" not in (c.get("source") or {}), cid
        parse_card(c, TABLES)                          # 登録形が parse できる
    # ファミリー解消: was_under_cards_return を含む行は rejects に残らない
    assert not [r["id"] for r in rej.values()
                if "was_under_cards_return" in (r.get("gaps") or [])]


# ---------- 実挙動 ----------

def _wire(e, host_defn, under_defns, p=0):
    """bz に置いた札同士で進化スタックを組む（第294弾テストと同じ）。"""
    host = next(c for c in e.zlist("bz", p) if e.s.cards[c].defn == host_defn
                and e.s.cards[c].top_of < 0)
    unders = []
    for ud in under_defns:
        u = next(c for c in e.zlist("bz", p) if e.s.cards[c].defn == ud
                 and e.s.cards[c].top_of < 0 and c != host)
        e.s.cards[u].top_of = host
        unders.append(u)
    e.s.cards[host].under = unders
    e.s.cards[host].stack_bases = list(unders)
    return host, unders


def _drive(e, done, cast=None, target_defn=None, pick_defn=None, yes=True,
           steps=400):
    """done(e) が真になるまで汎用に答える。cast は相手（p1）の main で
    1回だけ唱える。yes は yes_no への既定回答（形Aの下置き辞退など）。"""
    st = {"cast": False}
    for _ in range(steps):
        if done(e):
            return st
        d = e.advance()
        assert d is not None, "game ended before done"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and cast and not st["cast"] \
                and d.get("player") == 1 and f"play:{cast}" in keys:
            e.answer([keys.index(f"play:{cast}")])
            st["cast"] = True
        elif kind == "yes_no":
            want = "yes" if yes else "no"
            e.answer([keys.index(want)] if want in keys
                     else list(range(d.get("min", 0))))
        elif kind == "choose_cards":
            idx = None
            for want in (pick_defn, target_defn):
                if not want:
                    continue
                for o in d["options"]:
                    if e.s.cards[o["cid"]].defn == want:
                        idx = keys.index(o["key"])
                        break
                if idx is not None:
                    break
            e.answer([idx] if idx is not None else list(range(d.get("min", 0))))
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert done(e), "drive budget exhausted"


def _settle(e, steps=12):
    for _ in range(steps):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


P1_DESTROY = {"hand": ["T056"], "mana": ["T008"] * 3}


def test_form_a_registered_033_returns_was_under(rules):
    """dm25rp2-033（形A）: 破壊された時、下にあったカードをすべて
    墓地から手札に戻す。墓地にあっただけのカードは戻らない。
    ターン終了の下置きは辞退する（yes=False）。"""
    e = setup(rules, {"bz": ["dm25rp2-033", "T001"], "graveyard": ["T003"]},
              dict(P1_DESTROY))
    host, unders = _wire(e, "dm25rp2-033", ["T001"])
    base = unders[0]
    _drive(e, lambda e: e.s.cards[base].zone == "hand",
           cast="T056", target_defn="dm25rp2-033", yes=False)
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"
    assert e.s.cards[base].zone == "hand"
    t003 = next(c for c in e.zlist("graveyard", 0)
                if e.s.cards[c].defn == "T003")
    assert e.s.cards[t003].zone == "graveyard"


def test_form_b_registered_004_summons_only_was_under_funky(rules):
    """dmex12-004（形B）: 破壊された時、下にあったファンキー・ナイトメア
    だけが墓地から出る。下でない同種族・下の他種族は出ない。"""
    e = setup(rules, {"bz": ["dmex12-004", "T886", "T001"],
                      "graveyard": ["T886"]},
              dict(P1_DESTROY))
    host, unders = _wire(e, "dmex12-004", ["T886", "T001"])
    funky_under, plain_under = unders
    funky_gy = next(c for c in e.zlist("graveyard", 0)
                    if e.s.cards[c].defn == "T886")
    _drive(e, lambda e: e.s.cards[funky_under].zone == "bz"
           and e.s.cards[funky_under].top_of < 0,
           cast="T056", target_defn="dmex12-004")
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"
    assert e.s.cards[plain_under].zone == "graveyard"
    assert e.s.cards[funky_gy].zone == "graveyard"


def test_form_c_registered_037_may_summon_one(rules):
    """dmex12-037（形C）: 破壊された時、下にあったカードのうち1枚を
    墓地から出してもよい。選ばなかった方は墓地に残る。"""
    e = setup(rules, {"bz": ["dmex12-037", "T001", "T002"]},
              dict(P1_DESTROY), filler="T007")
    host, unders = _wire(e, "dmex12-037", ["T001", "T002"])
    picked = next(u for u in unders if e.s.cards[u].defn == "T002")
    other = next(u for u in unders if e.s.cards[u].defn == "T001")
    _drive(e, lambda e: e.s.cards[picked].zone == "bz"
           and e.s.cards[picked].top_of < 0,
           cast="T056", target_defn="dmex12-037", pick_defn="T002", yes=True)
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"
    assert e.s.cards[other].zone == "graveyard"


def test_form_d_registered_012_leaves_was_under_to_hand(rules):
    """dm24bd5-012（形D）: 離れた時（ここでは破壊）、下にあったカードを
    すべて手札に加える。本体は墓地へ。"""
    e = setup(rules, {"bz": ["dm24bd5-012", "T001", "T002"]},
              dict(P1_DESTROY), filler="T007")
    host, unders = _wire(e, "dm24bd5-012", ["T001", "T002"])
    _drive(e, lambda e: all(e.s.cards[u].zone == "hand" for u in unders),
           cast="T056", target_defn="dm24bd5-012")
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"
