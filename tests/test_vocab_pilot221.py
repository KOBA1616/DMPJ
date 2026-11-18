"""語彙パイロット第221弾: bio_t（バイオ・T）。

「バイオ・T―自分の<種族>が攻撃して、バトルが始まった時、このカードを
自分の手札から捨ててもよい。そうした場合、（攻撃しているクリーチャーに
関する効果）」は、既存語彙だけのイディオムで表せる。新規エンジン語彙は無し。

- 手札からの誘発: trigger {zone: hand, when: {event: battle_start,
  subject: {owner: you, filter: {races: [<種族>]}}}}（zone_trigger_defs が
  手札の誘発を拾う。battle_start レコードは subject=攻撃側・opponent=
  防御側を持つ）
- 捨てる: may の body 先頭で {op: discard, select: {ref: self}}
  （discard マクロ＝墓地へ reason: discard）。その後の条項は
  {ref: event.subject}（攻撃側）/ {ref: event.opponent}（防御側）で指す
- 条項の形: パワー＝modify {power: {amount, count: {zone: hand}}}
  （手札比例。count は特性計算時に評価されるため手札枚数を追う）、
  固定パワー＝modify {power: N}（duration 既定 end_of_turn）、
  スレイヤー付与＝modify {grant: [slayer]}、パワーアタッカー付与＝
  modify {power_when: {amount, when: attacking}}。battle_power は
  _battle_bonus が自身の static しか見ないため modify では死に、
  gain で static を与える形もエンジンが展開しない（後述の潜在問題）。
  power_when は chars 集約で継続的効果からも効く。dm20-051 の
  modify＋battle_power 付与も同じ理由で死んでいるはず（未検証・別途確認）、
  両バウンス＝bounce {ref: event.subject} + bounce {ref: event.opponent}
  （バトルは battle_run の alive 検査で止まる）、
  終了時アンタップ＝choose {as: t, select: {ref: event.subject}}
  （ref だけの select は決定を出さない）+ delayed_trigger
  {when: {event: turn_end}, effect: [untap {ref: t}]}
  （忍者チェンジの turn_end 遅延誘発と同じ既存形）

潜在問題（本弾では未修正）: mod.gain で static 能力を与える形は
エンジンが展開しない。abilities() は gain 由来の能力を kind != "static"
の時だけ返し（core.py:296）、_chars_calc は集めた mod の gain を
展開しない。実証: dmr12-048 猛友情 五郎丸・G の「パワーアタッカー+2000」
付与は、対象（dm25sp2-017）の abilities(cid, "static") に現れない
（T576 の gain-static 型も同じ理由でバトルに負ける）。付与には
dm20-051 / dm21-031 の battle_power 形を使う。gain-static の
対応は専用の弾＋全体テストで行う。

Rust: battle_start の誘発・zone: hand は _simple_trigger の範囲外
（_OK_EVENTS に無く、zone は bz/graveyard のみ）なので、この札を
含む局は supports() が False を返し Python へフォールバックする
（既存の battle_start 持ちカードと同じ扱い）。dmcore の再構築は不要。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T572", "T573", "T574", "T575", "T576", "T577", "T578", "T579")


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
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if e.s.cards[c].controller == p] if zone == "bz" else \
           [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _drive(e, handler, turns=5, limit=4000, stop_when=None):
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


def _make_handler(logs, attacker="T579", target="T005", attack_turn=3,
                  attack_player=0, accept=True, hand_log=None):
    """attack_turn の attack で attacker:target を選ぶ。yes_no は logs に
    記録して accept で答える。手札枚数は yes_no 提示時に hand_log へ。"""
    state = {"attacked": False}

    def h(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            if hand_log is not None:
                hand_log.append(len(e.zlist("hand", d.get("player"))))
            e.answer([0] if accept else [1])
            return True
        if attacker is not None and not state["attacked"] \
                and d["kind"] == "attack" and e.s.turn == attack_turn \
                and d.get("player") == attack_player \
                and f"attack:{attacker}:{target}" in keys:
            state["attacked"] = True
            e.answer([keys.index(f"attack:{attacker}:{target}")])
            return True
        return False

    return h, state


def _battle(rules, p0_hand, p1_bz=None, p0_bz=None):
    return setup(rules, {"bz": p0_bz or ["T579"], "hand": p0_hand},
                 {"bz": p1_bz or ["T005"]}, filler="T002")


def test_bio_t_power_per_hand(rules):
    # may 時の手札は [T572] なら2枚（先攻は1ターン目に引かないため
    # 3ターン目までのドローは1枚）。捨てると残り1枚→+1000。
    # 手札を2枚増やすと +3000 になり、T571（4000）への勝敗が
    # 負け→勝ちに変わる（ちょうど1000/枚の証明）。
    hand_log = []
    logs = []
    h, state = _make_handler(logs, target="T571", hand_log=hand_log)
    e = _battle(rules, ["T572", "T003", "T006"], p1_bz=["T571"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == [(3, 0)]
    assert hand_log == [4]                    # 提示時の手札（3枚＋1ドロー）
    assert "T572" in _defns(e, "graveyard", 0)   # 捨てた
    assert "T579" in _defns(e, "bz", 0)          # 5000>4000 で勝ち残り
    assert "T571" in _defns(e, "graveyard", 1)   # 守備側は破壊

    hand_log2 = []
    logs2 = []
    h2, state2 = _make_handler(logs2, target="T571", hand_log=hand_log2)
    e2 = _battle(rules, ["T572"], p1_bz=["T571"])
    _drive(e2, h2, turns=5, stop_when=lambda e2, d: e2.s.turn >= 4)
    assert state2["attacked"] and logs2 == [(3, 0)]
    assert hand_log2 == [2]                   # 2枚少ない
    assert "T579" in _defns(e2, "graveyard", 0)  # 3000<4000 で負ける
    assert "T571" in _defns(e2, "bz", 1)


def test_bio_t_power_per_hand_decline(rules):
    logs = []
    h, state = _make_handler(logs, accept=False)
    e = _battle(rules, ["T572"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == [(3, 0)]
    assert "T572" in _defns(e, "hand", 0)        # 断れば手札に残る
    assert "T579" in _defns(e, "graveyard", 0)   # 2000<3000 で負ける
    assert "T005" in _defns(e, "bz", 1)


def test_bio_t_power_and_untap(rules):
    logs = []
    h, state = _make_handler(logs, target="T002")
    e = _battle(rules, ["T573"], p1_bz=["T002"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == [(3, 0)]
    assert "T573" in _defns(e, "graveyard", 0)
    assert "T579" in _defns(e, "bz", 0)          # 3500>1000 で勝ち残り
    # 遅延アンタップはターン3の終わりに発火した（前ターンの履歴に残る）。
    # ターン4開始の一括アンタップではもうタップされていないので今ターンは無し。
    assert e.s.prev_counters.get("hist:untap:0") == 1
    assert e.s.turn_counters.get("hist:untap:0") is None


def test_bio_t_power_and_untap_decline(rules):
    logs = []
    h, state = _make_handler(logs, target="T002", accept=False)
    e = _battle(rules, ["T573"], p1_bz=["T002"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == [(3, 0)]
    assert "T573" in _defns(e, "hand", 0)
    assert "T579" in _defns(e, "bz", 0)          # 2000>1000 で勝ち残る
    # ターン4は相手ターン。ターン3の終わりにはアンタップしていない
    # （前ターンの履歴に untap は無い）。
    assert e.s.prev_counters.get("hist:untap:0") is None
    # 断ったのでタップされたまま。自分の次のターン（ターン5）開始の
    # 一括アンタップで初めてアンタップされる。
    _drive(e, h, turns=6, stop_when=lambda e, d: e.s.turn >= 5)
    assert e.s.turn_counters.get("hist:untap:0") == 1


def test_bio_t_bounce_both(rules):
    logs = []
    h, state = _make_handler(logs)
    e = _battle(rules, ["T574"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == [(3, 0)]
    assert "T574" in _defns(e, "graveyard", 0)
    assert "T579" in _defns(e, "hand", 0)        # 攻撃側も手札へ戻る
    assert "T005" in _defns(e, "hand", 1)        # 防御側も手札へ戻る
    # バトルは行われない（両者とも場にいない）


def test_bio_t_bounce_both_decline(rules):
    logs = []
    h, state = _make_handler(logs, accept=False)
    e = _battle(rules, ["T574"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == [(3, 0)]
    assert "T574" in _defns(e, "hand", 0)
    assert "T579" in _defns(e, "graveyard", 0)   # バトルして負ける
    assert "T005" in _defns(e, "bz", 1)


def test_bio_t_grant_slayer(rules):
    logs = []
    h, state = _make_handler(logs)
    e = _battle(rules, ["T575"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == [(3, 0)]
    assert "T575" in _defns(e, "graveyard", 0)
    assert "T579" in _defns(e, "graveyard", 0)   # 2000<3000 でバトルに負ける
    assert "T005" in _defns(e, "graveyard", 1)   # が、スレイヤーで道連れ


def test_bio_t_grant_slayer_decline(rules):
    logs = []
    h, state = _make_handler(logs, accept=False)
    e = _battle(rules, ["T575"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == [(3, 0)]
    assert "T579" in _defns(e, "graveyard", 0)
    assert "T005" in _defns(e, "bz", 1)          # スレイヤー無しでは残る


def test_bio_t_gain_power_attacker(rules):
    logs = []
    h, state = _make_handler(logs)
    e = _battle(rules, ["T576"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == [(3, 0)]
    assert "T576" in _defns(e, "graveyard", 0)
    assert "T579" in _defns(e, "bz", 0)          # 攻撃中 2000+4000=6000
    assert "T005" in _defns(e, "graveyard", 1)


def test_bio_t_flat_power(rules):
    logs = []
    h, state = _make_handler(logs)
    e = _battle(rules, ["T577"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == [(3, 0)]
    assert "T577" in _defns(e, "graveyard", 0)
    assert "T579" in _defns(e, "bz", 0)          # 2000+2000=4000>3000
    assert "T005" in _defns(e, "graveyard", 1)


def test_bio_t_no_trigger_for_other_race(rules):
    # 別種族の攻撃では、手札のバイオ・T は聞かれない。
    logs = []
    h, state = _make_handler(logs, attacker="T578")
    e = _battle(rules, ["T572"], p0_bz=["T579", "T578"])
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"] and logs == []
    assert "T572" in _defns(e, "hand", 0)


def test_bio_t_no_trigger_for_opponent_attack(rules):
    # 相手のテストが攻撃しても、自分の手札のバイオ・T は聞かれない。
    logs = []
    h, state = _make_handler(logs, attacker="T579", target="T005",
                             attack_turn=2, attack_player=1)
    e = setup(rules, {"bz": ["T005"], "hand": ["T572"]},
              {"bz": ["T579", "T002"]}, filler="T002")
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 3)
    assert state["attacked"] and logs == []
    assert "T572" in _defns(e, "hand", 0)
