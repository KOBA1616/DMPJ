"""語彙パイロット第309弾の対象カード検証（ラウンド344で登録済み）。

dmrp21-tr2 天地命動 バラギアラ / 輪廻暴冥 はギャップ名
`rinne_infinity` の純粋1件だった。第267弾で実装された輪廻∞の
機構（面項目 rinne ＋ cast via: rinne 誘発イディオム）の
対象はギャップ名 `rinne` の3件で、本件は輪廻暴冥の印刷
としてギャップ名だけが違ったため残っていた。第309弾で
全条項が第267弾の確立形で書けることを固定し（新規語彙・
エンジン変更なし。実挙動は第309弾本体のプロト T956 で固定）、
ラウンド344で登録した。本ファイルは登録形の固定に書き換えた
（実挙動は test_vocab_round344_cards.py が登録カード自身で固定）。

登録形:
- クリーチャー面（自然コスト9・パワー17000・
  マスター・ハザード/グランセクト）: rinne: true ＋
  CIP {event: move, to: bz, subject: self,
  reason: summon} → untap {zone: mana, owner: you,
  count: all} ＋ {event: cast, via: rinne,
  subject: self} → repeat {times: {count: {zone: bz,
  owner: you, filter: {name_has: 天地命動 バラギアラ}}}}
  [move {from_top: 1} → mana] ＋ triple_breaker
  （登録済み dm26rp3-s011 と同型）。
- 呪文面（輪廻暴冥、闇コスト6、S・トリガー）:
  choose {zone: bz, owner: opp, count: 1} as x →
  modify {ref: x, power: -4000, duration: end_of_turn} ＋
  move {zone: graveyard, owner: you, filter:
  {types: [creature], cost_le: 5}, count: 1} → bz,
  reason: put。

登録時の注意（実施済み）:
- partial の faces はプレースホルダ（名前 x / y・
  火コスト1）で実データではなかったため、提出形は公式データ
  （by_product/rp21）から構築した（本ファイルの FORM が正本）。
  text も reject 行はクリーチャー面分しか無かったので、
  公式の両面テキストから復元した。
- alias は dmrp08-mh03（reject 行は無い）。identity で
  canon_id が対象自身・mh03 の canon も対象であることを
  照合し、source.aliases への記録とした。mh03 の公式テキストは
  チャージ条件が「バトルゾーンにある自分の《…》」と
  明記する版だが、数え方は bz カウントで同一。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
TABLES = load_tables()

TARGET = "dmrp21-tr2"
ALIAS = "dmrp08-mh03"

FACE0_TEXT = ("このクリーチャーが召喚によって出た時、自分のマナゾーンにあるカードをすべてアンタップする。\n"
              "輪廻∞：このカードの呪文側を、バトルゾーンに置いたまま唱えてもよい。"
              "そうした時、自分の《天地命動 バラギアラ》１体につき、自分の山札の上から１枚をマナゾーンに置く。"
              "（その呪文のコストは支払う）\n"
              "T・ブレイカー")
FACE1_TEXT = ("S・トリガー\n"
              "相手のクリーチャーを１体選ぶ。このターン、そのクリーチャーのパワーを－4000する。\n"
              "コスト５以下のクリーチャーを１体、自分の墓地から出す。")

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self",
                "reason": "summon"},
       "effect": [{"op": "untap",
                   "select": {"zone": "mana", "owner": "you",
                              "count": "all"}}]}

CHARGE = {"kind": "trigger",
          "when": {"event": "cast", "via": "rinne", "subject": "self"},
          "effect": [{"op": "repeat",
                      "times": {"count": {"zone": "bz", "owner": "you",
                                          "filter": {"name_has": "天地命動 バラギアラ"}}},
                      "body": [{"op": "move",
                                "select": {"zone": "deck", "owner": "you",
                                           "from_top": 1},
                                "to": "mana", "reason": "put"}]}]}

BOUMEI = [{"op": "choose",
           "select": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"]}, "count": 1},
           "as": "x"},
          {"op": "modify", "select": {"ref": "x"},
           "mod": {"power": -4000}, "duration": "end_of_turn"},
          {"op": "move",
           "select": {"zone": "graveyard", "owner": "you",
                      "filter": {"types": ["creature"], "cost_le": 5},
                      "count": 1},
           "to": "bz", "reason": "put"}]

FORM = {"id": TARGET,
        "name": "天地命動 バラギアラ / 輪廻暴冥",
        "mana": 1,
        "faces": [
            {"name": "天地命動 バラギアラ",
             "types": ["creature"], "civs": ["nature"],
             "cost": 9, "power": 17000,
             "races": ["マスター・ハザード", "グランセクト"],
             "keywords": ["triple_breaker"],
             "rinne": True,
             "abilities": [CIP, CHARGE],
             "text": FACE0_TEXT},
            {"name": "輪廻暴冥",
             "types": ["spell"], "civs": ["darkness"],
             "cost": 6,
             "keywords": ["s_trigger"],
             "spell": BOUMEI,
             "text": FACE1_TEXT}],
        "text": (FACE0_TEXT.replace("\n", " ") + " ／ "
                 + FACE1_TEXT.replace("\n", " "))}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_target_registered():
    rows = _rows()
    assert TARGET not in rows  # 登録により reject 行は外れた
    assert ALIAS not in rows   # alias に reject 行は元々無い
    # 登録形: converted の id にあり、alias は source.aliases に記録
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10248 and len(rows) == 2073
    assert not (ids & set(rows))
    c = next(c for c in conv if c["id"] == TARGET)
    assert (c.get("source") or {}).get("aliases") == [ALIAS]
    assert not (c.get("source") or {}).get("unsupported")
    assert ALIAS not in ids  # 独立エントリではない
    for k in ("name", "mana", "faces", "text"):
        assert c.get(k) == FORM[k], k
    # rinne_infinity は解消。rinne も解消済みのまま
    assert not {rid for rid, r in rows.items()
                if "rinne_infinity" in (r.get("gaps") or [])}
    assert not {rid for rid, r in rows.items()
                if "rinne" in (r.get("gaps") or [])}


def test_established_form_parses():
    d = parse_card(FORM, TABLES)
    f0, f1 = d.faces
    assert f0.rinne is True
    assert f0.types == ["creature"] and f0.civs == ["nature"]
    assert f0.cost == 9 and f0.power == 17000
    assert f0.races == ["マスター・ハザード", "グランセクト"]
    assert "triple_breaker" in f0.keywords
    trigs = [ab for ab in f0.abilities if ab["kind"] == "trigger"]
    assert trigs == [CIP, CHARGE]
    assert f1.types == ["spell"] and f1.civs == ["darkness"]
    assert f1.cost == 6
    assert "s_trigger" in f1.keywords
    assert [o["op"] for o in f1.spell] == ["choose", "modify", "move"]
    assert f1.spell[1]["mod"] == {"power": -4000}
    assert f1.spell[2]["select"]["filter"] == {"types": ["creature"],
                                               "cost_le": 5}
    assert f1.spell[2]["to"] == "bz" and f1.spell[2]["reason"] == "put"
