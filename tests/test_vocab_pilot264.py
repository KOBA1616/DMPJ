"""第264弾: 誘発の2度トリガー（trigger_doubling）。

常在 mod trigger_double {when, source?, source_subject?, may?, once_per_turn?,
first_per_turn?, cost?} を追加する。誘発の収集時（_collect_triggers）に、
条件に合う誘発型能力へ適用する:
- 強制: その場で pending を複製する（2度目の解決は vars を分ける）。
- 任意 (may): 同じ窓に double_ask の pending を積み、解決時に決定を尋ねる。
  対象が先に解決されていたら尋ねない。once_per_turn は「はい」で消費し、
  first_per_turn は最初の一致で枠を使い切る（断ってもそのターンはもう来ない）。
- 継続的効果（modify で付与）も見る。呪文 T725 の付与型がその経路。
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _by_defn(e, zone, p):
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


def _in_zone(e, zone, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _hand_n(e, p=0):
    return len(e.zlist("hand", p))


def _drive(e, stop, choose=None, play=None, attack_with=None, attacker=0, dbl=None, limit=800):
    """汎用ドライバ（第263弾のものを流用し、order_pending / choose_double_trigger を足す）。
    dbl は (e, d) -> 選択肢の添字。None なら「はい」。"""
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "order_pending":
            hit = next((i for i, k in enumerate(keys) if k.startswith("pending:double_ask:")), None)
            e.answer([hit if hit is not None else 0])
            if stop(e):
                return
            continue
        if kind == "choose_double_trigger":
            ans = dbl(e, d) if dbl is not None else 0
            e.answer([ans])
            if stop(e):
                return
            continue
        if kind == "choose_cards" and choose is not None:
            ans = choose(e, d)
            if ans is not None:
                e.answer(ans)
                if stop(e):
                    return
                continue
        if kind == "main" and play is not None:
            ans = play(e, d)
            if ans is not None:
                e.answer(ans)
                if stop(e):
                    return
                continue
        if kind == "attack" and attack_with is not None and e.s.active == attacker:
            hit = next((i for i, k in enumerate(keys)
                        if k.startswith(f"attack:{attack_with}:")), None)
            if hit is not None:
                e.answer([hit])
                if stop(e):
                    return
                continue
        if kind == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if stop(e):
            return
    raise AssertionError("limit reached")


def _play(defn, seen, max_n=1):
    """main で defn を max_n 回まで出す play フック。"""
    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if f"play:{defn}" in keys and seen["n"] < max_n:
            seen["n"] += 1
            return [keys.index(f"play:{defn}")]
        return None
    return play


def _pick_defn(defn):
    """choose_cards で defn のカードを1枚選ぶ。"""
    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == defn]
        assert idx, f"選択対象の {defn} が候補に無い"
        return idx[:1]
    return choose


# ---------- parse / validation ----------

def test_pilot264_protos_parse():
    rules = load_rules()
    assert rules.cards["T717"].abilities[0]["mod"]["trigger_double"]["when"] == \
        {"event": "move", "to": "bz", "subject": {"owner": "you", "filter": {"types": ["creature"]}}}
    assert rules.cards["T717"].abilities[0]["mod"]["trigger_double"]["source_subject"] is True
    td = rules.cards["T719"].abilities[0]["mod"]["trigger_double"]
    assert td["may"] is True and td["once_per_turn"] is True
    td = rules.cards["T720"].abilities[0]["mod"]["trigger_double"]
    assert td["may"] is True and td["first_per_turn"] is True
    assert rules.cards["T724"].abilities[0]["mod"]["trigger_double"]["cost"] == \
        [{"op": "tap", "select": {"ref": "self"}}]
    assert rules.cards["T725"].spell[1]["mod"]["trigger_double"]["when"] == \
        {"event": "attack", "subject": "self"}
    assert rules.cards["T726"].abilities[0]["mod"]["trigger_double"]["source"] == \
        {"owner": "you", "filter": {"types": ["creature"]}}


def test_trigger_double_validation():
    base = {"id": "test-264", "name": "試験", "types": ["creature"], "civs": ["water"],
            "cost": 3, "power": 3000, "races": ["テスト"], "text": "",
            "source": {"official": "test-264", "review": "pending"}}

    def card(td):
        return dict(base, abilities=[{"kind": "static", "affects": "self",
                                      "mod": {"trigger_double": td}}])

    entry = {"event": "move", "to": "bz",
             "subject": {"owner": "you", "filter": {"types": ["creature"]}}}
    with pytest.raises(DefError):   # when が無い
        parse_card(card({"source_subject": True}), TABLES)
    with pytest.raises(DefError):   # 知らないイベント
        parse_card(card({"when": {"event": "explode"}}), TABLES)
    with pytest.raises(DefError):   # source の owner が不正
        parse_card(card({"when": entry, "source": {"owner": "me"}}), TABLES)
    with pytest.raises(DefError):   # cost は may が要る
        parse_card(card({"when": entry, "cost": [{"op": "tap", "select": {"ref": "self"}}]}), TABLES)
    with pytest.raises(DefError):   # may は bool のみ
        parse_card(card({"when": entry, "may": 1}), TABLES)
    parse_card(card({"when": entry, "source_subject": True}), TABLES)
    parse_card(card({"when": entry, "source": {"owner": "you", "filter": {"types": ["creature"]},
                                               "other": True},
                      "may": True, "once_per_turn": True,
                      "cost": [{"op": "tap", "select": {"ref": "self"}}]}), TABLES)
    parse_card(card({"when": entry, "source": "self", "may": True,
                      "first_per_turn": True}), TABLES)


# ---------- 強制の出た時2度トリガー（T717 / T718） ----------

def test_mandatory_entry_doubling():
    """T717 がいれば出た時ドローが2度トリガーし、2枚引く。"""
    e = setup(load_rules(), {"bz": ["T717"], "hand": ["T718"], "mana": ["T718", "T718"]}, {})
    seen = {"n": 0}
    _drive(e, lambda e: e.s.turn == 1 and seen["n"] == 1 and _hand_n(e) == 2,
           play=_play("T718", seen))
    assert _hand_n(e) == 2   # 初期1枚 - 召喚1枚 + 出た時2枚（先攻1ターン目はドローなし）


def test_entry_no_doubler_single():
    """2度トリガーが無ければ出た時ドローは1枚だけ。"""
    e = setup(load_rules(), {"hand": ["T718"], "mana": ["T718", "T718"]}, {})
    seen = {"n": 0}
    _drive(e, lambda e: e.s.turn == 1 and seen["n"] == 1 and _hand_n(e) == 1,
           play=_play("T718", seen))
    assert _hand_n(e) == 1


def test_bystander_not_doubled():
    """T717 は「出たクリーチャー自身の能力」だけを2度にする。傍観者 T728 の誘発は1回だけ。
    T718 の出た時2枚 + T728 の傍観者1枚 = 3枚引く。"""
    e = setup(load_rules(), {"bz": ["T717", "T728"], "hand": ["T718"],
                             "mana": ["T718", "T718"]}, {})
    seen = {"n": 0}
    _drive(e, lambda e: e.s.turn == 1 and seen["n"] == 1 and _hand_n(e) == 3,
           play=_play("T718", seen))
    assert _hand_n(e) == 3


# ---------- 任意・ターン1回（T719） ----------

def test_may_once_per_turn_yes_then_used():
    """T719: 1体目は「はい」で2枚、2体目は回数を使い切って1枚。合計3枚引く。"""
    e = setup(load_rules(), {"bz": ["T719"], "hand": ["T718", "T718"],
                             "mana": ["T718"] * 4}, {})
    seen = {"n": 0}
    asks = {"n": 0}

    def dbl(e, d):
        asks["n"] += 1
        return 0   # はい

    _drive(e, lambda e: e.s.turn == 1 and seen["n"] == 2 and _hand_n(e) == 3,
           play=_play("T718", seen, max_n=2), dbl=dbl)
    assert asks["n"] == 1   # 2体目には尋ねない
    assert _hand_n(e) == 3


def test_may_once_per_turn_decline_then_yes():
    """T719: 1体目を断っても回数は残り、2体目で「はい」すれば2枚引ける。合計3枚引く。"""
    e = setup(load_rules(), {"bz": ["T719"], "hand": ["T718", "T718"],
                             "mana": ["T718"] * 4}, {})
    seen = {"n": 0}
    asks = {"n": 0}

    def dbl(e, d):
        asks["n"] += 1
        return 1 if asks["n"] == 1 else 0   # 1回目はいいえ、2回目ははい

    _drive(e, lambda e: e.s.turn == 1 and seen["n"] == 2 and _hand_n(e) == 3,
           play=_play("T718", seen, max_n=2), dbl=dbl)
    assert asks["n"] == 2
    assert _hand_n(e) == 3


# ---------- 任意・ターン初回（T720 / T721） ----------

def test_first_per_turn_tamaseed():
    """T720: 1枚目のタマシードは2枚、2枚目は初回枠を使い切って1枚。合計3枚引く。"""
    e = setup(load_rules(), {"bz": ["T720"], "hand": ["T721", "T721"],
                             "mana": ["T721"] * 4}, {})
    seen = {"n": 0}
    asks = {"n": 0}

    def dbl(e, d):
        asks["n"] += 1
        return 0

    _drive(e, lambda e: e.s.turn == 1 and seen["n"] == 2 and _hand_n(e) == 3,
           play=_play("T721", seen, max_n=2), dbl=dbl)
    assert asks["n"] == 1
    assert _hand_n(e) == 3


def test_first_per_turn_decline_consumes():
    """T720: 1枚目を断ると初回枠を使い切り、2枚目には尋ねず1枚だけ。合計2枚引く。"""
    e = setup(load_rules(), {"bz": ["T720"], "hand": ["T721", "T721"],
                             "mana": ["T721"] * 4}, {})
    seen = {"n": 0}
    asks = {"n": 0}

    def dbl(e, d):
        asks["n"] += 1
        return 1   # いいえ

    _drive(e, lambda e: e.s.turn == 1 and seen["n"] == 2 and _hand_n(e) == 2,
           play=_play("T721", seen, max_n=2), dbl=dbl)
    assert asks["n"] == 1
    assert _hand_n(e) == 2


# ---------- 攻撃による誘発（T722 / T723）と呪文付与（T725） ----------

def test_attack_trigger_doubling():
    """T722 がいれば攻撃時ドローが2度トリガーし、2枚引く。"""
    e = setup(load_rules(), {"bz": ["T722", "T723"]}, {"bz": ["T001"]})
    _drive(e, lambda e: e.s.turn == 1 and _hand_n(e) == 2, attack_with="T723", attacker=0)
    assert _hand_n(e) == 2   # 攻撃時2枚（先攻1ターン目はドローなし・初期手札0枚）


def test_attack_trigger_no_doubler_single():
    """2度トリガーが無ければ攻撃時ドローは1枚だけ。"""
    e = setup(load_rules(), {"bz": ["T723"]}, {"bz": ["T001"]})
    _drive(e, lambda e: e.s.turn == 1 and _hand_n(e) == 1, attack_with="T723", attacker=0)
    assert _hand_n(e) == 1


def test_spell_grants_attack_doubling_for_turn():
    """T725 を唱えたターンの攻撃は2枚引き、次の自分のターン（3ターン目）の攻撃は1枚だけ。"""
    e = setup(load_rules(), {"bz": ["T723"], "hand": ["T725"], "mana": ["T725", "T725"]},
              {"bz": ["T001"]})
    seen = {"n": 0}
    _drive(e, lambda e: e.s.turn == 3 and _hand_n(e) == 4,
           play=_play("T725", seen), choose=_pick_defn("T723"),
           attack_with="T723", attacker=0)
    assert _hand_n(e) == 4   # 1ターン目: 初期1 - 呪文1 + 攻撃2 = 2。3ターン目: ドロー1 + 攻撃1 = 4


# ---------- タップコスト（T724） ----------

def test_tap_cost_doubling():
    """T724 がアンタップなら「はい」でタップして2枚引き、2体目（タップ済み）では尋ねず1枚。
    合計3枚引く。"""
    e = setup(load_rules(), {"bz": ["T724"], "hand": ["T718", "T718"],
                             "mana": ["T718"] * 4}, {})
    seen = {"n": 0}
    asks = {"n": 0}

    def dbl(e, d):
        asks["n"] += 1
        return 0

    _drive(e, lambda e: e.s.turn == 1 and seen["n"] == 2 and _hand_n(e) == 3,
           play=_play("T718", seen, max_n=2), dbl=dbl)
    assert asks["n"] == 1
    assert _hand_n(e) == 3
    assert _by_defn(e, "bz", 0)["T724"] is not None
    assert e.s.cards[_by_defn(e, "bz", 0)["T724"]].tapped is True


# ---------- 離脱時の誘発（T726 / T727） ----------

def test_leave_trigger_doubling():
    """T726 がいれば T727 の離脱時ドローが2度トリガーし、2枚引く。"""
    e = setup(load_rules(), {"bz": ["T726", "T727"], "hand": ["T710"],
                             "mana": ["T710"]}, {"bz": ["T001"]})
    seen = {"n": 0}
    _drive(e, lambda e: e.s.turn == 1 and _in_zone(e, "graveyard", 0, "T727") and _hand_n(e) == 2,
           play=_play("T710", seen), choose=_pick_defn("T727"))
    assert _in_zone(e, "graveyard", 0, "T727")
    assert _hand_n(e) == 2   # 初期1枚 - 呪文1枚 + 離脱時2枚


def test_leave_trigger_no_doubler_single():
    """2度トリガーが無ければ離脱時ドローは1枚だけ。
    単独の待機は order_pending の決定が出ないため、ターン1の決定点が無くターン2で止める。"""
    e = setup(load_rules(), {"bz": ["T727"], "hand": ["T710"], "mana": ["T710"]},
              {"bz": ["T001"]})
    seen = {"n": 0}
    _drive(e, lambda e: e.s.turn == 2 and _in_zone(e, "graveyard", 0, "T727") and _hand_n(e) == 1,
           play=_play("T710", seen), choose=_pick_defn("T727"))
    assert _hand_n(e) == 1
