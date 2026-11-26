"""再変換ラウンド441（第406弾 distinct_race_count）の記録テスト。

- 新規登録1件: dmx12b-058 口寄の化身
  （登録形は提出形と完全一致〔差分は validate が
  identity.aliases_for から自動付与した
  source.aliases のみ〕: partial の骨格
  〔クリーチャー / 自然 / コスト6 / パワー4000 /
  種族 ミステリー・トーテム、mana 1、keywords・
  abilities ともに無し〕に第406弾の確立形 trigger
  〔when {event: move, to: bz, subject: self}、
  effect [may [draw {count: {distinct_race_count:
  {selector: {zone: bz, owner: you},
  exclude_races: [ミステリー・トーテム]}}}]]]〕
  1件を足し、unsupported を外したもの。
  abilities はこの1件ちょうど、keywords は
  無いまま。**補完あり: text のみ**〔partial の
  text は断片「種族１種類につき」のため公式
  テキスト全文を入れ、登録後の全文一致も
  照合済み〕）。
- alias 畳み込み0件（alias 4件 dm14-010 /
  dmc42-015 / dmc57-015 / dmc61-010 はいずれも
  rejects に独自行が無く converted にも登録なし。
  登録エントリの source.aliases は validate が
  identity.aliases_for から自動付与した4件。
  正本判定は通常型: 対象 id と alias 4件を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1173 の notes 内参照のみ〕、identity
  実測で canon_id は対象・全 alias とも
  dmx12b-058）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔distinct_race_count〕の出力は対象
  1件ちょうど）。
- converted 10,385→10,386 / rejects 1,927→1,926、
  canonical 重なり0・漏れ0。distinct_race_count
  は完全解消。
- distinct_race_count の構造化形 {selector,
  exclude_races} は新規の式形で、本ラウンドが
  初回登録（監査は converted に載ったフィールド
  しか見ないため test_data_audit を再実行して
  確認済み）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第406弾本体と同形（対象を proto T1173 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（単一種族役＝種族
テスト）/ T787（2種族役＝アンノウン＋ゼニス）/
T189（種族 テストを持つタマシード役）/ T1174
（多種族トーテム役＝ミステリー・トーテム＋
アース・ドラゴン）。バトルゾーンは共有ゾーン
なので所有は zlist(zone, p) で見る。
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
from tests.test_vocab_pilot406 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmx12b-058"
GAP = "distinct_race_count"
NAME = "口寄の化身"
ALIASES = ["dm14-010", "dmc42-015", "dmc57-015", "dmc61-010"]
MANA = ["T001"] * 6   # 自然6（対象は自然コスト6）


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


def test_round441_disposition():
    rej = _reject_rows()
    assert len(rej) == 1926
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10386
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = [rid for rid, r in rej.items()
           if GAP in (r.get("gaps") or [])]
    assert fam == []                     # ファミリー完全解消
    for a in ALIASES:
        assert a not in rej              # alias に独自行は無い（漏れ0）
        assert a not in ids              # alias は登録エントリにならない
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"]
    assert c["civs"] == ["nature"]
    assert c["cost"] == 6 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ミステリー・トーテム"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完あり: text のみ）
    # 登録形は提出形と完全一致: abilities は確立形 trigger 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")          # keywords は無いまま
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    assert len(d.abilities) == 1
    assert d.keywords == []
    assert d.abilities[0]["effect"][0]["body"][0]["count"] == {
        "distinct_race_count":
            {"selector": {"zone": "bz", "owner": "you"},
             "exclude_races": ["ミステリー・トーテム"]}}
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第406弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _summon(rules, bz0=(), bz1=(), may_yes=True):
    """p0 が登録カードを召喚し、CIP の may に答えて解決まで
    進める。（engine, 召喚したか, may が出たか）を返す。
    bz0 / bz1 は事前に置く判別役。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": MANA, "bz": list(bz0)},
               {"bz": list(bz1)})
    played = False
    may_seen = False
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and f"play:{TARGET}" in keys:
            played = True
            e.answer([keys.index(f"play:{TARGET}")])
            continue
        if played and d["kind"] == "yes_no":
            may_seen = True
            e.answer([keys.index("yes" if may_yes else "no")])
            continue
        if played and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, played, may_seen


def _hand_count(e):
    return len(e.zlist("hand", 0))


def test_registered_only_self_draws_zero(rules):
    # 自分の種族はミステリー・トーテムのみ → 除外され0枚
    e, played, may_seen = _summon(rules)
    assert played and may_seen
    assert _hand_count(e) == 0
    assert TARGET in [e.cdef(c).id for c in e.zlist("bz", 0)]


def test_registered_one_distinct_race_draws_one(rules):
    e, played, may_seen = _summon(rules, bz0=["T001"])
    assert played and may_seen
    assert _hand_count(e) == 1


def test_registered_same_race_twice_draws_one(rules):
    # 同種族（テスト）が2体いても種類数は1 → 1枚
    e, played, may_seen = _summon(rules, bz0=["T001", "T001"])
    assert played and may_seen
    assert _hand_count(e) == 1


def test_registered_multi_race_totem_other_race_counts(rules):
    # 種族名単位の除外の判別: ミステリー・トーテム＋
    # アース・ドラゴンの多種族獣は、アース・ドラゴンが
    # 数えられ1枚（カード単位の除外では0枚になる）
    e, played, may_seen = _summon(rules, bz0=["T1174"])
    assert played and may_seen
    assert _hand_count(e) == 1


def test_registered_tamaseed_race_counts(rules):
    # クリーチャー限定なしの判別: 種族を持つタマシード
    # （T189、種族 テスト）でも1枚
    e, played, may_seen = _summon(rules, bz0=["T189"])
    assert played and may_seen
    assert _hand_count(e) == 1


def test_registered_opponent_races_do_not_count(rules):
    # owner: you の判別: 相手の2種族獣は数えない
    e, played, may_seen = _summon(rules, bz1=["T787"])
    assert played and may_seen
    assert _hand_count(e) == 0


def test_registered_decline_may_draws_nothing(rules):
    # 引いてもよい = may。断れば種族があっても引かない
    e, played, may_seen = _summon(rules, bz0=["T787"], may_yes=False)
    assert played and may_seen
    assert _hand_count(e) == 0


def test_registered_mixed_board_draws_four(rules):
    # テスト（T001）＋アンノウン・ゼニス（T787）＋
    # アース・ドラゴン（T1174。MT は除外）= 4種 → 4枚
    e, played, may_seen = _summon(rules, bz0=["T001", "T787", "T1174"])
    assert played and may_seen
    assert _hand_count(e) == 4
