"""語彙パイロット第423弾: trigger_after_battle_win_or_lose（ドリフト）。

対象は dm10-013 粛清者アイザク（光 / コスト4 / パワー4000 /
種族 ソルトルーパー）。公式テキスト:
「ブロッカー
このクリーチャーは、相手プレイヤーを攻撃できない。
このクリーチャーがブロックする時、バトルゾーンにある
自分のクリーチャーを１体選んでもよい。このクリーチャーの
バトルの後、選んだクリーチャーをアンタップする。」

行の注記は「『バトルの後』は勝敗を問わないが、遅延誘発で
待てるのは battle_win だけ（battle_lose イベントが無い）」
だが、実測で覆る: battle_lose イベントは defs の EVENTS
にあり combat.py が敗者レコードを出して登録済み3件が
使用する。さらに本件に必要なのは勝敗どちらかではなく
「バトルの後」そのもので、第211弾で battle_end レコード
（両参加者を subject とする）が新設され、trigger
{when: {event: battle_end, subject: self}} が確立形に
なっている（登録済み dmpcd03-b11 / dmc44-017 等）。
遅延側は op delayed_trigger（603.6）が確立済みで、
when は誘発と同じ文法、生成時の env（self と vars）を
スナップショットして保持し、発生源の生死に紐付かない。
したがって第3条項は確立部品の組み合わせで表せる
（第410・411・418・420・422弾と同じ覆し型。新規語彙・
エンジン・defs・スキーマ変更なし）:
  trigger {when: {event: block, subject: self},
           effect: [may [choose {select: {zone: bz,
             owner: you, filter: {types: [creature]},
             count: 1}, as: pick},
             delayed_trigger {when: {event: battle_end,
               subject: self},
               effect: [untap {select: {ref: pick}}]}]]}
block 誘発は第401・422弾の確立形、choose の as 束縛は
第414・422弾の確立形、delayed_trigger の vars
スナップショットで pick が遅延効果に届く。勝っても
負けても（発生源がバトルで破壊されても）battle_end は
両参加者ぶん出るため、勝敗を問わない文面と一致する。
delayed の duration は既定 end_of_turn で足りる
（バトルは同一ターン内に終わる）。
第1・第2条項は partial に keywords [blocker,
cannot_attack_player] として構築済み。

partial は骨格＋keywords まで構築済みで text は公式全文
（補完なし）。alias は無し（identity 実測で canon_id は
対象自身、aliases_for = []）。登録ブロッカーの確認
（第375弾の教訓）: rule_convert.split（対象行）は
(['blocker', 'cannot_attack_player'], 条項テキスト, [])
を返し、定型所有はキーワードのみで part[2] の能力所有は
空＝二重付着ブロッカー無し。

proto: T1199（dm10-013 型）。既存 proto の流用: T001
（パワー2000バニラ＝味方役・弱いアタッカー役）/ T1196
（パワー5000＝発生源がバトルに負ける判別役・第2の
アタッカー役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の作法）。
観測点: 対象の攻撃が解決した後、同じ相手ターンの次の
attack 決定の時点（遅延誘発は解決済みで、自ターンの
アンタップステップにはまだ入っていない）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

FORM = [
    {"kind": "trigger",
     "when": {"event": "block", "subject": "self"},
     "effect": [{"op": "may", "body": [
         {"op": "choose",
          "select": {"zone": "bz", "owner": "you",
                     "filter": {"types": ["creature"]}, "count": 1},
          "as": "pick"},
         {"op": "delayed_trigger",
          "when": {"event": "battle_end", "subject": "self"},
          "effect": [{"op": "untap", "select": {"ref": "pick"}}]}]}]},
]
FULL_TEXT = ("ブロッカー\n"
             "このクリーチャーは、相手プレイヤーを攻撃できない。\n"
             "このクリーチャーがブロックする時、バトルゾーンにある"
             "自分のクリーチャーを１体選んでもよい。このクリーチャーの"
             "バトルの後、選んだクリーチャーをアンタップする。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1199")
    assert c["name"] == "粛清者アイザク"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ソルトルーパー"]
    assert c["keywords"] == ["blocker", "cannot_attack_player"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert FORM[0] in d.abilities
    for tid in ("T001", "T1196"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX423", "name": "x",
                    "types": ["creature"], "civs": ["light"],
                    "cost": 4, "power": 4000, "mana": 1,
                    "races": ["ソルトルーパー"],
                    "keywords": ["blocker", "cannot_attack_player"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert FORM[0] in d.abilities


def test_bad_forms_rejected(rules):
    base = proto_card("T1199")
    # 誘発 when の未知イベントは DefError
    bad = copy.deepcopy(base)
    bad["abilities"][0]["when"] = {"event": "blocked", "subject": "self"}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # delayed effect の未知 op は DefError
    bad2 = copy.deepcopy(base)
    bad2["abilities"][0]["effect"][0]["body"][1]["effect"] = \
        [{"op": "untapp", "select": {"ref": "pick"}}]
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # choose の select の未知キーは DefError
    bad3 = copy.deepcopy(base)
    bad3["abilities"][0]["effect"][0]["body"][0]["select"] = \
        {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]},
         "count": 1, "bogus": 1}
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)
    # delayed_trigger の未知引数は DefError
    bad4 = copy.deepcopy(base)
    bad4["abilities"][0]["effect"][0]["body"][1]["bogus"] = 1
    with pytest.raises(DefError):
        parse_card(bad4, TABLES)
    # 注記: delayed_trigger の when 自体は op 署名が
    # when="any" のため parse では型チェックされない
    # （第420弾の when.subject 漏れと同種の検証漏れ。
    # 本弾の形は確立キー battle_end / subject: self のみを
    # 使うので影響なし）


# ---------- 駆動ヘルパ ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "pay_mana":
        e.answer([0])
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    # バトルゾーンは共有ゾーンなので controller でも絞る
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == p)


def _drive(e, attack_key, block=True, may=True, choose_cid=None,
           tap_cid=None, limit=400):
    """相手（p1）の attack_key の攻撃を一度だけ行わせ、
    T1199 でブロックさせ、may / choose に答える。攻撃が
    解決した後の同じ相手ターンの次の attack 決定の時点で
    止める（遅延誘発は解決済み、自ターンのアンタップ
    ステップ前）。tap_cid は攻撃宣言の直前にタップする
    （build 直後にタップしても自ターンのアンタップ
    ステップで解けてしまうため）。"""
    attacked = False
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if attacked and d["kind"] == "attack" and d["player"] == 1:
            return
        if not attacked and d["kind"] == "attack" and d["player"] == 1 \
                and attack_key in keys:
            if tap_cid is not None:
                e.s.cards[tap_cid].tapped = True
            e.answer([keys.index(attack_key)])
            attacked = True
            continue
        if d["kind"] == "block":
            if block:
                hit = [i for i, k in enumerate(keys)
                       if k.startswith("bz:T1199")]
                assert hit, "T1199 がブロック候補に無い"
                e.answer([hit[0]])
            else:
                e.answer([keys.index("no_block")])
            continue
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes" if may else "no")])
            continue
        if d["kind"] == "choose_cards":
            hit = [i for i, o in enumerate(d["options"])
                   if o.get("cid") == choose_cid]
            assert hit, "choose 候補に指定クリーチャーが無い"
            e.answer([hit[0]])
            continue
        _answer_default(e, d)
    raise AssertionError("観測点に到達しなかった")


def _setup(rules, attackers):
    """p0: T1199＋味方 T001（攻撃直前にタップする）。
    p1: attackers。"""
    e = _build(rules, {"bz": ["T1199", "T001"]}, {"bz": attackers})
    return e, _cid(e, 0, "T1199"), _cid(e, 0, "T001")


def test_block_win_untaps_chosen_ally(rules):
    # バトルに勝った場合: ブロックしてタップした発生源は
    # そのまま、選んだ味方はバトルの後にアンタップする。
    e, isaac, ally = _setup(rules, ["T001", "T1196"])
    atk = _cid(e, 1, "T001")
    _drive(e, "attack:T001:player", choose_cid=ally, tap_cid=ally)
    assert e.s.cards[atk].zone == "graveyard"      # 2000 は 4000 に負ける
    assert e.s.cards[isaac].zone == "bz"
    assert e.s.cards[isaac].tapped is True         # ブロックでタップしたまま
    assert e.s.cards[ally].tapped is False         # バトルの後にアンタップ


def test_block_lose_still_untaps_chosen_ally(rules):
    # バトルに負けた場合（勝敗を問わない判別）: 発生源が
    # バトルで破壊されても、選んだ味方はバトルの後に
    # アンタップする。battle_win のみで待つ形では落ちる。
    e, isaac, ally = _setup(rules, ["T1196", "T001"])
    _drive(e, "attack:T1196:player", choose_cid=ally, tap_cid=ally)
    assert e.s.cards[isaac].zone == "graveyard"    # 4000 は 5000 に負ける
    assert e.s.cards[ally].tapped is False         # それでもアンタップする


def test_decline_may_keeps_ally_tapped(rules):
    # 「選んでもよい」を辞退したら何も起きない。
    e, isaac, ally = _setup(rules, ["T001", "T1196"])
    _drive(e, "attack:T001:player", may=False, tap_cid=ally)
    assert e.s.cards[isaac].zone == "bz"
    assert e.s.cards[ally].tapped is True


def test_choose_self_untaps_after_battle(rules):
    # 発生源自身も「自分のクリーチャー」に含まれる:
    # ブロックでタップした発生源が、バトルの後に
    # アンタップする。味方は選ばれていないのでタップのまま。
    e, isaac, ally = _setup(rules, ["T001", "T1196"])
    _drive(e, "attack:T001:player", choose_cid=isaac, tap_cid=ally)
    assert e.s.cards[isaac].zone == "bz"
    assert e.s.cards[isaac].tapped is False
    assert e.s.cards[ally].tapped is True


def test_no_block_no_untap(rules):
    # ブロックしなければ誘発しない（シールドが割れる）。
    e, isaac, ally = _setup(rules, ["T001", "T1196"])
    _drive(e, "attack:T001:player", block=False, tap_cid=ally)
    assert e.s.cards[isaac].tapped is False        # ブロックしていない
    assert e.s.cards[ally].tapped is True          # アンタップしない
