"""語彙パイロット第330弾 destroyed_while_tapped の検証。

対象は pure 2件:
- dm26ex1-021 勝利龍装 クラッシュ"覇道"（B・A・D ２／スピード
  アタッカー／W・ブレイカー／破壊された時、これがタップされて
  いれば、このターンの後に自分のターンを追加する／バトル中、
  このクリーチャーのパワーを+5000する）
- dmr18-s04 超復讐 ギャロウィン（進化／侵略／このクリーチャー
  または自分の他のクリーチャーが破壊された時、このクリーチャー
  がタップしていたら、相手のクリーチャーを１体破壊し、
  《超復讐 ギャロウィン》以外の闇のクリーチャーを１体自分の
  墓地から手札に戻す）

結論はエンジン拡張（条件キー subject_tapped の追加）:
「破壊された時、これがタップされていれば」は、破壊された
カード自身が移動直前にタップしていたかを条件にする。移動
イベントの収集レコードには対象の lki（移動直前の姿）が
`tapped` を含んで載る（events.py の lki スナップショット）が、
それを読む条件キーが無かった。新条件 {subject_tapped: bool} は
env["event"]["lki"]["tapped"] を読む（alt_paid / vivid_paid が
event の旗を読むのと同じ作法）。defs.py Checker.cond と
schema.py（card.schema.json 再生成）に同キーを追加する3点セット
＋ selectors.py の eval_cond。

他の条項は既存形: 追加ターンは op extra_turn、バトル中の
パワー修整は mod {battle_power: {amount: 5000}}、自分の他の
クリーチャーが破壊された場合のタップ条件は partial どおり
exists {ref: self, filter: {tapped: true}}。

proto T1001 = dm26ex1-021 型、T1002 = dmr18-s04 型、
T1003 = 駆動用の破壊呪文。
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402
from tests.conftest import setup  # noqa: E402

TABLES = load_tables()

BAD = {"kind": "static", "affects": "self", "zone": "hand",
       "mod": {"opt_reduce": {"amount": 2, "then": "destroy"}}}

DESTROYED_TAPPED_330 = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "subject": "self"},
    "if": {"subject_tapped": True},
    "effect": [{"op": "extra_turn"}]}

BATTLE_POWER = {"kind": "static", "affects": "self",
                "mod": {"battle_power": {"amount": 5000}}}

FORM_1001 = [BAD, DESTROYED_TAPPED_330, BATTLE_POWER]

DECLARE = {"kind": "declare", "zone": "hand",
           "when": {"event": "attack",
                    "subject": {"owner": "you",
                                "filter": {"civs": ["darkness"],
                                           "race_has": "コマンド"}}},
           "effect": [{"op": "may",
                       "body": [{"op": "invade",
                                 "onto": {"ref": "event.subject"}}]}]}

EFFECT_1002 = [
    {"op": "destroy",
     "select": {"zone": "bz", "owner": "opp",
                "filter": {"types": ["creature"]}, "count": 1}},
    {"op": "move",
     "select": {"zone": "graveyard", "owner": "you",
                "filter": {"civs": ["darkness"],
                           "types": ["creature"],
                           "not_name": "試験用ギャロウィン"},
                "count": 1},
     "to": "hand", "reason": "return"}]

OTHER_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy",
             "subject": {"owner": "you", "other": True,
                         "filter": {"types": ["creature"]}}},
    "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
    "effect": EFFECT_1002}

SELF_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "subject": "self"},
    "if": {"subject_tapped": True},
    "effect": EFFECT_1002}

FORM_1002 = [DECLARE, OTHER_TRIGGER, SELF_TRIGGER]


def test_proto_parse_and_forms():
    c = proto_card("T1001")
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    assert c["abilities"] == FORM_1001
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    c = proto_card("T1002")
    assert c["abilities"] == FORM_1002
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    c = proto_card("T1003")
    assert c["spell"] == [{"op": "destroy",
                           "select": {"zone": "bz", "owner": "you",
                                      "filter": {"types": ["creature"]},
                                      "count": 1}}]
    parse_card(c, TABLES)


# ---------- ドライバ ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _cast_destroy_own(e, target_defn, tap_defn=None):
    """T1003 を唱え、自分の target_defn を破壊する。破壊後の誘発の
    選択（破壊対象・回収対象）まで処理する。tap_defn を指定すると、
    唱える直前にそのクリーチャーをタップ状態にする（セットアップ
    直後のタップ指定はターン開始のアンタップで消えるため、main の
    決定時点で指定する）。"""
    cast = False
    destroyed = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended before destroy"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T1003" in keys:
            if tap_defn is not None:
                e.s.cards[_bz(e, 0, tap_defn)].tapped = True
            e.answer([keys.index("play:T1003")])
            cast = True
            continue
        if cast and d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if cast and d["kind"] == "choose_cards":
            pick = next((k for k in keys if target_defn in k), None)
            if pick is not None and not destroyed:
                e.answer([keys.index(pick)])
                destroyed = True
            else:
                e.answer([0])
            continue
        if cast and d["kind"] in ("charge", "main", "attack"):
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("destroy did not resolve")


def _destroy_then_next_charge(e, tap):
    """T1001 を T1003 で破壊し（tap=True なら直前にタップ状態に
    する）、そのターンの後に来る最初の charge 決定の
    （プレイヤー, extra_turn 旗）を返す。"""
    cast = False
    destroyed = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T1003" in keys:
            if tap:
                e.s.cards[_bz(e, 0, "T1001")].tapped = True
            e.answer([keys.index("play:T1003")])
            cast = True
            continue
        if cast and _in_zone(e, 0, "graveyard", "T1001"):
            destroyed = True
        if destroyed and d["kind"] == "charge":
            return d.get("player"), bool(e.s.extra_turn)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("next charge did not appear")


def test_destroyed_while_tapped_grants_extra_turn():
    """T1001: タップ状態で破壊されると、このターンの後に自分の
    ターンが追加される（次の charge は自分の追加ターン。
    subject_tapped が lki の tapped を読む）。"""
    rules = load_rules()
    e = setup(rules, {"bz": ["T1001"], "hand": ["T1003"],
                      "mana": ["T053"]}, {})
    player, is_extra = _destroy_then_next_charge(e, tap=True)
    assert _in_zone(e, 0, "graveyard", "T1001")
    assert (player, is_extra) == (0, True), (player, is_extra)


def test_destroyed_while_untapped_no_extra_turn():
    """T1001: アンタップ状態で破壊されても追加ターンは得ない
    （次の charge は相手の通常ターン）。"""
    rules = load_rules()
    e = setup(rules, {"bz": ["T1001"], "hand": ["T1003"],
                      "mana": ["T053"]}, {})
    player, is_extra = _destroy_then_next_charge(e, tap=False)
    assert _in_zone(e, 0, "graveyard", "T1001")
    assert (player, is_extra) == (1, False), (player, is_extra)


def test_battle_power_plus_5000():
    """T1001: バトル中はパワー+5000（9000+5000 > 13000 で
    T1004（ブロッカー）に勝つ。通常時 9000 なら負ける）。"""
    rules = load_rules()
    e = setup(rules, {"bz": ["T1001"]}, {"bz": ["T1004"]})
    t = _bz(e, 0, "T1001")
    e.s.cards[t].entered_turn = -1
    blocked = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended before battle"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:T1001:player" in keys:
            e.answer([keys.index("attack:T1001:player")])
            continue
        if d["kind"] == "block":
            pick = next((k for k in keys if "T1004" in k), None)
            assert pick is not None, keys
            e.answer([keys.index(pick)])
            blocked = True
            continue
        if blocked and d["kind"] in ("charge", "main", "attack"):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert blocked
    assert _in_zone(e, 1, "graveyard", "T1004")
    assert e.s.cards[_bz(e, 0, "T1001")].zone == "bz"


def test_self_destroyed_while_tapped():
    """T1002: 自分がタップ状態で破壊されると、相手のクリーチャーを
    1体破壊し、闇のクリーチャーを墓地から手札に戻す。"""
    rules = load_rules()
    e = setup(rules, {"bz": ["T1002"], "graveyard": ["T053"],
                      "hand": ["T1003"], "mana": ["T053"]},
              {"bz": ["T004"]})
    _cast_destroy_own(e, "T1002", tap_defn="T1002")
    assert _in_zone(e, 0, "graveyard", "T1002")
    assert _in_zone(e, 1, "graveyard", "T004")
    assert _in_zone(e, 0, "hand", "T053")


def test_self_destroyed_while_untapped():
    """T1002: 自分がアンタップ状態で破壊されても効果は誘発しない。"""
    rules = load_rules()
    e = setup(rules, {"bz": ["T1002"], "graveyard": ["T053"],
                      "hand": ["T1003"], "mana": ["T053"]},
              {"bz": ["T004"]})
    _cast_destroy_own(e, "T1002")
    assert _in_zone(e, 0, "graveyard", "T1002")
    assert e.s.cards[_bz(e, 1, "T004")].zone == "bz"
    assert _in_zone(e, 0, "graveyard", "T053")


def test_other_destroyed_while_self_tapped():
    """T1002: 自分の他のクリーチャーが破壊された時、このクリーチャー
    がタップしていれば効果が誘発する（partial の既存形）。"""
    rules = load_rules()
    e = setup(rules, {"bz": ["T1002", "T001"], "graveyard": ["T053"],
                      "hand": ["T1003"], "mana": ["T053"]},
              {"bz": ["T004"]})
    _cast_destroy_own(e, "T001", tap_defn="T1002")
    assert _in_zone(e, 0, "graveyard", "T001")
    assert _in_zone(e, 1, "graveyard", "T004")
    assert _in_zone(e, 0, "hand", "T053")
