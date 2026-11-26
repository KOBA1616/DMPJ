"""再変換ラウンド462（第427弾 turn_history_attacked）の
記録テスト。

- 新規登録1件: dmd27-016 轟速 ザ・ゼット
  （partial の骨格〔クリーチャー / 火 / コスト4 /
  パワー7000 / 種族 ソニック・コマンド/侵略者、
  mana 1、keywords [speed_attacker, double_breaker]、
  text 公式全文〕に ability 1件〔trigger {when:
  {event: turn_end, player: you}, if: {cmp:
  [{turn_count: {kind: attack_by, ref: self}},
  ">=", 1]}, effect: [destroy {select: {ref:
  self}}]}（第427弾のドリフト。attack_by は
  第159・161弾の確立式、turn_end + player: you は
  登録済み dm10-041 の確立形）〕を足し、unsupported
  を外したもの。登録形は提出形と完全一致、abilities
  はこの1件ちょうど、keywords は [speed_attacker,
  double_breaker] のまま）。
- 補完なし（partial の text は公式全文、登録後も
  照合済み）。
- split はキーワードのみ定型所有で part[2] は空
  ＝ツール側ブロッカーなし。
- alias 畳み込み0件（別刷り promoy15-052 は rejects
  に独自行なし、登録エントリの source.aliases に
  のみ収載。正本判定は通常型: 対象 id と別刷りを
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1205 の notes 内参照のみ〕、identity
  実測で canon_id は対象自身、別刷りの canon も
  対象、aliases_for = [promoy15-052]）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔turn_history_attacked〕の出力は対象
  1件ちょうど＝巻き込みなし）。
- converted 10,406→10,407 / rejects
  1,905→1,904、canonical 重なり0・漏れ0。
  turn_history_attacked は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第427弾本体と同形（対象を proto T1205 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（他のクリーチャーだけが
攻撃した時の対照）/ T004（パワー3000ブロッカー）/
T1126（パワー8000ブロッカー）。
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
from tests.test_vocab_pilot427_cards import SUBMIT, TRIGGER  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmd27-016"
ALIAS = "promoy15-052"
GAP = "turn_history_attacked"
NAME = "轟速 ザ・ゼット"
FULL_TEXT = SUBMIT["text"]


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


def test_round462_disposition():
    rej = _reject_rows()
    assert len(rej) == 1904
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10407
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
    # 登録後は abilities が1件ちょうど（trigger 1）・
    # keywords [speed_attacker, double_breaker] のまま
    assert c["abilities"] == [TRIGGER]
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]  # 別刷りは source.aliases のみ
    assert _conv_cache.find(CONVERTED, ALIAS) is None
    d = parse_card(c, TABLES)
    parsed = {"kind": "trigger",
              "when": {"event": "turn_end", "player": "you"},
              "if": {"cmp": [{"turn_count": {"kind": "attack_by",
                                             "ref": "self"}},
                             ">=", 1]},
              "effect": [{"op": "move", "select": {"ref": "self"},
                          "to": "graveyard", "reason": "destroy"}]}
    assert parsed in d.abilities   # destroy は move に正規化される
    assert d.keywords == ["speed_attacker", "double_breaker"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第427弾本体と同形、対象は登録カード） ----------

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


def _drive(e, attacker=None, blocker=None, stop=None, limit=600):
    """attacker（攻撃キー）を一度だけ攻撃させ、blocker
    （proto id）がいればブロックさせる。stop(e) が真に
    なるまで進める。"""
    st = {"attacked": False}
    for _ in range(limit):
        if stop and stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if attacker and not st["attacked"] and d["kind"] == "attack" \
                and attacker in keys:
            e.answer([keys.index(attacker)])
            st["attacked"] = True
            continue
        if d["kind"] == "block" and blocker:
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"bz:{blocker}")]
            if hit:
                e.answer([hit[0]])
                continue
        _answer_default(e, d)
    return st


ATK = f"attack:{TARGET}:player"


def test_attacked_destroyed_at_own_turn_end(rules):
    """攻撃したら自分のターンの終わりに破壊される
    （登録カード自身）。W・ブレイカーでシールドは
    2枚ブレイクする。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    src = _cid(e, 0, TARGET)
    st = _drive(e, attacker=ATK,
                stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[src].zone == "graveyard"
    assert len(e.zlist("shield", 1)) == 3


def test_not_attacked_survives_turn_end(rules):
    """攻撃しなければターンの終わりに破壊されない
    （相手ターンも1巡して自分の攻撃ステップに戻るまで
    場に残る。player: you の判別も兼ねる）。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    src = _cid(e, 0, TARGET)
    seen = {"n": 0}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "attack" and d.get("player") == 0:
            seen["n"] += 1
            if seen["n"] >= 2:   # 自分の2回目の攻撃ステップ
                break
        _answer_default(e, d)
    assert seen["n"] >= 2
    assert e.s.cards[src].zone == "bz"


def test_other_creature_attack_does_not_count(rules):
    """判別: 他の自分のクリーチャーだけが攻撃した場合は
    破壊されない（所有者単位の kind: attack ではなく
    attack_by {ref: self} で数えていることの確認）。"""
    e = _build(rules, {"bz": [TARGET, "T001"]}, {"bz": []})
    src = _cid(e, 0, TARGET)
    seen = {"n": 0}
    st = {"attacked": False}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if not st["attacked"] and d["kind"] == "attack" \
                and "attack:T001:player" in keys:
            e.answer([keys.index("attack:T001:player")])
            st["attacked"] = True
            continue
        if d["kind"] == "attack" and d.get("player") == 0 \
                and st["attacked"]:
            seen["n"] += 1
            if seen["n"] >= 1:   # 次の自分の攻撃ステップ＝1巡した
                break
        _answer_default(e, d)
    assert st["attacked"]
    assert e.s.cards[src].zone == "bz"


def test_blocked_but_won_still_destroyed(rules):
    """ブロックされてバトルに勝っても「攻撃していた」
    ことに変わりはなく、ターンの終わりに破壊される。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T004"]})
    src = _cid(e, 0, TARGET)
    blk = _cid(e, 1, "T004")
    st = _drive(e, attacker=ATK, blocker="T004",
                stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[blk].zone == "graveyard"   # パワー3000はバトルで破壊
    assert e.s.cards[src].zone == "graveyard"   # ターン終了時に破壊
    assert len(e.zlist("shield", 1)) == 5       # ブロックされたので無傷


def test_destroyed_in_battle_stays_graveyard(rules):
    """対照: より強いブロッカーにバトルで破壊された場合は
    その時点で墓地にあり、ターン終了時に二重の処理は
    起きない（場に残らない）。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1126"]})
    src = _cid(e, 0, TARGET)
    st = _drive(e, attacker=ATK, blocker="T1126",
                stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[src].zone == "graveyard"
    assert len(e.zlist("shield", 1)) == 5
