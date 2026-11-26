"""語彙パイロット第370弾: set_power_to_zero（ドリフト）。

センサス（rejects 1,963件を取り直し）: pure 1,815件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜369弾）は再提案しない。第369弾で
「表現可能」と評価済みだった set_power_to_zero
（pure 1件、multi にも現れない）を、取り直した
センサスで裏取りして選定した（pure 1件が最小単位で、
これより小さいファミリーは無い）。

対象は pure 1件すべて: dm24ex2-042
騎士のコード オルタナティブ（ゼロ / コスト7 /
パワー6543 / アンノウン・セレス）。partial は骨格では
なく、水晶ソウル2（crystal_soul: 2、第154弾で宣言化）、
W・ブレイカー（keywords [double_breaker]）、破壊時誘発
（may で無色ゼニスを手札から無料召喚）が組立て済みで、
未解決は unsupported の set_power_to_zero 1件だけ。
partial の text は行の公式テキスト全文と一致する
（補完なし）。単面カードで未検証の面は無い。

残る条項「このクリーチャーが出た時、相手のクリーチャーを
１体選ぶ。このターン、そのクリーチャーのパワーを０に
する」は既存部品で正確に表せる（追加語彙なし）:

- CIP 誘発の標準形 trigger {event: move, to: bz,
  subject: self} の effect に、登録先例 dmrp11-zs01
  （零、「攻撃する時、相手のクリーチャーを1体選ぶ。
  そのパワーをこのクリーチャーに追加し、選んだ
  クリーチャーのパワーを0にする」）と同形の
  choose {select: {zone: bz, owner: opp, filter:
  {types: [creature]}, count: 1}, as: victim} →
  modify {select: {ref: victim}, mod: {power_set: 0},
  duration: end_of_turn} を置く。power_set は第272弾の
  mod で、加算のすべてを上書きして最後に適用される。
- 括弧書き「（パワー０以下のクリーチャーは破壊
  される）」はルール注記で、状況起因処理（703.4c、
  ops の効果解決中チェックと turn の期限切れ処理）が
  エンジンに実装済みのため、条項としては書かない。

確立形: abilities = [CIP 誘発, 破壊時誘発（partial
既存）] の2件（公式テキストの条項順）。

proto T1113（dm24ex2-042 型）/ T1114（自己パワー
+3000役＝実効6000。power_set が加算ごと上書きする
ことの判別役）。判別役は既存 proto も流用: T1105
（パワー4000ブロッカー＝素の対象役）、T1107
（能力なしパワー2000＝自分のクリーチャーが候補に
入らないことの対照）、T1106（win_all_battles 持ち
＝T1113 をバトルで破壊する役）、T789（無色ゼニス
＝破壊時誘発の召喚先）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED
が復活するので scenario.build を直接包む
（第319弾以降の作法）。マナ役は zero 文明の T1112 を
使う: 本エンジンは支払いでも civs の zero を文字どおり
照合するため、zero 文明カードの召喚には zero 文明の
マナが要る（_mana_choices の実測で確認。T1112 自身の
召喚でも同じ）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [
           {"op": "choose",
            "select": {"zone": "bz", "owner": "opp",
                       "filter": {"types": ["creature"]}, "count": 1},
            "as": "victim"},
           {"op": "modify",
            "select": {"ref": "victim"},
            "mod": {"power_set": 0},
            "duration": "end_of_turn"}]}
DESTROYED = {"kind": "trigger",
             "when": {"event": "move", "from": "bz",
                      "to": "graveyard", "reason": "destroy",
                      "subject": "self"},
             "effect": [
                 {"op": "may",
                  "body": [
                      {"op": "play_free",
                       "select": {"zone": "hand", "owner": "you",
                                  "filter": {"types": ["creature"],
                                             "colorless": True,
                                             "race_has": "ゼニス"},
                                  "count": 1}}]}]}
FORM = [CIP, DESTROYED]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1113")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["zero"]
    assert c["cost"] == 7 and c["power"] == 6543
    assert c["races"] == ["アンノウン・セレス"] and c["mana"] == 1
    assert c["crystal_soul"] == 2
    assert c["keywords"] == ["double_breaker"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert CIP in d.abilities and DESTROYED in d.abilities
    for tid in ("T1114", "T1105", "T1107", "T1106", "T789"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX370", "name": "x",
                    "types": ["creature"], "civs": ["zero"],
                    "cost": 7, "power": 6543, "mana": 1,
                    "crystal_soul": 2,
                    "races": ["アンノウン・セレス"],
                    "keywords": ["double_breaker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert CIP in d.abilities and DESTROYED in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn):
    cards = e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)
    return next(c for c in cards if e.cdef(c).id == defn)


def _drive(e, plays=(), yes=True, pick=None, stop=None, limit=600):
    """汎用ドライバ（第361弾と同形）。plays は p0 の main で
    使う play キー、pick は choose 系で優先するキー断片、
    yes_no は yes で答える。"""
    plays = list(plays)
    for _ in range(limit):
        if stop is not None and stop():
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "yes_no":
            want = "yes" if yes else "no"
            e.answer([keys.index(want)] if want in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and d.get("player") == 0:
            hit = next((k for k in plays if k in keys), None)
            if hit is not None:
                plays.remove(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def test_cip_sets_chosen_power_zero_and_destroys(rules):
    """実挙動: T1113 を召喚し、相手のパワー4000（T1105）を
    選ぶと、そのパワーが0になり状況起因処理で破壊されて
    墓地に行く。T1113 自身は場に残る。"""
    e = _build(rules,
               {"hand": ["T1113"], "mana": ["T1112"] * 7},
               {"bz": ["T1105"]})
    _drive(e, plays=["play:T1113"], pick="T1105",
           stop=lambda: "T1105" in _defns(e, "graveyard", 1))
    assert "T1113" in _defns(e, "bz", 0)
    assert "T1105" not in _defns(e, "bz", 1)
    assert "T1105" in _defns(e, "graveyard", 1)


def test_cip_power_set_overwrites_power_additions(rules):
    """判別: 実効パワー6000（印刷3000＋static +3000）の
    T1114 を選んでも、power_set は加算ごと上書きして
    0にするため破壊される（印刷パワー分の減算では
    3000が残って破壊されないはず）。"""
    e = _build(rules, {}, {"bz": ["T1114"]})
    ch = e.chars(_find(e, "bz", 1, "T1114"))
    assert ch["power"] == 6000          # 前提: 加算が効いている
    e = _build(rules,
               {"hand": ["T1113"], "mana": ["T1112"] * 7},
               {"bz": ["T1114"]})
    _drive(e, plays=["play:T1113"], pick="T1114",
           stop=lambda: "T1114" in _defns(e, "graveyard", 1))
    assert "T1114" not in _defns(e, "bz", 1)
    assert "T1114" in _defns(e, "graveyard", 1)
    assert "T1113" in _defns(e, "bz", 0)


def test_cip_no_opponent_creature_no_effect(rules):
    """判別: 相手のクリーチャーがいなければ choose の
    候補は無く（自分のクリーチャーは owner: opp で
    候補に入らない）、効果は空振りで解決する。
    自分の T1107 は無事で、T1113 は場に出る。"""
    e = _build(rules,
               {"bz": ["T1107"], "hand": ["T1113"],
                "mana": ["T1112"] * 7},
               {})
    _drive(e, plays=["play:T1113"],
           stop=lambda: "T1113" in _defns(e, "bz", 0)
           and e.s.turn >= 3)
    assert "T1113" in _defns(e, "bz", 0)
    assert "T1107" in _defns(e, "bz", 0)
    assert _defns(e, "graveyard", 0) == []
    assert _defns(e, "graveyard", 1) == []


def test_destroyed_trigger_summons_zenith_free(rules):
    """実挙動（partial 既存の破壊時誘発）: T1113 が
    バトルで破壊された時、may で手札の無色ゼニス
    （T789）をコストを支払わずに召喚できる。
    T1113 はブロッカーではないので、T1113 の攻撃を
    ブロッカーかつ win_all_battles 持ちの T1106 に
    ブロックさせて破壊する（パワーでは T1113 が
    上でも、すべてのバトルに勝つ側が勝つ）。"""
    e = _build(rules,
               {"bz": ["T1113"], "hand": ["T789"]},
               {"bz": ["T1106"]})
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if "T789" in _defns(e, "bz", 0) and state["attacked"]:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "charge":
            # charge:T789 を拾うと召喚先がマナに落ちてしまう
            e.answer([keys.index("pass")] if "pass" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "attack" and d.get("player") == 0:
            hit = [i for i, k in enumerate(keys)
                   if k == "attack:T1113:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if k.startswith("bz:T1106:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif any("T789" in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if "T789" in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert state["attacked"]
    assert "T1113" in _defns(e, "graveyard", 0)   # バトルで破壊された
    assert "T789" in _defns(e, "bz", 0)           # 無料で召喚された
    assert "T1106" in _defns(e, "bz", 1)          # 勝者は残る
