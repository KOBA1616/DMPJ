"""再変換ラウンド458（第423弾
trigger_after_battle_win_or_lose）の記録テスト。

- 新規登録1件: dm10-013 粛清者アイザク
  （partial の骨格〔クリーチャー / 光 / コスト4 /
  パワー4000 / 種族 ソルトルーパー、mana 1、
  keywords [blocker, cannot_attack_player]〕に
  第423弾の確立形 ability 1件〔trigger {when:
  {event: block, subject: self}, effect: [may
  [choose {select: {zone: bz, owner: you,
  filter: {types: [creature]}, count: 1},
  as: pick}, delayed_trigger {when: {event:
  battle_end, subject: self}, effect: [untap
  {select: {ref: pick}}]}]]}〕（block 誘発は
  第401・422弾、choose の as 束縛は第414・422弾、
  battle_end は第211弾、delayed_trigger は
  603.6 の確立 op で vars スナップショットにより
  pick が遅延効果に届く。勝っても負けても発生源が
  バトルで破壊されても battle_end は両参加者ぶん
  出るため勝敗を問わない文面と一致）を足し、
  unsupported を外したもの。登録形は提出形と
  完全一致、abilities は1件ちょうど、keywords は
  [blocker, cannot_attack_player] のまま）。
- 補完なし: partial の text は公式全文で、登録後の
  text も公式全文と完全一致を照合済み。
- split はキーワードのみ定型所有で part[2] は空
  ＝ツール側ブロッカーなし。
- alias 畳み込み0件（alias 無し。正本判定は通常型
  で対象 id を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1199 の notes 内参照のみ〕、
  identity 実測で canon_id は対象自身、
  aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件:
  reopen（trigger_after_battle_win_or_lose）の
  出力は対象1件ちょうど（巻き込みなし）。
- converted 10,402→10,403 / rejects
  1,909→1,908、canonical 重なり0・漏れ0。
  trigger_after_battle_win_or_lose は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第423弾本体と同形（対象を proto T1199 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（パワー2000バニラ＝
味方役・弱いアタッカー役）/ T1196（パワー5000＝
発生源がバトルに負ける判別役）。
観測点: 対象の攻撃が解決した後、同じ相手ターンの
次の attack 決定の時点（遅延誘発は解決済みで、
自ターンのアンタップステップにはまだ入っていない）。
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
from tests.test_vocab_pilot423 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm10-013"
GAP = "trigger_after_battle_win_or_lose"
NAME = "粛清者アイザク"


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


def test_round458_disposition():
    rej = _reject_rows()
    assert len(rej) == 1908
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10403
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ソルトルーパー"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は1件
    # ちょうど、keywords はそのまま
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["blocker", "cannot_attack_player"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    assert FORM[0] in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第423弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "pay_mana":
        e.answer([0])
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    # バトルゾーンは共有ゾーンなので controller でも絞る
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == p)


def _drive(e, attack_key, block=True, may=True, choose_cid=None,
           tap_cid=None, limit=400):
    """相手（p1）の attack_key の攻撃を一度だけ行わせ、
    登録カードでブロックさせ、may / choose に答える。
    攻撃が解決した後の同じ相手ターンの次の attack
    決定の時点で止める（遅延誘発は解決済み、自ターン
    のアンタップステップ前）。tap_cid は攻撃宣言の
    直前にタップする。"""
    attacked = False
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if attacked and d["kind"] == "attack" and d["player"] == 1:
            return
        if not attacked and d["kind"] == "attack" and d["player"] == 1 \
                and attack_key in keys:
            if tap_cid is not None:
                e.s.cards[tap_cid].tapped = True
            e.answer([keys.index(attack_key)])
            attacked = True
            continue
        if d["kind"] == "block":
            if block:
                hit = [i for i, k in enumerate(keys)
                       if k.startswith(f"bz:{TARGET}")]
                assert hit, "登録カードがブロック候補に無い"
                e.answer([hit[0]])
            else:
                e.answer([keys.index("no_block")])
            continue
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes" if may else "no")])
            continue
        if d["kind"] == "choose_cards":
            hit = [i for i, o in enumerate(d["options"])
                   if o.get("cid") == choose_cid]
            assert hit, "choose 候補に指定クリーチャーが無い"
            e.answer([hit[0]])
            continue
        _answer_default(e, d)
    raise AssertionError("観測点に到達しなかった")


def _setup(rules, attackers):
    """p0: 登録カード＋味方 T001（攻撃直前にタップする）。
    p1: attackers。"""
    e = _build(rules, {"bz": [TARGET, "T001"]}, {"bz": attackers})
    return e, _cid(e, 0, TARGET), _cid(e, 0, "T001")


def test_block_win_untaps_chosen_ally(rules):
    # バトルに勝った場合（登録カード自身）: ブロックして
    # タップした発生源はそのまま、選んだ味方はバトルの
    # 後にアンタップする。
    e, isaac, ally = _setup(rules, ["T001", "T1196"])
    atk = _cid(e, 1, "T001")
    _drive(e, "attack:T001:player", choose_cid=ally, tap_cid=ally)
    assert e.s.cards[atk].zone == "graveyard"      # 2000 は 4000 に負ける
    assert e.s.cards[isaac].zone == "bz"
    assert e.s.cards[isaac].tapped is True         # ブロックでタップしたまま
    assert e.s.cards[ally].tapped is False         # バトルの後にアンタップ


def test_block_lose_still_untaps_chosen_ally(rules):
    # バトルに負けた場合（登録カード自身、勝敗を問わない
    # 判別）: 発生源がバトルで破壊されても、選んだ味方は
    # バトルの後にアンタップする。battle_win のみで待つ
    # 形では落ちる。
    e, isaac, ally = _setup(rules, ["T1196", "T001"])
    _drive(e, "attack:T1196:player", choose_cid=ally, tap_cid=ally)
    assert e.s.cards[isaac].zone == "graveyard"    # 4000 は 5000 に負ける
    assert e.s.cards[ally].tapped is False         # それでもアンタップする


def test_decline_may_keeps_ally_tapped(rules):
    # 「選んでもよい」を辞退したら何も起きない
    # （登録カード自身）。
    e, isaac, ally = _setup(rules, ["T001", "T1196"])
    _drive(e, "attack:T001:player", may=False, tap_cid=ally)
    assert e.s.cards[isaac].zone == "bz"
    assert e.s.cards[ally].tapped is True


def test_choose_self_untaps_after_battle(rules):
    # 発生源自身も「自分のクリーチャー」に含まれる
    # （登録カード自身）: ブロックでタップした発生源が、
    # バトルの後にアンタップする。味方は選ばれていない
    # のでタップのまま。
    e, isaac, ally = _setup(rules, ["T001", "T1196"])
    _drive(e, "attack:T001:player", choose_cid=isaac, tap_cid=ally)
    assert e.s.cards[isaac].zone == "bz"
    assert e.s.cards[isaac].tapped is False
    assert e.s.cards[ally].tapped is True


def test_no_block_no_untap(rules):
    # ブロックしなければ誘発しない（登録カード自身）。
    e, isaac, ally = _setup(rules, ["T001", "T1196"])
    _drive(e, "attack:T001:player", block=False, tap_cid=ally)
    assert e.s.cards[isaac].tapped is False        # ブロックしていない
    assert e.s.cards[ally].tapped is True          # アンタップしない
