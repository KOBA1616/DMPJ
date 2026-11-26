"""語彙パイロット第356弾: destroy_after_attack（ドリフト）。

センサス（rejects 1,977件を取り直し）: pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone 105 /
dragheart 45 / psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）で、残りは pure 1〜4件の小家族が多数。
評価済み却下（negate_effects / opponent_choice_branch /
shield_grant / cost_matching_selection /
per_civilization_selection / flying / delayed_return /
draw_up_to / look_reorder 等、第316〜320弾の記録）は再提案しない。
4件組（cost_sum_of_revealed / shield_manipulation /
spell_replay / victory_icon_filter）は各カードに重い他条項が
残り均一な小語彙にならない。範囲内・未評価で最小の
destroy_after_attack（pure 1件、multi にも現れない）を選定した:
dm24rp2-064 プランタ＝ランター。

結論はドリフト（追加語彙なし）。条項は2つとも確立済みの部品:
- 「攻撃する時、その攻撃の後、このクリーチャーを破壊する」は
  第319弾形Aそのもの: 攻撃誘発 {event: attack, subject: self}
  → delayed_trigger {when: {event: attack_end, subject: self},
  duration: during_attack} → destroy {ref: self}。
  gap 名が destroy_self_after_attacking と違うだけで機構は同一
  （第319弾で解消済みのファミリーの別名行）。
- 「自分の超化獣クリーチャーがあれば、このクリーチャーに
  スレイヤーを与える」は条件つき static grant の登録先例
  dm21-s04（static {affects: self, if: {exists: {...}},
  mod: {grant: [...]}}）と同形で、照合を
  exists {zone: bz, owner: you, filter: {race_has: 超化獣}}
  に替えたもの。partial は骨格（keywords [blocker] のみ）で、
  未解決は unsupported の destroy_after_attack 1件だけだが、
  提出形ではスレイヤー条項も上の static で組む必要がある。

proto T1070（064型）/ T1071（超化獣フィクスチャ）/
T1072（相手アタッカー）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
scenario.build を直接包む（第355弾の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

TRIGGER_A = {"kind": "trigger",
             "when": {"event": "attack", "subject": "self"},
             "effect": [{"op": "delayed_trigger",
                         "when": {"event": "attack_end",
                                  "subject": "self"},
                         "duration": "during_attack",
                         "effect": [{"op": "destroy",
                                     "select": {"ref": "self"}}]}]}
STATIC_SLAYER = {"kind": "static", "affects": "self",
                 "if": {"exists": {"zone": "bz", "owner": "you",
                                   "filter": {"race_has": "超化獣"}}},
                 "mod": {"grant": ["slayer"]}}
FORM = [TRIGGER_A, STATIC_SLAYER]

# parse 後は destroy マクロが move（to: graveyard, reason: destroy）
# に展開される。static は素通し。parse 比較は展開形で行う。
PARSED_TRIGGER = copy.deepcopy(TRIGGER_A)
PARSED_TRIGGER["effect"][0]["effect"] = [
    {"op": "move", "select": {"ref": "self"},
     "to": "graveyard", "reason": "destroy"}]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1070")
    assert c["abilities"] == FORM
    assert c["keywords"] == ["blocker"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert PARSED_TRIGGER in d.abilities
    assert STATIC_SLAYER in d.abilities


def test_form_raw_parse():
    d = parse_card({"id": "TX356", "name": "x",
                    "types": ["creature"], "civs": ["darkness"],
                    "cost": 2, "power": 1000,
                    "keywords": ["blocker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert PARSED_TRIGGER in d.abilities
    assert STATIC_SLAYER in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive(e, attacker, blocker=None, limit=1500):
    """attacker（defn）でプレイヤーを攻撃させ、blocker（defn）の
    ブロック肢が現れたらブロックする。攻撃したターンの2つ先の
    ターンまで進める。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(limit):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
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
                   if blocker and k.startswith(f"bz:{blocker}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


# ---------- 実挙動: 形A（攻撃の後に自壊） ----------

def test_attack_destroys_self_at_attack_end(rules):
    """T1070 が攻撃すると、攻撃の後（攻撃終了時）に破壊される。"""
    e = _build(rules, {"bz": ["T1070"]}, {})
    st = _drive(e, "T1070")
    assert st["attacked"]
    assert "T1070" in _defns(e, "graveyard", 0)
    assert "T1070" not in _defns(e, "bz", 0)


def test_no_attack_no_destroy(rules):
    """攻撃しなければ破壊されない。"""
    e = _build(rules, {"bz": ["T1070"]}, {})
    for _ in range(400):
        if e.s.turn >= 2:
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T1070" in _defns(e, "bz", 0)
    assert "T1070" not in _defns(e, "graveyard", 0)


# ---------- 実挙動: 条件つきスレイヤー付与 ----------

def test_slayer_destroys_attacker_after_lost_battle(rules):
    """超化獣（T1071）がいれば T1070 はスレイヤーを得る:
    パワー3000の攻撃をブロックしてバトルに負けても、
    バトルの後に攻撃クリーチャーが破壊される。"""
    e = _build(rules, {"bz": ["T1070", "T1071"]}, {"bz": ["T1072"]})
    st = _drive(e, "T1072", blocker="T1070")
    assert st["attacked"]
    assert "T1070" in _defns(e, "graveyard", 0)      # バトル敗北
    assert "T1072" in _defns(e, "graveyard", 1)      # スレイヤーで破壊
    assert "T1072" not in _defns(e, "bz", 1)
    assert "T1071" in _defns(e, "bz", 0)             # 条件側は残る


def test_no_slayer_without_choukajuu(rules):
    """超化獣がいなければスレイヤーは付かず、バトルに勝った
    攻撃クリーチャーは場に残る。"""
    e = _build(rules, {"bz": ["T1070"]}, {"bz": ["T1072"]})
    st = _drive(e, "T1072", blocker="T1070")
    assert st["attacked"]
    assert "T1070" in _defns(e, "graveyard", 0)      # バトル敗北
    assert "T1072" in _defns(e, "bz", 1)             # 破壊されない
    assert "T1072" not in _defns(e, "graveyard", 1)
