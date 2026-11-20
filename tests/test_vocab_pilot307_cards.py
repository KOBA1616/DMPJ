"""語彙パイロット第307弾の対象カード検証（ラウンド342で登録済み）。

exlife_shield_left_any は dm26ex2-mc009 不敬合成王
ロマティックダム・アルキング 1件のみで、ラウンド342で
登録された。第307弾で when.subject の exlife_of に "any" を
追加し（移動記録の LKI が保持する移動前の紐付けの有無だけを
見る）、「自分の『EXライフ』シールド（どのクリーチャーの
ものでも）が離れた時」が書けるようにした。ラウンド328で
一旦提出・登録されたが subject 形が無く登録を取り消して
差し戻された条項が、これで解けた。残りの条項はすべて
既存語彙で partial に完成していた:

- 進化GV・Ω = evolve_from の3ゾーン指定（墓地/マナ/バトルゾーン、
  第293弾で zone が効くようになった形）
- エクストラEXライフ = キーワード extra_ex_life、ワールド・
  ブレイカー = キーワード world_breaker
- シールドゾーンのディスペクターすべてに G・ストライク =
  static {affects: {zone: shield, owner: you, filter:
  {race_has: ディスペクター}}, mod: {grant: [g_strike]}}

実挙動は第307弾本体（プロト T945）とラウンド342 cards
（登録カード自身）で固定済み。ここでは登録形が第307弾の
確立形（partial ＋ 誘発）と完全一致し、対象行が rejects
から解消したことを固定する。

正本判定（ラウンド342で identity を実データ照合）:
- canon_id は dm26ex2-mc009 自身＝独立正本。alias 3件
  （dm22ex2-8a / dm22ex2-8b / dm22ex2-s15）の canon_id は
  いずれも dm26ex2-mc009 で aliases_for とも一致する。
  alias は登録カードの source.aliases への記録のみで、
  独立エントリ・reject 行はいずれも無い。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活
するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
import _conv_cache  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
TABLES = load_tables()

TARGET = "dm26ex2-mc009"
ALIASES = ["dm22ex2-8a", "dm22ex2-8b", "dm22ex2-s15"]

STATIC = {"kind": "static",
          "affects": {"zone": "shield", "owner": "you",
                      "filter": {"race_has": "ディスペクター"}},
          "mod": {"grant": ["g_strike"]}}

TRIGGER = {"kind": "trigger",
           "when": {"event": "move", "from": "shield",
                    "subject": {"owner": "you", "exlife_of": "any"}},
           "effect": [
               {"op": "move",
                "select": {"under_of": "self", "count": 1},
                "to": "graveyard", "reason": "put", "as": "buried"},
               {"op": "if",
                "cond": {"exists": {"ref": "buried",
                                    "filter": {"types": ["creature"],
                                               "not_types": ["evolution"]}}},
                "then": [{"op": "play_free",
                          "select": {"ref": "buried"}}]},
           ]}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_target_registered_in_pilot307_form():
    rows = _rows()
    assert TARGET not in rows            # rejects から外れた
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None                 # converted に登録済み
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == ALIASES
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    assert c["abilities"] == [STATIC, TRIGGER]
    d = parse_card(c, TABLES)
    assert d.types == ["creature", "evolution"]
    assert d.keywords == ["extra_ex_life", "world_breaker"]
    assert [z.get("zone") for z in d.evolve_from] == \
        ["graveyard", "mana", "bz"]
    trigs = [a for a in d.abilities if a.get("kind") == "trigger"]
    assert trigs == [TRIGGER]
    statics = [a for a in d.abilities if a.get("kind") == "static"]
    # キーワード world_breaker の展開分＋G・ストライク付与の2件
    assert len(statics) == 2
    assert STATIC in statics
    # exlife_shield_left_any は解消
    holders = {rid for rid, r in rows.items()
               if "exlife_shield_left_any" in (r.get("gaps") or [])}
    assert holders == set(), holders


def test_aliases_have_no_independent_entries():
    rows = _rows()
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {x["id"] for x in conv}
    for a in ALIASES:
        assert a not in ids              # 独立エントリは無い
        assert a not in rows             # reject 行も無い
