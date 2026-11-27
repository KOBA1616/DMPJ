"""再変換ラウンド476（第442弾 destroy_attack_target_without_battle）の記録テスト。

- 新規登録1件: dm20-028 エンドブリンガー・ドラグーン
  （提出形は partial〔クリーチャー / 闇 / コスト3 /
  パワー2000 / 種族 ティラノ・ドレイク、mana 1、
  keywords 無し、text は公式全文の内容だが改行が
  空白に潰れた形〕に第442弾の確立形 abilities 2件
  〔(1) trigger {when: {event: attack, subject:
  self, target: creature}, effect: [destroy
  {select: {ref: event.target}}]}、(2) trigger
  {when: {event: attack, target: self}, effect:
  [destroy {select: {ref: self}}]}〕を足し、
  unsupported を外したもの。登録形は提出形と完全
  一致〔source 以外の全フィールドを照合〕、
  abilities は trigger 2件ちょうど、keywords は
  付いていない、text は公式の改行形）。
- 補完あり: abilities（trigger 2件とも。unsupported
  の text は第1条項だけだが第2条項も同一機構で
  text から構築）＋text の改行復元。
- alias 畳み込み0件（alias 無し。正本判定: 対象 id を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1232 の notes 内参照のみ〕、identity
  実測で canon_id は対象自身、aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔destroy_attack_target_without_battle〕
  の出力は対象1件ちょうど＝巻き込みなし。
  destroy_attack_target_without_battle は完全解消）。
- converted 10,421→10,422 / rejects 1,890→1,889、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ
  （第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第442弾本体と同形（対象を proto T1232 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（パワー2000＝バトルなら
相打ち）/ T004（ブロッカー）/ T008（パワー1000＝
バトルなら負ける攻撃役）/ T163（破壊不能）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402
from tests.test_vocab_pilot442_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot442 import FULL_TEXT, NAME  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm20-028"
GAP = "destroy_attack_target_without_battle"


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


def test_round476_disposition():
    rej = _reject_rows()
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 2      # abilities は trigger 2件ちょうど
    assert all(a["kind"] == "trigger" for a in c["abilities"])
    assert "keywords" not in c           # keywords は付いていない
    assert c["text"] == FULL_TEXT        # text は公式の改行形
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    d = parse_card(c, TABLES)
    assert d.name == NAME and d.power == 2000
    assert len(d.abilities) == 2
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第442弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif d["kind"] in ("declare_strigger", "declare_sback"):
        e.answer([])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _drive(e, attacks=(), arrange=None, finish_player=None,
           limit=1500):
    st = {"done": [], "block_offered": False}
    queue = list(attacks)
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if arrange:
            arrange(e, d)
        if not queue and finish_player is not None \
                and d["kind"] == "charge" \
                and d.get("player") == finish_player:
            return st
        if d["kind"] == "block":
            st["block_offered"] = True
        if queue and d["kind"] == "attack" and queue[0] in keys:
            e.answer([keys.index(queue[0])])
            st["done"].append(queue.pop(0))
            continue
        _answer_default(e, d)
    raise AssertionError("driver limit reached")


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    # bz は共有ゾーンなのでコントローラーまで見て引く
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == p)


def _zone(e, cid):
    return e.s.cards[cid].zone


def _tap_on_opp_turn(e, p, defn):
    def arrange(eng, d):
        if eng.s.active == p and d["kind"] in ("charge", "main"):
            for c in eng.zlist("bz", p):
                if eng.s.cards[c].defn == defn \
                        and eng.s.cards[c].controller == p:
                    eng.s.cards[c].tapped = True
    return arrange


def test_clause1_destroys_target_and_no_battle(rules):
    """登録カード（2000）がタップした T001（2000）を
    攻撃: 宣言時に T001 が破壊され、バトルは行われ
    ない。バトルなら相打ちのため、登録カードが場に
    残ることが判別になる。シールドも割れない。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T001"]})
    src = _cid(e, 0, TARGET)
    tgt = _cid(e, 1, "T001")
    st = _drive(e, attacks=[f"attack:{TARGET}:T001"],
                arrange=_tap_on_opp_turn(e, 1, "T001"),
                finish_player=1)
    assert st["done"] == [f"attack:{TARGET}:T001"]
    assert _zone(e, tgt) == "graveyard"
    assert _zone(e, src) == "bz"
    assert e.s.cards[src].tapped
    assert len(e.zlist("shield", 1)) == 5


def test_clause1_block_window_never_opens(rules):
    """攻撃先が宣言時に破壊されればブロック宣言自体が
    起きない: 相手のブロッカー T004 はアンタップの
    まま。"""
    e = _build(rules, {"bz": [TARGET]},
               {"bz": ["T001", "T004"]})
    src = _cid(e, 0, TARGET)
    tgt = _cid(e, 1, "T001")
    blk = _cid(e, 1, "T004")
    st = _drive(e, attacks=[f"attack:{TARGET}:T001"],
                arrange=_tap_on_opp_turn(e, 1, "T001"),
                finish_player=1)
    assert st["done"] == [f"attack:{TARGET}:T001"]
    assert _zone(e, tgt) == "graveyard"
    assert not st["block_offered"]
    assert not e.s.cards[blk].tapped
    assert _zone(e, src) == "bz"


def test_clause1_indestructible_target_battle_proceeds(rules):
    """破壊不能の T163（3000）が攻撃先なら破壊は通らず
    バトルが通常どおり行われる（cancel_attack を
    併記していないことの判別）: 登録カード（2000）は
    バトルで負けて破壊され、T163 は場に残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T163"]})
    src = _cid(e, 0, TARGET)
    tgt = _cid(e, 1, "T163")
    st = _drive(e, attacks=[f"attack:{TARGET}:T163"],
                arrange=_tap_on_opp_turn(e, 1, "T163"),
                finish_player=1)
    assert st["done"] == [f"attack:{TARGET}:T163"]
    assert _zone(e, tgt) == "bz"
    assert _zone(e, src) == "graveyard"


def test_clause1_player_attack_breaks_normally(rules):
    """プレイヤーを攻撃する時は第1条項は発火せず、
    通常どおりシールドを1枚ブレイクする。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    src = _cid(e, 0, TARGET)
    st = _drive(e, attacks=[f"attack:{TARGET}:player"],
                finish_player=1)
    assert st["done"] == [f"attack:{TARGET}:player"]
    assert len(e.zlist("shield", 1)) == 4
    assert _zone(e, src) == "bz"
    assert e.zlist("graveyard", 0) == []
    assert e.zlist("graveyard", 1) == []


def test_clause2_destroys_self_and_attacker_survives(rules):
    """T008（1000）がタップした登録カード（2000）を
    攻撃: 宣言時に登録カードが自身を破壊し、バトルは
    行われない。バトルなら T008 が負けるため、T008 が
    場に残ることが判別になる。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T008"]})
    src = _cid(e, 0, TARGET)
    atk = _cid(e, 1, "T008")
    st = _drive(e, attacks=[f"attack:{TARGET}:player",
                            f"attack:T008:{TARGET}"],
                finish_player=0)
    assert st["done"] == [f"attack:{TARGET}:player",
                          f"attack:T008:{TARGET}"]
    assert _zone(e, src) == "graveyard"
    assert _zone(e, atk) == "bz"
    assert e.s.cards[atk].tapped
    assert len(e.zlist("shield", 0)) == 5


def test_clause2_not_fired_when_player_attacked(rules):
    """相手がプレイヤーを攻撃しても第2条項は発火
    しない: 登録カードは場に残り、シールドが1枚
    ブレイクされる。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T008"]})
    src = _cid(e, 0, TARGET)
    st = _drive(e, attacks=["attack:T008:player"],
                finish_player=0)
    assert st["done"] == ["attack:T008:player"]
    assert _zone(e, src) == "bz"
    assert len(e.zlist("shield", 0)) == 4


def test_mirror_clause1_destroys_defending_copy(rules):
    """相打ち形の相互作用: 相手の登録カードが自分の
    タップした登録カードを攻撃すると、第1条項で
    防御側が破壊され攻撃は終わる。攻撃側は場に残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": [TARGET]})
    mine = _cid(e, 0, TARGET)
    theirs = _cid(e, 1, TARGET)
    st = _drive(e, attacks=[f"attack:{TARGET}:player",
                            f"attack:{TARGET}:{TARGET}"],
                finish_player=0)
    assert st["done"] == [f"attack:{TARGET}:player",
                          f"attack:{TARGET}:{TARGET}"]
    assert _zone(e, mine) == "graveyard"
    assert _zone(e, theirs) == "bz"
    assert len(e.zlist("shield", 0)) == 5
