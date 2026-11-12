"""語彙パイロット第192弾のカード適用テスト（登録形）。

ラウンド228で choose_player_effect 対象10件のうち8件を新規登録、
1件を差し戻し、1件は既存の手書き変換と重なる stale 行の掃除。
- 登録8件: converted.yaml から読み、choose_player 節を含むことを確認。
  dm26sd1-p005 は ace: true＋第50弾の once マナ召喚静的も併せて解消。
  dm24bd2-007 の無償召喚誘発は when: {unpaid: true}＋ref: event.subject、
  dm24ex4-025 のマナ裏向きは flip_down、と既存語彙で書けた。
- dm24ex1-sp7 は差し戻し: 「その持ち主は選ばれたカードを好きな順序で
  山札の下に置く」の並び順を決めるのが持ち主で、move の order: choose は
  効果の使用者に聞くため表せない（新ギャップ owner_ordered_deck_put）。
  choose_player 形は partial に残した。
- dmrp07-009 は real_akashic.yaml に手書き変換済みだった（H.D.2. の
  プレイヤー選択は modal で表現）。rejects の重複行を掃除しただけ。
"""
import copy
import json
from pathlib import Path

import yaml

from dmsim import cardstore
from dmsim.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
AKASHIC = Path(__file__).parent.parent / "data" / "cards" / "real_akashic.yaml"

REGISTERED = ("dm24bd2-007", "dm24ex4-025", "dm24ex4-075", "dm25ex3-061",
              "dm25ex3-065", "dm25ex3-rp4004", "dmsd19-001", "dm26sd1-p005")


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


def _ops(card):
    out = []

    def walk(x):
        if isinstance(x, dict):
            if "op" in x:
                out.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(card.get("abilities") or [])
    walk(card.get("spell") or [])
    walk(card.get("faces") or [])
    return out


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        assert any(o["op"] == "choose_player" for o in _ops(card)), \
            f"{cid}: choose_player 節が無い"


def test_p005_ace_and_mana_summon():
    card = _converted("dm26sd1-p005")
    assert card["types"] == ["tamaseed"] and card.get("ace") is True
    statics = [a for a in card["abilities"] if a["kind"] == "static"]
    assert any(s["mod"]["allow"] == [{"action": "summon_from_mana", "once": True}]
               for s in statics)


def test_sp7_bounced_with_banked_form():
    r = _reject("dm24ex1-sp7")
    assert r["gaps"] == ["owner_ordered_deck_put"]
    assert any(o["op"] == "choose_player" for o in _ops(r["partial"])), \
        "解けた節（choose_player 形）が partial に残っていない"


def test_dmrp07_009_is_akashic_cleanup():
    with open(AKASHIC, encoding="utf-8") as f:
        aka = yaml.safe_load(f)
    assert any(c["id"] == "dmrp07-009" for c in aka["cards"])
    with open(REJECTS, encoding="utf-8") as f:
        assert "dmrp07-009" not in f.read()
