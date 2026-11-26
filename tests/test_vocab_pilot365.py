"""語彙パイロット第365弾: entered_this_turn_cannot_attack_opponents
（ドリフト）。

センサス（rejects 1,968件を取り直し）: pure 1,820件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜364弾）は再提案しない。本弾で個別に
評価して見送った候補: creatures_enter_tapped
（pure 1、dm06-001。他者の入場をタップ状態に変える
常在 mod が無く、入場置換の新設が要る）、
speed_attacker_rule（pure 1、dmex11-004。keyword
フィルタ＋owner: any の static 適用に登録先例が無く、
付与されたスピードアタッカーへの波及の検証が別途
要る）、e_soul / w_soul（各 pure 1。ソウル標識は
種族ではなく特性で、進化元フィルタ等への横断的な
扱いの設計が要る）、trigger_when_battling（pure 1、
dm24-037。バトル時誘発の照合に加え、公開した
カードの枚数を参照する動的パワーが要る）、
untap_trigger（pure 1、dmr02-s01。アンタップの
イベント照合が無く、効果自体も山札全引き＋
無制限の無償詠唱・召喚で大きい）。
範囲内・未評価で最小の
entered_this_turn_cannot_attack_opponents
（pure 1件、multi にも現れない）を選定した:
dm22ex1-cho37 月砂 フロッガ-1「相手の進化ではない
クリーチャーは、出たターン、攻撃できない」。
partial は既存能力としてササゲール1の static
{affects: self, mod: {sac_reduce: 1}}（第201弾の
確立形）を持ち、未解決は unsupported の本 gap
1件だけ。単面カードで未検証の面は無く、partial に
欠けた要素も無い（補完なし）。

結論はドリフト（追加語彙なし）:
- 本条項は第362弾の確立形（登録先例 dm23rp4x-014
  の同文条項「相手のクリーチャーは、出たターン、
  攻撃できない」＝ static {affects: {zone: bz,
  owner: opp, filter: {types: [creature],
  entered_this_turn: true}}, mod: {deny:
  [attack_player, attack_creature]}}）そのものに、
  「進化ではない」の限定としてフィルタへ
  not_types: [evolution] を足した形。
- not_types は affects フィルタの標準キー
  （FILTER_KEYS 収載。converted に多数の使用例が
  あり、第364弾では opponent_filter でも使用）。

確立形: partial 既存の sac_reduce static ＋
static {affects: {zone: bz, owner: opp, filter:
{types: [creature], not_types: [evolution],
entered_this_turn: true}}, mod: {deny:
[attack_player, attack_creature]}}。

proto T1098（dm22ex1-cho37 型）/ T1099（進化では
ないスピードアタッカー役）/ T1100（進化クリーチャー
のスピードアタッカー役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED
が復活するので scenario.build を直接包む
（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

SAC = {"kind": "static", "affects": "self", "mod": {"sac_reduce": 1}}
STATIC = {"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"],
                                 "not_types": ["evolution"],
                                 "entered_this_turn": True}},
          "mod": {"deny": ["attack_player", "attack_creature"]}}
FORM = [SAC, STATIC]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1098")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"]
    assert c["cost"] == 2 and c["power"] == 2000
    d = parse_card(copy.deepcopy(c), TABLES)
    assert SAC in d.abilities
    assert STATIC in d.abilities
    for tid in ("T1099", "T1100"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX365", "name": "x",
                    "types": ["creature"], "civs": ["fire"],
                    "cost": 2, "power": 2000,
                    "races": ["デューンゲッコー", "ディスタス"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert SAC in d.abilities
    assert STATIC in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


def _drive(e, player, play=None, attack=None):
    """player の最初の main のターン（target_turn）だけを
    対象に進めるドライバ（第362弾と同形）。

    play があればそのターンの main で1回だけ使い、
    attack があれば target_turn の attack 決定で
    attack:<attack>:player を選ぶ。target_turn の次の
    ターンに入ったら止める。"""
    seen = {"attack_keys": [], "deny": None, "played": False,
            "attacked": False, "target_turn": None}
    for _ in range(600):
        if seen["target_turn"] is not None \
                and e.s.turn > seen["target_turn"] + 1:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind in ("charge", "main", "attack") \
                and pl == player and seen["target_turn"] is None:
            seen["target_turn"] = e.s.turn
        if kind == "main" and pl == player and play \
                and not seen["played"]:
            hit = [i for i, k in enumerate(keys)
                   if k == f"play:{play}"]
            if hit:
                seen["played"] = True
                seen["target_turn"] = e.s.turn
                e.answer([hit[0]])
                continue
        if kind == "attack" and pl == player \
                and e.s.turn == seen["target_turn"]:
            seen["attack_keys"].extend(keys)
            hit = [i for i, k in enumerate(keys)
                   if attack and k == f"attack:{attack}:player"]
            if hit and not seen["attacked"]:
                seen["attacked"] = True
                e.answer([hit[0]])
                continue
        if kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def test_entered_this_turn_opp_non_evolution_sa_cannot_attack(rules):
    """相手の進化ではないスピードアタッカーは、出た
    ターン、プレイヤーへもクリーチャーへも攻撃できない
    （deny が両方付く）。"""
    e = _build(rules,
               {"bz": ["T1098", "T1091"]},
               {"hand": ["T1099"], "mana": ["T1099", "T1099"]})
    shields = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, play="T1099")
    assert seen["played"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1099:")]
    assert "T1099" in _defns(e, "bz", 1)
    assert not e.s.cards[_cid(e, "T1099", 1)].tapped  # 攻撃していない
    assert len(e.zlist("shield", 0)) == shields        # ブレイクなし


def test_control_without_source_sa_can_attack_on_entry_turn(rules):
    """対照: 発生源が無ければ、出たターンのスピード
    アタッカーはプレイヤーを攻撃でき、シールドが1枚減る。"""
    e = _build(rules,
               {"bz": ["T1091"]},
               {"hand": ["T1099"], "mana": ["T1099", "T1099"]})
    before = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, play="T1099", attack="T1099")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1


def test_entered_this_turn_opp_evolution_sa_can_attack(rules):
    """相手の進化クリーチャーは not_types: [evolution]
    で制限の対象外: 出たターンでもスピードアタッカーで
    プレイヤーを攻撃でき、シールドが1枚減る（本弾の
    判別の核）。"""
    e = _build(rules,
               {"bz": ["T1098", "T1091"]},
               {"bz": ["T1099"], "hand": ["T1100"],
                "mana": ["T1099", "T1099", "T1099", "T1099"]})
    before = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, play="T1100", attack="T1100")
    assert seen["played"] and seen["attacked"]
    assert "T1100" in _defns(e, "bz", 1)
    assert len(e.zlist("shield", 0)) == before - 1


def test_non_evolution_sa_from_previous_turn_can_attack(rules):
    """前ターンからいる進化ではないスピードアタッカー
    には制限が及ばず、発生源がいても攻撃できる
    （entered_this_turn の判別）。"""
    e = _build(rules,
               {"bz": ["T1098", "T1091"]},
               {"bz": ["T1099"]})
    before = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, attack="T1099")
    assert seen["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1


def test_own_non_evolution_sa_entered_this_turn_can_attack(rules):
    """自分のクリーチャーには及ばない: 自分のスピード
    アタッカーは出たターンに相手プレイヤーを攻撃できる。"""
    e = _build(rules,
               {"bz": ["T1098"], "hand": ["T1099"],
                "mana": ["T1099", "T1099"]},
               {})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T1099", attack="T1099")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 1


def test_chars_deny_discrimination(rules):
    """特性レベルの判別: 出たターンの相手クリーチャー
    のうち、進化ではないものだけに deny の両方が付き、
    進化クリーチャー・自分のクリーチャー・前ターンから
    いる相手クリーチャーには付かない。発生源自身は
    sac_reduce 1 を持つ（partial 既存能力の確認）。"""
    e = _build(rules,
               {"bz": ["T1098", "T1099"]},
               {"bz": ["T1099", "T1100"]})
    src = _cid(e, "T1098", 0)
    assert e.chars(src)["sac_reduce"] == 1
    opp = _cid(e, "T1099", 1)
    evo = _cid(e, "T1100", 1)
    own = _cid(e, "T1099", 0)
    for c in (opp, evo, own):
        e.s.mut_card(c).entered_turn = e.s.turn
    deny_opp = e.chars(opp)["deny"]
    assert "attack_player" in deny_opp
    assert "attack_creature" in deny_opp
    deny_evo = e.chars(evo)["deny"]
    assert "attack_player" not in deny_evo
    assert "attack_creature" not in deny_evo
    deny_own = e.chars(own)["deny"]
    assert "attack_player" not in deny_own
    assert "attack_creature" not in deny_own
    e.s.mut_card(opp).entered_turn = e.s.turn - 1
    deny_prev = e.chars(opp)["deny"]
    assert "attack_player" not in deny_prev
    assert "attack_creature" not in deny_prev
