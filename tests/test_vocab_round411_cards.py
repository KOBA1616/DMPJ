"""再変換ラウンド411（第376弾 mana_all_civs）の記録テスト。

- 新規登録1件: dmex14-010 暴歌の妖精
  （登録形は提出形と完全一致: partial の骨格
  〔自然 / コスト3 / パワー3000 / 種族 スノーフェアリー・
  暴拳王国、mana 1、keywords・abilities ともに無し〕に
  第376弾の確立形2能力〔static {affects: {zone: mana,
  owner: you}, mod: {add_civs: [light, water, darkness,
  fire, nature]}}（第123弾・登録先例 dmex01-014 と同形）
  ＋ CIP 誘発 {event: move, to: bz, subject: self,
  if: {exists: {zone: bz, owner: you, filter:
  {types: [creature], multicolor: true}}} →
  move {select: {zone: deck, owner: you, from_top: 1},
  to: mana, reason: put}（第206弾レインボーナスの
  イディオム、登録先例 dmex14-083 と同形）〕を足し、
  unsupported を外したもの。abilities は2件ちょうど、
  keywords は無いまま。補完あり: partial の text は
  第1条項の断片だけのため、text には行の公式テキスト
  全文を入れた。第260弾の常在キー mana_all_civs は
  支払い計算専用で意味が違うため使っていない）。
- alias 畳み込み0件（alias 自体が無い）。正本判定:
  対象 id dmex14-010 を real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / proto.yaml /
  converted.yaml と照合し、いずれにも登録なし
  （proto.yaml のヒットは T1124 の notes 内参照のみ）。
  identity 実測で canon(dmex14-010) = dmex14-010
  （対象 id が正本）、aliases_for(暴歌の妖精,
  dmex14-010) = []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [mana_all_civs] のため reopen で
  外してから submit（reopen の出力は対象1件ちょうど）。
- converted 10,355→10,356 / rejects 1,957→1,956、
  canonical 重なり0・漏れ0。mana_all_civs は
  ファミリーがこの1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第376弾本体の薄い包み（対象 T1124 を登録カードに
差し替えたもの）で、tests.conftest は import しない
（第319弾以降の作法）。判別役は既存 proto を流用
（T030=光水の多色 / T001=自然の素 / T277=火・コスト2）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex14-010"
GAP = "mana_all_civs"
ALL_CIVS = ["light", "water", "darkness", "fire", "nature"]

STATIC = {"kind": "static", "affects": {"zone": "mana", "owner": "you"},
          "mod": {"add_civs": ALL_CIVS}}
CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "if": {"exists": {"zone": "bz", "owner": "you",
                         "filter": {"types": ["creature"],
                                    "multicolor": True}}},
       "effect": [{"op": "move",
                   "select": {"zone": "deck", "owner": "you",
                              "from_top": 1},
                   "to": "mana", "reason": "put"}]}
FORM = [STATIC, CIP]
FULL_TEXT = ("自分のマナゾーンにあるカードを、すべての文明のカードとして扱う。\n"
             "レインボーナス：このクリーチャーがバトルゾーンに出た時、"
             "バトルゾーンに自分の多色クリーチャーがあれば、"
             "自分の山札の上から１枚目をマナゾーンに置く。")


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


def test_round411_disposition():
    rej = _reject_rows()
    assert len(rej) == 1956
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10356
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0（aliases 欄）
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: 確立形2能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("keywords")         # keywords は無いまま
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完）
    assert c["name"] == "暴歌の妖精"
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 3 and c["power"] == 3000 and c["mana"] == 1
    assert c["races"] == ["スノーフェアリー", "暴拳王国"]
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第376弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _find(e, zone, player, defn):
    for i, c in enumerate(e.s.cards):
        if c.defn == defn and c.zone == zone and c.owner == player:
            return i
    raise AssertionError(f"{defn} not in {zone} of p{player}")


def test_registered_chars_mana_counts_as_all_civilizations(rules):
    """登録カード: 特性レベルで、登録カードがバトル
    ゾーンにあれば自分のマナゾーンの自然カードは
    すべての文明を持つ。"""
    e = _build(rules, {"bz": [TARGET], "mana": ["T001"]})
    ch = e.chars(_find(e, "mana", 0, "T001"))
    assert set(ch["civs"]) == set(ALL_CIVS)


def test_registered_payment_with_all_civs_mana(rules):
    """登録カード: 実挙動で、自然マナだけで火コスト
    （文明: 火）の支払いができる。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T277"],
                       "mana": ["T001", "T001"]})
    cid = _find(e, "hand", 0, "T277")
    assert e._mana_choices(cid, 0) != []


def _drive(e, on_decision, limit=600):
    for _ in range(limit):
        if e.s.result is not None:
            return "result"
        d = e.advance()
        if d is None:
            return "done"
        r = on_decision(e, d)
        if r == "stop":
            return "stopped"
        if r == "ok":
            continue
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("driver limit reached")


def _summon_target(rules, bz=()):
    """登録カードを手札から召喚し、解決後の観測点
    （次のチャージ決定）まで進める。戻り値:
    (engine, 召喚時点の山札リスト)。"""
    e = scenario.build(rules,
                       {"p0": {"hand": [TARGET], "mana": ["T001"] * 3,
                               "deck": ["T827", "T003", "T339", "T827"],
                               "bz": list(bz)},
                        "p1": {"deck": ["T827"] * 3},
                        "filler": "T002", "seed": 1, "deck_size": 20,
                        "deck_exact": [True, True]})
    snap = []
    played = []

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and f"play:{TARGET}" in keys:
            played.append(True)
            snap.append(list(e.s.zones["deck"][0]))
            e.answer([keys.index(f"play:{TARGET}")])
            return "ok"
        if played and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        if played and d["kind"] == "charge":
            return "stop"                  # 解決済みの観測点
        return None

    _drive(e, on_dec)
    assert played, "target was not played"
    return e, snap[0]


def test_registered_cip_puts_deck_top_to_mana_with_multicolor(rules):
    """登録カード: 多色クリーチャー（T030）が自分の
    バトルゾーンにあれば、出た時に山札の上から
    １枚目がマナゾーンに置かれる（レインボーナス）。"""
    e, deck0 = _summon_target(rules, bz=["T030"])
    top = deck0[0]
    assert e.s.cards[top].zone == "mana"
    assert len(e.s.zones["mana"][0]) == 4        # 支払い3枚＋置かれた1枚
    assert list(e.s.zones["deck"][0]) == deck0[1:]


def test_registered_cip_no_mana_put_without_multicolor(rules):
    """登録カード: 多色クリーチャーが無ければ（自身は
    単色）条件が外れ、山札はそのままでマナも増えない。"""
    e, deck0 = _summon_target(rules)
    assert list(e.s.zones["deck"][0]) == deck0
    assert len(e.s.zones["mana"][0]) == 3
