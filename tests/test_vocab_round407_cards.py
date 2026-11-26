"""再変換ラウンド407（第372弾 set_power）の記録テスト。

- 新規登録1件: dm32-011 超神龍イエス・ヤザリス
  （登録形は提出形と完全一致: partial の骨格
  〔光 / コスト5 / パワー5500 / 種族
  アポロニア・ドラゴン、keywords [blocker]、
  abilities・evolve_from ともに無し〕に
  **補完2点**〔types への evolution 追加・
  evolve_from {types: [creature], keyword: blocker}
  の追加（同セットの登録先例 dm32-002・dm32-072 と
  同文・同形）〕と第372弾の確立形 CIP 誘発
  〔trigger {event: move, to: bz, subject: self} →
  modify {select: {zone: bz, owner: opp, filter:
  {types: [creature], not_types: [evolution]},
  count: all}, mod: {power_set: 500},
  duration: end_of_turn}〕1件を足し、unsupported を
  外したもの。abilities は1件ちょうど、text は
  partial の時点で公式全文と一致するため text の
  補完はなし）。
- alias 畳み込み0件。正本判定: 対象 id dm32-011 と
  alias dm32-011hc の両方を real.yaml /
  real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml と
  照合し、いずれにも登録なし（proto.yaml のヒットは
  T1116 の notes 内参照のみ）。identity 実測で
  canon(dm32-011) = dm32-011（対象 id が正本）、
  canon(dm32-011hc) = dm32-011、
  aliases_for(超神龍イエス・ヤザリス, dm32-011) =
  [dm32-011hc]。alias dm32-011hc は partial の
  source.aliases にあるだけで rejects に独自行は
  無く、登録形の source.aliases に記録のみ。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [set_power] のため reopen で
  外してから submit（reopen の出力は対象1件
  ちょうど、alias 行の巻き込みなし）。
- converted 10,351→10,352 / rejects 1,961→1,960、
  canonical 重なり0・alias 重なり0・漏れ0。
  set_power はファミリーがこの1件だけだったため
  完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第372弾本体の薄い包み（対象を登録カードに差し
替えたもの）で、tests.conftest は import しない
（第319弾以降の作法）。判別役は proto T1117
（ブロッカー進化元役＋光マナ役）/ T1118（パワー
7000・非進化役）/ T1119（パワー4000・進化役）/
T1120（パワー300・非進化役）/ T1114（自己パワー
+3000役＝実効6000）/ T1107（能力なしパワー2000＝
ブロッカーを持たない進化元対照）。
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
TARGET = "dm32-011"
ALIAS = "dm32-011hc"
GAP = "set_power"

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [
           {"op": "modify",
            "select": {"zone": "bz", "owner": "opp",
                       "filter": {"types": ["creature"],
                                  "not_types": ["evolution"]},
                       "count": "all"},
            "mod": {"power_set": 500},
            "duration": "end_of_turn"}]}
EVOLVE_FROM = {"types": ["creature"], "keyword": "blocker"}
FORM = [CIP]
FULL_TEXT = ("ブロッカー\n"
             "進化-自分の「ブロッカー」を持つクリーチャー１体の上に置く。\n"
             "このクリーチャーをバトルゾーンに出した時、そのターン、"
             "バトルゾーンにある相手の進化ではないクリーチャーすべての"
             "パワーは500になる。")


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


def test_round407_disposition():
    rej = _reject_rows()
    assert len(rej) == 1960
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10352
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    assert TARGET not in rej             # 対象行は解消
    assert ALIAS not in rej              # 対象 alias に独自行なし
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")
    assert (c.get("source") or {}).get("aliases") == [ALIAS]
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: abilities 1件ちょうど、
    # 補完2点（types / evolve_from）が入っている
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["types"] == ["creature", "evolution"]
    assert c["evolve_from"] == EVOLVE_FROM
    assert c["keywords"] == ["blocker"]
    assert c["text"] == FULL_TEXT        # text の補完はなし
    assert c["name"] == "超神龍イエス・ヤザリス"
    assert c["civs"] == ["light"]
    assert c["cost"] == 5 and c["power"] == 5500 and c["mana"] == 1
    assert c["races"] == ["アポロニア・ドラゴン"]
    d = parse_card(c, TABLES)
    assert CIP in d.abilities
    assert d.evolve_from == EVOLVE_FROM
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第372弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn):
    cards = e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)
    return next(c for c in cards if e.cdef(c).id == defn)


def _power(e, p, defn):
    return e.chars(_find(e, "bz", p, defn))["power"]


def _drive(e, plays=(), pick=None, stop=None, on_main=None,
           limit=600):
    """汎用ドライバ（第372弾本体と同形）。"""
    plays = list(plays)
    for _ in range(limit):
        if stop is not None and stop():
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and d.get("player") == 0:
            if on_main is not None:
                on_main(keys)
            hit = next((k for k in plays if k in keys), None)
            if hit is not None:
                plays.remove(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def _summon_setup(rules, p1_bz):
    return _build(rules,
                  {"bz": ["T1117"], "hand": [TARGET],
                   "mana": ["T1117"] * 5},
                  {"bz": p1_bz})


def test_registered_cip_sets_all_opponent_non_evolution_powers(rules):
    """登録カード: ブロッカー（T1117）の上に進化させて
    出すと、そのターン、相手の進化ではないクリーチャー
    すべてのパワーが500になる。パワー7000（T1118）は
    500に下がり、パワー300（T1120）は500に上がり、
    実効6000（T1114）も加算ごと上書きされて500になる。
    進化クリーチャー（T1119、パワー4000）は対象外。"""
    e = _summon_setup(rules, ["T1118", "T1119", "T1120", "T1114"])
    assert _power(e, 1, "T1118") == 7000     # 前提
    assert _power(e, 1, "T1114") == 6000     # 前提: 加算が効いている
    assert _power(e, 1, "T1120") == 300      # 前提
    assert _power(e, 1, "T1119") == 4000     # 前提
    _drive(e, plays=[f"play:{TARGET}"], pick="T1117",
           stop=lambda: _power(e, 1, "T1118") == 500)
    assert TARGET in _defns(e, "bz", 0)
    assert _power(e, 0, TARGET) == 5500      # 自分は対象外
    assert _power(e, 1, "T1118") == 500
    assert _power(e, 1, "T1120") == 500      # 引き上げも起きる
    assert _power(e, 1, "T1114") == 500      # 加算ごと上書き
    assert _power(e, 1, "T1119") == 4000     # 進化は対象外


def test_registered_power_set_expires_at_end_of_turn(rules):
    """登録カード: 持続は『そのターン』だけ。ターンが
    終わればパワーは元に戻る（duration: end_of_turn）。"""
    e = _summon_setup(rules, ["T1118"])
    _drive(e, plays=[f"play:{TARGET}"], pick="T1117",
           stop=lambda: _power(e, 1, "T1118") == 500)
    assert _power(e, 1, "T1118") == 500
    _drive(e, stop=lambda: e.s.turn >= 2)
    assert "T1118" in _defns(e, "bz", 1)
    assert _power(e, 1, "T1118") == 7000


def test_registered_no_evolution_onto_non_blocker_base(rules):
    """登録カード: ブロッカーを持たないクリーチャー
    （T1107）の上には進化できない（evolve_from の
    補完が効いている）。main の選択肢に play が一度も
    現れず、手札に留まる。"""
    e = _build(rules,
               {"bz": ["T1107"], "hand": [TARGET],
                "mana": ["T1117"] * 5},
               {})
    offered = {"play": False}

    def on_main(keys):
        if f"play:{TARGET}" in keys:
            offered["play"] = True

    _drive(e, plays=[f"play:{TARGET}"], on_main=on_main,
           stop=lambda: e.s.turn >= 5, limit=300)
    assert not offered["play"]
    assert TARGET in _defns(e, "hand", 0)
    assert TARGET not in _defns(e, "bz", 0)


def test_registered_cip_with_no_opponent_creatures(rules):
    """登録カード: 相手のクリーチャーがいなければ一括
    modify の対象は無く、効果は空振りで解決する。
    登録カードは通常どおり場に出る。"""
    e = _summon_setup(rules, [])
    _drive(e, plays=[f"play:{TARGET}"], pick="T1117",
           stop=lambda: TARGET in _defns(e, "bz", 0)
           and e.s.turn >= 2)
    assert TARGET in _defns(e, "bz", 0)
    assert _power(e, 0, TARGET) == 5500
    assert _defns(e, "graveyard", 0) == []
    assert _defns(e, "graveyard", 1) == []
