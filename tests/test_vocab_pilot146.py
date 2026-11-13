"""語彙パイロット第146弾: shield_break_replacement（ブレイクの自己置換）。

公式FAQどおり自己置換効果として実装する。語彙は既存の kind: replace＋when: {event: break} に統一し、
エンジン側は h_break に諮問段を新設した（chosen 確定後、S・トリガー宣言の前。諮問順は
ターン・プレイヤー→非ターン・プレイヤー、1シールドに適用できる置換は1つだけ＝連鎖しない）。
- ブレイク側: when: {event: break, subject: self}。被ブレイク側: when: {event: break, player: you}。
- 置換されたシールドは「ブレイクされた」ことにならない（QA 33466）: S・トリガー宣言・S・バックの
  対象から外れ、break レコードにも数えない（実際にブレイクされるシールドが0枚ならレコード自体を
  出さず、broke_in も立てない）。この扱いは「ブレイクする時、かわりに」型でも
  「手札に加えるかわりに」型でも同じとする【裁定待ち: 設計ノート pilot146 §5-1】。
- 割り込み型（ガイアール・ベイビー）は新キー continue: true（instead の後もブレイクが続く）。
- 諮問 env の変数 shield（束の ref 列）と {ref: event.shield} でブレイクされるシールドを参照できる。
- 擬似ブレイク（効果でシールドを手札に加える。113.6、fire_break: False）では諮問しない。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _rule_card(cid):
    with open(Path(__file__).parent / "rule_cards.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _play_out(e, attacker, replace_plan=None, shield_pick=None, put_defn=None):
    """攻撃宣言から攻撃の終わりまで進め、現れた Decision の kind の列を返す。

    replace_plan: choose_replacement の何回目かを受けて "replace" / "decline" を返す関数。
    shield_pick: choose_shields の選択肢キー列を受けて選ぶ添字列を返す関数。
    put_defn: choose_cards で選びたいカードの defn（A型の instead で手札から出す時）。
    """
    seen = []
    calls = {"replace": 0}
    for _ in range(500):
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind in ("charge", "main"):
            e.answer([keys.index("pass")])
        elif kind == "attack":
            hit = [i for i, k in enumerate(keys) if k == f"attack:{attacker}:player"]
            if not hit:
                e.answer([keys.index("pass")])
                break   # 攻撃ステップを抜けた（攻撃側はタップ済み）
            e.answer([hit[0]])
        elif kind == "choose_breaker":
            e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
        elif kind == "choose_shields":
            e.answer(shield_pick(keys) if shield_pick else list(range(d["min"])))
        elif kind == "choose_replacement":
            act = replace_plan(calls["replace"], keys) if replace_plan else "decline"
            calls["replace"] += 1
            if act == "replace":
                e.answer([next(i for i, k in enumerate(keys) if k.startswith("replace:"))])
            else:
                e.answer([keys.index("decline")])
        elif kind in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif kind == "choose_cards":
            hit = [i for i, k in enumerate(keys) if put_defn and put_defn in k]
            e.answer([hit[0]] if hit else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return seen


def _bundle(e, p, top_defn, under_defn):
    """p のシールド（top_defn）の下に、手札の under_defn を束として入れる（シールド・プラスと同じ形）。"""
    top = next(c for c in e.zlist("shield", p) if e.cdef(c).id == top_defn)
    und = next(c for c in e.zlist("hand", p) if e.cdef(c).id == under_defn)
    e._raw_move(und, "shield")
    lst = e.s.zones["shield"][0 if e.zshared("shield") else p]
    if und in lst:
        lst.remove(und)
    e.s.cards[top].under.append(und)
    e.s.cards[und].top_of = top
    return top


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


# ---------- parse ----------

def test_break_replace_parses():
    for cid in ("T177", "T178", "T179"):
        assert parse_card(_proto_card(cid), TABLES) is not None
    ab = parse_card(_proto_card("T178"), TABLES).abilities[0]
    assert ab["kind"] == "replace" and ab["continue"] is True
    ab = parse_card(_rule_card("R104"), TABLES).abilities[0]
    assert ab["kind"] == "replace" and ab["optional"] is True


def test_continue_validation():
    """continue は break の replace にだけ書ける（それ以外は DefError）。"""
    base = {"id": "test-cont", "name": "試験", "types": ["creature"], "civs": ["fire"],
            "cost": 3, "power": 3000, "races": ["テスト"], "text": "",
            "source": {"official": "test-cont", "review": "pending"}}
    bad_event = dict(base, abilities=[{"kind": "replace", "when": {"event": "move", "to": "graveyard"},
                                       "continue": True, "instead": [{"op": "draw", "count": 1}]}])
    with pytest.raises(DefError):
        parse_card(bad_event, TABLES)
    bad_kind = dict(base, abilities=[{"kind": "trigger", "when": {"event": "break"},
                                      "continue": True, "effect": [{"op": "draw", "count": 1}]}])
    with pytest.raises(DefError):
        parse_card(bad_kind, TABLES)


# ---------- 実挙動 ----------

def test_b_type_replaces_both_shields(rr):
    """(1) B型: 置換されたシールドは墓地へ行き、S・トリガー宣言が出ず、break レコードが立たない。"""
    e = setup(rr, {"bz": ["T177"]}, {"shield": ["T006", "T001"]})
    seen = _play_out(e, "T177")
    assert _defns(e, "graveyard", 1) == ["T001", "T006"]   # 2つとも墓地へ（S・トリガーの T006 も手札ではない）
    assert e.zlist("shield", 1) == []
    assert "declare_strigger" not in seen                  # 宣言の機会自体がない
    assert e.s.turn_counters.get("broken:1", 0) == 0       # break レコードに数えない
    assert not any(k.startswith("broke_in:") for k in e.s.turn_counters)


def test_b_type_bundle_goes_to_graveyard_together(rr):
    """(2) B型＋束シールド（シールド・プラス）: 束ごと墓地へ行き、下の S・トリガーも宣言できない。"""
    e = setup(rr, {"bz": ["T177"]}, {"shield": ["T001"], "hand": ["T006"]})
    _bundle(e, 1, "T001", "T006")
    seen = _play_out(e, "T177")
    assert _defns(e, "graveyard", 1) == ["T001", "T006"]
    assert e.zlist("shield", 1) == []
    assert "declare_strigger" not in seen
    assert e.s.turn_counters.get("broken:1", 0) == 0


def test_a_type_interrupt_then_breaks(rr):
    """(3) A型（continue: true）: 割り込みで手札から出してから、通常どおりブレイクする。

    シールドは T006（コスト3）。手札の T001（コスト2）は「その中のカード1枚よりコストが小さい」を満たす。
    """
    e = setup(rr, {"bz": ["T178", "T002"], "hand": ["T001"]}, {"shield": ["T006"]})
    seen = _play_out(e, "T178", put_defn="T001")
    assert "T001" in _defns(e, "bz", 0)                    # 割り込みで出した
    assert "declare_strigger" in seen                      # ブレイクが続くので宣言の機会がある
    assert _defns(e, "hand", 1) == ["T006"]                # ブレイクされて手札へ
    assert e.s.turn_counters.get("broken:1", 0) == 1       # break レコードに数える
    assert any(k.startswith("broke_in:") for k in e.s.turn_counters)


def test_a_type_bundle_cost_reference_is_max(rr):
    """(4) A型の束: コスト参照は束の中の最大コスト（FAQ qa_old/36515 の存在読み）。

    束はトップ T001（コスト2）＋下 T004（コスト3）。参照がトップだけなら上限は1で
    手札の T001（コスト2）は出せないが、最大コスト3を参照すれば上限2で出せる。
    """
    e = setup(rr, {"bz": ["T178", "T002"], "hand": ["T001"]}, {"shield": ["T001"], "hand": ["T004"]})
    _bundle(e, 1, "T001", "T004")
    _play_out(e, "T178", put_defn="T001")
    assert "T001" in _defns(e, "bz", 0)                    # 最大コスト参照で出せた
    assert _defns(e, "hand", 1) == ["T001", "T004"]        # 束はまとめて手札へ
    assert e.s.turn_counters.get("broken:1", 0) == 1


def test_c_type_decline_breaks_normally(rr):
    """(5a) C型: decline すれば通常どおりブレイクされる（手札は減らない）。"""
    e = setup(rr, {"bz": ["T001", "T002"]}, {"bz": ["T179"], "hand": ["T004"]})
    _play_out(e, "T001", replace_plan=lambda n, keys: "decline")
    assert _defns(e, "hand", 1) == ["T001", "T004"]        # 捨てず、ブレイクされたシールドが加わる
    assert e.zlist("graveyard", 1) == []
    assert len(e.zlist("shield", 1)) == 4
    assert e.s.turn_counters.get("broken:1", 0) == 1


def test_c_type_accept_cancels_break(rr):
    """(5b) C型: 受ければ手札を捨ててブレイクが取り消され、シールドは残る。"""
    e = setup(rr, {"bz": ["T001", "T002"]}, {"bz": ["T179"], "hand": ["T004"]})
    _play_out(e, "T001", replace_plan=lambda n, keys: "replace", put_defn="T004")
    assert _defns(e, "graveyard", 1) == ["T004"]           # 支払いの手札捨て
    assert e.zlist("hand", 1) == []
    assert len(e.zlist("shield", 1)) == 5                  # ブレイクされていない
    assert e.s.turn_counters.get("broken:1", 0) == 0


def test_c_type_rider_destroys_breaker(rr):
    """(6) デス型（R104）: シールドは墓地へ（手札ではない）、ブレイクしたクリーチャーを破壊する。"""
    e = setup(rr, {"bz": ["T001", "T002"]}, {"bz": ["R104"]})
    _play_out(e, "T001", replace_plan=lambda n, keys: "replace")
    assert _defns(e, "graveyard", 1) == ["T001"]           # ブレイクされたシールド（フィラー）
    assert e.zlist("hand", 1) == []                        # 手札には加わらない
    assert _defns(e, "graveyard", 0) == ["T001"]           # 攻撃クリーチャーが破壊された
    assert [e.cdef(c).id for c in e.bz_tops(0)] == ["T002"]   # 残るのはバイスタンダーだけ
    assert e.s.turn_counters.get("broken:1", 0) == 0


def test_partial_replacement_counts_one_break(rr):
    """(7) W・ブレイカーで1つだけ置換・1つは通常: break レコードの count は1。"""
    e = setup(rr, {"bz": ["T005", "T002"]}, {"bz": ["T179"], "hand": ["T004", "T002"]})
    plan = lambda n, keys: "replace" if n == 0 else "decline"   # 1つ目は受け、2つ目は decline
    _play_out(e, "T005", replace_plan=plan, shield_pick=lambda keys: [0, 1], put_defn="T004")
    assert e.s.turn_counters.get("broken:1", 0) == 1       # ブレイクとして数えるのは1つだけ
    assert len(e.zlist("shield", 1)) == 4                  # 取り消された1つは残る
    assert _defns(e, "graveyard", 1) == ["T004"]           # 支払いは1回だけ
    assert _defns(e, "hand", 1) == ["T001", "T002"]        # ブレイクされたシールドが手札へ


def test_pseudo_break_no_consultation(rr):
    """(8) 擬似ブレイク（効果でシールドを手札に加える。113.6）では諮問が発火しない。"""
    e = setup(rr, {"bz": ["T179"], "hand": ["R020"], "mana": ["T001"]}, {})
    seen = []
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind == "main" and "play:R020" in keys:
            e.answer([keys.index("play:R020")])
        elif kind in ("charge", "main") and "pass" in keys:
            e.answer([keys.index("pass")])
        elif kind == "attack":
            e.answer([keys.index("pass")])
            break
        else:
            e.answer(list(range(d["min"])))
    assert "choose_replacement" not in seen               # 諮問は走らない
    assert _defns(e, "hand", 0) == ["T001"]                # 自分のシールドが手札に加わった
    assert _defns(e, "graveyard", 0) == ["R020"]           # 捨て札は呪文だけ（T179 の支払いは起きていない）


def test_replacement_does_not_chain(rr):
    """(9) 置換は連鎖しない: 攻撃側の置換が適用されたシールドに、被ブレイク側の置換は諮問されない。"""
    e = setup(rr, {"bz": ["T177", "T002"]}, {"bz": ["T179"], "hand": ["T004"], "shield": ["T001", "T001"]})
    seen = _play_out(e, "T177")
    assert "choose_replacement" not in seen               # T179 への諮問自体が発生しない
    assert _defns(e, "hand", 1) == ["T004"]                # 捨てる機会もなかった
    assert _defns(e, "graveyard", 1) == ["T001", "T001"]
    assert e.s.turn_counters.get("broken:1", 0) == 0


def test_effect_break_also_consulted(rr):
    """(10) 効果ブレイク（op break。S・トリガー先処理＝in_effect）でも諮問段を通る。

    自分のシールドをブレイクする呪文（R022）を、自分の C型（T179）がいる時に使う。
    置換を受ければブレイクは取り消され、呪文の後続（1ドロー）は通常どおり処理される。
    """
    e = setup(rr, {"bz": ["T179"], "hand": ["R022", "T004"], "mana": ["T001"]}, {})
    seen = []
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind == "main" and "play:R022" in keys:
            e.answer([keys.index("play:R022")])
        elif kind == "choose_replacement":
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("replace:"))])
        elif kind == "choose_cards":
            hit = [i for i, k in enumerate(keys) if "T004" in k]
            e.answer([hit[0]] if hit else list(range(d["min"])))
        elif kind in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif kind == "attack":
            e.answer([keys.index("pass")])
            break
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert "choose_replacement" in seen                   # 効果ブレイクでも諮問が走った
    assert len(e.zlist("shield", 0)) == 5                  # ブレイクは取り消された
    assert _defns(e, "graveyard", 0) == ["R022", "T004"]   # 呪文と支払いの捨て札
    assert len(e.zlist("hand", 0)) == 1                    # 後続の1ドロー
    assert e.s.turn_counters.get("broken:0", 0) == 0
