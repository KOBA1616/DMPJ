"""語彙パイロット第365弾の対象カード（登録形の検証）。

対象は pure な entered_this_turn_cannot_attack_opponents
の全1件で、ラウンド400で登録:
- dm22ex1-cho37 月砂 フロッガ-1
（partial は既存能力としてササゲール1の static
{affects: self, mod: {sac_reduce: 1}} を持ち、
未解決は unsupported の本 gap 1件だけだった。
提出形は partial の既存能力に第365弾の確立形
〔static {affects: {zone: bz, owner: opp, filter:
{types: [creature], not_types: [evolution],
entered_this_turn: true}}, mod: {deny:
[attack_player, attack_creature]}}〕1能力を足し、
unsupported を外したもの。partial に欠けた要素は
無い＝補完なし。単面カードで未検証の面は無い。
登録形は提出形と完全一致）

正本判定（ラウンド400で実施）: 対象 id dm22ex1-cho37
と alias dmrp19-041 の両方を real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml と照合し、いずれにも
登録なし（proto.yaml のヒットは T1098 の notes 内
参照のみ）。alias dmrp19-041 は partial の
source.aliases にあるだけで rejects に独自行は
無く、alias 畳み込み0件（登録形の source.aliases
に記録のみ）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
TARGET = "dm22ex1-cho37"
ALIAS = "dmrp19-041"

SAC = {"kind": "static", "affects": "self", "mod": {"sac_reduce": 1}}
STATIC = {"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"],
                                 "not_types": ["evolution"],
                                 "entered_this_turn": True}},
          "mod": {"deny": ["attack_player", "attack_creature"]}}
FORM = [SAC, STATIC]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not c.get("aliases")          # top-level の畳み込みなし
    # alias は source.aliases に記録のみ（独自行なし）
    assert (c.get("source") or {}).get("aliases") == [ALIAS]
    # 登録形は提出形と完全一致: 2能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["name"] == "月砂 フロッガ-1"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 2 and c["power"] == 2000
    assert c["races"] == ["デューンゲッコー", "ディスタス"]
    assert not c.get("keywords")
    d = parse_card(c, TABLES)
    assert SAC in d.abilities
    assert STATIC in d.abilities


def test_proto_form_matches():
    assert proto_card("T1098")["abilities"] == FORM
