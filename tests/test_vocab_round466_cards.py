"""再変換ラウンド466（第431弾
after_battle_trigger）の記録テスト。

- 新規登録1件: dmrp14-072 血誓怪人ザミザニン
  （対象行は partial も reason フィールドも無い
  素行で、公式データ行〔by_product/rp14.jsonl〕
  から決定的に構築した骨格〔クリーチャー / 闇 /
  コスト2 / パワー5000 / 種族 デビルマスク、
  mana 1、keywords [blocker, cannot_attack]、
  text 公式全文〕に第431弾の確立形 ability 1件
  〔trigger {when: {event: battle_end, subject:
  self}, effect: [destroy {select: {ref:
  self}}]}〕（第211弾の battle_end 形。登録済み
  dmpcd03-b11 が同一の条項構造をこの形で保持
  する）を足したもの。登録形は提出形と完全一致
  〔source 以外の全フィールドを照合〕、
  abilities は trigger 1件ちょうど、keywords
  [blocker, cannot_attack] のまま）。
- 補完なし（text は公式全文で、登録後の全文
  一致も照合済み）。
- alias 畳み込み0件（alias 無し。正本判定は
  通常型で対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1212 の
  notes 内参照のみ〕、identity 実測で canon_id
  は対象自身、aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔after_battle_trigger〕の出力は
  0件＝対象行に reason フィールドが無いため、
  ラウンド428・450・451の実測どおり。submit が
  登録成功時に行を除去）。
- converted 10,411→10,412 / rejects
  1,900→1,899、canonical 重なり0・漏れ0。
  after_battle_trigger はもう1件の dmrp09-074
  （勝者参照が要る）が残るため完全解消には
  ならない。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第431弾本体と同形（対象を proto T1212 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（パワー2000バニラ＝
ブロックして勝つ相手）/ T1126（パワー8000
ブロッカー＝ブロックして負ける相手）。
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
from tests.test_vocab_pilot431_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot431 import FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmrp14-072"
OTHER = "dmrp09-074"
GAP = "after_battle_trigger"


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


def test_round466_disposition():
    rej = _reject_rows()
    assert len(rej) == 1899
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10412
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == [OTHER]                # dmrp09-074 が残る（解消しない）
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 1      # abilities は trigger 1件ちょうど
    assert c["abilities"][0]["kind"] == "trigger"
    assert c["abilities"][0]["when"] == {"event": "battle_end",
                                         "subject": "self"}
    assert c["keywords"] == ["blocker", "cannot_attack"]
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    assert d.types == ["creature"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第431弾本体と同形、対象は登録カード） ----------

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


def _drive_battle(e, attacker_key, block_key, stop, limit=600):
    """相手（p1）の attacker_key を一度だけプレイヤー攻撃
    させ、block_key（自軍ブロッカー）が提示されれば
    ブロックする。stop(e) が真になるまで進める。"""
    st = {"attacked": False, "blocked": False}
    for _ in range(limit):
        if stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if not st["attacked"] and d["kind"] == "attack" \
                and attacker_key in keys:
            e.answer([keys.index(attacker_key)])
            st["attacked"] = True
            continue
        if d["kind"] == "block":
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"bz:{block_key}")]
            if hit:
                e.answer([hit[0]])
                st["blocked"] = True
                continue
        _answer_default(e, d)
    return st


def test_block_and_win_destroys_self_after_battle(rules):
    """登録カードがブロックしてバトルに勝っても、バトルの
    後に自分を破壊する。攻撃側はバトルで破壊される
    （破壊がバトルの後であることの判別: バトル開始時
    破壊なら攻撃側は生き残る）。シールドは無傷。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T001"]})
    src = _cid(e, 0, TARGET)
    atk = _cid(e, 1, "T001")
    st = _drive_battle(
        e, "attack:T001:player", TARGET,
        stop=lambda: e.s.cards[src].zone == "graveyard"
        and e.s.cards[atk].zone == "graveyard")
    assert st["attacked"] and st["blocked"]
    assert e.s.cards[atk].zone == "graveyard"   # パワー2000はバトルで破壊
    assert e.s.cards[src].zone == "graveyard"   # バトルの後に自己破壊
    assert len(e.zlist("shield", 0)) == 5       # ブロックしたので無傷


def test_block_and_lose_stays_graveyard(rules):
    """登録カードがブロックしてバトルに負けた場合はその
    時点で墓地にあり、battle_end 誘発の解決で二重の
    処理や異常は起きない。攻撃側は場に残り、シールドは
    無傷。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1126"]})
    src = _cid(e, 0, TARGET)
    atk = _cid(e, 1, "T1126")
    st = _drive_battle(
        e, "attack:T1126:player", TARGET,
        stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"] and st["blocked"]
    assert e.s.cards[src].zone == "graveyard"
    assert e.s.cards[atk].zone == "bz"
    assert len(e.zlist("shield", 0)) == 5
    # 誘発解決後もゲームが正常に進むこと
    for _ in range(30):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        _answer_default(e, d)
    assert e.s.cards[src].zone == "graveyard"


def test_no_battle_no_destroy_and_cannot_attack(rules):
    """登録カードはバトルしなければ破壊されない。また、
    攻撃できない（自分の攻撃ステップに攻撃選択肢が
    提示されない）まま1巡しても場に残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    src = _cid(e, 0, TARGET)
    turns = {"n": 0}
    for _ in range(600):
        d = e.advance()
        if d is None:   # 山札切れでゲーム終了（両者とも
            break       # チャージのみの構成のため）
        keys = _keys(d)
        # 攻撃できない: どの決定にも攻撃選択肢は現れない
        assert not any(k.startswith(f"attack:{TARGET}") for k in keys)
        if d["kind"] == "charge" and d.get("player") == 0:
            turns["n"] += 1   # 自分のターンが回ってきた回数
        _answer_default(e, d)
    assert turns["n"] >= 2   # 自分のターンが2回以上回った
    assert e.s.cards[src].zone == "bz"
