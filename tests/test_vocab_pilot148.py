"""語彙パイロット第148弾: shield_stack / flip_up / shield_flip（シールドの重ね置きと向き変更）。

- move の新キー stack_on: <セレクタ>（to: shield の時だけ）: 移動したカードが対象の束の新しい
  トップになる。move イベント経由なので「シールドゾーンに置かれた時」「表向きで置かれた時」が
  正しく発火する。対象の束は効果の使用者が選ぶ（セレクタの owner は候補の絞り込み）。
  重ねる先が無い場合は置けないので移動しない（裁キ型で自分のシールドが無ければ通常どおり墓地へ）。
- セレクタ新キー bundle_of: 解決した束（トップ）ごとに [トップ]＋その下すべてを候補にする。
  束の中の（覆われている）表向きカードも「シールドゾーンにある表向きのカード」の数え・選択に
  含める（ユーザー決定 2026-11-08）。素の zone: shield はトップだけを見るので、変換では
  こちらを標準形にする。
- op flip_up（新設）／flip_down のシールド拡張: イベントを作らない直操作（「置かれた時」は
  誘発しない）。両方向の選択は modal で書く。束の中のカードは bundle_of で指す。
- ブレイク処理は無変更（束はトップへの move で under ごと動き、束のカード全員が
  S・トリガー宣言できる。既存実装の確認のみ）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import DefError, card_yaml_files, load_rules, load_tables, parse_card

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


def _drive(e, stop=None, play_key=None, yes_seq=(), yes_fn=None, modes=(), choose_cid=None,
           attack=None, shield_cid=None, record=None, hook=None, maxn=500):
    """stop(e) が真になるまで決定に答えながら進める。

    標準の答え方: main は play_key を1回だけ使う（他は pass）／yes_no は yes_seq を順に消費
    （yes_fn があればそちらで決める。尽きたら yes）／choose_mode は modes を順に消費／
    choose_cards は choose_cid に一致する選択肢を優先／attack は attack（defn）の player 攻撃を
    1回だけ／choose_shields は shield_cid を選ぶ／S・トリガー類は宣言しない。
    record があれば全 Decision を貯める。hook(e, d) が True を返したら標準の答え方をしない。
    """
    ys, ms = list(yes_seq), list(modes)
    played = attacked = False
    for _ in range(maxn):
        if stop and stop(e):
            return
        d = e.advance()
        if d is None:
            return
        if record is not None:
            record.append(d)
        if hook and hook(e, d):
            continue
        keys = [o["key"] for o in d["options"]]
        k = d["kind"]
        if k == "main" and play_key and not played and play_key in keys:
            played = True
            e.answer([keys.index(play_key)])
        elif k == "yes_no":
            a = yes_fn(e, d) if yes_fn else (ys.pop(0) if ys else "yes")
            e.answer([keys.index(a)])
        elif k == "choose_mode":
            m = ms.pop(0) if ms else 0
            e.answer([keys.index(f"mode:{m}")])
        elif k == "choose_cards":
            hit = [i for i, o in enumerate(d["options"]) if choose_cid is not None and o.get("cid") == choose_cid]
            e.answer(hit[:d["max"]] if hit else list(range(d["min"])))
        elif k == "attack" and attack and not attacked:
            hit = [i for i, o in enumerate(d["options"]) if o["key"] == f"attack:{attack}:player"]
            if hit:
                attacked = True
                e.answer([hit[0]])
            else:
                e.answer([keys.index("pass")])
        elif k == "choose_shields":
            hit = [i for i, o in enumerate(d["options"]) if shield_cid is not None and o.get("cid") == shield_cid]
            e.answer(hit[:max(d["min"], 1)] if hit else list(range(d["min"])))
        elif k in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _cid(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.cdef(c).id == defn)


# ---------- parse / 検証 ----------

def test_pilot148_parses():
    for cid in ("T183", "T184", "T185"):
        assert parse_card(_proto_card(cid), TABLES) is not None
    for cid in ("R106", "R107"):
        assert parse_card(_rule_card(cid), TABLES) is not None
    ab = parse_card(_proto_card("T183"), TABLES).abilities[0]
    assert ab["kind"] == "replace" and ab["zone"] == "hold"
    ins = ab["instead"][0]
    assert ins["stack_on"] == {"zone": "shield", "owner": "you", "count": 1} and ins["face_up"] is True
    eff = str(parse_card(_proto_card("T185"), TABLES).abilities)
    assert "flip_up" in eff and "flip_down" in eff and "bundle_of" in eff
    assert "modal" in str(parse_card(_rule_card("R107"), TABLES).spell)


def _spell(ops_list):
    return {"id": "test-p148", "name": "試験", "types": ["spell"], "civs": ["light"], "cost": 3,
            "races": ["テスト"], "text": "", "spell": ops_list,
            "source": {"official": "test-p148", "review": "pending"}}


def test_stack_on_validation():
    """stack_on は to: shield の時だけ。対象セレクタの count は1だけ（defs で検証）。"""
    move = {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1},
            "to": "shield", "reason": "put", "stack_on": {"zone": "shield", "owner": "you", "count": 1}}
    assert parse_card(_spell([move]), TABLES) is not None
    with pytest.raises(DefError):
        parse_card(_spell([dict(move, to="graveyard")]), TABLES)
    with pytest.raises(DefError):
        parse_card(_spell([dict(move, stack_on={"zone": "shield", "owner": "you", "count": 2})]), TABLES)
    with pytest.raises(DefError):   # bundle_of の中身も再帰検証される
        parse_card(_spell([{"op": "flip_up", "select": {"bundle_of": {"zone": "nowhere"}, "count": 1}}]), TABLES)


# ---------- 実挙動 ----------

def test_b_type_stack_forms_one_bundle_and_fires_placed_trigger(rr):
    """(2) B型: 山札上を裏向きの新シールドにし、別の山札上を表向きでその上に重ねる。
    束は1つのシールドのまま。2回の配置とも「シールドゾーンに置かれた時」（R106）が発火する。"""
    e = setup(rr, {"hand": ["T184"], "mana": ["T004", "T003"] * 4, "bz": ["R106"]}, {"shield": ["T001"]})
    deck_before = len(e.zlist("deck", 0))
    _drive(e, play_key="play:T184",
           stop=lambda e: any(e.s.cards[c].under for c in e.zlist("shield", 0)) and len(e.zlist("hand", 0)) == 2)
    tops = e.zlist("shield", 0)
    assert len(tops) == 6                                   # 既存5＋新しい束1（束は1つと数える）
    top = next(c for c in tops if e.s.cards[c].under)
    under = e.s.cards[top].under
    assert len(under) == 1
    assert e.s.cards[top].face_up is True                   # 重ねたカードは表向き
    assert e.s.cards[under[0]].face_up is False             # 新シールドは裏向き
    assert e.s.cards[under[0]].top_of == top
    assert len(e.zlist("deck", 0)) == deck_before - 4       # 山札から4枚減る（シールド化2枚＋R106 のドロー2枚）
    assert len(e.zlist("hand", 0)) == 2                     # R106 が2回の配置で2回誘発し2ドロー


def test_bundle_break_both_cards_can_declare_strigger(rr):
    """(1) 重ねた束をブレイクすると束ごと手札に動き、旧トップと新トップの両方が
    S・トリガー宣言できる。シールドの数は束1つ分だけ減る。"""
    e = setup(rr, {"hand": ["T184"], "mana": ["T004", "T003"] * 4, "deck": ["T006", "T006"]},
              {"bz": ["T001", "T001", "T005"], "shield": ["T001"]})   # T005 はブレイク後に同じターン内で決定が残るための攻撃役（D型で1体、攻撃で1体が使われる）
    _drive(e, play_key="play:T184", stop=lambda e: any(e.s.cards[c].under for c in e.zlist("shield", 0)))
    bundle_top = next(c for c in e.zlist("shield", 0) if e.s.cards[c].under)
    bundle = [bundle_top] + list(e.s.cards[bundle_top].under)
    assert [e.cdef(c).id for c in bundle] == ["T006", "T006"]
    state = {}
    record = []

    def hook(e_, d):
        if e_.s.cards[bundle_top].zone == "hand" and "counters" not in state:
            state["counters"] = dict(e_.s.turn_counters)
        return False

    _drive(e, attack="T001", shield_cid=bundle_top, record=record, hook=hook,
           stop=lambda e: e.s.cards[bundle_top].zone == "hand")
    decl = next(d for d in record if d["kind"] == "declare_strigger")
    offered = sorted(o["cid"] for o in decl["options"] if o.get("cid") is not None)
    assert offered == sorted(bundle)                        # 束の2枚とも宣言候補に出る
    assert sum(1 for c in e.zlist("hand", 0) if e.cdef(c).id == "T006") == 2
    assert len(e.zlist("shield", 0)) == 5                   # 6→5（束1つ分）
    assert state["counters"].get("broken:0") == 1           # ブレイクは1回（束1つ）として数える


def test_d_type_stacks_opponents_creature_on_own_shield(rr):
    """(6) D型: 選択者は効果の使用者（自分）で、相手のクリーチャーを表向きで持ち主の
    シールドの上に置く。(2) 置かれたカード自身の「表向きで置かれた時」も発火する。"""
    e = setup(rr, {"hand": ["T184"], "mana": ["T004", "T003"] * 4, "bz": ["R106"]},
              {"bz": ["T052"], "shield": ["T001", "T002"]})
    t052 = _cid(e, "bz", 1, "T052")
    target = _cid(e, "shield", 1, "T002")
    record = []
    _drive(e, play_key="play:T184", choose_cid=target, record=record,
           stop=lambda e: e.s.cards[t052].zone == "shield" and len(e.zlist("hand", 1)) == 3)
    c = e.s.cards[t052]
    assert c.zone == "shield" and c.face_up is True
    assert t052 in e.zlist("shield", 1)                     # 持ち主（相手）のシールドのトップ
    assert [e.cdef(u).id for u in c.under] == ["T002"]      # 選んだ束の上に重なった
    assert len(e.zlist("hand", 1)) == 3                     # T052 の「表向きで置かれた時」が相手に3ドローさせた
    picks = [d for d in record if d["kind"] == "choose_cards"]
    assert len(picks) == 1 and picks[0]["player"] == 0      # 束の選択は使用者（自分）の決定
    assert target in [o["cid"] for o in picks[0]["options"]]


def test_covered_face_up_card_stays_face_up_and_counts_via_bundle_of(rr):
    """(3) 覆われた旧トップは face_up のまま残り、bundle_of＋face_up フィルタで
    数え・選択できる（ユーザー決定）。素の zone: shield はトップだけを見る。"""
    e = setup(rr, {"hand": ["T185", "T183"], "mana": ["T003", "T004"] * 6, "shield": ["T001"]},
              {"shield": ["T001"]})
    t001 = _cid(e, "shield", 0, "T001")
    t183 = _cid(e, "hand", 0, "T183")
    _drive(e, play_key="play:T185", yes_seq=["yes", "no"], stop=lambda e: e.s.cards[t001].face_up)
    assert e.s.cards[t001].face_up is True
    _drive(e, play_key="play:T183", stop=lambda e: e.s.cards[t183].zone == "shield")
    c = e.s.cards[t001]
    assert c.zone == "shield" and c.face_up is True and c.top_of == t183   # 覆われても表向きのまま
    env = {"you": 0}
    sel = {"bundle_of": {"zone": "shield", "owner": "you"}, "filter": {"face_up": True}}
    assert sorted(e.candidates(sel, env)) == sorted([t001, t183])
    assert e.eval_expr({"count": sel}, env) == 2
    plain = {"zone": "shield", "owner": "you", "filter": {"face_up": True}}
    assert e.candidates(plain, env) == [t183]               # 素のセレクタはトップだけ（変換では bundle_of を使う）


def test_flip_fires_no_placed_trigger_and_galaxy_summon_next_turn(rr):
    """(4) flip_up はイベントを作らない: 「置かれた時」（R106）も「表向きで置かれた時」
    （T052 自身）も誘発しない。反転したギャラクシールドは次の自分のターンのはじめに
    状態条件で召喚される（相手のターンのはじめでは召喚されない）。"""
    e = setup(rr, {"hand": ["T185"], "mana": ["T003", "T004"] * 2, "shield": ["T052"], "bz": ["R106"]},
              {"shield": ["T001"]})
    t052 = _cid(e, "shield", 0, "T052")
    assert e.s.cards[t052].face_up is False
    record = []
    _drive(e, play_key="play:T185", record=record,
           yes_fn=lambda e_, d: "no" if e_.s.cards[t052].face_up else "yes",
           stop=lambda e: e.s.cards[t052].face_up)
    assert e.s.cards[t052].zone == "shield"
    assert len(e.zlist("hand", 0)) == 0                     # ドロー誘発は一切発火していない
    assert sum(1 for d in record if d["kind"] == "yes_no") == 2   # T185 の may 2回だけ（余分な誘発の may が無い）
    seen = []

    def hook(e_, d):
        seen.append((e_.s.active, e_.s.cards[t052].zone))
        return False

    _drive(e, hook=hook, stop=lambda e: e.s.cards[t052].zone == "bz")
    assert e.s.active == 0                                  # 次の自分のターンのはじめに召喚された
    assert all(z == "shield" for a, z in seen if a == 1)    # 相手のターンの間はシールドにいた（召喚されない）


def test_modal_flips_covered_card_both_ways(rr):
    """(5) modal（R107、シンクロ・ルピア呪文面の型）で束の中のカードを表向きにも
    裏向きにもできる。反転では「置かれた時」（R106）は誘発しない。"""
    e = setup(rr, {"hand": ["R107", "R107"], "mana": ["T003"] * 6, "shield": ["T001"], "bz": ["R106"]},
              {"shield": ["T001"]})
    top = _cid(e, "shield", 0, "T001")
    pool = e.zlist("deck", 0)[0]
    e._raw_move(pool, "shield")
    e.zlist("shield", 0).remove(pool)
    e.s.cards[top].under.append(pool)
    e.s.cards[pool].top_of = top
    assert e.s.cards[pool].face_up is False
    record = []
    _drive(e, play_key="play:R107", modes=[0], choose_cid=pool, record=record,
           stop=lambda e: e.s.cards[pool].face_up)
    assert e.s.cards[pool].face_up is True                  # 束の中のカードを表向きにできた
    assert e.s.cards[top].face_up is False                  # トップは変わらない
    assert [e.cdef(c).id for c in e.zlist("hand", 0)] == ["R107"]   # R106 のドローは無い（残り手札は R107 1枚）
    _drive(e, play_key="play:R107", modes=[1], choose_cid=pool, record=record,
           stop=lambda e: not e.s.cards[pool].face_up)
    assert e.s.cards[pool].face_up is False                 # 裏向きにも戻せる
    assert sum(1 for c in e.zlist("graveyard", 0) if e.cdef(c).id == "R107") == 2
    assert all(e.cdef(c).id != "R107" for c in e.zlist("hand", 0))   # 手札に残るのはターン開始時のドローだけ
    assert sum(1 for d in record if d["kind"] == "yes_no") == 2      # may は各呪文に1回だけ（R106 の may は無い）


def test_saiki_stacks_on_shield_instead_of_graveyard(rr):
    """(7) 裁キ型（T183）: 唱えた後の墓地送りが置換され、自分のシールドの上に
    表向きで重なる。束は1つのシールドのまま。"""
    e = setup(rr, {"hand": ["T183"], "mana": ["T004"] * 4}, {"shield": ["T001"]})
    t183 = _cid(e, "hand", 0, "T183")
    _drive(e, play_key="play:T183", stop=lambda e: e.s.cards[t183].zone == "shield")
    c = e.s.cards[t183]
    assert c.face_up is True
    assert [e.cdef(u).id for u in c.under] == ["T001"]      # 既存シールドの上に重なった
    assert len(e.zlist("shield", 0)) == 5
    assert t183 not in e.zlist("graveyard", 0)
    assert len(e.zlist("hand", 0)) == 1                     # 呪文のドロー1枚


def test_saiki_without_shield_goes_to_graveyard(rr):
    """(7) 自分のシールドが無い場合は重ねられないので、通常どおり墓地に置かれる。"""
    e = setup(rr, {"hand": ["T183"], "mana": ["T004"] * 4, "shield": []}, {"shield": ["T001"]})
    t183 = _cid(e, "hand", 0, "T183")
    seen = set()

    def hook(e_, d):
        seen.add(e_.s.cards[t183].zone)
        return False

    _drive(e, play_key="play:T183", hook=hook,
           stop=lambda e: e.s.turn >= 2 and e.s.cards[t183].zone == "graveyard")
    assert e.s.cards[t183].zone == "graveyard"
    assert "shield" not in seen                             # 一度もシールドゾーンには置かれていない
    assert len(e.zlist("shield", 0)) == 0


def test_stacked_evolution_keeps_its_unders_below(rr):
    """(8) 進化クリーチャーを重ねると、その下のカードは新しいトップの直下に残り、
    その下に旧束が続く（順序: 新トップ → 自分の下 → 旧トップ → 旧トップの下）。"""
    e = setup(rr, {"hand": ["T184"], "mana": ["T004", "T003"] * 4},
              {"bz": ["T005"], "shield": ["T004"], "hand": ["T002"]})
    top5 = _cid(e, "bz", 1, "T005")
    und2 = _cid(e, "hand", 1, "T002")
    e._raw_move(und2, "bz")
    e.zlist("bz", 1).remove(und2)
    e.s.cards[top5].under.append(und2)
    e.s.cards[und2].top_of = top5
    _drive(e, play_key="play:T184", stop=lambda e: e.s.cards[top5].zone == "shield")
    c = e.s.cards[top5]
    assert c.face_up is True
    assert [e.cdef(u).id for u in c.under] == ["T002", "T004"]
    assert all(e.s.cards[u].top_of == top5 for u in c.under)
    assert len(e.zlist("shield", 1)) == 1                   # 束は1つのシールド
