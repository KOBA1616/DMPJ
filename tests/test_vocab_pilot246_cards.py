"""第246弾の登録形: dmc45-008（cause.defn 置換）と dm23ex1-020（cause.name_has 誘発）。ラウンド280。"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build


def _drive(e, stop, plays, cap=300):
    for _ in range(cap):
        if stop():
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        play = next((i for i, k in enumerate(keys) if k in plays), None)
        atk = next((i for i, k in enumerate(keys) if k.startswith("attack:") and k.endswith(":player")), None)
        if d["kind"] == "main" and play is not None:
            e.answer([play])
        elif atk is not None:
            e.answer([atk])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return stop()


def test_bushido_pair_registered():
    rules = load_rules()
    assert "dmc45-008" in rules.cards and "dmc45-009" in rules.cards
    # ホストは登録済みのサムライ（T655 は proto なので登録形では実カードを使う）
    e = build(rules, {"p0": {"bz": ["T655", "dmc45-008", "dmc45-009"]},
                      "p1": {"bz": ["T667"]}, "filler": "T001", "seed": 1, "deck_size": 20})
    host = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T655")
    for g in ("dmc45-008", "dmc45-009"):
        gc = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == g)
        e.s.cards[gc].crossed = e.s.ref(host)
    tgt = next(c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T667")
    ok = _drive(e, lambda: tgt in e.zlist("graveyard", 1) and host in e.zlist("bz", 0), plays=set())
    assert ok, "ブシドー・スピリットの破壊が置換されなかった"
    assert host in e.zlist("bz", 0)


def test_yamato_registered():
    rules = load_rules()
    assert "dm23ex1-020" in rules.cards
    # 名前に《武者》とある登録済みカードを1種探す（破壊効果を持つもの）
    import json
    musha = None
    for cid, c in rules.cards.items():
        if "武者" in c.name and cid != "dm23ex1-020" and "spell" in c.types:
            musha = cid
            break
    assert musha, "《武者》名の呪文が converted に無い"
    e = build(rules, {"p0": {"bz": ["dm23ex1-020"], "hand": [musha], "mana": ["T060"] * 9},
                      "p1": {"bz": ["T002", "T002"]}, "filler": "T001", "seed": 1, "deck_size": 20})
    victims = [c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T002"]
    ok = _drive(e, lambda: all(v in e.zlist("graveyard", 1) for v in victims),
                plays={f"play:{musha}"})
    assert ok, "武者効果の破壊→大和ドラゴンの誘発で2体目が落ちなかった"
