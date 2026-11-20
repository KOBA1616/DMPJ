"""語彙パイロット第317弾: all_civilizations_condition
（「すべての文明が揃っていれば」）— ドリフト（追加語彙なし）。

対象は純粋3件: dm26sd1-b013 フェアリー・ミラクル /
dm27-050 ゴレン・キャノン / dm26sd1-b005 魔誕と光喜と
楽識と炎怒と哀樹の決断。第316弾で「マナ全文明条件の
イディオム検証が未了」として残された候補。

条件の確立イディオムは登録済み dmx16-064 奇跡の面
ボアロジー（フェアリー・ミラクルと同文の CIP）と同一:
{op: if, cond: {all: [cmp: [{count: {zone: mana, owner: you,
filter: {civs: [文明]}}}, ">=", 1] ×5文明]}, then: [...]}。
「すべての文明」は5文明（光・水・闇・火・自然）で、
多色カードは各文明を満たす。山札の上から置く形は
from_top: 1（登録多数形。dmx16-064 の count: 1 形と
指す先は同じ）。

- 形A（b013）: mana_put の後に if を置く（条件は1枚目を
  置いた後に判定する。本文の「置く。揃っていれば、もう
  1枚」の順序どおり）。
- 形B（dm27-050）: destroy の後に同型の if＋destroy。
- 形C（b005）: 条件は「自分のエレメント」であって
  マナゾーンではない。総合ルール403.1（エレメントを
  参照する効果は、他のゾーンの記載がない限りバトル
  ゾーンのエレメントのみを参照する）により zone: bz で
  数える。根拠: 本カードは5文明コストのため、通常の
  唱え方では支払い時点でマナに5文明が必ず揃い、マナ
  読みでは置換条項が無条件になってしまう（カードの
  設計上ありえない）。dmwiki のカードページの達成例も
  魔法陣サイクル・デドダム等のバトルゾーンのカード
  のみ。本体テストで「マナ全文明でも場が揃わなければ
  不成立」を判別テストとして固定する。なお第145弾の
  バラバラエティ（コスト参照）は本弾では触らない。
  本体は {op: if, cond, then: [may [modal 全モード]
  else [modal 2回・同選択可]], else: [modal 2回]}。
  modal {count: 5}（モード5種・repeat なし）は全選択が
  自動決定され、書かれた順に解決する（公式の解決順）。
  モードは既存先例の合成: シールド化＝move to: shield /
  reason: charge（dm22ex2-068）、2ドロー、見ないで捨て
  させる＝discard chooser: random（dm24ex1-003）、
  エレメント破壊＝destroy {zone: bz, filter: cost_le}
  （dm26rp3-011 モード3）、マナ置き＋may でマナ回収
  （move to: hand / reason: return の先例形）。

プロト:
- T972: 形A（自然3コスト呪文。dm26sd1-b013 型）
- T973: 形B（火5コスト呪文。dm27-050 型）
- T974: 形C（5文明5コスト呪文。dm26sd1-b005 型）
対照には既存の T001（自然）/ T004（光・3000）/ T008（闇）/
T010（水・4000）/ T030（光水）/ T034（火・3000）を使う。
"""
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()

CIVS5 = ["light", "water", "darkness", "fire", "nature"]


def _all_civs(zone):
    return {"all": [{"cmp": [{"count": {"zone": zone, "owner": "you",
                                         "filter": {"civs": [c]}}},
                             ">=", 1]}
                    for c in CIVS5]}


# parse_card はマクロを展開するため、期待形は展開形で書く
# （提出形・プロトの原文は mana_put / destroy / discard の
# マクロ表記。変換後の格納形もマクロ表記のまま）
MANA_PUT_TOP = {"op": "move",
                "select": {"zone": "deck", "owner": "you", "from_top": 1},
                "to": "mana", "reason": "put"}
DESTROY_3000 = {"op": "move",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"],
                                      "power_le": 3000},
                           "count": 1},
                "to": "graveyard", "reason": "destroy"}

FORM_A = [MANA_PUT_TOP,
          {"op": "if", "cond": _all_civs("mana"), "then": [MANA_PUT_TOP]}]
FORM_B = [DESTROY_3000,
          {"op": "if", "cond": _all_civs("mana"), "then": [DESTROY_3000]}]

MODES = [
    [{"op": "move",
      "select": {"zone": "deck", "owner": "you", "from_top": 1},
      "to": "shield", "reason": "charge"}],
    [{"op": "draw", "count": 2}],
    [{"op": "move",
      "select": {"zone": "hand", "owner": "opp", "count": 1,
                 "chooser": "random"},
      "to": "graveyard", "reason": "discard"}],
    [{"op": "move",
      "select": {"zone": "bz", "owner": "opp",
                 "filter": {"cost_le": 6}, "count": 1},
      "to": "graveyard", "reason": "destroy"}],
    [MANA_PUT_TOP,
     {"op": "may",
      "body": [{"op": "move",
                "select": {"zone": "mana", "owner": "you", "count": 1},
                "to": "hand", "reason": "return"}]}],
]
_MODAL_ALL = {"op": "modal", "count": 5, "modes": MODES}
_MODAL_TWO = {"op": "modal", "count": 2, "repeat": True, "modes": MODES}
FORM_C = [{"op": "if", "cond": _all_civs("bz"),
           "then": [{"op": "may", "body": [_MODAL_ALL],
                     "else": [_MODAL_TWO]}],
           "else": [_MODAL_TWO]}]


def _by_defn(e, zone, defn, player=0):
    return [c for c in e.zlist(zone, player)
            if e.s.cards[c].defn == defn
            and (zone != "bz" or e.s.cards[c].controller == player)]


def _count(e, zone, player=0):
    return len(e.zlist(zone, player))


def _run(e, handler, limit=900, done=None):
    for _ in range(limit):
        if e.s.result is not None or (done and done()):
            return
        d = e.advance()
        if d is None:
            return
        r = handler(e, d)
        if r is not None:
            e.answer(r)
            continue
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))


def _cast_hook(tid, extra=None):
    def hook(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 0 \
                and f"play:{tid}" in keys:
            return [keys.index(f"play:{tid}")]
        if d["kind"] == "pay_mana":
            return [0]
        if extra:
            return extra(e, d, keys)
        return None
    return hook


# ---------------------------------------------------------------- parse

def test_parse_forms(rules):
    d = parse_card(proto_card("T972"), TABLES)
    assert d.types == ["spell"] and d.civs == ["nature"] and d.cost == 3
    assert d.spell == FORM_A
    d = parse_card(proto_card("T973"), TABLES)
    assert d.types == ["spell"] and d.civs == ["fire"] and d.cost == 5
    assert d.spell == FORM_B
    d = parse_card(proto_card("T974"), TABLES)
    assert d.types == ["spell"] and d.civs == CIVS5 and d.cost == 5
    assert d.spell == FORM_C


# ---------------------------------------------------------------- 形A

def test_form_a_second_put_when_completed_by_first(rules):
    # マナは火だけ欠け、山札の上が火。1枚目を置いた時点で
    # 全文明が揃うため、もう1枚置く（条件判定は1枚目の後）
    e = setup(rules,
              {"hand": ["T972"], "deck": ["T034"],
               "mana": ["T004", "T010", "T008", "T001"]},
              {"hand": ["T001"]})
    _run(e, _cast_hook("T972"),
         done=lambda: len(_by_defn(e, "graveyard", "T972", 0)) == 1)
    mana = [e.s.cards[c].defn for c in e.zlist("mana", 0)]
    assert len(mana) == 6, mana
    assert mana.count("T034") == 1          # 山札の上の火が入った
    assert mana.count("T001") == 2          # 2枚目は次の山札（自然）


def test_form_a_no_second_put_when_still_missing(rules):
    # 山札の上が既にある自然では火が揃わず、2枚目は置かない
    e = setup(rules,
              {"hand": ["T972"], "deck": ["T001"],
               "mana": ["T004", "T010", "T008", "T001"]},
              {"hand": ["T001"]})
    _run(e, _cast_hook("T972"),
         done=lambda: len(_by_defn(e, "graveyard", "T972", 0)) == 1)
    mana = [e.s.cards[c].defn for c in e.zlist("mana", 0)]
    assert len(mana) == 5, mana
    assert "T034" not in mana


# ---------------------------------------------------------------- 形B

def test_form_b_destroys_twice_when_all_civs(rules):
    # 全文明がマナに揃えば2体目も破壊する。パワー4000は
    # 3000以下のフィルタで常に対象外
    e = setup(rules,
              {"hand": ["T973"],
               "mana": ["T004", "T010", "T008", "T034", "T001"]},
              {"bz": ["T001", "T004", "T010"]})
    _run(e, _cast_hook("T973"),
         done=lambda: len(_by_defn(e, "graveyard", "T973", 0)) == 1)
    assert len(_by_defn(e, "graveyard", "T001", 1)) == 1
    assert len(_by_defn(e, "graveyard", "T004", 1)) == 1
    assert len(_by_defn(e, "bz", "T010", 1)) == 1


def test_form_b_destroys_once_without_all_civs(rules):
    e = setup(rules,
              {"hand": ["T973"], "mana": ["T034"] * 5},
              {"bz": ["T001", "T004"]})
    _run(e, _cast_hook("T973"),
         done=lambda: len(_by_defn(e, "graveyard", "T973", 0)) == 1)
    dead = len(_by_defn(e, "graveyard", "T001", 1)) \
        + len(_by_defn(e, "graveyard", "T004", 1))
    alive = len(_by_defn(e, "bz", "T001", 1)) \
        + len(_by_defn(e, "bz", "T004", 1))
    assert dead == 1 and alive == 1


# ---------------------------------------------------------------- 形C

def _c1_extra(st):
    def extra(e, d, keys):
        if d["kind"] == "yes_no":
            st["yes_no"] = st.get("yes_no", 0) + 1
            return [0]                       # すべて使う／回収する
        if d["kind"] == "choose_mode":
            return list(range(len(keys)))    # 全選択（自動決定の保険）
        return None
    return extra


def test_form_c_all_modes_once_when_bz_all_civs(rules):
    # 場のエレメントに全文明が揃い、全モード使用を選ぶと
    # 5モードが書かれた順に1回ずつ解決する
    st = {}
    e = setup(rules,
              {"hand": ["T974"],
               "mana": ["T004", "T010", "T008", "T034", "T001"],
               "bz": ["T030", "T008", "T034", "T001"]},
              {"hand": ["T001", "T001"], "bz": ["T001"]})
    _run(e, _cast_hook("T974", _c1_extra(st)),
         done=lambda: len(_by_defn(e, "graveyard", "T974", 0)) == 1
         and _count(e, "hand", 0) == 3)
    assert st.get("yes_no") == 2             # 全使用の may＋回収の may
    assert _count(e, "shield", 0) == 6       # モード1: シールド化
    assert _count(e, "hand", 0) == 3         # モード2: 2ドロー＋モード5: 回収1
    assert _count(e, "hand", 1) == 1         # モード3: 見ないで1枚捨て
    assert len(_by_defn(e, "graveyard", "T001", 1)) == 2  # 捨て札＋モード4の破壊
    assert _count(e, "mana", 0) == 5         # 5＋1（モード5）−1（回収）


def test_form_c_mana_all_civs_is_not_enough(rules):
    # 判別テスト: マナに全文明が揃っていても、場の
    # エレメントが揃っていなければ置換は提示されない
    # （条件はバトルゾーン参照。403.1）
    st = {"modes": [], "yes_no": 0}

    def extra(e, d, keys):
        if d["kind"] == "yes_no":
            st["yes_no"] += 1
            return [0]
        if d["kind"] == "choose_mode":
            st["modes"].append(1)
            return [keys.index("mode:1")]   # ドローを2回選ぶ
        return None

    e = setup(rules,
              {"hand": ["T974"],
               "mana": ["T004", "T010", "T008", "T034", "T001"]},
              {"hand": ["T001"]})
    _run(e, _cast_hook("T974", extra),
         done=lambda: len(_by_defn(e, "graveyard", "T974", 0)) == 1
         and _count(e, "hand", 0) == 4)
    assert st["yes_no"] == 0                 # 置換の may は出ない
    assert st["modes"] == [1, 1]             # 通常の2回選択（同選択可）
    assert _count(e, "hand", 0) == 4
    assert _count(e, "shield", 0) == 5


def test_form_c_decline_falls_back_to_two_picks(rules):
    # 場が揃っていても全使用を断れば通常の2回選択になる
    st = {"yes_no": 0, "modes": []}

    def extra(e, d, keys):
        if d["kind"] == "yes_no":
            st["yes_no"] += 1
            return [1]                       # 断る
        if d["kind"] == "choose_mode":
            st["modes"].append(1)
            return [keys.index("mode:1")]
        return None

    e = setup(rules,
              {"hand": ["T974"],
               "mana": ["T004", "T010", "T008", "T034", "T001"],
               "bz": ["T030", "T008", "T034", "T001"]},
              {"hand": ["T001"]})
    _run(e, _cast_hook("T974", extra),
         done=lambda: len(_by_defn(e, "graveyard", "T974", 0)) == 1
         and _count(e, "hand", 0) == 4)
    assert st["yes_no"] == 1                 # 置換の may は提示された
    assert st["modes"] == [1, 1]
    assert _count(e, "hand", 0) == 4
    assert _count(e, "shield", 0) == 5       # シールド化はしていない
