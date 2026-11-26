"""再変換ラウンド454（第419弾 turn_count_cost_reduction）
の記録テスト。

- 新規登録1件: dmex14-054 捧程者 アコギエレキ
  （partial の骨格〔クリーチャー / 火 / コスト5 /
  パワー5000 / 種族 ムートピア、美孔麗王国、mana 1、
  keywords [speed_attacker]〕に第419弾の確立形
  static 1件〔{kind: static, zone: hand, affects:
  self, mod: {cost: {amount: -2, count: {sum:
  [{turn_count: {kind: summon, owner: you}},
  {turn_count: {kind: cast, owner: you}}]},
  cost_min: 1}}}〕（登録済み dm24ex3-rp2003 /
  dm24ex3-rp2004・第177弾の同文型の kind を
  summon / cast に差し替えただけのドリフト）を
  足し、unsupported を外したもの。登録形は提出形と
  完全一致、abilities は static 1件ちょうど、
  keywords は [speed_attacker] のまま）。
- 補完なし: partial の text は公式全文で、登録後の
  text も公式全文と完全一致を照合済み。
- split はキーワードのみ定型所有で part[2] は空
  ＝ツール側ブロッカーなし。
- alias 畳み込み0件（alias 無し。対象 id を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1190 の notes 内参照のみ〕、identity
  実測で canon_id は対象自身）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔turn_count_cost_reduction〕の出力は
  対象1件ちょうど＝巻き込みなし）。
- converted 10,398→10,399 / rejects
  1,913→1,912、canonical 重なり0・漏れ0。
  turn_count_cost_reduction は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第419弾本体と同形（対象を proto T1190 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T277（火・コスト2バニラ＝
召喚役／マナ役）/ T962（火・コスト2ドロー呪文＝
詠唱役）/ T538（火・コスト2復活呪文＝「出す」は
召喚でないことの判別役）。
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
from tests.test_vocab_pilot419 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex14-054"
GAP = "turn_count_cost_reduction"
NAME = "捧程者 アコギエレキ"


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


def test_round454_disposition():
    rej = _reject_rows()
    assert len(rej) == 1912
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10399
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は登録で解消
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 5 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["ムートピア", "美孔麗王国"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は static
    # 1件ちょうど、keywords は [speed_attacker] のまま
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["speed_attacker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 2   # static 1件＋キーワード展開1件
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第419弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")] if "yes" in keys
                 else list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _hand_cid(e, player=0, defn=TARGET):
    return next(c for c in e.zlist("hand", player)
                if e.s.cards[c].defn == defn)


def _pay(e, player=0):
    return e.chars_ro(_hand_cid(e, player))["pay_cost"]


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _main(e, player, play=None):
    """player の main まで進める。play があればその key を
    選んで解決し、次の main まで進めてから選択肢キーを返す。"""
    for _ in range(900):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == player:
            if play is not None:
                assert play in keys, f"{play} not in {keys}"
                e.answer([keys.index(play)])
                play = None
                continue
            return keys
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        _answer_default(e, d)
    raise AssertionError("main not reached")


def _settle(e, done):
    """done() になるまで受動的に進める（第412弾の作法）。"""
    for _ in range(600):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        _answer_default(e, d)
    return done()


def test_pay_cost_progression_and_floor(rules):
    # 登録カード自身で判別: 素のコスト5 → 召喚1回で3 →
    # 詠唱1回で1（合計2件×-2）→ さらに召喚1回（合計
    # 3件）でも下限1で止まる。最後に軽減後の1コストで
    # 実際に召喚できることも確認する。
    e = _build(rules,
               {"hand": [TARGET, "T277", "T277", "T962"],
                "mana": ["T277"] * 10},
               {})
    _main(e, 0)
    assert _pay(e) == 5
    _main(e, 0, play="play:T277")
    assert e.s.turn_counters.get("hist:summon:0", 0) == 1
    assert _pay(e) == 3
    _main(e, 0, play="play:T962")
    assert e.s.turn_counters.get("hist:cast:0", 0) == 1
    assert _pay(e) == 1
    _main(e, 0, play="play:T277")
    assert e.s.turn_counters.get("hist:summon:0", 0) == 2
    assert _pay(e) == 1          # 合計3件×-2=6 → 下限1
    tapped_before = _tapped_mana(e, 0)
    keys = _main(e, 0)
    assert f"play:{TARGET}" in keys
    e.answer([keys.index(f"play:{TARGET}")])
    assert _settle(e, lambda: any(e.s.cards[c].defn == TARGET
                                  for c in e.zlist("bz", 0)))
    assert _tapped_mana(e, 0) == tapped_before + 1   # 支払いは1だけ


def test_put_is_not_summon(rules):
    # 効果で墓地から「出す」（reason: put）は召喚ではない:
    # T538 の復活では詠唱ぶん（-2）だけが数えられ、
    # 出したクリーチャーぶんは数えられない（5→3）。
    e = _build(rules,
               {"hand": [TARGET, "T538"], "graveyard": ["T277"],
                "mana": ["T277"] * 6},
               {})
    _main(e, 0)
    assert _pay(e) == 5
    _main(e, 0, play="play:T538")
    assert any(e.s.cards[c].defn == "T277" for c in e.zlist("bz", 0))
    assert e.s.turn_counters.get("hist:cast:0", 0) == 1
    assert e.s.turn_counters.get("hist:summon:0", 0) == 0
    assert _pay(e) == 3


def test_opponent_actions_do_not_count(rules):
    # 相手の召喚は owner: you の数えに入らない:
    # 相手が1体召喚した後でも自分の登録カードは
    # 素のコスト5。
    e = _build(rules,
               {"hand": [TARGET], "mana": ["T277"] * 3},
               {"hand": ["T277"], "mana": ["T277"] * 3})
    keys = _main(e, 1)
    assert "play:T277" in keys
    e.answer([keys.index("play:T277")])
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T277"
                                  for c in e.zlist("bz", 1)))
    recorded = (e.s.turn_counters.get("hist:summon:1", 0)
                + e.s.prev_counters.get("hist:summon:1", 0))
    assert recorded == 1                     # 相手の召喚は記録された
    assert e.s.turn_counters.get("hist:summon:0", 0) == 0
    assert e.s.prev_counters.get("hist:summon:0", 0) == 0
    assert _pay(e, 0) == 5
