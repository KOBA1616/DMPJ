"""語彙パイロット第436弾: mana_tap_trigger（新規語彙＝支払いタップのイベント化）。

センサス（rejects 1,896件を取り直し）: pure 1,748件
（984家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜435弾）は原則として再提案しない。残置群
（graveyard_replacement 残り dm25ex2-cho021、
battle_opponent_reference 残り dmr01-049、
untap_restriction 残り2件、does_not_untap 残り
dm25ex2-031、cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、after_battle_trigger 残り dmrp09-074、
s_trigger_suppression 2件＝第435弾で専用ステージ
送り確定、次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn、後続候補の
distinct_civ_count、将来の新規語彙候補 first_time_tap /
turn_history_entry / played_free_condition、専用
ステージ送りの power_threshold_keyword_gain）は
覆す根拠が無く再提案しない。

範囲内・最小の **mana_tap_trigger（pure 1件、multi
にも現れない）** を選定した。本ファミリーは第434弾で
「支払いタップのイベント化は影響が広い」として
見送られたが、本弾の実測で影響範囲は列挙可能な狭さ
（直接タップ箇所6か所、tap/untap の when 全量
121件の内訳は下記）と判明したため、その評価を覆して
着手する（第435弾が均一性却下を新証拠で覆した進め方
と同型）。対象は dmx08-010 大喰の超人（自然 /
コスト8 / パワー8000 / 種族 ジャイアント/ハンター /
mana 1）。partial は骨格＋abilities 完備で text も
公式全文。**補完なし**。

結論は新規語彙（エンジン変更2点。defs・スキーマ
変更なし）:

- 条項1「自分のマナゾーンのカードをタップする時、
  そのうちの好きな枚数のカードの、マナの数字を
  ２または３にしてもよい」は static
  mana_boost {values: [2, 3]}。第212弾・ラウンド248
  の確立形（解決済み）。
- 条項2「自分のマナゾーンのカードをタップした時、
  そのカードを自分の墓地に置く」は trigger
  {when: {event: tap, subject: {owner: you,
  zone: mana}}, effect: [move {select:
  {ref: subject}, to: graveyard, reason: put}]}。
  照合側は第212弾で確立済み（subject の zone 指定、
  proto T536＝本条項そのもの、第212弾テストで
  「イベントとして流れたタップでは誘発する」ことを
  検証済み）。欠けていたのは支払いのタップが
  ev_task を経由せず直接 tapped を書き換えていた
  点で、本弾で支払い・コストのマナタップ6か所
  （h_play 通常支払い／バズレンダ追加支払い／
  O・ドライブ追加タップ、h_cross の支払い、
  h_activate の tap_mana コスト、op pay_or_lose の
  支払い）をイベント化した。代替コストのタップ
  （第57弾）が既に ev_task 経由である先例に揃えた。
  誘発の解決は通常の待機・解決窓（プレイ完了後の
  チェックポイント）で CIP 等と同時に待機する。
- あわせて _match_when に tap/untap の subject
  ゾーン既定規則を追加した: subject が dict 形で
  zone を指定しない場合、subject のゾーンが bz の
  時だけ一致する。登録済み＋proto の tap/untap の
  when 全量（tap 101件＋untap 20件）は subject: self
  が大半、zone: bz 明示3件、zone: mana 明示は T536
  の1件だけで、zone 無指定の dict 形（tap 11件・
  untap 2件）の公式テキストは全て「クリーチャーが
  タップ／アンタップした時」＝bz 前提。規則が無いと
  支払いタップのイベント化でこの11件がマナゾーンの
  クリーチャーカードに誤発する。さらに実測では、
  ターン開始の一括アンタップ（マナ分も既にイベント
  化済み）で dm26rp2-s007 {owner: opp} が相手マナの
  アンタップに誤発する既存の不正確さがあり（本弾の
  テストで修正前は order_pending 2件、本弾で解消を
  実測）、dm25ex3-tf26 も同型。本規則は第212弾の
  「マナを見る形は zone: mana を明示する」規約の
  裏側で、登録済みカードの意図する挙動は変わらない。

proto T1226（dmx08-010 型）。判別役は T536（条項2
のみの第212弾 proto）/ T001（バニラ＝召喚先・マナ
役）/ T062（クロスギア）/ T109（tap_mana 起動）と
実カード dm26ex1-033（zone 無指定の tap 監視）/
dm26rp2-s007（zone 無指定の untap 監視）を流用する。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。
"""
import copy
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import (  # noqa: E402
    DefError, load_rules, load_tables, parse_card)
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

BOOST = {"kind": "static", "mana_boost": {"values": [2, 3]}}
TRIG = {"kind": "trigger",
        "when": {"event": "tap", "subject": {"owner": "you", "zone": "mana"}},
        "effect": [{"op": "move", "select": {"ref": "subject"},
                    "to": "graveyard", "reason": "put"}]}
FORM = [BOOST, TRIG]
FULL_TEXT = ("自分のマナゾーンのカードをタップする時、そのうちの好きな枚数の"
             "カードの、マナの数字を２または３にしてもよい。\n"
             "自分のマナゾーンのカードをタップした時、そのカードを自分の墓地に置く。\n"
             "W・ブレイカー(このクリーチャーはシールドを２枚ブレイクする)")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _keys(d):
    return [o.get("key") for o in d["options"]]


def _drive(e, want=None, limit=300, seen=None):
    """want(kind, keys) -> 答えるキーの文字列 or None。
    それ以外は pass / no_block / 最小限で流す。見た決定の
    (kind, keys) を seen に集める。"""
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if seen is not None:
            seen.append((d["kind"], d.get("player"), list(keys)))
        if want is not None:
            k = want(d["kind"], keys)
            if k is not None:
                e.answer([keys.index(k)])
                continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return e


def _zone_defns(e, zone, player=0):
    return sorted(e.s.cards[c].defn for c in e.zlist(zone, player))


def test_proto_form(rules):
    card = proto_card("T1226")
    assert card["abilities"] == FORM
    parsed = parse_card(card, TABLES)
    # キーワード double_breaker は先頭の static に正規化され、残りが FORM と一致する
    assert parsed.abilities[0] == {"kind": "static", "affects": "self",
                                   "mod": {"breaks": 2}, "keyword": "double_breaker"}
    assert list(parsed.abilities[1:]) == FORM
    assert card["text"] == FULL_TEXT
    assert card["keywords"] == ["double_breaker"]


def test_form_def_errors():
    base = {"id": "X436", "name": "x", "types": ["creature"],
            "civs": ["nature"], "cost": 8, "power": 8000,
            "races": ["テスト"], "mana": 1, "text": "x",
            "keywords": ["double_breaker"], "abilities": copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][1]["when"] = {"event": "tapzz",
                                   "subject": {"owner": "you", "zone": "mana"}}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][0] = {"kind": "static", "mana_boost": {"values": [1, 3]}}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][1]["effect"] = [{"op": "explode"}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_payment_tap_goes_to_graveyard(rules):
    """通常支払い: タップしたマナはプレイ完了後に墓地へ。タップしていないマナは残る。"""
    e = scenario.build(rules, {"p0": {"bz": ["T1226"], "hand": ["T001"],
                                      "mana": ["T001", "T001", "T001"]},
                              "filler": "T002"})
    seen = []

    def want(kind, keys):
        if kind == "main" and "play:T001" in keys:
            return "play:T001"
        if kind == "pay_mana":
            # 2枚組の選択肢（ブースト無しの通常支払い）を選ぶ
            return None
        return None

    # pay_mana は cids の数が選べるよう、キーではなく index で拾うため個別に回す
    played = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        seen.append((d["kind"], list(keys)))
        if not played and d["kind"] == "main" and "play:T001" in keys:
            e.answer([keys.index("play:T001")])
            played = True
            continue
        if d["kind"] == "pay_mana":
            two = [i for i, o in enumerate(d["options"]) if len(o["cids"]) == 2]
            assert two, keys
            e.answer([two[0]])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if played and _zone_defns(e, "bz") == ["T001", "T1226"]:
            # 誘発の解決まで進めるため少し回してから抜ける
            pass
    assert played
    assert _zone_defns(e, "bz") == ["T001", "T1226"]
    assert _zone_defns(e, "graveyard") == ["T001", "T001"]   # 支払った2枚は墓地
    assert _zone_defns(e, "mana") == ["T001"]               # 残り1枚はマナに残る


def test_payment_tap_boost_still_works(rules):
    """ブースト併用: マナ3枚（通常合計3）では足りないコスト8を 3+3+2 で支払え、
    タップした3枚すべてが墓地へ行く。"""
    e = scenario.build(rules, {"p0": {"bz": ["T1226"], "hand": ["T1226"],
                                      "mana": ["T001", "T001", "T001"]},
                              "filler": "T002"})
    played = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not played and d["kind"] == "main" and "play:T1226" in keys:
            e.answer([keys.index("play:T1226")])
            played = True
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert played   # ブーストが無ければ play 自体が出ない（判別）
    assert _zone_defns(e, "bz") == ["T1226", "T1226"]
    assert _zone_defns(e, "graveyard") == ["T001", "T001", "T001"]
    assert _zone_defns(e, "mana") == []


def test_opponent_watcher_does_not_fire(rules):
    """相手の T1226 は、自分のマナタップでは誘発しない（owner: you は発生源側）。"""
    e = scenario.build(rules, {"p0": {"hand": ["T001"], "mana": ["T001", "T001"]},
                               "p1": {"bz": ["T1226"]}, "filler": "T002"})
    played = False
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T001" in keys:
            e.answer([keys.index("play:T001")])
            played = True
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if played and d["kind"] == "charge" and d.get("player") == 1:
            break   # プレイ完了後の相手ターン開始で止める（自分のターン開始のアンタップ前）
    assert played
    assert _zone_defns(e, "graveyard") == []
    tapped = [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert len(tapped) == 2   # 支払ったマナはタップされたままマナに残る


def test_bz_creature_tap_does_not_fire(rules):
    """バトルゾーンのクリーチャーのタップ（攻撃）では誘発しない（zone の判別）。"""
    e = scenario.build(rules, {"p0": {"bz": ["T1226"], "mana": ["T001"]}, "filler": "T002"})
    attacked = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not attacked and d["kind"] == "attack" and "attack:T1226:player" in keys:
            e.answer([keys.index("attack:T1226:player")])
            attacked = True
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if attacked and any(e.s.cards[c].defn == "T1226" and e.s.cards[c].tapped
                            for c in e.zlist("bz", 0)):
            break
    assert attacked
    assert _zone_defns(e, "mana") == ["T001"]
    assert _zone_defns(e, "graveyard") == []


def test_activate_tap_mana_goes_to_graveyard(rules):
    """起動コストの tap_mana: タップしたマナ2枚が墓地へ行き、効果（ドロー）も解決する。"""
    e = scenario.build(rules, {"p0": {"bz": ["T1226", "T109"],
                                      "mana": ["T001", "T001", "T001"],
                                      "hand": ["T001"]}, "filler": "T002"})
    hand0 = len(e.zlist("hand", 0))
    acted = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        hit = next((k for k in keys if k.startswith("activate:T109")), None)
        if not acted and hit:
            e.answer([keys.index(hit)])
            acted = True
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if acted and _zone_defns(e, "graveyard") == ["T001", "T001"]:
            break   # 誘発が解決した時点で止める（後続ターンのドローと混ざらないよう）
    assert acted
    assert _zone_defns(e, "graveyard") == ["T001", "T001"]
    assert _zone_defns(e, "mana") == ["T001"]
    assert len(e.zlist("hand", 0)) == hand0 + 1   # ドローが解決した


def test_cross_payment_goes_to_graveyard(rules):
    """クロスの支払い: タップしたマナが墓地へ行き、クロス自体も成立する。"""
    e = scenario.build(rules, {"p0": {"bz": ["T1226", "T001", "T062"],
                                      "mana": ["T001", "T001", "T001"]},
                              "filler": "T002"})
    crossed = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not crossed and d["kind"] == "main" and "cross:T062:T001" in keys:
            e.answer([keys.index("cross:T062:T001")])
            crossed = True
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert crossed
    gear = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T062")
    assert e.s.cards[gear].crossed is not None
    grave = _zone_defns(e, "graveyard")
    assert grave and all(g == "T001" for g in grave)
    assert len(_zone_defns(e, "mana")) + len(grave) == 3


def test_bazurenda_payment_goes_to_graveyard(rules):
    """バズレンダの追加支払い: 通常支払い5枚＋追加支払い3枚の全てが墓地へ行く。"""
    e = scenario.build(rules, {"p0": {"bz": ["T1226"], "hand": ["T078"],
                                      "mana": ["T001"] * 8},
                               "filler": "T002"})
    played = False
    bz_prompts = 0
    pays = 0
    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not played and d["kind"] == "main" and "play:T078" in keys:
            e.answer([keys.index("play:T078")])
            played = True
            continue
        if d["kind"] == "pay_mana":
            want_n = 5 if pays == 0 else 3
            cand = [i for i, o in enumerate(d["options"]) if len(o["cids"]) == want_n]
            assert cand, (want_n, keys)
            e.answer([cand[0]])
            pays += 1
            continue
        if d["kind"] == "yes_no" and "バズレンダ" in (d.get("prompt") or ""):
            bz_prompts += 1
            e.answer([keys.index("yes" if bz_prompts == 1 else "no")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if played and _zone_defns(e, "graveyard") == ["T001"] * 8:
            break
    assert played and pays == 2 and bz_prompts >= 2
    assert "T078" in _zone_defns(e, "bz")
    assert _zone_defns(e, "graveyard") == ["T001"] * 8


def test_odrive_payment_goes_to_graveyard(rules):
    """O・ドライブの追加タップ: 通常支払い5枚＋追加タップ2枚の全てが墓地へ行く。"""
    e = scenario.build(rules, {"p0": {"bz": ["T1226"], "hand": ["T081"],
                                      "mana": ["T081"] * 7},
                               "filler": "T002"})
    played = False
    pays = 0
    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not played and d["kind"] == "main" and "play:T081" in keys:
            e.answer([keys.index("play:T081")])
            played = True
            continue
        if d["kind"] == "pay_mana":
            cand = [i for i, o in enumerate(d["options"]) if len(o["cids"]) == 5]
            assert cand, keys
            e.answer([cand[0]])
            pays += 1
            continue
        if d["kind"] == "yes_no" and "O・ドライブ" in (d.get("prompt") or ""):
            e.answer([keys.index("yes")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if played and _zone_defns(e, "graveyard") == ["T081"] * 7:
            break
    assert played and pays == 1
    assert "T081" in _zone_defns(e, "bz")
    assert _zone_defns(e, "graveyard") == ["T081"] * 7
    assert _zone_defns(e, "mana") == []


def test_guard_zone_less_tap_watcher(rules):
    """ゾーン既定規則（tap）: dm26ex1-033「自分のクリーチャーがタップした時」は、
    マナゾーンのクリーチャーカードの支払いタップでは誘発せず、
    バトルゾーンのクリーチャーのタップ（自身の攻撃）では誘発する。"""
    e = scenario.build(rules, {"p0": {"bz": ["dm26ex1-033"], "hand": ["T001"],
                                      "mana": ["T001", "T001"]}, "filler": "T002"})
    seen = []
    played = False
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        seen.append(list(keys))
        if not played and d["kind"] == "main" and "play:T001" in keys:
            e.answer([keys.index("play:T001")])
            played = True
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if played and d["kind"] == "attack":
            break
    assert played
    assert not any("dm26ex1-033" in k for ks in seen for k in ks
                   if k.startswith("pending:")), seen
    # 攻撃で自身がタップすると誘発する（判別）。誘発は1件だけなので
    # order_pending は自動解決され、may の yes/no 決定とドローで観測する
    seen2 = []
    attacked = False
    hand_before = len(e.zlist("hand", 0))
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        seen2.append(list(keys))
        if not attacked and d["kind"] == "attack" \
                and "attack:dm26ex1-033:player" in keys:
            e.answer([keys.index("attack:dm26ex1-033:player")])
            attacked = True
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if attacked and len(e.zlist("hand", 0)) == hand_before + 1:
            break   # ドローが解決した時点で止める（後続ターンのドローと混ざらないよう）
    assert attacked
    assert ["yes", "no"] in seen2, seen2   # 「引いてもよい」の確認が出た
    assert len(e.zlist("hand", 0)) == hand_before + 1   # ドローが解決した


def test_guard_zone_less_untap_watcher(rules):
    """ゾーン既定規則（untap）: dm26rp2-s007「相手のクリーチャーがアンタップした時」は、
    相手のマナのアンタップでは誘発しない（修正前は誤発していた既存事象の判別）、
    相手のクリーチャーのアンタップでは誘発する。"""
    e = scenario.build(rules, {"p0": {"bz": ["dm26rp2-s007"]},
                               "p1": {"bz": ["T001", "T001"],
                                      "mana": ["T002", "T002"]},
                               "filler": "T002"})
    for c in e.zlist("mana", 1):
        e.s.mut_card(c).tapped = True
    seen = []
    e._push(e.ev_task([{"ev": "untap", "subject": e.s.ref(c)}
                       for c in e.zlist("mana", 1)]))
    _drive(e, limit=30, seen=seen)
    assert not any("dm26rp2-s007" in k for _, _, ks in seen for k in ks
                   if k.startswith("pending:")), seen
    # 相手クリーチャーのアンタップでは誘発する（判別）。2体分を同時に流し、
    # order_pending のキーで観測する（1件だけだと自動解決されてキーに出ない）
    tgts = [c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T001"]
    for c in tgts:
        e.s.mut_card(c).tapped = True
    seen2 = []
    e._push(e.ev_task([{"ev": "untap", "subject": e.s.ref(c)} for c in tgts]))
    _drive(e, limit=30, seen=seen2)
    assert any("dm26rp2-s007" in k for _, _, ks in seen2 for k in ks
               if k.startswith("pending:")), seen2
