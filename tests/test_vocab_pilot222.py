"""語彙パイロット第222弾: mana_placement_reveal。

「このカードを自分の手札からマナゾーンに置いた時、自分の手札にある
<種族>・カードを１枚、表向きにしてもよい。そうしたら、このカードを
アンタップする。」（dm26ex2-030〜035 の決闘5枚）は、既存語彙だけの
イディオムで表せる。**新規エンジン語彙は無し**（第215弾・第221弾と
同型のイディオム弾）。

- 手札からのマナ配置誘発: trigger {zone: hand, when: {event: move,
  from: hand, to: mana, subject: self}}。チャージ（turn.py st_charge）
  は ev_task {ev: move, to: mana, reason: charge} を発行し、_apply_one
  が lki（移動前の手札の姿）付きの move レコードを作る。_collect_triggers
  の lki 経路（events.py: 手札等から離れたカード自身の誘発）が
  zone == "hand" の能力を拾う。支払い時のマナタップがイベント化
  されない第212弾の教訓（mana_tap_trigger）は配置には当てはまらない。
  移動後のゾーンが mana のため zone_trigger_defs 経路との二重発火も無い
  （手札の束からは既に離れている）。
- 公開: may の body で choose {select: {zone: hand, owner: you,
  filter: {races: [<種族>]}}, reveal: true, as: r}（choose の
  reveal: true が note_public("reveal") で全員への公開を記録する。
  公開は情報開示のみで、ゲーム状態への副作用はアンタップだけ）。
- アンタップは公開した場合だけ: choose は候補0件で空リストを返し
  （selectors.select の mx == 0 分岐）、そのままでは後続の untap が
  空振りでなく実行されてしまうため、op: if {cond: {exists: {ref: r}}}
  でガードする（{exists: {ref: <変数>}} は変換済み先例あり）。
  「してもよい」を断った場合は may 自体が body を実行しない。
- アンタップの対象は {ref: self_moved}: _raw_move は gen を+1する
  （400.5 で新しいオブジェクトになる）ため、誘発の env に残る self
  は移動前の世代で alive にならず、{ref: self} の untap は常時不発
  になる（ラスト・バーストと同じ罠。第31弾）。移動がちょうど1回
  （手札→マナ）の場合だけ今の姿を指す self_moved を使う。
- マナの既定はアンタップで置かれる（opp_mana_tapped 持ちがいる時だけ
  タップで置かれる。_apply_one の mana 分岐）。そのため既定では
  アンタップは状態変化なしの空振りだが、相手のタップ置き効果がある
  時にこそ意味を持つ。テストは T582（opp_mana_tapped 持ち）で
  タップ置きを再現してアンタップの有無を判定する。

dm26ex2-046 断罪のロスト・サインは本 family の対象外: 公式テキスト
（data/cards/raw/by_product/26ex2.jsonl、promoy25-123 も同一）には
マナ配置条項が無く、rejects 行の gaps: [mana_placement_reveal] は
誤タグである。ラウンド258での再判定材料として vocab-pilot.md に記録。

Rust: move イベントの誘発・zone: hand は _simple_trigger の範囲外
（_OK_EVENTS に無く、zone は bz/graveyard のみ）なので、この札を
含む局は supports() が False を返し Python へフォールバックする
（既存の手札誘発持ちカードと同じ扱い）。dmcore の再構築は不要。
stamp は据え置き。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T580", "T581", "T582")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _mana_card(e, p, defn):
    for c in e.zlist("mana", p):
        if e.s.cards[c].defn == defn:
            return e.s.cards[c]
    return None


def _reveals(e, defn=None):
    return [r for r in e.s.pub if r["kind"] == "reveal"
            and (defn is None or r.get("defn") == defn)]


def _drive(e, handler, turns=2, limit=4000, stop_when=None):
    for _ in range(limit):
        if e.s.turn > turns:
            break
        d = e.advance()
        if d is None:
            break
        if stop_when is not None and stop_when(e, d):
            break
        if handler(e, d):
            continue
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _make_handler(logs, charge=None, accept=True, play=None):
    """charge: ターン1にプレイヤー0がチャージする札（"T580" 等）。
    play: ターン1のメインで唱える札。yes_no は logs に記録して accept で答える。"""
    state = {"charged": False, "played": False}

    def h(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([0] if accept else [1])
            return True
        if charge is not None and not state["charged"] \
                and d["kind"] == "charge" and e.s.turn == 1 \
                and d.get("player") == 0 and f"charge:{charge}" in keys:
            state["charged"] = True
            e.answer([keys.index(f"charge:{charge}")])
            return True
        if play is not None and not state["played"] \
                and d["kind"] == "main" and e.s.turn == 1 \
                and d.get("player") == 0 and f"play:{play}" in keys:
            state["played"] = True
            e.answer([keys.index(f"play:{play}")])
            return True
        return False

    return h, state


def _game(rules, p0_hand, p1_bz=None, p0_mana=None):
    return setup(rules, {"hand": p0_hand, "mana": p0_mana or []},
                 {"bz": p1_bz or ["T005"]}, filler="T002")


def test_charge_reveal_untaps_when_tapped(rules):
    # 相手の T582 によりチャージはタップで置かれる。公開すればアンタップされる。
    logs = []
    h, state = _make_handler(logs, charge="T580")
    e = _game(rules, ["T580", "T579"], p1_bz=["T582"])
    _drive(e, h, turns=2, stop_when=lambda e, d: e.s.turn >= 2)
    assert state["charged"] and logs == [(1, 0)]
    assert "T580" in _defns(e, "mana", 0)
    assert _mana_card(e, 0, "T580").tapped is False   # 公開したのでアンタップ
    assert _reveals(e, "T579")                        # T579 を表向きにした
    assert not _reveals(e, "T578")


def test_charge_reveal_default_untapped(rules):
    # タップ置きが無ければ既定でアンタップ置き。公開は記録され、状態は変わらない。
    logs = []
    h, state = _make_handler(logs, charge="T580")
    e = _game(rules, ["T580", "T579"])
    _drive(e, h, turns=2, stop_when=lambda e, d: e.s.turn >= 2)
    assert state["charged"] and logs == [(1, 0)]
    assert "T580" in _defns(e, "mana", 0)
    assert _mana_card(e, 0, "T580").tapped is False
    assert _reveals(e, "T579")


def test_charge_reveal_decline(rules):
    # may を断れば公開もアンタップも無い（タップ置きのまま）。
    logs = []
    h, state = _make_handler(logs, charge="T580", accept=False)
    e = _game(rules, ["T580", "T579"], p1_bz=["T582"])
    _drive(e, h, turns=2, stop_when=lambda e, d: e.s.turn >= 2)
    assert state["charged"] and logs == [(1, 0)]
    assert "T580" in _defns(e, "mana", 0)
    assert _mana_card(e, 0, "T580").tapped is True    # 断ったのでタップのまま
    assert not _reveals(e)


def test_charge_no_matching_race(rules):
    # T581 は別種フィルタ。手札に別種が無ければ、may に yes でも公開なし・アンタップなし。
    logs = []
    h, state = _make_handler(logs, charge="T581")
    e = _game(rules, ["T581", "T579"], p1_bz=["T582"])
    _drive(e, h, turns=2, stop_when=lambda e, d: e.s.turn >= 2)
    assert state["charged"] and logs == [(1, 0)]
    assert "T581" in _defns(e, "mana", 0)
    assert _mana_card(e, 0, "T581").tapped is True    # 公開できずアンタップなし
    assert not _reveals(e)


def test_charge_wrong_race_only(rules):
    # 手札にあるのが別種（T578）だけでも、テスト・フィルタの T580 は公開できない。
    logs = []
    h, state = _make_handler(logs, charge="T580")
    e = _game(rules, ["T580", "T578"], p1_bz=["T582"])
    _drive(e, h, turns=2, stop_when=lambda e, d: e.s.turn >= 2)
    assert state["charged"] and logs == [(1, 0)]
    assert "T580" in _defns(e, "mana", 0)
    assert _mana_card(e, 0, "T580").tapped is True
    assert not _reveals(e)


def test_charge_empty_hand_after(rules):
    # チャージ後に手札が空なら、公開するカードが無くアンタップも無い。
    logs = []
    h, state = _make_handler(logs, charge="T580")
    e = _game(rules, ["T580"], p1_bz=["T582"])
    _drive(e, h, turns=2, stop_when=lambda e, d: e.s.turn >= 2)
    assert state["charged"] and logs == [(1, 0)]
    assert "T580" in _defns(e, "mana", 0)
    assert _mana_card(e, 0, "T580").tapped is True
    assert not _reveals(e)


def test_charge_other_card_no_trigger(rules):
    # 決闘以外をチャージしても、手札の決闘は聞かれない。
    logs = []
    h, state = _make_handler(logs, charge="T579")
    e = _game(rules, ["T580", "T579"], p1_bz=["T582"])
    _drive(e, h, turns=2, stop_when=lambda e, d: e.s.turn >= 2)
    assert state["charged"] and logs == []            # may は出ない
    assert "T580" in _defns(e, "hand", 0)             # 決闘は手札に残る
    assert "T579" in _defns(e, "mana", 0)
    assert not _reveals(e)


def test_cast_does_not_trigger(rules):
    # 唱えて墓地へ行く時はマナ配置ではないので誘発しない。呪文本体（1ドロー）は解決する。
    logs = []
    h, state = _make_handler(logs, play="T580")
    e = _game(rules, ["T580", "T006"], p0_mana=["T580"] * 6)
    _drive(e, h, turns=2, stop_when=lambda e, d: e.s.turn >= 2)
    assert state["played"] and logs == []             # may は出ない
    assert "T580" in _defns(e, "graveyard", 0)        # 唱えた
    assert len(e.zlist("hand", 0)) == 2               # T006＋ドロー1枚
    assert not _reveals(e)


def test_two_charges_fire_independently(rules):
    # 2枚目の決闘も別ターンにチャージすれば、自分の誘発がもう一度聞かれる。
    logs = []
    state = {"charged": []}

    def h(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([0])
            return True
        if d["kind"] == "charge" and d.get("player") == 0 \
                and "charge:T580" in keys and len(state["charged"]) < 2 \
                and (e.s.turn, "T580") not in state["charged"]:
            state["charged"].append((e.s.turn, "T580"))
            e.answer([keys.index("charge:T580")])
            return True
        return False

    e = _game(rules, ["T580", "T580", "T579"], p1_bz=["T582"])
    _drive(e, h, turns=4, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["charged"] == [(1, "T580"), (3, "T580")]
    assert logs == [(1, 0), (3, 0)]                  # 2回とも may が聞かれる
    assert _defns(e, "mana", 0).count("T580") == 2
    assert all(not e.s.cards[c].tapped for c in e.zlist("mana", 0)
               if e.s.cards[c].defn == "T580")        # 両方アンタップ済み
    assert len(_reveals(e, "T579")) == 2              # T579 を2回公開
