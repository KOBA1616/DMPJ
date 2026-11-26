"""再変換ラウンド455（第420弾 does_not_untap）
の記録テスト。

- 新規登録1件: dm22rp1-011 予言者マンプクルト
  （partial の骨格〔クリーチャー / 光 / コスト1 /
  パワー3500 / 種族 ライトブリンガー、mana 1、
  keywords [blocker]〕に第420弾の確立形
  abilities 3件〔(1) static {affects: self, mod:
  {deny: [untap_at_start]}}（第400弾・登録済み
  dmrp06-027 の登録形そのもの）／(2) static
  {affects: self, if: {not: {exists: {zone: bz,
  owner: you, filter: {types: [tamaseed]}}}},
  mod: {deny: [attack_player]}}（登録済み
  dmrp21-072 の同文条項と完全一致）／(3) trigger
  {when: {event: move, to: bz, subject: {owner:
  you, filter: {types: [tamaseed]}}}, effect:
  [untap {select: {ref: self}}]}（登録済み
  dm24rp4-031 の監視誘発の subject をタマシード
  に替えた形、may なし）〕を足し、unsupported を
  外したもの。登録形は提出形と完全一致、abilities
  は3件ちょうど、keywords は [blocker] のまま）。
- 補完なし: partial の text は公式全文で、登録後の
  text も公式全文と完全一致を照合済み。
- split はキーワードのみ定型所有で part[2] は空
  ＝ツール側ブロッカーなし。
- alias 畳み込み0件（alias 無し。対象 id を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1191 の notes 内参照のみ〕、identity
  実測で canon_id は対象自身）。
- stale クリーンアップ0件・差し戻し1件:
  reopen（does_not_untap）の出力は2件で、
  ファミリーの残り1件 dm25ex2-031（形が異なる
  ため対象外）は unsupported を残した partial の
  まま差し戻し、行全体が HEAD と同一であることを
  照合済み。does_not_untap は完全解消しない
  （残り1件）。
- converted 10,399→10,400 / rejects
  1,912→1,911、canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第420弾本体と同形（対象を proto T1191 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T506（自然・コスト2タマシード
＝第3条項の発生源役）/ T001（自然バニラ＝対照役・
クリーチャー参入役・マナ役）/ T030（光水の多色＝
光マナ役）。
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
from tests.test_vocab_pilot420 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm22rp1-011"
BOUNCE = "dm25ex2-031"
GAP = "does_not_untap"
NAME = "予言者マンプクルト"


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


def test_round455_disposition():
    rej = _reject_rows()
    assert len(rej) == 1911
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10400
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == [BOUNCE]               # ファミリーは解消しない
    brow = rej[BOUNCE]                   # 差し戻し行は HEAD と不変
    assert brow["gaps"] == [GAP] and brow["reason"] == "vocab"
    assert brow["partial"]["source"]["unsupported"] == [
        {"need": GAP, "text": "アンタップしない"}]
    assert brow["partial"]["keywords"] == ["quad_breaker"]
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 1 and c["power"] == 3500 and c["mana"] == 1
    assert c["races"] == ["ライトブリンガー"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は3件
    # ちょうど、keywords は [blocker] のまま
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 3
    assert c["keywords"] == ["blocker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")
    d = parse_card(c, TABLES)
    for ab in FORM:
        assert ab in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第420弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "pay_mana":
        e.answer([0])
    elif d["kind"] == "choose_shields":
        e.answer(list(range(d["min"])))
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _mine(e, defn, player=0):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn)


def _drive(e, script, max_steps=6000):
    state = {}
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if script(e, d, state):
            if state.get("done"):
                return state
            continue
        _answer_default(e, d)
    raise AssertionError(f"script not finished: {state}")


def _attack_flow(e, defn, cid_box):
    """第420弾の共通フロー: 自ターン1: 召喚。自ターン2:
    攻撃してタップしシールドを1枚ブレイク。自ターン3の
    はじめのタップ状態を cid_box['at_turn3'] に記録する。"""
    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 0:
            st["charges"] = st.get("charges", 0) + 1
            if st["charges"] == 3:
                cid_box["at_turn3"] = \
                    e.s.cards[cid_box["cid"]].tapped
                st["done"] = True
                return True
            return False
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("summoned"):
            key = f"play:{defn}"
            assert key in keys, keys
            st["summoned"] = True
            e.answer([keys.index(key)])
            return True
        if st.get("summoned") and "cid" not in cid_box:
            cid_box["cid"] = _mine(e, defn)
            return False
        if d["kind"] == "attack" and d.get("player") == 0 \
                and st.get("summoned") and not st.get("attacked"):
            hit = [k for k in keys
                   if k == f"attack:{defn}:player"]
            if hit:
                st["attacked"] = True
                cid_box["shields_before"] = len(e.zlist("shield", 1))
                e.answer([keys.index(hit[0])])
                return True
            return False
        if st.get("attacked") and not st.get("after_attack"):
            if d["kind"] in ("main", "charge", "attack"):
                st["after_attack"] = True
                assert e.s.cards[cid_box["cid"]].tapped is True
                assert len(e.zlist("shield", 1)) \
                    == cid_box["shields_before"] - 1
                return True
            return False
        return False
    return script


def test_stays_tapped_at_own_turn_start(rules):
    # 第1条項の実フロー（登録カード自身）: タマシードが
    # いるため第2条項の制限は掛からずプレイヤーを攻撃
    # でき、タップした状態で次の自ターンのはじめを
    # 迎えてもアンタップしない。
    e = _build(rules,
               {"bz": ["T506"], "hand": [TARGET],
                "mana": ["T030", "T001", "T001"]},
               {"bz": []})
    cid_box = {}
    _drive(e, _attack_flow(e, TARGET, cid_box))
    assert cid_box["at_turn3"] is True


def test_control_creature_untaps(rules):
    # 対照: deny を持たない通常クリーチャーは同じ
    # フローで自ターン3のはじめにアンタップしている。
    e = _build(rules,
               {"hand": ["T001"],
                "mana": ["T001", "T001", "T001"]},
               {"bz": []})
    cid_box = {}
    _drive(e, _attack_flow(e, "T001", cid_box))
    assert cid_box["at_turn3"] is False


def test_attack_player_denied_without_tamaseed(rules):
    # 第2条項の特性判別（登録カード自身）: 自分の
    # タマシードがなければ attack_player だけが
    # 不許可（attack_creature と block は許可のまま）。
    # タマシードがいれば許可、相手のタマシードでは
    # 許可されない。
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    cid = _mine(e, TARGET)
    assert e.permits(cid, "attack_player") is False
    assert e.permits(cid, "attack_creature") is True
    assert e.permits(cid, "block") is True
    assert e.permits(cid, "untap_at_start") is False
    e2 = _build(rules, {"bz": [TARGET, "T506"]}, {"bz": []})
    cid2 = _mine(e2, TARGET)
    assert e2.permits(cid2, "attack_player") is True
    e3 = _build(rules, {"bz": [TARGET]}, {"bz": ["T506"]})
    cid3 = _mine(e3, TARGET)
    assert e3.permits(cid3, "attack_player") is False


def _play_from_hand(e, player, defn, cid):
    """player の main で defn を出し、解決後に cid の
    タップ状態を返す。"""
    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == player \
                and not st.get("played"):
            key = f"play:{defn}"
            assert key in keys, keys
            st["played"] = True
            e.answer([keys.index(key)])
            return True
        if st.get("played") and any(
                e.s.cards[c].defn == defn
                for c in e.zlist("bz", player)):
            if d["kind"] in ("main", "charge", "attack"):
                st["tapped"] = e.s.cards[cid].tapped
                st["done"] = True
                return True
            return False
        return False
    st = _drive(e, script)
    return st["tapped"]


def test_tamaseed_entry_untaps_self(rules):
    # 第3条項（登録カード自身）: タップ状態の発生源が
    # いる盤面で自分のタマシードが出ると、発生源が
    # アンタップする。
    e = _build(rules,
               {"bz": [TARGET], "hand": ["T506"],
                "mana": ["T001", "T001", "T001"]},
               {"bz": []})
    cid = _mine(e, TARGET)
    e.s.cards[cid].tapped = True   # タップ状態にして観測する
    assert _play_from_hand(e, 0, "T506", cid) is False


def test_creature_entry_does_not_untap(rules):
    # 対照: 自分のクリーチャーが出ても発火しない。
    e = _build(rules,
               {"bz": [TARGET], "hand": ["T001"],
                "mana": ["T001", "T001", "T001"]},
               {"bz": []})
    cid = _mine(e, TARGET)
    e.s.cards[cid].tapped = True
    assert _play_from_hand(e, 0, "T001", cid) is True


def test_opponent_tamaseed_does_not_untap(rules):
    # 対照: 相手のタマシードが出ても発火しない
    # （subject owner: you）。
    e = _build(rules,
               {"bz": [TARGET], "mana": ["T001"]},
               {"hand": ["T506"],
                "mana": ["T001", "T001", "T001"]})
    cid = _mine(e, TARGET)
    e.s.cards[cid].tapped = True
    assert _play_from_hand(e, 1, "T506", cid) is True
