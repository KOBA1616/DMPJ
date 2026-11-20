"""修繕ステージ: 変換済み側の死に形 delayed_trigger
{when: turn_end, duration: during_attack} の是正。

第319弾の発見（変換済み9件の旧近似形は発火しない）の実測センサス:
when.event == turn_end かつ duration == during_attack の
delayed_trigger は **17箇所・16カード**あった（第319弾の9件は
dm26-055 を除き一致。dm26-055 は duration が end_of_turn の別形で、
残り8件＝dmr05-073 / dmr16s-003 / dmr17-004 / dmrp01-009 /
dmrp01-075 / dmrp03-043 / dmrp04s-055 / dmsd05-005 が未報告分）。
during_attack の遅延誘発は攻撃タスク完了時（combat の 510.2 の
_expire）に除去され、turn_end まで残らないため全て発火しない。

カードごとの判定と是正形（本文照合済み）:
- 形A（攻撃誘発 → delayed {attack_end, subject: self}、第319弾）:
  dmex12-094 / dmrp05-074 / dmex14-075 / dmpcd01-r14 /
  dmr16s-003 / dmr17-004 / dmrp01-009 / dmrp01-075 /
  dmrp04s-055 / dmsd05-005 / dmsd06-015（効果は破壊・マナ置き・
  アンタップ・任意タップ＋アンタップ・任意捨て＋ドローの現行どおり）
- 形B（ブロック誘発 → delayed {attack_end, target: self}）:
  dmr05-073（アンタップ）/ dmr06-043（破壊）
- 両形: dmrp08-077（攻撃側＝形A、ブロック側＝形B）
- 監視形: dmrp03-043（自分の他のクリーチャーの攻撃で誘発。
  delayed の when は素の {attack_end}。dmrp03-015 等の登録先例と同形）
- dmpcd01-r14 は本文が「相手プレイヤーを攻撃する時」のため、
  あわせて攻撃誘発の when に target: player を追加した
  （{attack, subject: self, target: player} は登録先例あり）
- dmpcd03-b11 は本文が「バトルする時、バトルの後」で、このカードは
  攻撃できない。旧形は攻撃誘発で代表させていたため二重に発火不能
  だった。第211弾の battle_end 誘発 {when: {event: battle_end,
  subject: self}} → destroy self に置き換えた（delayed は残らない）
- dm26-055 は同系の別形（when turn_end / duration end_of_turn）:
  発火はするがターンの終わりで、「その攻撃の後」とずれていた。
  形A（when attack_end / subject self、duration during_attack）に是正

類似パターンの報告（本ステージでは是正しない）:
- dm25sp1-004 は attack 誘発 → delayed {turn_end, end_of_turn} で
  「攻撃の終わりに」をターンの終わりで近似する同系の別形。
  本ステージの対象（第319弾の報告9件＋実測の during_attack 群）
  には含めず、別ステージ送りとして記録する。
- 他の {turn_end, end_of_turn} 群（dm25ex3-td08 等10件）は本文が
  いずれも「このターンの終わりに」で、遅延形として正しい。無変更。
- delayed {when: break / battle_win, duration: during_attack} 群は
  攻撃中に起きるイベントを待つ形で正しい。無変更。

converted 10,262 / rejects 2,055 は不変（件数の増減なし）。

プロトテストとは別プロセスで実行すること（conftest の
DMSIM_SKIP_CONVERTED 復活の汚染回避のため tests.conftest は
import しない）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

FORM_A = ["dmex12-094", "dmrp05-074", "dmex14-075", "dmpcd01-r14",
          "dmr16s-003", "dmr17-004", "dmrp01-009", "dmrp01-075",
          "dmrp04s-055", "dmsd05-005", "dmsd06-015", "dm26-055"]
FORM_B = ["dmr05-073", "dmrp08-077"]        # 077 はブロック側のみ形B
FORM_B_DESTROY = ["dmr06-043"]
WATCHER = ["dmrp03-043"]
BATTLE_END = ["dmpcd03-b11"]
ALL_FIXED = FORM_A + FORM_B + FORM_B_DESTROY + WATCHER + BATTLE_END


def _delayed(card):
    out = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("op") == "delayed_trigger":
                out.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(card.get("abilities"))
    return out


def _byid():
    cards = _conv_cache.all_cards(CONVERTED)
    return cards, {c["id"]: c for c in cards}


def test_disposition_counts_and_forms():
    rej = [json.loads(l) for l in open(REJECTS, encoding="utf-8") if l.strip()]
    assert len(rej) == 2055
    cards, byid = _byid()
    assert len({c["id"] for c in cards}) == 10262
    # 死に形は converted 全体から消えている
    for c in cards:
        for d in _delayed(c):
            assert not (d.get("when", {}).get("event") == "turn_end"
                        and d.get("duration") == "during_attack"), c["id"]
    # 形A: delayed の when は {attack_end, subject: self}、duration は during_attack
    for cid in FORM_A:
        ds = _delayed(byid[cid])
        assert len(ds) == 1, cid
        assert ds[0]["when"] == {"event": "attack_end", "subject": "self"}, cid
        assert ds[0]["duration"] == "during_attack", cid
        parse_card(byid[cid], TABLES)
    # 形B（ブロック側）: {attack_end, target: self}
    for cid in FORM_B + FORM_B_DESTROY:
        ds = [d for d in _delayed(byid[cid])
              if d["when"] == {"event": "attack_end", "target": "self"}]
        assert len(ds) == 1, cid
        parse_card(byid[cid], TABLES)
    # ツリドンは攻撃側＝形A・ブロック側＝形B の2件
    ds = _delayed(byid["dmrp08-077"])
    assert len(ds) == 2
    assert {"event": "attack_end", "subject": "self"} in [d["when"] for d in ds]
    assert {"event": "attack_end", "target": "self"} in [d["when"] for d in ds]
    # 監視形: 素の {attack_end}
    ds = _delayed(byid["dmrp03-043"])
    assert len(ds) == 1 and ds[0]["when"] == {"event": "attack_end"}
    # dmpcd01-r14: 攻撃誘発が target: player で限定されている
    trig = [a for a in byid["dmpcd01-r14"]["abilities"]
            if a.get("kind") == "trigger"
            and a.get("when", {}).get("event") == "attack"]
    assert len(trig) == 1
    assert trig[0]["when"] == {"event": "attack", "subject": "self",
                               "target": "player"}
    # dmpcd03-b11: delayed は無く battle_end 誘発に置き換わっている
    c = byid["dmpcd03-b11"]
    assert _delayed(c) == []
    be = [a for a in c["abilities"] if a.get("kind") == "trigger"
          and a.get("when", {}).get("event") == "battle_end"]
    assert len(be) == 1
    assert be[0]["when"] == {"event": "battle_end", "subject": "self"}
    parse_card(c, TABLES)
    # 類似パターン dm25sp1-004 は本ステージでは是正しない（記録のみ）
    ds = _delayed(byid["dm25sp1-004"])
    assert len(ds) == 1
    assert ds[0]["when"] == {"event": "turn_end"}
    assert ds[0]["duration"] == "end_of_turn"


# ---------- 実挙動ドライバ ----------

def _defns(e, zone, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(zone, p)
                  if e.s.cards[c].controller == p)


def _card(e, defn, p):
    for c in e.zlist("bz", p):
        card = e.s.cards[c]
        if card.defn == defn and card.controller == p:
            return card
    return None


def _drive(e, stop, attack=None, block=None, steps=1500):
    """attack: (player, defn, target) target は "player" か対象 defn。
    block: (player, defn)。stop(e, d, state) が真になった決定は
    回答せずに返す（その時点のゾーン状態を検証する）。
    build() のゲームでは「攻撃後に何もすることがない」場合メイン
    決定自体が現れないため、各テストは攻撃側にマナと手札を持たせ、
    攻撃後のメイン決定（同じターン内）で止める。"""
    state = {"attacked": False, "blocked": False}
    for _ in range(steps):
        d = e.advance()
        assert d is not None, "game ended"
        if stop(e, d, state):
            return state
        kind = d["kind"]
        pl = d.get("player")
        keys = [o["key"] for o in d["options"]]
        if kind == "attack" and attack and pl == attack[0] \
                and not state["attacked"]:
            want = f"attack:{attack[1]}:{attack[2]}"
            if want in keys:
                e.answer([keys.index(want)])
                state["attacked"] = True
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = []
            if block and pl == block[0]:
                hit = [i for i, k in enumerate(keys)
                       if k.startswith(f"bz:{block[1]}:")]
            if hit:
                e.answer([hit[0]])
                state["blocked"] = True
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "choose_cards":
            e.answer([] if d.get("min", 0) == 0
                     else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("drive budget exhausted")


def _after_own_attack(e, d, state):
    return state["attacked"] and d["kind"] == "main" and d.get("player") == 0


def _after_block(e, d, state):
    return state["blocked"] and d["kind"] == "main" and d.get("player") == 1


def _next_attack_decision(attacker_player):
    """タイミング判別用チェックポイント: このエンジンのターン構造は
    チャージ→メイン→攻撃ステップ→ターン終了で、攻撃後に同一ターンへ
    戻るメイン決定が無い。そのため「攻撃の後（attack_end）」と
    「ターンの終わり（turn_end）」を区別するには、同じ攻撃ステップ内
    の2体目の攻撃決定（attack_end 処理後・turn_end 処理前）で止める。"""
    def stop(e, d, state):
        return (state["attacked"] or state["blocked"]) \
            and d["kind"] == "attack" and d.get("player") == attacker_player
    return stop


MANA2 = ["T002", "T002"]     # 攻撃後のメイン決定を出現させるための手札＋マナ


def _game(rules, p0bz, p1bz, p0mana=(), p1mana=()):
    return build(rules, {"p0": {"bz": p0bz, "mana": list(p0mana)},
                         "p1": {"bz": p1bz, "mana": list(p1mana)},
                         "filler": "T002", "seed": 1})


# ---------- 形A: 攻撃の後に破壊 ----------

def test_form_a_destroy_after_attack(rules):
    """dmex12-094（形A）: 攻撃すると攻撃の後に破壊される。
    修繕前は死に形のため場に残り続け、この検証は失敗していた。"""
    e = _game(rules, ["dmex12-094"], [], p0mana=MANA2)
    st = _drive(e, _after_own_attack, attack=(0, "dmex12-094", "player"))
    assert st["attacked"]
    assert "dmex12-094" in _defns(e, "graveyard", 0)
    assert "dmex12-094" not in _defns(e, "bz", 0)


def test_form_a_move_to_mana_after_attack(rules):
    """dmsd05-005（形A・マナ置き）: 攻撃の後、マナゾーンに置かれる。"""
    e = _game(rules, ["dmsd05-005"], [], p0mana=MANA2)
    st = _drive(e, _after_own_attack, attack=(0, "dmsd05-005", "player"))
    assert st["attacked"]
    assert "dmsd05-005" in _defns(e, "mana", 0)
    assert "dmsd05-005" not in _defns(e, "bz", 0)


def test_form_a_untap_self_after_attack(rules):
    """dmr16s-003（形A・アンタップ）: 攻撃の後、自身をアンタップする
    （任意タップは辞退）。同一攻撃ステップ内の2体目の攻撃決定で
    止めて判定する（修繕前はその時点でもタップしたままだった）。"""
    e = _game(rules, ["dmr16s-003", "T001"], [], p0mana=MANA2)
    st = _drive(e, _next_attack_decision(0),
                attack=(0, "dmr16s-003", "player"))
    assert st["attacked"]
    card = _card(e, "dmr16s-003", 0)
    assert card is not None
    assert not card.tapped


# ---------- 形B: ブロックの後に破壊／アンタップ ----------

def test_form_b_destroy_after_block(rules):
    """dmr06-043（形B）: ブロックしてバトルに勝っても、バトルの後に
    破壊される。修繕前は場に残り続けた。"""
    e = _game(rules, ["dmr06-043"], ["T001"], p1mana=MANA2)
    st = _drive(e, _after_block, attack=(1, "T001", "player"),
                block=(0, "dmr06-043"))
    assert st["blocked"]
    assert "T001" in _defns(e, "graveyard", 1)
    assert "dmr06-043" in _defns(e, "graveyard", 0)
    assert "dmr06-043" not in _defns(e, "bz", 0)


def test_form_b_untap_after_block(rules):
    """dmr05-073（形B・アンタップ）: ブロックした時、バトルの後に
    アンタップする。相手の2体目の攻撃決定（同じ攻撃ステップ内）で
    止めて判定する（修繕前はその時点でもタップしたままだった）。"""
    e = _game(rules, ["dmr05-073"], ["T001", "T007"], p1mana=MANA2)
    st = _drive(e, _next_attack_decision(1), attack=(1, "T001", "player"),
                block=(0, "dmr05-073"))
    assert st["blocked"]
    card = _card(e, "dmr05-073", 0)
    assert card is not None
    assert not card.tapped


def test_tsuridon_both_forms(rules):
    """dmrp08-077（両形）: 攻撃してもブロックしても、その攻撃の後で
    破壊される。"""
    e = _game(rules, ["dmrp08-077"], [], p0mana=MANA2)
    st = _drive(e, _after_own_attack, attack=(0, "dmrp08-077", "player"))
    assert st["attacked"]
    assert "dmrp08-077" in _defns(e, "graveyard", 0)

    e = _game(rules, ["dmrp08-077"], ["T001"], p1mana=MANA2)
    st = _drive(e, _after_block, attack=(1, "T001", "player"),
                block=(0, "dmrp08-077"))
    assert st["blocked"]
    assert "dmrp08-077" in _defns(e, "graveyard", 0)
    assert "dmrp08-077" not in _defns(e, "bz", 0)


# ---------- 監視形・battle_end・タイミング・限定 ----------

def test_watcher_destroyed_at_ally_attack_end(rules):
    """dmrp03-043（監視形）: 自分の他のクリーチャーが攻撃する時、
    その攻撃の終わりにこのクリーチャーを破壊する。攻撃した
    クリーチャー自身は残る。修繕前は発火しなかった。"""
    e = _game(rules, ["dmrp03-043", "T001"], [], p0mana=MANA2)
    st = _drive(e, _after_own_attack, attack=(0, "T001", "player"))
    assert st["attacked"]
    assert "dmrp03-043" in _defns(e, "graveyard", 0)
    assert "T001" in _defns(e, "bz", 0)


def test_b11_destroyed_after_battle(rules):
    """dmpcd03-b11（battle_end 形）: 攻撃できないこのクリーチャーが
    ブロックしてバトルに勝つと、バトルの後に破壊される。
    修繕前は攻撃誘発で代表されていたため発火しなかった。"""
    e = _game(rules, ["dmpcd03-b11"], ["T001"], p1mana=MANA2)
    st = _drive(e, _after_block, attack=(1, "T001", "player"),
                block=(0, "dmpcd03-b11"))
    assert st["blocked"]
    assert "T001" in _defns(e, "graveyard", 1)
    assert "dmpcd03-b11" in _defns(e, "graveyard", 0)
    assert "dmpcd03-b11" not in _defns(e, "bz", 0)


def test_dm26_055_destroyed_at_attack_end_not_turn_end(rules):
    """dm26-055（タイミング是正）: W・ブレイカー付与を選んだ場合、
    ターンの終わりではなく攻撃の直後に破壊される。同一攻撃
    ステップ内の2体目の攻撃決定で止めて判定する（修繕前は
    その時点ではまだ場に残っており、ターンの終わりに落ちた）。"""
    e = _game(rules, ["dm26-055", "T001"], [], p0mana=MANA2)
    st = _drive(e, _next_attack_decision(0),
                attack=(0, "dm26-055", "player"))
    assert st["attacked"]
    assert "dm26-055" in _defns(e, "graveyard", 0)
    assert "dm26-055" not in _defns(e, "bz", 0)
    assert "T001" in _defns(e, "bz", 0)


def test_r14_player_attack_gate(rules):
    """dmpcd01-r14（限定の追加）: 相手プレイヤーを攻撃した時は
    その攻撃の後に破壊されるが、クリーチャーを攻撃した時は
    破壊されない。"""
    e = _game(rules, ["dmpcd01-r14"], [], p0mana=MANA2)
    st = _drive(e, _after_own_attack, attack=(0, "dmpcd01-r14", "player"))
    assert st["attacked"]
    assert "dmpcd01-r14" in _defns(e, "graveyard", 0)

    # 相手の T001 が先に攻撃してタップした後、それを攻撃する
    e = _game(rules, ["dmpcd01-r14"], ["T001"], p0mana=MANA2, p1mana=MANA2)
    _drive(e, lambda e, d, s: e.s.turn >= 3 and d.get("player") == 0,
           attack=(1, "T001", "player"))
    st = _drive(e, _after_own_attack, attack=(0, "dmpcd01-r14", "T001"))
    assert st["attacked"]
    assert "T001" in _defns(e, "graveyard", 1)      # バトルでは勝つ
    assert "dmpcd01-r14" in _defns(e, "bz", 0)      # しかし破壊されない
