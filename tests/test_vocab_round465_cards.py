"""再変換ラウンド465（第430弾
infinity_power_attacker）の記録テスト。

- 新規登録1件: dmr09-v02 武闘将軍 カツキング
  （partial の骨格〔クリーチャー / 火 / コスト8 /
  パワー11000 / 種族 アウトレイジMAX、mana 1、
  text 公式全文〕に abilities 8件〔CIP 誘発
  （modify {allow: [attack_creature, other:
  {tapped: false}]}, duration: end_of_turn）／
  battle_win 誘発（break {count: 1, player:
  opp}）／ドロン・ゴー誘発（may [move {select:
  {zone: hand, owner: you, filter: {name_has:
  武闘, types: [exile_creature]}, count: 1},
  to: bz, reason: put}]）／deny 静的効果5件
  （hand / graveyard / mana / deck / shield、
  同 filter＋if {not: {exists: {zone: [hand,
  bz], owner: you, filter: {name_has:
  チーム・エグザイル}}}}、mod {deny:
  [enter_bz]}）〕を並べ、unsupported を外した
  もの。登録形は提出形と完全一致〔source 以外の
  全フィールドを照合〕、abilities は8件
  ちょうど、types [creature, exile_creature]、
  keywords [speed_attacker, double_breaker,
  infinite_power_attacker]）。
- 補完・修正あり: types への exile_creature
  追加＋keywords への infinite_power_attacker
  追加（unsupported 解消分はこれのみ）＋
  ドロン・ゴーと deny 5件の filter を partial の
  races [アウトレイジMAX] 代理から登録先例
  dmd11-001 / dmd11-005 の {name_has: 武闘,
  types: [exile_creature]} へ修正（代理は同値で
  ないことを第430弾で実測）＋deny 5件に
  チーム・エグザイル無視の if を追加。text は
  補完なし＝公式全文で、登録後の全文一致も
  照合済み。
- alias 畳み込み0件（alias 無し。正本判定は
  通常型で対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1209 の
  notes 内参照のみ〕、identity 実測で canon_id
  は対象自身、aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔infinity_power_attacker〕の出力は
  対象1件ちょうど＝巻き込みなし。split は
  キーワードのみ定型所有で part[2] は空）。
- converted 10,410→10,411 / rejects
  1,901→1,900、canonical 重なり0・漏れ0。
  infinity_power_attacker は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第430弾本体と同形（対象を proto T1209 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1210（《武闘》名エグザイル）/
T1211（《武闘》名・非エグザイル）/ T736
（チーム・エグザイル）/ T763（パワー99999
ブロッカー）/ T1207（火マナ役）/ T011（自軍
破壊呪文）。バトルゾーンは共有ゾーンなので
対象カードの cid は controller でも絞ること
（第423弾の注意）。
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
from tests.test_vocab_pilot430_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot430 import FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr09-v02"
GAP = "infinity_power_attacker"


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


def test_round465_disposition():
    rej = _reject_rows()
    assert len(rej) == 1900
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10411
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 8      # abilities 8件ちょうど
    assert c["types"] == ["creature", "exile_creature"]
    assert c["keywords"] == ["speed_attacker", "double_breaker",
                             "infinite_power_attacker"]
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    assert d.types == ["creature", "exile_creature"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第430弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(zone, p))


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif d["kind"] == "pay_mana":
        e.answer([0])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _play_once(defn, seen):
    def play(e, d):
        keys = _keys(d)
        if f"play:{defn}" in keys and seen["n"] < 1:
            seen["n"] += 1
            return [keys.index(f"play:{defn}")]
        return None
    return play


def _battle_vs_99999(rules, attacker):
    """attacker でプレイヤーを攻撃し、T763 にブロックさせる。"""
    e = _build(rules, {"bz": [attacker]}, {"bz": ["T763"]})
    st = {"attacked": False}
    for _ in range(800):
        if st["attacked"] and len(e.zlist("shield", 1)) < 5:
            break
        if attacker in _defns(e, "graveyard", 0):
            break
        if "T763" in _defns(e, "graveyard", 1):
            break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "attack" and not st["attacked"] \
                and f"attack:{attacker}:player" in keys:
            e.answer([keys.index(f"attack:{attacker}:player")])
            st["attacked"] = True
            continue
        if d["kind"] == "block":
            hit = [i for i, k in enumerate(keys)
                   if k.startswith("bz:T763")]
            if hit:
                e.answer([hit[0]])
                continue
        _answer_default(e, d)
    return e, st


def test_infinite_power_beats_99999_and_breaks(rules):
    """パワー99999 のブロッカーにブロックされても ∞ のため
    バトルに勝ち（T763 は破壊され、登録カードは残る）、
    バトル勝利誘発でシールドを1枚ブレイクする。"""
    e, st = _battle_vs_99999(rules, TARGET)
    for _ in range(200):
        if len(e.zlist("shield", 1)) == 4:
            break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        _answer_default(e, d)
    assert st["attacked"]
    assert "T763" in _defns(e, "graveyard", 1)
    assert TARGET in _defns(e, "bz", 0)
    assert len(e.zlist("shield", 1)) == 4


def test_attack_untapped_only_on_entry_turn(rules):
    """召喚したターン: アンタップ状態の相手クリーチャー
    （T1211）への攻撃が選択肢に出る。次の自分のターン:
    出ない（プレイヤーへの攻撃は出る）。"""
    e = _build(rules, {"hand": [TARGET], "mana": ["T1207"] * 8},
               {"bz": ["T1211"]})
    seen = {"n": 0, "steps": []}
    play = _play_once(TARGET, seen)
    for _ in range(1200):
        if len(seen["steps"]) >= 2:
            break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "main":
            ans = play(e, d)
            if ans is not None:
                e.answer(ans)
                continue
        if d["kind"] == "attack" and d.get("player") == 0 \
                and f"attack:{TARGET}:player" in keys:
            seen["steps"].append(list(keys))
            e.answer([keys.index("pass")])
            continue
        _answer_default(e, d)
    assert seen["n"] == 1
    assert len(seen["steps"]) == 2
    first, second = seen["steps"]
    assert f"attack:{TARGET}:T1211" in first       # 出たターン: 可
    assert f"attack:{TARGET}:T1211" not in second  # 次のターン: 不可
    assert f"attack:{TARGET}:player" in second


def _destroy_own_then_doron(rules, hand):
    """T011 で自軍の登録カードを破壊し、ドロン・ゴーを解決する。"""
    e = _build(rules, {"bz": [TARGET], "hand": hand,
                       "mana": ["T1207"] * 2}, {"bz": []})
    seen = {"n": 0, "may": False, "doron_opts": None, "post": 0}
    play = _play_once("T011", seen)
    for _ in range(800):
        if TARGET in _defns(e, "graveyard", 0):
            seen["post"] += 1
            if seen["may"] and seen["post"] > 3:
                break
            if seen["post"] > 40:
                break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "main":
            ans = play(e, d)
            if ans is not None:
                e.answer(ans)
                continue
        if d["kind"] == "choose_cards":
            defns = [e.s.cards[o["cid"]].defn for o in d["options"]]
            if TARGET in defns and TARGET in _defns(e, "bz", 0):
                e.answer([defns.index(TARGET)])  # T011 の破壊対象
                continue
            if defns:
                seen["doron_opts"] = defns       # ドロン・ゴーの候補
                if "T1210" in defns:
                    e.answer([defns.index("T1210")])
                    continue
            e.answer(list(range(d.get("min", 0))))
            continue
        if d["kind"] == "yes_no":
            seen["may"] = True
            e.answer([0])  # may は「はい」
            continue
        _answer_default(e, d)
    return e, seen


def test_doron_go_chooses_only_exile(rules):
    """破壊された時、手札の《武闘》名エグザイル（T1210）
    だけが候補になり、非エグザイルの T1211 は候補に
    出ない（types フィルタの判別。代理フィルタでは
    T1211 も出てしまう）。"""
    e, seen = _destroy_own_then_doron(
        rules, ["T1210", "T1210", "T1211", "T011"])
    assert seen["n"] == 1 and seen["may"]
    assert seen["doron_opts"] == ["T1210", "T1210"]
    assert "T1210" in _defns(e, "bz", 0)
    assert "T1211" in _defns(e, "hand", 0)
    assert TARGET in _defns(e, "graveyard", 0)


def _play_keys(e, p=0):
    return [o["key"] for o in e._play_options(p)]


def test_restriction_discrimination(rules):
    """登録カードが場にいる間、《武闘》名エグザイル
    （T1210）は召喚できないが、非エグザイルの T1211 は
    召喚できる（types フィルタの判別）。2枚目の同名
    自身も「他の」にあたるため出せない。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1210", "T1211"],
                       "mana": ["T1207"] * 8}, {"bz": []})
    keys = _play_keys(e)
    assert "play:T1210" not in keys
    assert "play:T1211" in keys
    e2 = _build(rules, {"bz": [TARGET], "hand": [TARGET],
                        "mana": ["T1207"] * 8}, {"bz": []})
    assert f"play:{TARGET}" not in _play_keys(e2)


def test_restriction_lifted_by_team_exile(rules):
    """チーム・エグザイル（T736）が手札にあれば制限は
    働かない（deny 5件の if の判別）。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1210", "T736"],
                       "mana": ["T1207"] * 8}, {"bz": []})
    assert "play:T1210" in _play_keys(e)
