"""再変換ラウンド372（第337弾 evolution_base_from_graveyard）の記録テスト。

- 新規登録3件: dm25rp1-018 至高の邪騎 スベルニル /
  dm25rp2-sp3 魔光神官ルドルフ・アルカディア / dm25ex1-069
  神滅翔天ポッポ・ジュヴィラ。いずれも登録形は確立形と
  完全一致。
- alias 畳み込み0件（submit 時に 018 へ aliases 2件・sp3 へ
  5件・069 へ 3件が自動記録されたが rejects 行ではない）・
  差し戻し0件（submit 時の警告なし）。
- converted 10,294→10,297 / rejects 2,020→2,017、
  canonical 重なり0・漏れ0。evolution_base_from_graveyard
  の行は残っていない（ファミリー解消）。

実挙動は登録カード自身で固定する（スベルニルが墓地の
NEOを上に重ねる。ジュヴィラは :gevo で墓地のクリーチャーの
上に重なって出る）。ドライバは scenario.build の薄い包みで、
tests.conftest は import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

from tests import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

MOVE_STACK = {"op": "move", "select": {"ref": "p", "count": "all"},
              "to": "bz", "reason": "put", "stack_evo": True,
              "evo_source": {"ref": "self"}}
FORM_018 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "may", "body": [
        {"op": "choose",
         "select": {"zone": "graveyard", "owner": "you",
                    "filter": {"types": ["creature"], "cost_le": 5,
                               "any_of": [{"neo": True},
                                          {"evolution": True}],
                               "evolves_from": "self"},
                    "count": 1},
         "as": "p"},
        MOVE_STACK]}],
}]
FORM_SP3 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        {"op": "may", "body": [
            {"op": "move",
             "select": {"zone": "deck", "owner": "you", "from_top": 4},
             "to": "graveyard", "reason": "put"}]},
        {"op": "may", "body": [
            {"op": "choose",
             "select": {"zone": "graveyard", "owner": "you",
                        "filter": {"types": ["creature"], "cost_le": 8,
                                   "evolves_from": "self"},
                        "count": 1},
             "as": "p"},
            MOVE_STACK]}],
}]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round372_disposition():
    rej = _reject_rows()
    assert len(rej) == 2017
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10297
    assert not (ids & set(rej))          # canonical 重なり0
    for t, form in (("dm25rp1-018", FORM_018), ("dm25rp2-sp3", FORM_SP3)):
        c = _conv_cache.find(CONVERTED, t)
        assert c is not None and c["abilities"] == form, t
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    c = _conv_cache.find(CONVERTED, "dm25ex1-069")
    assert c is not None and c.get("grave_evo") is True
    assert not (c.get("source") or {}).get("unsupported")
    left = {rid for rid, r in rej.items()
            if "evolution_base_from_graveyard" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defn_in_key(key, defns):
    for dn in defns:
        if f":{dn}:" in key or key.endswith(f":{dn}"):
            return dn
    return None


def _stacked_on(e, top_defn, base_defn, p=0):
    top = next(c for c in e.bz_tops(p) if e.s.cards[c].defn == top_defn)
    base = e.s.cards[top].under
    return base and e.s.cards[base[0]].defn == base_defn


def test_registered_suberuniru_stacks_from_graveyard(rules):
    e = _build(rules, {"hand": ["dm25rp1-018"],
                       "mana": ["T053", "T001", "T001", "T001"],
                       "graveyard": ["T057", "T087", "T017", "T001"]})
    played = False
    seen = None
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if played and seen is not None and d["kind"] == "attack" \
                and d.get("player") == 0:
            break
        if d["kind"] == "main" and d.get("player") == 0 and not played \
                and "play:dm25rp1-018" in keys:
            e.answer([keys.index("play:dm25rp1-018")])
            played = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge" and not played:
            e.answer([keys.index("pass")] if "pass" in keys else [0])
            continue
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
            continue
        if d["kind"] == "choose_cards" and seen is None:
            seen = {dn for k in keys
                    for dn in [_defn_in_key(k, ["T057", "T087", "T017",
                                                "T001"])]
                    if dn}
            idx = next(i for i, k in enumerate(keys)
                       if _defn_in_key(k, ["T057"]) == "T057")
            e.answer([idx])
            continue
        if d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert seen == {"T057", "T087"}, seen
    assert _stacked_on(e, "T057", "dm25rp1-018")


def test_registered_juvira_grave_evo(rules):
    e = _build(rules, {"hand": ["dm25ex1-069"],
                       "mana": ["T053", "T005", "T001", "T001"],
                       "graveyard": ["T001"]})
    played = False
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if played and e.bz_tops(0):
            break
        if d["kind"] == "main" and d.get("player") == 0 and not played:
            assert "play:dm25ex1-069" in keys
            assert "play:dm25ex1-069:gevo" in keys
            e.answer([keys.index("play:dm25ex1-069:gevo")])
            played = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge" and not played:
            e.answer([keys.index("pass")] if "pass" in keys else [0])
            continue
        if any(_defn_in_key(k, ["T001"]) for k in keys) \
                and d["kind"] not in ("main", "charge"):
            idx = next(i for i, k in enumerate(keys)
                       if _defn_in_key(k, ["T001"]) == "T001")
            e.answer([idx])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert _stacked_on(e, "dm25ex1-069", "T001")
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == []
