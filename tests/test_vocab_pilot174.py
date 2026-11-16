"""語彙パイロット第174弾: dream_creature（ドリーム・クリーチャーの型印）。

ドリーム・クリーチャーはカードの「種類」（タイプ）であって、タイプ自体に
固有のゲームルールは無い（総合ルールにドリーム・クリーチャーだけの条文は
ない。D2フィールドの型印と同型の追加。第151弾の流儀）。

- defs の CARD_TYPES に `dream_creature` を追加。types には
  `["creature", "dream_creature"]`、進化なら
  `["creature", "evolution", "dream_creature"]`、G-NEO進化なら
  `["creature", "dream_creature"]` に `neo: true` と書く（NEOは types に
  evolution を含めない。dm25ex3-011 の実例どおり。types に evolution が
  あると通常召喚の選択肢が出ず、進化元なしでは main すら出ない）。
  `{types: [dream_creature]}`（selectors は汎用の集合照合のため変更なし）。
- schema は `python -m dmsim.schema` の再生成で追随（差分は型の列挙×2）。
- proto T378（ドリーム・クリーチャー。CIPドロー）/ T379（進化ドリーム。
  火のクリーチャーの上に置く。CIPドロー）/ T380（ドリーム言及。自分の
  ドリーム・クリーチャー全てに+1000、ドリームがあればCIPドロー）/
  T381（G-NEOドリーム。neo: true。火のアーマード・ドラゴンの上に置く）。
"""
import json
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent
IDS = ("T378", "T379", "T380", "T381")


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _settle(e, done, drive=None, max_steps=200):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive and drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def _play_drive(want_key, evo_pick=None):
    def drive(e, d, keys):
        if d["kind"] == "choose_evo_source":
            if evo_pick is None:
                e.answer([0])
            else:
                e.answer([next(i for i, k in enumerate(keys) if k.startswith(evo_pick))])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == want_key]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    return drive


def _in_bz(e, cid, player=0):
    return any(e.s.cards[c].defn == cid for c in e.bz_tops(player))


def _top(e, cid, player=0):
    return next(c for c in e.bz_tops(player) if e.s.cards[c].defn == cid)


def test_proto_parse():
    """T378〜T381 が parse でき、型印が types に載る。"""
    parsed = {cid: parse_card(_proto_card(cid), TABLES) for cid in IDS}
    assert parsed["T378"].types == ["creature", "dream_creature"]
    assert parsed["T379"].types == ["creature", "evolution", "dream_creature"]
    assert parsed["T380"].types == ["creature"]
    assert parsed["T381"].types == ["creature", "dream_creature"]
    assert parsed["T381"].neo is True
    assert parsed["T379"].evolve_from == {"civs": ["fire"]}
    assert parsed["T381"].evolve_from == {"races": ["アーマード・ドラゴン"]}


def test_invalid_forms():
    base = {"id": "test-dream-bad", "name": "試験ドリーム不良", "types": ["creature", "evolution", "dream_creature"],
            "civs": ["fire"], "cost": 5, "power": 3000, "mana": 1,
            "source": {"official": "test-dream-bad", "review": "pending"}}
    with pytest.raises(DefError) as e:
        parse_card(base, TABLES)
    assert "evolve_from" in str(e.value)
    with pytest.raises(DefError) as e:
        parse_card({**base, "types": ["creature", "dream_creature2"],
                    "evolve_from": {"civs": ["fire"]}}, TABLES)
    assert "unknown type" in str(e.value)


def test_schema_has_dream_creature():
    s = json.loads((ROOT / "data" / "schema" / "card.schema.json").read_text(encoding="utf-8"))
    assert "dream_creature" in s["properties"]["types"]["items"]["enum"]
    assert "dream_creature" in s["$defs"]["face"]["properties"]["types"]["items"]["enum"]


def test_dream_cip_draw(rules):
    """T378: ドリーム・クリーチャーを召喚すると CIP で1ドローする。"""
    e = setup(rules, {"hand": ["T378"], "mana": ["T005"] * 3}, {})
    assert _settle(e, lambda: _in_bz(e, "T378"), _play_drive("play:T378"))
    assert _settle(e, lambda: len(e.zlist("hand", 0)) == 1, None, 60)
    assert e.chars_ro(_top(e, "T378"))["power"] == 3000


def test_evolution_dream(rules):
    """T379: 火のクリーチャーの上に進化ドリームを重ねると CIP ドロー。"""
    e = setup(rules, {"bz": ["T005"], "hand": ["T379"], "mana": ["T005"] * 5}, {})
    assert _settle(e, lambda: _in_bz(e, "T379"), _play_drive("play:T379"))
    top = _top(e, "T379")
    assert e.s.cards[top].under and e.s.cards[e.s.cards[top].under[0]].defn == "T005"
    assert _settle(e, lambda: len(e.zlist("hand", 0)) == 1, None, 60)


def test_dream_reference_static_and_exists(rules):
    """T380: ドリームだけ+1000。ドリームがいれば CIP ドロー、いなければ引かない。"""
    e = setup(rules, {"bz": ["T378", "T005"], "hand": ["T380"], "mana": ["T005"] * 4}, {})
    assert _settle(e, lambda: _in_bz(e, "T380"), _play_drive("play:T380"))
    assert e.chars_ro(_top(e, "T378"))["power"] == 4000, "ドリームは+1000"
    assert e.chars_ro(_top(e, "T005"))["power"] == 3000, "非ドリームは変わらない"
    assert e.chars_ro(_top(e, "T380"))["power"] == 4000, "T380 自身はドリームではない"
    assert _settle(e, lambda: len(e.zlist("hand", 0)) == 1, None, 60), "ドリームがあるので CIP ドロー"

    e = setup(rules, {"bz": ["T005"], "hand": ["T380"], "mana": ["T005"] * 4}, {})
    assert _settle(e, lambda: _in_bz(e, "T380"), _play_drive("play:T380"))
    assert _settle(e, lambda: len(e.zlist("hand", 0)) == 0, None, 60), "ドリームが無いので引かない"
    assert e.chars_ro(_top(e, "T005"))["power"] == 3000


def test_neo_dream_normal_summon(rules):
    """T381: G-NEOドリームは進化元なしで通常召喚できる（下にカードは無い）。"""
    e = setup(rules, {"hand": ["T381"], "mana": ["T005"] * 6}, {})
    assert _settle(e, lambda: _in_bz(e, "T381"), _play_drive("play:T381"))
    top = _top(e, "T381")
    assert not e.s.cards[top].under
    assert e.chars_ro(top)["power"] == 8000


def test_neo_dream_evolution(rules):
    """T381: アーマード・ドラゴンの上に G-NEO進化で重ねられる。"""
    e = setup(rules, {"bz": ["T369"], "hand": ["T381"], "mana": ["T005"] * 6}, {})
    assert _settle(e, lambda: _in_bz(e, "T381"),
                   _play_drive("play:T381:neo", evo_pick="bz:T369"))
    top = _top(e, "T381")
    assert e.s.cards[top].under and e.s.cards[e.s.cards[top].under[0]].defn == "T369"
