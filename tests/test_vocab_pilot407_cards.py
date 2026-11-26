"""語彙パイロット第407弾の対象カード検証（登録形）。

対象は summoning_attack_rule（pure 2件）のうち形が
確定する1件:
- dmex02-011 超絶特Q ダンガンテイオー
ラウンド442で登録済み。登録形は提出形と完全一致
（差分は validate が identity.aliases_for から
自動付与した source.aliases のみ）: partial の
骨格（クリーチャー / ゼロ / コスト8 / パワー8000 /
種族 ジョーカーズ、mana 1、keywords
[double_breaker]、abilities 無し）に第407弾の
確立形 static 2件〔付与: affects {zone: bz,
owner: you, filter: {types: [creature],
entered_this_turn: true}}, mod: {player_rush:
true}／deny: affects {zone: bz, owner: opp,
filter: {types: [creature], entered_this_turn:
true}}, mod: {deny: [attack_player]}〕を足し、
unsupported を外したもの。abilities はこの2件
ちょうど、keywords は [double_breaker] のまま。
**補完なし**（partial の text は公式全文と一致）。

alias は promoy16-008 の1件で、identity 実測で
canon_id は対象・alias とも dmex02-011。
promoy16-008 には gap entered_turn_attack での
独自行があったが、同カードの別版で骨格と
イラストレーターが一致し、テキストは版差の
文面差のみで意味が同一であることを実測確認した
ため、ラウンド442で alias 畳み込みとして処理
した（reopen〔entered_turn_attack〕を併用して
行を解消。別カード dmbd11-d05 の同 gap 行は
差し戻して残留）。

ファミリーの残り1件 dmex07-s01 ガンバトラーG７
（alias dmsd04-001、独自行なし）は partial が
素で他条項が未構築のため対象外で、行は残る
（ファミリーは解消しない）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['double_breaker'], 条項テキスト,
[]) を返し定型所有は空（第407弾で実測）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore, identity  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402
from tests.test_vocab_pilot407 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmex02-011"
GAP = "summoning_attack_rule"
NAME = "超絶特Q ダンガンテイオー"
ALIASES = ["promoy16-008"]
OTHER = "dmex07-s01"

# 提出形: partial の骨格＋確立形 static 2件（補完なし）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["zero"],
    "cost": 8,
    "power": 8000,
    "races": ["ジョーカーズ"],
    "mana": 1,
    "keywords": ["double_breaker"],
    "text": FULL_TEXT,
    "abilities": FORM,
}


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def test_target_registered_and_family_state():
    rows = _reject_rows()
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == [OTHER]                # dmex07-s01 だけ残る
    assert rows[OTHER].get("gaps") == [GAP]
    assert rows[OTHER].get("reason") == "vocab"
    # alias の独自行は畳み込みで解消（stale 重複行にしない）
    assert ALIASES[0] not in rows
    assert identity.canon_id(ALIASES[0]) == TARGET
    assert identity.canon_id(TARGET) == TARGET
    assert identity.aliases_for(NAME, TARGET) == ALIASES
    assert "dmsd04-001" not in rows      # dmex07-s01 の alias に独自行は無い
    # entered_turn_attack は別カード dmbd11-d05 だけが残る
    et = sorted(i for i, x in rows.items()
                if "entered_turn_attack" in (x.get("gaps") or []))
    assert et == ["dmbd11-d05"]
    assert find(CONVERTED, TARGET) is not None
    for a in ALIASES:
        assert find(CONVERTED, a) is None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["zero"]
    assert c["cost"] == 8 and c["power"] == 8000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["text"] == FULL_TEXT        # 公式全文のまま（補完なし）
    # 登録形は提出形と完全一致: abilities は確立形 static 2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["keywords"] == ["double_breaker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    own = [a for a in d.abilities if not a.get("keyword")]
    assert own == FORM                   # double_breaker 由来 static を除く
    assert len(own) == 2
    assert d.keywords == ["double_breaker"]
    # プロト T1175 と abilities・text・骨格が完全一致
    proto = proto_card("T1175")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == SUBMIT[k]
    assert proto["keywords"] == SUBMIT["keywords"]
