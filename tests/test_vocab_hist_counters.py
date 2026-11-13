"""第3段・共通基盤その2a: 履歴カウンタ一般化（式 {turn_count:} / {used_count:} / {prev_shield_added:}、
when の {ord:}、mark の scope）。

- 記録: events.apply_batch が適用済みレコードを走査し、turn_counters の
  hist:<kind>:{player}（クリーチャー単位は hist:<kind>:{cid}）へ集約する。あわせて
  レコードへ rec["ord"] = {kind: 通し番号} を刻み、when の {ord: {kind, 比較}} で照合する。
  既存キー（entered: / drew: / broken: / broke_in:）は従来どおり別途維持し、挙動は変えない。
- 式: selectors.eval_expr の turn_count（kind: shield_put / shield_left / mana_put / cast /
  summon / attack / destroyed / broke_by_self / draw / broken / enter / discard / leave /
  tap / untap / block / enter_unpaid / attack_by / attack_on。attack は other / filter、
  attack_by / attack_on は ref 対応）、used_count（cast レコードと via: generate の実行を
  印刷特性スナップショットで数える）、prev_shield_added（st_start が退避する prev_counters を読む）。
- count_of の一般化で履歴式が mod の count に書ける（T236）。
- mark の scope: attack（その攻撃の中だけ）/ game（GameState.game_counters。ターン開始で消えない）。
  cond の marked は辞書形 {name, scope} を受ける。
- proto: T236（引き軽減。ティガウォック型）／T237（詠唱門。ガリアル型）／T238（ord ge。タクヤ型）／
  T239（ord eq。グラヴィッツ型）／T240＋T241（used_count）／T242＋T243（shield_left）／
  T244＋T245（prev_shield_added）／T246（broke_by_self）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _cid(e, p, defn, zone="bz"):
    return next(c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn)


def _settle_to(e, kind, player=None, max_steps=400):
    """指定の判断が来るまで既定回答で進め、その判断を未回答で返す。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == kind and (player is None or d["player"] == player):
            return d
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError(f"decision {kind} (player={player}) not reached")


def _play(e, d, key):
    """main 判断 d で key のカードを使い、次の main / attack 判断まで進めて返す。"""
    keys = [o["key"] for o in d["options"]]
    assert key in keys, f"{key} not in {keys}"
    e.answer([keys.index(key)])
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] in ("main", "attack"):
            return d
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("play did not settle")


def test_proto_parse(rules):
    """T236〜T246 が parse でき、履歴式・ord の検証が効く。"""
    for cid in ("T236", "T237", "T238", "T239", "T240", "T241", "T242", "T243", "T244", "T245", "T246"):
        parse_card(_proto_card(cid), TABLES)
    bad = _proto_card("T237")
    bad["abilities"][0]["if"] = {"cmp": [{"turn_count": {"kind": "bogus", "owner": "you"}}, "==", 0]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = _proto_card("T237")
    bad["abilities"][0]["if"] = {"cmp": [{"turn_count": {"kind": "draw", "owner": "any"}}, "==", 0]}
    with pytest.raises(DefError):   # any は destroyed / attack だけ
        parse_card(bad, TABLES)
    bad = _proto_card("T237")
    bad["abilities"][0]["if"] = {"cmp": [{"turn_count": {"kind": "attack_by"}}, "==", 0]}
    with pytest.raises(DefError):   # attack_by には ref が要る
        parse_card(bad, TABLES)
    bad = _proto_card("T240")
    bad["abilities"][0]["if"] = {"cmp": [{"used_count": {"owner": "any"}}, ">=", 1]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = _proto_card("T244")
    bad["abilities"][0]["if"] = {"cmp": [{"prev_shield_added": {"owner": "any"}}, ">=", 1]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    for bad_ord in ({"kind": "mana_put"}, {"kind": "mana_put", "eq": 1, "ge": 2},
                    {"kind": "shield_put", "eq": 1}, {"kind": "mana_put", "eq": 0}):
        bad = _proto_card("T238")
        bad["abilities"][0]["when"]["ord"] = bad_ord
        with pytest.raises(DefError):
            parse_card(bad, TABLES)


def test_draw_count_reduces_cost(rules):
    """T236: 引いた枚数だけ召喚コストが下がる（mod の count に履歴式。先攻1ターン目はドローが無い）。"""
    e = setup(rules, {"hand": ["T236", "T003"], "mana": ["T003"] * 4}, {})
    cid = _cid(e, 0, "T236", "hand")
    assert e.chars(cid)["pay_cost"] == 4   # まだ何も引いていない
    d = _settle_to(e, "main", player=0)
    d = _play(e, d, "play:T003")       # 2枚引く
    assert e.s.turn_counters.get("hist:draw:0") == 2
    assert e.chars(cid)["pay_cost"] == 2   # 支払うコストは 4 − 2（参照用の cost は 4 のまま）
    _play(e, d, "play:T236")           # 残りマナ2で召喚できる（コスト4のままなら払えない）
    assert any(e.s.cards[c].defn == "T236" for c in e.zlist("bz", 0))


def test_cast_gate_opens_after_casting(rules):
    """T237: 呪文を唱えるまでは召喚できず、唱えた後は召喚できる（turn_count cast）。"""
    e = setup(rules, {"hand": ["T237", "T003"], "mana": ["T003"] * 5}, {})
    d = _settle_to(e, "main", player=0)
    keys = [o["key"] for o in d["options"]]
    assert "play:T237" not in keys and "play:T003" in keys
    d = _play(e, d, "play:T003")
    assert e.s.turn_counters.get("hist:cast:0") == 1
    keys = [o["key"] for o in d["options"]]
    assert "play:T237" in keys
    _play(e, d, "play:T237")
    assert any(e.s.cards[c].defn == "T237" for c in e.zlist("bz", 0))


def test_ord_mana_put_fires_from_second(rules):
    """T238: 相手のマナ置きは、チャージ（1回目）では発火せず、CIP の2回目以降で発火する（ord ge）。"""
    e = setup(rules, {"bz": ["T238"]},
              {"hand": ["T002", "T002", "T001"], "mana": ["T001"] * 4})
    d = _settle_to(e, "charge", player=1)
    keys = [o["key"] for o in d["options"]]
    e.answer([keys.index("charge:T001")])
    d = _settle_to(e, "main", player=1)
    assert len(e.zlist("hand", 0)) == 0   # 1回目のマナ置き（ord 1）では引かない
    d = _play(e, d, "play:T002")          # CIP で2回目のマナ置き（ord 2）→ 発火
    assert len(e.zlist("hand", 0)) == 1
    d = _play(e, d, "play:T002")          # CIP で3回目（ord 3）→ また発火
    assert len(e.zlist("hand", 0)) == 2
    _settle_to(e, "charge", player=0)
    assert len(e.zlist("hand", 0)) == 3   # 自分のターン開始ドロー +1


def test_ord_enter_fires_only_first(rules):
    """T239: 相手の最初のクリーチャー入場でのみ発火する（ord eq）。
    発火回数は trace で数える（2体目は召喚酔いで攻撃判断が出ず、ターンが進んでしまうため）。"""
    e = setup(rules, {"bz": ["T239"]},
              {"hand": ["T001", "T001"], "mana": ["T001"] * 4})
    e.s.trace = []
    d = _settle_to(e, "main", player=1)
    d = _play(e, d, "play:T001")          # 1体目（ord 1）→ 発火
    assert len(e.zlist("hand", 0)) == 1
    d = _play(e, d, "play:T001")          # 2体目（ord 2）→ 発火しない
    fires = sum(1 for t in e.s.trace if t["ev"] == "move" and t["src"] == "T239")
    assert fires == 1
    assert len(e.zlist("hand", 0)) == 2   # 発火の1枚＋（2体目の解決後に進んだ）自分のターン開始ドロー1枚


def test_used_count_needs_costly_spell(rules):
    """T240: コスト5以上の呪文を唱えた時だけ覚醒する（used_count の特性スナップショット照合）。
    安い呪文（コスト2）では発火しないことが判別条件。"""
    e = setup(rules, {"bz": ["T240"], "hand": ["T003", "T241"], "mana": ["T003"] * 7}, {})
    cid = _cid(e, 0, "T240")
    assert e.chars(cid)["power"] == 3000
    d = _settle_to(e, "main", player=0)
    d = _play(e, d, "play:T003")          # コスト2の呪文: 「使った」履歴には入るが特性で弾かれる
    assert e.chars(cid)["power"] == 3000
    _play(e, d, "play:T241")              # コスト5の呪文
    assert e.chars(cid)["power"] == 6000


def test_shield_left_gate(rules):
    """T242: 自分のシールドが離れるまでは攻撃できず、自分のシールドを割ると攻撃できる（shield_left）。
    割る前は permits が攻撃を禁じ、1ターン経っても相手のシールドが減らないことが判別条件。"""
    e = setup(rules, {"bz": ["T242"], "hand": ["T243"], "mana": ["T008", "T001"]}, {})
    cid = _cid(e, 0, "T242")
    assert not e.permits(cid, "attack_player") and not e.permits(cid, "attack_creature")
    d = _settle_to(e, "main", player=0)
    keys = [o["key"] for o in d["options"]]
    e.answer([keys.index("pass")])        # 1ターン目は何もしない（攻撃ステップは選択肢が無く自動で流れる）
    d = _settle_to(e, "main", player=0)   # 次の自分のターン
    assert len(e.zlist("shield", 1)) == 5   # 攻撃できていないので減っていない
    d = _play(e, d, "play:T243")          # 自分のシールドを1つ割る
    assert e.s.turn_counters.get("hist:shield_left:0") == 1
    assert len(e.zlist("shield", 0)) == 4
    keys = [o["key"] for o in d["options"]]
    assert d["kind"] == "attack" and "attack:T242:player" in keys
    e.answer([keys.index("attack:T242:player")])
    _settle_to(e, "charge", player=1)
    assert len(e.zlist("shield", 1)) == 4   # ブレイクが通った


def test_prev_shield_added(rules):
    """T244: 相手が前のターンにシールドを加えていれば、次の自ターンにパワーが上がる（prev_shield_added）。
    加えた当人のターン（相手ターン）では上がらないことが判別条件。"""
    e = setup(rules, {"bz": ["T244"]}, {"bz": ["T001"], "hand": ["T245"], "mana": ["T001", "T001"]})
    cid = _cid(e, 0, "T244")
    assert e.chars(cid)["power"] == 3000
    d = _settle_to(e, "main", player=1)
    d = _play(e, d, "play:T245")          # 相手が自分のシールドを加える
    assert d["player"] == 1                # まだ相手のターン（攻撃判断で止まる）
    assert len(e.zlist("shield", 1)) == 6
    assert e.chars(cid)["power"] == 3000   # まだ「前のターン」ではない
    _settle_to(e, "attack", player=0)     # 次の自ターン（main は選択肢が無く自動で流れるため attack 判断で止める）
    assert e.chars(cid)["power"] == 6000


def test_broke_by_self(rules):
    """T246: 自分がシールドをブレイクしたターンにパワーが上がる（broke_by_self。クリーチャー単位の履歴）。"""
    e = setup(rules, {"bz": ["T246", "T001"]}, {})
    cid = _cid(e, 0, "T246")
    d = _settle_to(e, "attack", player=0)
    assert e.chars(cid)["power"] == 3000
    keys = [o["key"] for o in d["options"]]
    e.answer([keys.index("attack:T246:player")])
    d = _settle_to(e, "attack", player=0)   # もう1体の攻撃判断（まだ自ターン）
    assert e.s.turn_counters.get(f"hist:broke_by:{cid}") == 1
    assert e.chars(cid)["power"] == 5000


def _run_ops(e, ops, you=0):
    """効果を直接実行し、main / attack 判断が来るまで流す（tests/test_rules.py の run_ops と同じ形）。"""
    e.s.tasks.append(e._child(ops, {"you": you, "self": None, "vars": {}}))
    for _ in range(200):
        d = e.advance()
        assert d is not None
        if d["kind"] in ("main", "attack"):
            return
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("ops did not settle")


def test_recorder_counts_kinds(rules):
    """記録器の直接確認: 観測しにくい kind（discard / tap / untap / destroyed / leave 等）を
    turn_counters の値で確かめる。ターンが変わると消え、prev_counters に退避されることも確かめる。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T001", "T001"]}, {"bz": ["T004"]})
    d = _settle_to(e, "charge", player=0)
    keys = [o["key"] for o in d["options"]]
    e.answer([keys.index("pass")])
    tc = e.s.turn_counters
    assert tc.get("hist:mana_put:0", 0) == 0   # チャージしなかったので 0
    # 一連の出来事を1つの効果として流す（判断を未回答のまま次へ進めないため、まとめて実行する）
    _run_ops(e, [{"op": "draw", "player": "you", "count": 2},
                 {"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 1, "count": 1},
                  "to": "mana", "reason": "put"},
                 {"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 1, "count": 1},
                  "to": "shield", "reason": "put"},
                 {"op": "move", "select": {"zone": "shield", "owner": "you", "count": 1},
                  "to": "hand", "reason": "put"},
                 {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1},
                  "to": "graveyard", "reason": "discard"},
                 {"op": "tap", "select": {"zone": "bz", "owner": "you", "count": 1}},
                 {"op": "untap", "select": {"zone": "bz", "owner": "you", "count": 1}},
                 {"op": "move", "select": {"zone": "bz", "owner": "opp", "count": 1},
                  "to": "graveyard", "reason": "destroy"}])
    assert tc.get("hist:draw:0") == 2
    assert tc.get("hist:mana_put:0") == 1
    assert tc.get("hist:shield_put:0") == 1
    assert tc.get("hist:shield_left:0") == 1
    assert tc.get("hist:discard:0") == 1
    assert tc.get("hist:tap:0") == 1
    assert tc.get("hist:untap:0") == 1
    assert tc.get("hist:destroyed:1") == 1 and tc.get("hist:leave:1") == 1
    _settle_to(e, "charge", player=1)   # ターンが変わる
    tc2 = e.s.turn_counters   # st_start が辞書ごと差し替えるので、参照を取り直す
    assert tc2.get("hist:draw:0", 0) == 0 and tc2.get("hist:draw:1") == 1   # リセット＋相手のターン開始ドロー
    assert e.s.prev_counters.get("hist:draw:0") == 2   # 前のターンの履歴は退避されている


def test_game_scope_mark_survives_turns(rules):
    """mark の scope: game はターン開始で消えず、cond の marked 辞書形で読める。
    既定の turn スコープは従来どおりターンで消える。"""
    e = setup(rules, {"bz": ["T001"]}, {})
    env = {"you": 0, "self": None, "vars": {}}
    d = _settle_to(e, "charge", player=0)   # ゲームを開始してから ops を積む（開始前に積むと st_start のリセットで消える）
    keys = [o["key"] for o in d["options"]]
    e.answer([keys.index("pass")])
    _run_ops(e, [{"op": "mark", "name": "game_once", "scope": "game"},
                 {"op": "mark", "name": "turn_mark"}])
    assert e.s.game_counters.get("game_once") == 1 and e.s.turn_counters.get("turn_mark") == 1
    assert e.eval_cond({"marked": {"name": "game_once", "scope": "game"}}, env)
    assert e.eval_cond({"marked": "turn_mark"}, env)
    _settle_to(e, "charge", player=1)   # ターンが変わる
    assert e.s.turn_counters.get("turn_mark", 0) == 0
    assert e.s.game_counters.get("game_once") == 1
    assert e.eval_cond({"marked": {"name": "game_once", "scope": "game"}}, env)
    assert not e.eval_cond({"marked": "turn_mark"}, env)
