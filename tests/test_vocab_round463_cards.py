"""再変換ラウンド463（第428弾
unblockable_only_when_attacking_creatures）の記録テスト。

- 新規登録2件: dm09-030 ジョー・リザード /
  dm09-050 鳥神兵クウザ（同一文面。両件とも
  partial の骨格〔クリーチャー / 火、dm09-030 は
  コスト6 / パワー3000 / デューンゲッコー、
  dm09-050 は コスト3 / パワー1000 / アーマロイド、
  mana 1、text 公式全文〕に abilities 2件
  〔static {affects: self, mod:
  {unblockable_vs_creatures: true}}（第428弾の
  新規語彙・最小。第426弾 must_be_blocked と同型）
  ＋ static {affects: self, mod: {power_when:
  {amount: 3000, when: attacking}}}（確立形。
  split の定型所有形そのもの）〕を文面の条項順に
  並べ、unsupported を外したもの。partial 内の
  attack 誘発→modify 近似形は不採用）。
- 登録形は abilities 以外の全フィールドが提出形と
  完全一致。abilities は定型所有の power_when
  static が merge_split の再付着で先頭に来るため
  登録順は [power_when, unblockable_vs_creatures]
  （ラウンド410の先例と同型。両方とも self の
  静的効果で順序に意味は無い）。abilities は
  static 2件ちょうど、power_when は dedupe で
  1件だけを実測確認。
- 補完なし（partial の text は公式全文、登録後も
  照合済み）。
- alias 畳み込み0件（alias は両件とも無し。
  正本判定は通常型: 対象 id 2件を real /
  real_akashic / real_vocab / real_zone / proto /
  converted と照合し登録なし〔proto のヒットは
  T1206 / T1207 の notes 内参照のみ〕、identity
  実測で canon_id は対象自身、aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔unblockable_only_when_attacking_
  creatures〕の出力は対象2件ちょうど＝巻き込み
  なし）。
- converted 10,407→10,409 / rejects
  1,904→1,902、canonical 重なり0・漏れ0。
  unblockable_only_when_attacking_creatures は
  完全解消。unblockable_vs_creatures は新規
  mod キーの初登録。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第428弾本体と同形（対象を proto T1206 / T1207
から登録カードに差し替えたもの）で、
tests.conftest は import しない（第319弾以降の
作法）。判別役は既存 proto を流用: T001（対照の
通常クリーチャー／攻撃先）/ T004（パワー3000
ブロッカー）/ T1126（パワー8000ブロッカー）。
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
from tests.test_vocab_pilot428_cards import (  # noqa: E402
    FORM, FULL_TEXT, REG_ABILITIES, TARGETS, submit_form)

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
GAP = "unblockable_only_when_attacking_creatures"


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


def test_round463_disposition():
    rej = _reject_rows()
    assert len(rej) == 1902
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10409
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    for tid in TARGETS:
        assert tid not in rej            # 対象行は登録で解消（漏れ0）
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        sub = submit_form(tid)
        reg = {k: v for k, v in c.items() if k != "source"}
        reg_ab = reg.pop("abilities")
        sub.pop("abilities")
        assert reg == sub                # abilities 以外は完全一致
        # 登録後は abilities が static 2件ちょうど、
        # power_when は dedupe で1件だけ
        assert reg_ab == REG_ABILITIES
        assert len(reg_ab) == 2
        assert all(a["kind"] == "static" for a in reg_ab)
        pw = [a for a in reg_ab
              if (a.get("mod") or {}).get("power_when")]
        ub = [a for a in reg_ab
              if (a.get("mod") or {}).get("unblockable_vs_creatures")]
        assert len(pw) == 1 and len(ub) == 1
        assert c["text"] == FULL_TEXT    # 公式全文
        assert not c.get("aliases") and not c.get("keywords")
        src = c.get("source") or {}
        assert not src.get("unsupported")
        assert not src.get("aliases")
        d = parse_card(c, TABLES)
        for a in FORM:
            assert a in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第428弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _drive(e, attack_key=None, blocker=None, stop=None, limit=600):
    """attack_key を一度だけ攻撃させ、block 決定が出たら
    blocker（proto id）が選択肢にあればそれを選び、
    無ければ no_block を選ぶ。現れた block 決定の
    options 一覧を log に残す。"""
    st = {"attacked": False}
    log = []
    for _ in range(limit):
        if stop and stop():
            return st, log
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if attack_key and not st["attacked"] and d["kind"] == "attack" \
                and attack_key in keys:
            e.answer([keys.index(attack_key)])
            st["attacked"] = True
            continue
        if d["kind"] == "block":
            log.append(list(keys))
            if blocker:
                hit = [i for i, k in enumerate(keys)
                       if k.startswith(f"bz:{blocker}")]
                if hit:
                    e.answer([hit[0]])
                    continue
            e.answer([keys.index("no_block")])
            continue
        _answer_default(e, d)
    return st, log


def test_dm09_030_characteristic(rules):
    """特性判別: 登録カード dm09-030 は
    unblockable_vs_creatures が true で、素の
    パワーは印刷どおり。通常のクリーチャーは
    false。"""
    e = _build(rules, {"bz": ["dm09-030", "T001"]}, {"bz": []})
    src = _cid(e, 0, "dm09-030")
    ctl = _cid(e, 0, "T001")
    assert e.chars_ro(src)["unblockable_vs_creatures"] is True
    assert e.chars_ro(src)["power"] == 3000
    assert e.chars_ro(ctl)["unblockable_vs_creatures"] is False


def test_dm09_030_attack_creature_cannot_be_blocked(rules):
    """判別: dm09-030 がクリーチャーを攻撃する時は
    ブロックできない。相手にアンタップの
    ブロッカー（T004）がいても block 決定に
    ブロッカー選択肢が現れず、攻撃先（タップした
    T001）はバトルで破壊される。"""
    e = _build(rules, {"bz": ["dm09-030"]}, {"bz": ["T001", "T004"]})
    src = _cid(e, 0, "dm09-030")
    tgt = _cid(e, 1, "T001")
    blk = _cid(e, 1, "T004")
    e.s.cards[tgt].tapped = True
    st, log = _drive(e, attack_key="attack:dm09-030:T001",
                     stop=lambda: e.s.cards[tgt].zone == "graveyard")
    assert st["attacked"]
    assert all(not any(k.startswith("bz:") for k in ks) for ks in log)
    assert e.s.cards[tgt].zone == "graveyard"
    assert e.s.cards[src].zone == "bz"
    assert e.s.cards[blk].zone == "bz"
    assert not e.s.cards[blk].tapped


def test_dm09_030_attack_player_can_be_blocked(rules):
    """判別: dm09-030 がプレイヤーを攻撃する時は
    通常どおりブロックできる。強いブロッカー
    （T1126、パワー8000）にブロックされると
    攻撃側（攻撃中パワー6000）は破壊され、
    シールドは減らない。"""
    e = _build(rules, {"bz": ["dm09-030"]}, {"bz": ["T1126"]})
    src = _cid(e, 0, "dm09-030")
    st, log = _drive(e, attack_key="attack:dm09-030:player",
                     blocker="T1126",
                     stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert any(any(k.startswith("bz:T1126") for k in ks) for ks in log)
    assert e.s.cards[src].zone == "graveyard"
    assert len(e.zlist("shield", 1)) == 5


def test_dm09_030_attack_player_unblocked_breaks_one(rules):
    """dm09-030 のプレイヤー攻撃をブロックしなければ
    シールドが1枚ブレイクする（ブレイカー系の
    キーワードは持たない）。block 選択肢自体は
    提示される。"""
    e = _build(rules, {"bz": ["dm09-030"]}, {"bz": ["T004"]})
    src = _cid(e, 0, "dm09-030")
    st, log = _drive(e, attack_key="attack:dm09-030:player",
                     stop=lambda: len(e.zlist("shield", 1)) == 4)
    assert st["attacked"]
    assert any(any(k.startswith("bz:T004") for k in ks) for ks in log)
    assert len(e.zlist("shield", 1)) == 4
    assert e.s.cards[src].zone == "bz"


def test_dm09_050_attack_creature_cannot_be_blocked(rules):
    """dm09-050（パワー1000）も同形: クリーチャー
    攻撃はブロックされず、攻撃中パワー
    1000+3000=4000 で T001（2000）を破壊する。"""
    e = _build(rules, {"bz": ["dm09-050"]}, {"bz": ["T001", "T004"]})
    src = _cid(e, 0, "dm09-050")
    tgt = _cid(e, 1, "T001")
    e.s.cards[tgt].tapped = True
    st, log = _drive(e, attack_key="attack:dm09-050:T001",
                     stop=lambda: e.s.cards[tgt].zone == "graveyard")
    assert st["attacked"]
    assert all(not any(k.startswith("bz:") for k in ks) for ks in log)
    assert e.s.cards[tgt].zone == "graveyard"
    assert e.s.cards[src].zone == "bz"


def test_dm09_050_attack_player_blocked_battle(rules):
    """判別: dm09-050 のプレイヤー攻撃はブロック
    でき、ブロックした T004（パワー3000）は
    攻撃中パワー4000 に負けて破壊される
    （power_when +3000 がバトルで効くことと、
    プレイヤー攻撃ではブロック可能なことの
    同時判別）。シールドは減らない。"""
    e = _build(rules, {"bz": ["dm09-050"]}, {"bz": ["T004"]})
    src = _cid(e, 0, "dm09-050")
    blk = _cid(e, 1, "T004")
    st, log = _drive(e, attack_key="attack:dm09-050:player",
                     blocker="T004",
                     stop=lambda: e.s.cards[blk].zone == "graveyard")
    assert st["attacked"]
    assert any(any(k.startswith("bz:T004") for k in ks) for ks in log)
    assert e.s.cards[blk].zone == "graveyard"
    assert e.s.cards[src].zone == "bz"
    assert len(e.zlist("shield", 1)) == 5
