"""ステップ3で足した処理の検証テスト。各テストの docstring に対応する条文を書く。"""
import pytest
from conftest import answer, setup

from dmsim.defs import DefError, load_tables, parse_card
from dmsim.loop import LoopDetector, verify
from dmsim.play import passive_policy


def names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


def keys(d):
    return [o["key"] for o in d["options"]]


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


# ---- 許可・禁止（弱点1: キーワードの直書きをやめた） ----

def test_keywords_are_permissions(rules):
    """ブロッカー・W・ブレイカーはキーワード名ではなく許可と breaks で判定する。"""
    e = setup(rules, {"bz": ["T017"]}, {"bz": ["T004"]})
    assert e.chars(bz(e, 0, "T017"))["breaks"] == 2
    assert e.permits(bz(e, 1, "T004"), "block") and not e.permits(bz(e, 0, "T017"), "block")


def test_cannot_beats_can(rules):
    """101.2「できない」は「できる」に勝つ。dynamic な禁止は後から出たクリーチャーにも及ぶ。"""
    e = setup(rules, {"hand": ["T013"], "mana": ["T004"]},
              {"hand": ["T005", "T001"], "mana": ["T005"] * 3 + ["T001"] * 2})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T013")
    answer(e, "charge", "pass")             # 相手のターン（ドローは飛ばされる）
    answer(e, "main", "play:T005")
    answer(e, "pay_mana", "mana:T005,T005,T005")
    d = e.advance()
    assert d["kind"] == "main" and d["player"] == 1
    c = bz(e, 1, "T005")                     # スピードアタッカーだが、後から出ても攻撃できない
    assert not e.permits(c, "attack_player")
    e.s.continuous[0]["mod"]["allow"] = ["attack_player"]   # 許可を足しても禁止が勝つ
    assert not e.permits(c, "attack_player")
    e.answer([keys(d).index("pass")])
    d = e.advance()                          # 攻撃の選択肢がないので、次は自分のターン
    assert d["player"] == 0 and e.s.continuous == []


def test_granted_keyword_works(rules):
    """付与したキーワード（スピードアタッカー）の常在型能力も働く。"""
    e = setup(rules, {"hand": ["T001", "T014"], "mana": ["T001", "T001", "T005"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T001")
    answer(e, "pay_mana", "mana:T001,T001")
    answer(e, "main", "play:T014")
    d = e.advance()                          # 手札が空なのでメインは自動で終わる
    assert d["kind"] == "attack" and "attack:T001:player" in keys(d)


def test_skip_step(rules):
    """ターン構造はデータ。効果で相手のドローステップを飛ばせる。"""
    e = setup(rules, {"hand": ["T013"], "mana": ["T004"]}, {"hand": ["T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T013")
    hand1 = len(e.zlist("hand", 1))
    d = e.advance()                   # 相手のターン: ドローなしでマナチャージへ
    assert d["kind"] == "charge" and d["player"] == 1
    assert len(e.zlist("hand", 1)) == hand1
    assert e.s.tasks[0]["steps"] == ["start", "charge", "main", "attack", "end"]


# ---- 無視（608.4, 608.5） ----

def test_ignore_first_on_battlezone_wins(rules):
    """608.5 無視し合う時は先にバトルゾーンにあった側の無視が働く。"""
    e = setup(rules, {"bz": ["T015"]}, {"bz": ["T004"]})
    t004 = bz(e, 1, "T004")
    assert not e.permits(t004, "block")            # ブロッカーが無視される
    e._raw_move(e.zlist("hand", 1)[0] if e.zlist("hand", 1) else e.zlist("deck", 1)[0], "graveyard")
    late = next(c for c in e.s.zones["deck"][1])
    e.s.cards[late].defn = "T016"
    e._raw_move(late, "bz", controller=1)
    ign = e._ignored()
    assert late in ign and bz(e, 0, "T015") not in ign


# ---- 進化（801）・再構築（801.4） ----

def test_evolution_and_rebuild(rules):
    e = setup(rules, {"bz": ["T002"], "hand": ["T017"], "mana": ["T001", "T001"]})
    base = bz(e, 0, "T002")
    answer(e, "charge", "pass")
    e.s.cards[base].tapped = True
    answer(e, "main", "play:T017")
    e.advance()
    top = bz(e, 0, "T017")
    assert e.s.cards[top].under == [base] and e.s.cards[top].tapped     # 801.2 タップを引き継ぐ
    assert e.s.cards[top].entered_turn == -1                            # 801.3 召喚酔いしない
    # カードとして一番上だけを手札に戻すと、下のクリーチャーが再構築されて残る
    e.s.waiting = None
    e.s.tasks.append(e._child([{"op": "move", "select": {"ref": "self"}, "to": "hand", "reason": "return",
                                "card_only": True}], {"you": 0, "self": e.s.ref(top), "vars": {}}))
    e.advance()
    assert names(e, "bz", 0) == ["T002"] and e.s.cards[base].top_of == -1
    assert e.s.cards[base].tapped


def test_evolution_needs_source(rules):
    """801.1a 適正な進化元がなければ出せない。"""
    e = setup(rules, {"hand": ["T017"], "mana": ["T001", "T001"]})
    answer(e, "charge", "pass")
    d = e.advance()
    assert "play:T017" not in keys(d)


# ---- ツインパクト（810） ----

def test_twinpact_faces(rules):
    """810.3 どちらの面でも実行できる。呪文側を唱えても墓地では1枚のカード。"""
    e = setup(rules, {"hand": ["T018"], "mana": ["T003", "T003"]}, {"bz": ["T001"]})
    answer(e, "charge", "pass")
    d = e.advance()
    assert "play:T018:1" in keys(d) and "play:T018:0" not in keys(d)   # 火のマナがない
    e.answer([keys(d).index("play:T018:1")])
    e.advance()
    assert names(e, "graveyard", 0) == ["T018"] and names(e, "hand", 1).count("T001") >= 1


def test_twinpact_strigger_and_creature_side(rules):
    e = setup(rules, {"bz": ["T005"]}, {"shield": ["T018"] * 5, "bz": ["T001"]})
    answer(e, "attack", "attack:T005:player")
    e.advance()
    e.answer([0, 1])
    d = e.advance()
    assert d["kind"] == "declare_strigger" and "strigger:T018:1" in keys(d)
    e.answer([0])
    d = e.advance()
    e.advance()                              # 呪文側の効果で攻撃側のクリーチャーを手札へ（候補が1体なので自動）
    assert "T005" in names(e, "hand", 0)
    c = e.zlist("graveyard", 1)[0]
    e._raw_move(c, "bz", controller=1)
    assert e.chars(c)["name"] == "双刃の竜" and e.chars(c)["power"] == 3000   # 810.4 バトルゾーンではクリーチャー側


# ---- 使用宣言（603.2e/f, 506.3）・遅延誘発（603.6） ----

def test_ninja_strike(rules):
    """非ターン・プレイヤーは攻撃の後に宣言して、コストなしで召喚し、ブロックに使える。ターンの終わりに山札の下へ。"""
    e = setup(rules, {"bz": ["T005"]}, {"hand": ["T019"], "mana": ["T001", "T001"]})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "declare_attack" and d["player"] == 1 and keys(d) == ["declare:T019:1"]
    e.answer([0])
    d = e.advance()
    assert d["kind"] == "block" and "bz:T019:0" in keys(d)
    e.answer([keys(d).index("bz:T019:0")])
    d = e.advance()                          # バトル（4000 > 3000）→ ターンの終わり → 相手のターンへ
    assert d["player"] == 1 and names(e, "graveyard", 0) == ["T005"]
    assert names(e, "bz", 1) == [] and e.s.cards[e.zlist("deck", 1)[-1]].defn == "T019"   # 遅延誘発で山札の一番下


def test_ninja_strike_condition(rules):
    """宣言の条件（マナ2枚以上）を満たさなければ宣言できない。"""
    e = setup(rules, {"bz": ["T005"]}, {"hand": ["T019"], "mana": ["T001"]})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "choose_shields"     # 宣言の Decision は出ない


def test_revolution_change_keeps_attack(rules):
    """701.26a 革命チェンジで入れ替わったクリーチャーは攻撃中の状態を引き継ぐ（T・ブレイカーで3枚）。"""
    e = setup(rules, {"bz": ["T005"], "hand": ["T020"]})
    answer(e, "charge", "pass")
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "declare_attack" and d["player"] == 0
    e.answer([0])
    d = e.advance()
    assert d["kind"] == "choose_shields" and d["min"] == 3
    assert names(e, "bz", 0) == ["T020"] and "T005" in names(e, "hand", 0)
    assert e.s.cards[bz(e, 0, "T020")].tapped


def test_delayed_trigger_only_sees_later_events(rules):
    """603.6a 遅延誘発は生成された後のイベントだけを見る。1回で消える。"""
    e = setup(rules, {"hand": ["T022", "T006", "T006"], "mana": ["T008"] + ["T005"] * 6}, {"bz": ["T001", "T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:T022")
    e.advance()
    assert len(e.s.delayed) == 1
    h = len(e.zlist("hand", 0))
    answer(e, "main", "play:T006")
    while (d := e.advance())["kind"] != "main":
        e.answer([0])
    assert len(e.zlist("hand", 0)) == h - 1 + 1 and e.s.delayed == []


# ---- ターンをまたぐロック ----

def test_round_lock_is_detected(rules):
    """毎ターン相手のマナを全部墓地へ → 相手は何もできず山札が先に尽きる（ラウンド周期のロック）。"""
    e = setup(rules, {"bz": ["T021"]}, {}, deck_left=[30, 12])
    det = LoopDetector(me=0, period="round", hand_keys=set())
    cert = None
    for _ in range(4000):
        d = e.advance()
        if d is None:
            break
        if d["player"] == 0 and d["kind"] == "charge":
            cert = det.observe(e)
            if cert:
                break
        if d["kind"] == "charge" and d["player"] == 1:
            e.answer([0])          # 相手はマナを置き続ける（毎ターン墓地に送られる）
        else:
            e.answer(passive_policy(e, d))
    assert cert is not None and cert.period == "round"
    assert cert.delta["deck:1"] == -1 and cert.win_by == "opp_deck_out"
    v = verify(e, cert, times=2)
    assert v.verified == 2, v.notes


# ---- 型（弱点2）: LLM 変換データの機械チェック ----

def test_unknown_op_arg_is_rejected(rules):
    tables = load_tables()
    bad = {"id": "X1", "name": "x", "types": ["spell"], "civs": ["fire"], "cost": 1,
           "spell": [{"op": "draw", "count": 1, "playr": "you"}]}
    with pytest.raises(DefError, match="unknown arg 'playr'"):
        parse_card(bad, tables)
    bad["spell"] = [{"op": "modify", "select": {"zone": "bz"}, "mod": {"deny": ["fly"]}}]
    with pytest.raises(DefError, match="unknown action 'fly'"):
        parse_card(bad, tables)


def test_task_shapes_are_checked(rules):
    e = setup(rules, {})
    e.s.tasks.append({"t": "effect", "ops": [], "pc": 0, "env": {}, "os": {}, "typo": 1})
    with pytest.raises(TypeError, match="extra=\\['typo'\\]"):
        e.advance()


