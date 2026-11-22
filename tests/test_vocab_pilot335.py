"""語彙パイロット第335弾: per_card_tap_or_untap（pure 3件）。

対象:
- dm25bd2-015 清浄の精霊ウル: 「このクリーチャーが出た時、
  クリーチャーを１体選び、タップまたはアンタップする」
- dm24rp2-051 粛清者ゴットハルト: 「このクリーチャーが出た時、
  クリーチャーを２体まで選び、それぞれタップまたは
  アンタップする」
- dm25-002 超鎧亜キングダム・ゲオルグ: 「このクリーチャーが
  攻撃する時、バトルゾーンにある進化ではないクリーチャー
  １体をタップまたはアンタップしてもよい」

結論はドリフト（エンジン拡張なし）。確立形は dm26rp3-055
（ヒトリダチ モンキッド）の形: まず choose
{select: {zone: bz, owner: any, filter: {types: [creature]},
count: 1}, as: target} で対象を束縛し、続けて modal
{modes: [[tap {ref: target}], [untap {ref: target}]]} で
タップ／アンタップを選ぶ。
- ゴットハルトは「２体まで、それぞれ」なので、この
  choose＋modal を repeat {times: 2} の body に置き、
  choose には up_to: true を付ける（dm26sd1-g007 の
  repeat 構造）。
- ゲオルグは攻撃時誘発＋may で包み、choose の filter に
  evolution: false を足す。
- 「マナゾーンに置く時、このカードはタップして置く」は
  既存の扱いに従い原文のみ。

実測で分かった注意点（本弾の教訓）:
- select の owner 既定は "you"。modal のモード内に
  tap {select: ...} を直接書く旧形（dmbd03-004 /
  dmex11-032 / dmex14-082 の登録形）は相手のクリーチャーを
  対象にできず、自分の候補が1体だけだと ask の一意省略
  （min==max==候補数）で決定自体が出ず自動で自分をタップ
  する。dm26sd1-g007 の choose も owner 指定が無く同じ
  制限を持つ。これらの登録カードは潜在的に自軍のみが
  対象になっており、本弾の対象外のため修正はしていない
  （記録のみ）。
- 相手のクリーチャーをタップした効果は、相手のターン開始の
  アンタップで消える。検証は自分のターンのうちに行う
  （攻撃フェイズの決定で止めて確認する）。

proto:
- T1015: dm25bd2-015 型（光クリーチャー、CIP）。
- T1016: dm24rp2-051 型（光クリーチャー、CIP repeat）。
- T1017: dm25-002 型（光/水/闇進化、攻撃時 may）。

ドライバは tests.conftest を import せず scenario.build を
直接使う（第329弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

CHOOSE_1 = {"op": "choose",
            "select": {"zone": "bz", "owner": "any",
                       "filter": {"types": ["creature"]}, "count": 1},
            "as": "target"}
MODAL_TU = {"op": "modal", "modes": [
    [{"op": "tap", "select": {"ref": "target"}}],
    [{"op": "untap", "select": {"ref": "target"}}]]}

FORM_1015 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [CHOOSE_1, MODAL_TU],
}]

CHOOSE_UP2 = {"op": "choose",
              "select": {"zone": "bz", "owner": "any",
                         "filter": {"types": ["creature"]},
                         "count": 1, "up_to": True},
              "as": "target"}

FORM_1016 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "repeat", "times": 2,
                "body": [CHOOSE_UP2, MODAL_TU]}],
}]

CHOOSE_E = {"op": "choose",
            "select": {"zone": "bz", "owner": "any",
                       "filter": {"types": ["creature"],
                                  "evolution": False}, "count": 1},
            "as": "target"}

FORM_1017 = [{
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "effect": [{"op": "may", "body": [CHOOSE_E, MODAL_TU]}],
}]


def test_proto_forms():
    for tid, form in (("T1015", FORM_1015), ("T1016", FORM_1016),
                      ("T1017", FORM_1017)):
        c = proto_card(tid)
        assert c["abilities"] == form, tid
        d = parse_card(c, TABLES)
        assert len(d.abilities) >= 1
    bad = copy.deepcopy(proto_card("T1015"))
    bad["abilities"][0]["effect"][1]["modes"][0][0]["op"] = "tapp"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _tapped(e, p, defn):
    return e.s.cards[_bz(e, p, defn)].tapped


def _pick(keys, defn):
    return next(i for i, k in enumerate(keys)
                if k.startswith("bz:") and k.split(":")[1] == defn)


def _charge_answer(keys, keep_defn):
    """charge ではキーカードをマナに置かない。"""
    if "pass" in keys:
        return [keys.index("pass")]
    for i, k in enumerate(keys):
        if keep_defn not in k:
            return [i]
    return [0]


def _opp_attacks(e, keep_defn):
    """p1 の T005 がプレイヤーを攻撃してタップするまで進める。
    セットアップ配置のクリーチャーは1ターン目から攻撃できる。
    攻撃が解決したら（p0 の charge）戻る。"""
    attacked = False
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if attacked and d["kind"] == "charge" and d.get("player") == 0:
            return
        if d["kind"] == "attack" and d.get("player") == 1 \
                and "attack:T005:player" in keys:
            e.answer([keys.index("attack:T005:player")])
            attacked = True
            continue
        if d["kind"] == "block":
            e.answer([keys.index("no_block")])
            continue
        if d["kind"] == "declare_strigger":
            e.answer([])
            continue
        if d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge":
            e.answer(_charge_answer(keys, keep_defn))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _summon_and_choose_modal(e, play_key, plan):
    """p0 の main で play_key を出し、choose_cards（対象の
    束縛）と choose_mode（tap/untap）に plan（(defn, mode)
    の列）で答える。plan を消化し、p0 の攻撃フェイズに
    着いたら戻る（相手のタップ状態がターン開始で消える前に
    検証できる）。"""
    plan = list(plan)
    played = False
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if played and not plan and d["kind"] == "attack" \
                and d.get("player") == 0:
            return
        if d["kind"] == "main" and d.get("player") == 0 and not played \
                and play_key in keys:
            e.answer([keys.index(play_key)])
            played = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge" and not played:
            e.answer(_charge_answer(keys, play_key.split(":")[1]))
            continue
        if d["kind"] == "choose_cards":
            e.answer([_pick(keys, plan[0][0])])
            continue
        if d["kind"] == "choose_mode":
            _, mode = plan.pop(0)
            e.answer([keys.index(f"mode:{mode}")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("summon/choose/modal did not resolve")


def test_t1015_tap_mode(rules):
    e = _build(rules, {"hand": ["T1015"], "mana": ["T004"] * 6,
                       "bz": ["T1004"]},
               {"bz": ["T005"]})
    assert not _tapped(e, 1, "T005")
    _summon_and_choose_modal(e, "play:T1015", [("T005", 0)])
    assert _tapped(e, 1, "T005")


def test_t1015_untap_mode(rules):
    e = _build(rules, {"hand": ["T1015"], "mana": ["T004"] * 6,
                       "bz": ["T1004"]},
               {"bz": ["T005"]})
    _opp_attacks(e, "T1015")
    assert _tapped(e, 1, "T005")
    _summon_and_choose_modal(e, "play:T1015", [("T005", 1)])
    assert not _tapped(e, 1, "T005")


def test_t1016_repeat_untap_then_tap(rules):
    e = _build(rules, {"hand": ["T1016"], "mana": ["T004"] * 4,
                       "bz": ["T1004"]},
               {"bz": ["T005", "T001"]})
    _opp_attacks(e, "T1016")
    assert _tapped(e, 1, "T005")
    assert not _tapped(e, 1, "T001")
    # 1体目: T005 を選んでアンタップ。2体目: T001 を選んでタップ。
    _summon_and_choose_modal(e, "play:T1016",
                             [("T005", 1), ("T001", 0)])
    assert not _tapped(e, 1, "T005")
    assert _tapped(e, 1, "T001")


def _attack_with_t1017(e, accept):
    """T1017 でプレイヤーを攻撃し、誘発の may に accept で
    答える。accept なら choose で T005 を選び modal mode:0。
    シールドブレイクの決定（choose_shields）に着いたら、
    choose_cards で見たキーとその時点の T005 のタップ状態を
    返す。"""
    state = {"attacked": False, "seen": None, "tapped_at_break": None}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "choose_shields":
            state["tapped_at_break"] = _tapped(e, 1, "T005")
            e.answer(list(range(d["min"])))
            return state
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state["attacked"] \
                and "attack:T1017:player" in keys:
            e.answer([keys.index("attack:T1017:player")])
            state["attacked"] = True
            continue
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes" if accept else "no")])
            continue
        if d["kind"] == "choose_cards":
            state["seen"] = keys
            e.answer([_pick(keys, "T005")])
            continue
        if d["kind"] == "choose_mode":
            e.answer([keys.index("mode:0")])
            continue
        if d["kind"] == "block":
            e.answer([keys.index("no_block")])
            continue
        if d["kind"] == "declare_strigger":
            e.answer([])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("attack did not resolve")


def test_t1017_attack_may_taps_non_evolution(rules):
    # 非進化の候補が2体いると choose の決定が出る（1体だけだと
    # ask の一意省略で自動で束縛される）
    e = _build(rules, {"bz": ["T1017"]},
               {"bz": ["T005", "T001", "T1017"]})
    st = _attack_with_t1017(e, accept=True)
    assert st["seen"] is not None
    # 進化クリーチャー（相手の T1017）は対象に選べない
    assert not any(k.split(":")[1] == "T1017" for k in st["seen"]
                   if k.startswith("bz:")), st["seen"]
    assert st["tapped_at_break"] is True


def test_t1017_decline_may(rules):
    e = _build(rules, {"bz": ["T1017"]}, {"bz": ["T005", "T1017"]})
    st = _attack_with_t1017(e, accept=False)
    assert st["seen"] is None          # choose 自体が出ない
    assert st["tapped_at_break"] is False
