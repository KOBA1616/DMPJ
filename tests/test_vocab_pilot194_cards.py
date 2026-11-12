"""語彙パイロット第194弾のカード適用テスト（登録形）。

ラウンド230で must_attack_creature_if_able の6件のうち5件を新規登録、
1件を差し戻した。
- 登録5件: converted.yaml から読み、must_attack_creature 系の mod を
  含むことを確認。dmex14-017 は attack_untapped（allow attack_creature）も
  併せて解消。dmr23-022 は modal の第2モード。
- dmr10-016 は差し戻し: シールドゾーンに表向きで置かれている間だけ効く
  常在型は未対応（新ギャップ shield_zone_static）。
"""
import copy
import json
from pathlib import Path

from dmsim import cardstore
from dmsim.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dmrp18-087", "dmr14-054", "dmr23-022", "dmrp04s-093", "dmex14-017")


def _converted(cid):
    for c in cardstore.read(CONVERTED):
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] == cid:
            return r
    raise KeyError(cid)


def _mods(card):
    out = []

    def walk(x):
        if isinstance(x, dict):
            if "mod" in x:
                out.append(x["mod"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(card.get("abilities") or [])
    walk(card.get("spell") or [])
    return out


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        mods = _mods(card)
        assert any("must_attack_creature" in m or "must_be_attacked" in m
                   for m in mods), cid


def test_specific_forms():
    m = _mods(_converted("dmrp18-087"))[0]
    assert m["grant"] == ["must_attack"] and m["must_attack_creature"] is True
    spell = _converted("dmr23-022")["spell"]
    assert spell[0]["op"] == "modal" and len(spell[0]["modes"]) == 2
    mods = _mods(_converted("dmex14-017"))
    assert any(mm.get("allow") == [{"action": "attack_creature",
                                     "other": {"tapped": False}}]
               for mm in mods)


def test_dmr10_016_bounced():
    r = _reject("dmr10-016")
    assert r["gaps"] == ["shield_zone_static"]
    assert (r["partial"].get("keywords") or []) != []
