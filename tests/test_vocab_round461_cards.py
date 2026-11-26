"""再変換ラウンド461（第426弾 must_be_blocked）の
記録テスト。

- 新規登録1件: dmex08-291 薩摩の超人
  （partial の骨格〔クリーチャー / 自然 / コスト9 /
  パワー13000 / 種族 ジャイアント/サムライ、mana 1、
  keywords [triple_breaker]、text 公式全文〕に
  abilities 2件を文面の条項順に並べたもの
  〔第1条項 static {affects: {zone: bz, owner: you,
  filter: {types: [creature], races: [ジャイアント]}},
  mod: {must_be_blocked: true}}（第426弾の新規語彙・
  最小。発生源自身もジャイアントなので自分も対象に
  含まれる＝「すべて」）＋第2条項は partial 構築済みの
  trigger {when: {event: battle_win, subject:
  {owner: you, filter: {races: [ジャイアント]}}},
  if: {is_turn: you}, effect: [break {player: opp,
  count: 1}]} をそのまま〕で、unsupported を外した
  もの。登録形は提出形と完全一致、abilities は
  この2件ちょうど、keywords は [triple_breaker]
  のまま）。
- 補完なし（partial の text は公式全文、登録後も
  照合済み）。
- split はキーワードのみ定型所有で part[2] は空
  ＝ツール側ブロッカーなし。
- alias 畳み込み0件（別刷り dm31-s03 は rejects に
  独自行なし、登録エントリの source.aliases にのみ
  収載。正本判定は通常型: 対象 id と別刷りを real /
  real_akashic / real_vocab / real_zone / proto /
  converted と照合し登録なし〔proto のヒットは
  T1204 の notes 内参照のみ〕、identity 実測で
  canon_id は対象自身、別刷りの canon も対象、
  aliases_for = [dm31-s03]）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔must_be_blocked〕の出力は対象1件
  ちょうど＝巻き込みなし）。
- converted 10,405→10,406 / rejects
  1,906→1,905、canonical 重なり0・漏れ0。
  must_be_blocked は完全解消（初登録の新規 mod
  キー。回帰に test_data_audit を含めた）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第426弾本体と同形（対象を proto T1204 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1044（自分の別のジャイアント
役・相手のジャイアント対照役）/ T001（非ジャイアント
対照）/ T004・T1078・T1085（防御側ブロッカー）。
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
from tests.test_vocab_pilot426 import FULL_TEXT, STATIC, TRIGGER  # noqa: E402
from tests.test_vocab_pilot426_cards import SUBMIT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex08-291"
ALIAS = "dm31-s03"
GAP = "must_be_blocked"
NAME = "薩摩の超人"


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


def test_round461_disposition():
    rej = _reject_rows()
    assert len(rej) == 1905
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10406
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["mana"] == 1
    assert c["text"] == FULL_TEXT        # 公式全文
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    # 登録後は abilities が2件ちょうど（static 1＋trigger 1）・
    # keywords [triple_breaker] のまま
    assert c["abilities"] == [STATIC, TRIGGER]
    assert len(c["abilities"]) == 2
    assert c["keywords"] == ["triple_breaker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]  # 別刷りは source.aliases のみ
    assert _conv_cache.find(CONVERTED, ALIAS) is None
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities and TRIGGER in d.abilities
    assert d.keywords == ["triple_breaker"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第426弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, defn, p, nth=0):
    return [c for c in e.bz_tops(p) if e.cdef(c).id == defn][nth]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _zone_tapped(e, defn):
    for cd in e.s.cards:
        if cd.defn == defn:
            return cd.zone, cd.tapped
    raise AssertionError(defn)


def _attack_until(e, attacker, done, block_answer=None, limit=300):
    """attacker（defn）でプレイヤー攻撃し、done() が真に
    なるまで進める。現れた block 決定の options を返す。"""
    seen = []
    atk = f"attack:{attacker}:player"
    for _ in range(limit):
        if done():
            return seen
        d = e.advance()
        if d is None:
            return seen
        ks = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 and atk in ks:
            e.answer([ks.index(atk)])
        elif d["kind"] == "block":
            seen.append(list(ks))
            if block_answer is not None and block_answer in ks:
                e.answer([ks.index(block_answer)])
            elif "no_block" in ks:
                e.answer([ks.index("no_block")])
            else:
                e.answer([0])
        elif "pass" in ks:
            e.answer([ks.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def test_chars_discrimination(rules):
    """特性レベルの判別（登録カード自身）: 自分の
    ジャイアント（発生源自身を含む）は must_be_blocked
    を得る。自分の非ジャイアントと相手のジャイアントは
    得ない。"""
    e = _build(rules,
               {"bz": [TARGET, "T1044", "T001"]},
               {"bz": ["T1044"]})
    assert e.chars(_cid(e, TARGET, 0))["must_be_blocked"] is True
    assert e.chars(_cid(e, "T1044", 0))["must_be_blocked"] is True
    assert e.chars(_cid(e, "T001", 0))["must_be_blocked"] is False
    assert e.chars(_cid(e, "T1044", 1))["must_be_blocked"] is False
    # T・ブレイカーは特性どおり3枚ブレイク
    assert e.chars(_cid(e, TARGET, 0))["breaks"] == 3


def test_forced_block_single_blocker(rules):
    """ブロッカーが1体だけでも強制（登録カード自身）:
    選択肢は一意で決定は出ず、ブロックが成立する。
    ブロッカーは破壊され、第2条項で相手のシールドが
    1つだけブレイクする。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T004"]})
    seen = _attack_until(e, TARGET,
                         lambda: len(e.zlist("shield", 1)) == 4)
    assert seen == []
    assert _zone_tapped(e, "T004") == ("graveyard", False)
    assert len(e.zlist("shield", 1)) == 4


def test_no_force_when_blocker_cannot_block(rules):
    """「可能なら」の判別: ブロッカーがタップしていて
    ブロックできない時は強制は働かず、攻撃は通って
    T・ブレイカーで3枚ブレイクする。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T004"]})
    e.s.cards[_cid(e, "T004", 1)].tapped = True
    seen = _attack_until(e, TARGET,
                         lambda: len(e.zlist("shield", 1)) == 2)
    assert seen == []
    assert len(e.zlist("shield", 1)) == 2


def test_non_giant_attacker_not_forced(rules):
    """対照: 非ジャイアントの攻撃には強制が掛からず、
    block 決定に no_block が残る。"""
    e = _build(rules, {"bz": [TARGET, "T001"]}, {"bz": ["T004"]})
    seen = _attack_until(e, "T001",
                         lambda: len(e.zlist("shield", 1)) == 4,
                         block_answer="no_block")
    assert seen == [["bz:T004:0", "no_block"]]
    assert _zone_tapped(e, "T004") == ("bz", False)
    assert len(e.zlist("shield", 1)) == 4


def test_two_blockers_defender_chooses(rules):
    """ブロッカーが2体いる時は決定が出るが no_block は
    無い。タップしてバトルするのは選ばれた1体だけ
    （第410弾の修正との整合）。第2条項のブレイクも
    1つ起きる。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1078", "T1085"]})
    seen = _attack_until(e, TARGET,
                         lambda: len(e.zlist("shield", 1)) == 4,
                         block_answer="bz:T1078:0")
    assert seen == [["bz:T1078:0", "bz:T1085:0"]]
    assert _zone_tapped(e, "T1078") == ("graveyard", False)
    assert _zone_tapped(e, "T1085") == ("bz", False)
    assert len(e.zlist("shield", 1)) == 4


def test_other_giant_forced_and_tie_no_break(rules):
    """発生源以外の自分のジャイアントの攻撃にも強制が
    掛かる。パワー同値の相打ちではバトルに勝っていない
    ので第2条項のブレイクは起きない。"""
    e = _build(rules, {"bz": [TARGET, "T1044"]}, {"bz": ["T004"]})
    seen = _attack_until(
        e, "T1044",
        lambda: _zone_tapped(e, "T004") != ("bz", False))
    assert seen == []
    assert _zone_tapped(e, "T1044") == ("graveyard", False)
    assert _zone_tapped(e, "T004") == ("graveyard", False)
    assert len(e.zlist("shield", 1)) == 5


def test_no_source_no_force(rules):
    """対照: 発生源（登録カード）がいなければ同じ
    ジャイアントの攻撃でも強制は無く、no_block が残る。"""
    e = _build(rules, {"bz": ["T1044"]}, {"bz": ["T004"]})
    seen = _attack_until(e, "T1044",
                         lambda: len(e.zlist("shield", 1)) == 4,
                         block_answer="no_block")
    assert seen == [["bz:T004:0", "no_block"]]
    assert _zone_tapped(e, "T004") == ("bz", False)
