"""語彙パイロット第373弾の対象カード検証（登録形）。

対象は pure な deck_bottom_to_hand の全1件:
- dmrp04s-011 ラジコンBOY
ラウンド408で登録済み。登録形は提出形と完全一致:
partial の骨格〔ゼロ / コスト6 / パワー3000 / 種族
ジョーカーズ、keywords [super_s_trigger]、xB 誘発
〔sst: true の出た時誘発、chooser: opp で相手自身に
3体選ばせ、手札・マナ・山札下へ1体ずつ〕1件〕の
abilities の**先頭**に第373弾の確立形 CIP 誘発
〔trigger {event: move, to: bz, subject: self} →
move {select: {zone: deck, owner: you,
from_bottom: 1}, to: hand, reason: draw}
（第287弾形A、登録先例 dmr06-002 と同形）〕を足し、
unsupported を外したもの。abilities は公式テキストの
条項順に [CIP, xB] の2件ちょうど。partial の text は
行の公式テキスト全文と一致するため補完なし。単面
カードで未検証の面は無い。alias は無い。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmrp04s-011"
GAP = "deck_bottom_to_hand"

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [{"op": "move",
                   "select": {"zone": "deck", "owner": "you", "from_bottom": 1},
                   "to": "hand", "reason": "draw"}]}
XB = {"kind": "trigger", "sst": True,
      "when": {"event": "move", "to": "bz", "subject": "self"},
      "effect": [
          {"op": "choose",
           "select": {"zone": "bz", "owner": "opp", "chooser": "opp",
                      "filter": {"types": ["creature"]}, "count": 3},
           "as": "trio"},
          {"op": "choose",
           "select": {"ref": "trio", "chooser": "opp", "count": 1},
           "as": "tohand"},
          {"op": "move", "select": {"ref": "tohand"},
           "to": "hand", "reason": "return"},
          {"op": "choose",
           "select": {"ref": "trio", "chooser": "opp", "count": 1},
           "as": "tomana"},
          {"op": "mana_put", "select": {"ref": "tomana"}},
          {"op": "move", "select": {"ref": "trio", "count": "all"},
           "to": "deck", "reason": "put", "position": "bottom"}]}
FORM = [CIP, XB]
FULL_TEXT = ("スーパー・S・トリガー（このクリーチャーを自分のシールドゾーンから"
             "手札に加える時、コストを支払わずにすぐ召喚してもよい。その時自分の"
             "シールドが１つもなければ、このクリーチャーにxB能力を与える）"
             "このクリーチャーがバトルゾーンに出た時、自分の山札の一番下の"
             "カードを手札に加える。xBこのクリーチャーがバトルゾーンに出た時、"
             "相手は自身のクリーチャーを３体選び、そのうちの１体を自身の手札に"
             "加え、１体をマナゾーンに置き、１体を山札の一番下に置く。")


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    assert TARGET not in rows            # 登録により対象行は解消
    fam = [i for i, x in rows.items() if GAP in (x.get("gaps") or [])]
    assert fam == []                     # ファミリーはこの1件だけだった
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["keywords"] == ["super_s_trigger"]
    assert c["types"] == ["creature"] and c["civs"] == ["zero"]
    assert c["cost"] == 6 and c["power"] == 3000
    assert c["races"] == ["ジョーカーズ"]
    assert c["mana"] == 1
    assert c["text"] == FULL_TEXT                    # 公式テキスト全文
    # 登録形は提出形と完全一致: abilities は [CIP, xB] の2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")                      # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    trigs = [a for a in d.abilities if a["kind"] == "trigger"]
    # parse は mana_put を move {to: mana, reason: put} に正規化する
    # （defs の op 正規化。それ以外は登録形のまま通る）
    xb_parsed = json.loads(json.dumps(XB))
    xb_parsed["effect"][4] = {"op": "move", "select": {"ref": "tomana"},
                              "to": "mana", "reason": "put"}
    assert trigs == [CIP, xb_parsed]
    # プロト T1121 と abilities が完全一致
    proto = proto_card("T1121")
    assert proto["abilities"] == FORM
    assert proto["keywords"] == c["keywords"]
