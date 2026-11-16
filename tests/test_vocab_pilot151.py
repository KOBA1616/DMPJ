"""語彙パイロット第151弾: d2_field（D2フィールドの型印・一意性・Dスイッチ）。

- 型印 `d2_field`: D2フィールドは types に ["field", "d2_field"] と併記する。D2だけを指す
  フィルタは {types: [d2_field]}（既存の types フィルタと exists で足りる）。
- 一意性はプール分離（公式裏取り済み）: D2フィールド同士だけが数え合う（703.4l。両プレイヤー
  合わせて1つ。行き先は破壊＝701.6＋109.1＋公式 QA 47896）。通常フィールド同士は第25弾の
  挙動を温存し、通常フィールドと D2 は互いに影響しない。適用は出現イベントごとに1回だけ
  （events の適用後フックは move の適用時にだけ走る）: 置換で生き残った D2 は、次の新しい
  D2 が出るまで残る。
- Dスイッチ: kind: trigger に `dswitch: true` を付け、効果の先頭に may＋{op: dswitch} を置く。
  使用済みは Card の `dswitched` 旗で数え、ゾーン移動でリセットされる（出直したら再使用可）。
  abilities() の出し分けで、使用済み・permits "d_switch" が deny の間は能力自体が出ない。
  「Dスイッチを使えず」は affects／modify＋deny: [d_switch]、「D2フィールドを展開できない」は
  deny: [generate]（メインの実行まで。第33弾の deny cast と同型）。
- proto T192〜T195、試験カード R109（ターンの終わり型の Dスイッチ観測用）。
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


X_CARDS = """
cards:
  - id: X192
    name: D禁止試験呪文
    types: [spell]
    civs: [light, water]
    cost: 3
    text: 次の自分のターンのはじめまで、相手はDスイッチを使えず、D2フィールドを展開できない。（dmr23-040 ワールド・ストップの手変換と同形）
    spell:
      - op: modify
        select: {zone: hand, owner: opp, filter: {types: [d2_field]}}
        mod: {deny: [generate]}
        dynamic: true
        duration: until_next_own_turn_start
      - op: modify
        select: {zone: bz, owner: opp, filter: {types: [d2_field]}}
        mod: {deny: [d_switch]}
        dynamic: true
        duration: until_next_own_turn_start
  - id: X193
    name: D2回収試験呪文
    types: [spell]
    civs: [nature]
    cost: 1
    text: 自分の墓地にあるD2フィールドを1枚、手札に戻す。
    spell:
      - {op: move, select: {zone: graveyard, owner: you, filter: {types: [d2_field]}, count: 1}, to: hand, reason: put}
  - id: X194
    name: クリーチャータップ試験呪文
    types: [spell]
    civs: [water]
    cost: 1
    text: 相手のクリーチャーを1体選んでタップする。
    spell:
      - {op: tap, select: {zone: bz, owner: opp, filter: {types: [creature]}, count: 1}}
"""


@pytest.fixture(scope="session")
def xr(tmp_path_factory):
    p = tmp_path_factory.mktemp("pilot151x") / "x_cards.yaml"
    p.write_text(X_CARDS, encoding="utf-8")
    return load_rules(card_yaml_files() + [p])


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _rule_card(cid):
    with open(Path(__file__).parent / "rule_cards.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _cid(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.cdef(c).id == defn)


def _drive(e, stop=None, play_key=None, yes_fn=None, attack=None, declare=None, record=None, maxn=800):
    """stop(e) が真になるまで決定に答えながら進める。

    main は play_key をこの呼び出しで1回だけ使う（他は pass）／yes_no は yes_fn(e, d) の
    返り値（無ければ "no"）／attack は attack（defn）の player 攻撃を1回だけ／
    declare_strigger は declare（defn）のカードを宣言する／pay_mana は先頭の組合せ
    （提示されるのは支払える組合せだけ）／それ以外は pass か最小数。
    """
    played = attacked = False
    for _ in range(maxn):
        if stop and stop(e):
            return
        d = e.advance()
        if d is None:
            return
        if record is not None:
            record.append(d)
        keys = [o["key"] for o in d["options"]]
        k = d["kind"]
        if k == "main" and play_key and not played and play_key in keys:
            played = True
            e.answer([keys.index(play_key)])
        elif k == "yes_no":
            a = yes_fn(e, d) if yes_fn else "no"
            e.answer([keys.index(a)])
        elif k == "attack" and attack and not attacked:
            hit = [i for i, o in enumerate(d["options"]) if o["key"] == f"attack:{attack}:player"]
            if hit:
                attacked = True
                e.answer([hit[0]])
            else:
                e.answer([keys.index("pass")])
        elif k == "declare_strigger":
            hit = [i for i, o in enumerate(d["options"])
                   if declare is not None and o.get("cid") is not None and e.cdef(o["cid"]).id == declare]
            e.answer(hit[:1] if hit else [])
        elif k == "choose_cards":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


# ---------- parse / 検証 ----------

def test_proto_parse(rr):
    """T192〜T195 と R109 が parse でき、dswitch の形が固定される。"""
    for cid in ("T192", "T193", "T194", "T195"):
        assert parse_card(_proto_card(cid), TABLES) is not None
    assert parse_card(_rule_card("R109"), TABLES) is not None
    t192 = next(c for c in rr.cards.values() if c.id == "T192")
    face = t192.face(None)
    assert face.types == ["field", "d2_field"]
    trig = next(a for a in face.abilities if a["kind"] == "trigger")
    assert trig["dswitch"] is True
    assert trig["effect"][0]["op"] == "may"
    assert trig["effect"][0]["body"][0] == {"op": "dswitch"}


def test_dswitch_key_validation():
    """dswitch は trigger に true でだけ書ける。"""
    base = {"id": "X900", "name": "検証用", "types": ["field", "d2_field"], "civs": ["nature"], "cost": 2}
    with pytest.raises(DefError):
        parse_card({**base, "abilities": [{"kind": "static", "dswitch": True, "affects": "self", "mod": {"power": 100}}]}, TABLES)
    with pytest.raises(DefError):
        parse_card({**base, "abilities": [{"kind": "trigger", "dswitch": False,
                                            "when": {"event": "turn_start", "player": "you"},
                                            "effect": [{"op": "draw", "count": 1}]}]}, TABLES)


# ---------- 一意性（プール分離） ----------

def test_d2_uniqueness_across_players(rules):
    """(1) 自分の D2 がある場に相手が別の D2 を出すと、先の D2 が破壊され、後の D2 が残る
    （両プレイヤー合わせて1つ。703.4l）。"""
    e = setup(rules, {"hand": ["T193"], "mana": ["T005", "T001"]},
              {"hand": ["T193"], "mana": ["T005", "T001"]})
    _drive(e, play_key="play:T193", stop=lambda e_: any(e_.cdef(c).id == "T193" for c in e_.bz_tops(0)))
    mine = _cid(e, "bz", 0, "T193")
    _drive(e, play_key="play:T193",
           stop=lambda e_: e_.s.cards[mine].zone == "graveyard" and any(e_.cdef(c).id == "T193" for c in e_.bz_tops(1)))
    assert e.s.cards[mine].zone == "graveyard"
    assert any(e.cdef(c).id == "T193" for c in e.bz_tops(1))


def test_d2_and_normal_field_coexist(rules):
    """(2) 通常フィールド（T069）と D2（T193）は共存する（プール分離）。出す順序を変えても同じ。"""
    for first, second in (("T069", "T193"), ("T193", "T069")):
        e = setup(rules, {"hand": [first, second], "mana": ["T001", "T002", "T003", "T005"]}, {})
        _drive(e, play_key=f"play:{first}", stop=lambda e_, f=first: any(e_.cdef(c).id == f for c in e_.bz_tops(0)))
        _drive(e, play_key=f"play:{second}",
               stop=lambda e_: all(any(e_.cdef(c).id == x for c in e_.bz_tops(0)) for x in ("T069", "T193")))
        assert all(any(e.cdef(c).id == x for c in e.bz_tops(0)) for x in ("T069", "T193")), \
            f"{first}→{second} の順で共存しなかった"
        assert not any(e.cdef(c).id in ("T069", "T193") for c in e.zlist("graveyard", 0))


def test_filter_field_includes_d2(rules):
    """(9) filter {types: [field]} では D2 も数えられ、{types: [d2_field]} は D2 だけを指す（併記の帰結）。"""
    e = setup(rules, {"bz": ["T193", "T069"]}, {})
    d2 = _cid(e, "bz", 0, "T193")
    normal = _cid(e, "bz", 0, "T069")
    assert e.filter_match(d2, {"types": ["field"]}) and e.filter_match(d2, {"types": ["d2_field"]})
    assert e.filter_match(normal, {"types": ["field"]}) and not e.filter_match(normal, {"types": ["d2_field"]})


# ---------- Dスイッチ ----------

def test_dswitch_decline_reoffer_use_then_gone(rules):
    """(3) Dスイッチは使うと効果（ドロー）が起き、次のターンのはじめには提示されない。
    断った場合は使用済みにならず、次の機会に再提示される。"""
    e = setup(rules, {"bz": ["T192"], "hand": ["T001"]}, {})
    fld = _cid(e, "bz", 0, "T192")
    offers = []   # (提示時の手札枚数, ターン)

    def yes_fn(e_, d):
        if d["player"] == 0:
            offers.append((len(e_.zlist("hand", 0)), e_.s.turn))
            return "yes" if len(offers) == 3 else "no"
        return "no"

    _drive(e, yes_fn=yes_fn, stop=lambda e_: e_.s.cards[fld].dswitched)
    assert len(offers) == 3, f"Dスイッチの提示回数が想定と違う: {offers}"
    # 断った2回目の提示→3回目の提示の間に増えるのは通常ドロー1枚だけ（断っても使用扱いにならず、
    # 効果のドローも起きない）。1回目→2回目の間は先攻1ターン目にドローが無いため同数
    assert offers[1][0] == offers[0][0]
    assert offers[2][0] == offers[1][0] + 1, "断ったターンに余分なドローをした（使用扱いになった）"
    assert e.s.cards[fld].dswitched is True
    # 使った後は、次の自分のターンのはじめを2回やり過ごしても提示されない
    turn_mark = e.s.turn
    n_offers = len(offers)
    _drive(e, yes_fn=yes_fn, stop=lambda e_: e_.s.turn >= turn_mark + 4 and e_.s.active == 0)
    assert len(offers) == n_offers, "使用済みの Dスイッチが再提示された"


def test_dswitch_draw_on_use(rules):
    """(3b) 使うと「そうしたら」の効果（1ドロー）が、そのターンの通常ドローと別に起きる。
    1回目の提示（先攻1ターン目）は断り、2回目（自分2ターン目）で使う。使用直後の
    charge 決定時点の手札は、提示時＋2（Dスイッチのドロー＋通常ドロー）になる。"""
    e = setup(rules, {"bz": ["T192"], "hand": ["T001"]}, {})
    fld = _cid(e, "bz", 0, "T192")
    offers = []
    charge_hand = []
    for _ in range(800):
        if charge_hand:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no" and d["player"] == 0:
            offers.append(len(e.zlist("hand", 0)))
            e.answer([keys.index("yes" if len(offers) == 2 else "no")])
        elif d["kind"] == "charge" and d["player"] == 0 and e.s.cards[fld].dswitched:
            charge_hand.append(len(e.zlist("hand", 0)))
            break
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert len(offers) == 2, f"Dスイッチの提示が想定と違う: {offers}"
    assert charge_hand and charge_hand[0] == offers[1] + 2, \
        f"使用ターンの手札が想定と違う（提示時 {offers[1]} → charge {charge_hand}。Dスイッチの1ドロー＋通常ドローで +2 のはず）"


def test_dswitch_turn_end_timing(rr):
    """R109（自分のターンの終わり型）: 使うとドローし、次のターンの終わりには提示されない。"""
    e = setup(rr, {"bz": ["R109"], "hand": ["T001"]}, {})
    fld = _cid(e, "bz", 0, "R109")
    offers = []

    def yes_fn(e_, d):
        if d["player"] == 0:
            offers.append(e_.s.turn)
            return "yes"
        return "no"

    _drive(e, yes_fn=yes_fn, stop=lambda e_: e_.s.cards[fld].dswitched)
    assert len(offers) == 1 and e.s.cards[fld].dswitched is True
    turn_mark = e.s.turn
    _drive(e, yes_fn=yes_fn, stop=lambda e_: e_.s.turn >= turn_mark + 4 and e_.s.active == 0)
    assert len(offers) == 1, "使用済みの Dスイッチ（ターン終わり型）が再提示された"


def test_dswitch_reusable_after_reentry(xr):
    """(4) D2 を墓地に置いて手札に戻し、出直すと Dスイッチが再び使える（旗はゾーン移動でリセット）。"""
    e = setup(xr, {"bz": ["T192"], "hand": ["X193"], "mana": ["T001"] * 5},
              {"hand": ["T193"], "mana": ["T005", "T001"]})
    fld = _cid(e, "bz", 0, "T192")
    offers = []

    def yes_yes(e_, d):
        if d["player"] == 0:
            offers.append(1)
            return "yes"
        return "no"

    _drive(e, yes_fn=yes_yes, stop=lambda e_: e_.s.cards[fld].dswitched)
    assert e.s.cards[fld].dswitched is True
    # 相手が D2 を出す → 自分の T192 は破壊されて墓地へ
    _drive(e, play_key="play:T193", stop=lambda e_: e_.s.cards[fld].zone == "graveyard")
    assert e.s.cards[fld].dswitched is False or e.s.cards[fld].zone == "graveyard"
    # 回収呪文で手札に戻す
    _drive(e, play_key="play:X193", stop=lambda e_: e_.s.cards[fld].zone == "hand")
    assert e.s.cards[fld].dswitched is False, "ゾーン移動で Dスイッチの旗がリセットされていない"
    # 出直す（相手の D2 は破壊される）
    _drive(e, play_key="play:T192", stop=lambda e_: e_.s.cards[fld].zone == "bz")
    assert any(e.cdef(c).id == "T193" for c in e.zlist("graveyard", 1))
    # 次の自分のターンのはじめに再び提示され、使える
    n0 = len(offers)
    _drive(e, yes_fn=yes_yes, stop=lambda e_: e_.s.cards[fld].dswitched)
    assert len(offers) > n0 and e.s.cards[fld].dswitched is True


# ---------- 禁止の受け皿 ----------

def test_deny_dswitch_and_generate(xr):
    """(5) deny: [d_switch] の間は Dスイッチが提示されず、deny: [generate] の間は D2 の
    展開選択肢だけが出ない。期限（次の自分のターンのはじめ）が切れれば両方戻る。"""
    e = setup(xr, {"bz": ["T192"], "hand": ["T193", "T001"], "mana": ["T001", "T002", "T005"]},
              {"hand": ["X192"], "mana": ["T004", "T003", "T001"]})
    offers = []

    def yes_fn(e_, d):
        if d["player"] == 0:
            offers.append(e_.s.turn)
        return "no"

    _drive(e, yes_fn=yes_fn, play_key="play:X192",
           stop=lambda e_: any(c_["duration"].startswith("until_turn_start:1") for c_ in e_.s.continuous))
    assert e.s.continuous, "禁止の継続的効果が置かれなかった"
    # 相手の次のターン（禁止中）: ターンのはじめに Dスイッチは提示されず、main で D2 だけ展開できない
    record = []
    n0 = len(offers)
    _drive(e, yes_fn=yes_fn, record=record,
           stop=lambda e_: any(d["kind"] == "main" and d["player"] == 0 for d in record))
    denied_main = next((d for d in record if d["kind"] == "main" and d["player"] == 0), None)
    assert denied_main is not None
    keys = [o["key"] for o in denied_main["options"]]
    assert "play:T193" not in keys, "deny: [generate] の間に D2 が展開できてしまう"
    assert "play:T001" in keys, "D2 以外のカードまで展開できなくなっている"
    assert len(offers) == n0, "deny: [d_switch] の間に Dスイッチが提示された"
    # 期限切れ後の自分のターン: Dスイッチが提示され、D2 も展開できる
    record2 = []
    _drive(e, yes_fn=yes_fn, record=record2,
           stop=lambda e_: len(offers) > n0 and any(d["kind"] == "main" and d["player"] == 0 for d in record2))
    assert len(offers) > n0, "期限切れ後も Dスイッチが提示されない"
    free_main = next(d for d in record2 if d["kind"] == "main" and d["player"] == 0)
    assert "play:T193" in [o["key"] for o in free_main["options"]], "期限切れ後も D2 が展開できない"


# ---------- S・トリガー / 言及カード / 対象指定 ----------

def test_strigger_d2_deploys_free(rules):
    """(6) S・トリガー持ちの D2（T195）は、シールドがブレイクされた時、コストを支払わずに展開できる。"""
    e = setup(rules, {"shield": ["T195"]}, {"bz": ["T001"]})
    tgt = _cid(e, "shield", 0, "T195")
    _drive(e, attack="T001", declare="T195",
           stop=lambda e_: e_.s.cards[tgt].zone == "bz")
    assert e.s.cards[tgt].zone == "bz"
    assert tgt in e.bz_tops(0)
    assert tgt not in e.zlist("hand", 0)


def test_referring_creature_conditions(rules):
    """(7) T194「自分のD2フィールドがあれば引く」: 自分の D2 がある時だけ引く。
    相手の D2 だけ／通常フィールドだけでは引かない。"""
    # 自分の D2 がある → 引く
    e = setup(rules, {"bz": ["T193"], "hand": ["T194"], "mana": ["T001"] * 3}, {})
    seen = {}
    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and "play:T194" in keys:
            seen["before"] = len(e.zlist("hand", 0))
            e.answer([keys.index("play:T194")])
            break
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    _drive(e, stop=lambda e_: any(e_.cdef(c).id == "T194" for c in e_.bz_tops(0)))
    assert len(e.zlist("hand", 0)) == seen["before"], \
        "自分の D2 があるのに引けなかった（手札: 出す前と同数＝-1＋1ドローのはず）"
    # 通常フィールドだけ → 引かない／相手の D2 だけ → 引かない
    for p0, p1 in (({"bz": ["T069"]}, {}), ({}, {"bz": ["T193"]})):
        e = setup(rules, {**p0, "hand": ["T194"], "mana": ["T001"] * 3}, p1)
        before = {}
        for _ in range(400):
            d = e.advance()
            if d is None:
                break
            keys = [o["key"] for o in d["options"]]
            if d["kind"] == "main" and d["player"] == 0 and "play:T194" in keys:
                before["n"] = len(e.zlist("hand", 0))
                e.answer([keys.index("play:T194")])
                break
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
        _drive(e, stop=lambda e_: any(e_.cdef(c).id == "T194" for c in e_.bz_tops(0)))
        assert len(e.zlist("hand", 0)) == before["n"] - 1, "D2 が無いのに引いてしまった"


def test_d2_not_creature_target_or_attacker(xr):
    """(8) D2フィールドはクリーチャーを対象とする選択に現れず、攻撃もしない。"""
    e = setup(xr, {"hand": ["X194"], "mana": ["T003"]}, {"bz": ["T193", "T001", "T002"]})
    d2 = _cid(e, "bz", 1, "T193")
    record = []
    _drive(e, play_key="play:X194", record=record,
           stop=lambda e_: any(e_.cdef(c).id == "X194" for c in e_.zlist("graveyard", 0)))
    assert any(e.cdef(c).id == "X194" for c in e.zlist("graveyard", 0)), "タップ呪文が解決されなかった"
    picks = [d for d in record if d["kind"] == "choose_cards"]
    assert picks, "クリーチャー2体から選ぶ決定が出なかった"
    cand = {o["cid"] for d in picks for o in d["options"] if o.get("cid") is not None}
    assert cand == {_cid(e, "bz", 1, "T001"), _cid(e, "bz", 1, "T002")}, \
        "クリーチャー選択の候補に D2フィールドが混ざっている（またはクリーチャーが漏れている）"
    assert d2 not in cand
    # 攻撃の選択肢に D2 は現れない
    e2 = setup(xr, {}, {"bz": ["T193", "T001"]})
    record2 = []
    _drive(e2, record=record2,
           stop=lambda e_: any(d["kind"] == "attack" for d in record2) and e_.s.active == 0)
    atk = [d for d in record2 if d["kind"] == "attack"]
    assert atk, "攻撃ステップの決定が無かった"
    all_keys = [o["key"] for d in atk for o in d["options"]]
    assert "attack:T001:player" in all_keys
    assert not any(k.startswith("attack:T193") for k in all_keys)
    assert "creature" not in e2.chars(_cid(e2, "bz", 1, "T193"))["types"]
