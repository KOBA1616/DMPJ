"""語彙パイロット第296弾: 「S・トリガーは使えない」
（shield_trigger_restriction / s_trigger_disable）。

rejects の shield_trigger_restriction 純粋3件（dmx18-003 / dmx21-064 /
dmx22b-023）と s_trigger_disable 純粋3件（dmr13-003 / dmrp01-s03 /
dm26rp2-066）、計6件。共通条項は「手札に加えた（加わる）シールド
カードの S・トリガーは使えない」で、不足は次の2形に分かれる:

- 形A（そのカード形、5件）: 効果で自分のシールドを手札に加える時、
  そのカードの「S・トリガー」は使えない。機構は既存（ギャップ名と
  語彙名のドリフト）: move op の引数 strigger: "off"（バンドC2 U68。
  escape キーワードの instead 形が keywords.yaml に、実挙動は第281弾
  test_796 で固定済み）。効果の shield→hand 移動は op_move が break
  タスク（phase 1・fire_break: False）へ回し、宣言諮問の時点で
  t["strigger"] == "off" がその束の宣言肢を消す。シールド以外の
  カードが手札に加わる場合は Card.strigger_off の印が付き、手札を
  離れると消える（core の印リセット）。本弾は対象行の形（CIP 誘発・
  攻撃誘発の素の move）でこの形を再検証する。
- 形B（常在形、1件・dmrp01-s03）: 「自分の光ではないカードの
  S・トリガーは使えない」常在型。dm24ex1-001（変換済み）の
  affects zone: shield ＋ mod grant [s_trigger] の鏡像で、
  {kind: static, affects: {zone: shield, owner: you,
    filter: {not_civs: [light]}}, mod: {deny: [s_trigger]}}
  と書く。permits は deny → allow → 既定の順（101.2「できない」は
  「できる」に勝つ）で、キーワード s_trigger の allow（zone: shield
  の自己常在）を打ち消す。ブレイク経路・効果経路のどちらも宣言
  諮問は combat の phase 1 で _permits_face を見るため両方に効く。

新規 op・面フィールド・GameState フィールドはなし（state.rs 変更
なし、スキーマ再生成なし）。プロト T892（形A）/ T893（形Aの対照:
strigger 指定なし）/ T894（形B）。シールド役は既存プロト
T279（闇・S・トリガー持ちクリーチャー）と T207（光・同）を使う。

注意（本弾の範囲外）: 印 strigger_on（付与）と形B の deny が重なった
場合、combat phase 1 の elif 分岐は印側を優先して宣言肢を復活させ
うる（permits の deny と印の優劣が未分離）。対象6件にはこの重なりは
無く、既存の印つき変換カードにも形B の発生源と同居するものは無い
ため、本弾では触らない。
"""
import copy

import pytest

from dmsim.cards.defs import DefError, load_tables, parse_card
from tests.conftest import setup

TABLES = load_tables()

CIP = {"event": "move", "to": "bz", "subject": "self"}
MOVE_OFF = {"op": "move", "select": {"zone": "shield", "owner": "you", "count": 1},
            "to": "hand", "reason": "return", "strigger": "off"}
MOVE_PLAIN = {"op": "move", "select": {"zone": "shield", "owner": "you", "count": 1},
              "to": "hand", "reason": "return"}
FORM_B = {"kind": "static",
          "affects": {"zone": "shield", "owner": "you", "filter": {"not_civs": ["light"]}},
          "mod": {"deny": ["s_trigger"]}}

EXPECTED = {
    "T892": {"kind": "trigger", "when": dict(CIP), "effect": [dict(MOVE_OFF)]},
    "T893": {"kind": "trigger", "when": dict(CIP), "effect": [dict(MOVE_PLAIN)]},
    "T894": dict(FORM_B),
}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _drive(e, stop, play_key=None, choose_defn=None, limit=800):
    """play_key を1回出し、choose_defn を choose_cards で選び、
    現れた Decision の kind 列を返す汎用ドライバ。"""
    seen = []
    played = {"done": False}
    for _ in range(limit):
        if stop(e):
            return seen
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind == "declare_strigger":
            e.answer([])          # 宣言しない（機会の有無だけを見る）
        elif kind == "main" and play_key and not played["done"]:
            hit = [i for i, k in enumerate(keys)
                   if play_key in k and not k.startswith("charge:")]
            if hit:
                played["done"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_cards" and choose_defn:
            hit = [i for i, o in enumerate(d["options"])
                   if e.cdef(o["cid"]).id == choose_defn]
            if hit:
                e.answer(hit[:max(d.get("min", 1), 1)])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif kind == "order_pending":
            e.answer([0])
        elif kind == "block":
            e.answer([keys.index("no_block")] if "no_block" in keys
                     else list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


def _attack_out(e, attacker, shield_defn):
    """attacker でプレイヤーを攻撃し、shield_defn のシールドを割る。
    現れた Decision の kind 列を返す（第146弾 _play_out と同形）。
    宣言への回答直後はまだシールドが手札へ動いていない（break タスクの
    phase 2 で動く）ため、移動が済んで静かになるまで進める。"""
    seen = []
    for _ in range(500):
        if shield_defn in _defns(e, "hand", 1) and _quiet(e):
            break
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind in ("charge", "main"):
            e.answer([keys.index("pass")])
        elif kind == "attack":
            hit = [i for i, k in enumerate(keys) if k == f"attack:{attacker}:player"]
            if not hit:
                e.answer([keys.index("pass")])
                break
            e.answer([hit[0]])
        elif kind == "choose_breaker":
            e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
        elif kind == "choose_shields":
            hit = [i for i, o in enumerate(d["options"])
                   if e.cdef(o["cid"]).id == shield_defn]
            e.answer(hit[:1] if hit else list(range(d["min"])))
        elif kind in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif kind == "block":
            e.answer([keys.index("no_block")] if "no_block" in keys
                     else list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return seen


# ---------- parse / validation ----------

def test_pilot296_protos_parse(rules):
    for cid, want in EXPECTED.items():
        d = rules.cards[cid]
        assert want in d.abilities, cid


def test_pilot296_forms_raw_parse():
    for ab in ({"kind": "trigger", "when": dict(CIP), "effect": [dict(MOVE_OFF)]},
               dict(FORM_B)):
        d = parse_card({"id": "TX296", "name": "x", "types": ["creature"],
                        "civs": ["light"], "cost": 4, "power": 4000,
                        "abilities": [copy.deepcopy(ab)]}, TABLES)
        assert ab in d.abilities


def test_pilot296_form_b_validation():
    # deny の action は permissions の action 名でなければならない
    bad = copy.deepcopy(FORM_B)
    bad["mod"] = {"deny": ["s_triger"]}
    with pytest.raises(DefError):
        parse_card({"id": "TX296", "name": "x", "types": ["creature"],
                    "civs": ["darkness"], "cost": 4, "power": 4000,
                    "abilities": [bad]}, TABLES)
    # affects の filter は FILTER_KEYS の範囲でなければならない
    bad2 = copy.deepcopy(FORM_B)
    bad2["affects"] = {"zone": "shield", "owner": "you", "filter": {"civ": ["light"]}}
    with pytest.raises(DefError):
        parse_card({"id": "TX296", "name": "x", "types": ["creature"],
                    "civs": ["darkness"], "cost": 4, "power": 4000,
                    "abilities": [bad2]}, TABLES)


# ---------- 実挙動: 形A（CIP の素の move） ----------

def test_form_a_cip_move_suppresses_strigger(rules):
    """T892 の CIP で手札に加えたシールド（T279）は宣言できない。"""
    e = setup(rules, {"hand": ["T892"], "mana": ["T004"] * 4,
                      "shield": ["T279", "T001", "T001", "T001", "T001"]}, {})
    t279 = next(c for c in e.zlist("shield", 0) if e.cdef(c).id == "T279")
    seen = _drive(e, lambda ev: "T279" in _defns(ev, "hand", 0) and _quiet(ev),
                  play_key="play:T892", choose_defn="T279")
    assert "T279" in _defns(e, "hand", 0)
    assert "declare_strigger" not in seen
    assert e.s.cards[t279].strigger_off is True     # 印が付いている


def test_form_a_control_offers_strigger(rules):
    """対照 T893（strigger 指定なし）では宣言の機会がある。"""
    e = setup(rules, {"hand": ["T893"], "mana": ["T004"] * 4,
                      "shield": ["T279", "T001", "T001", "T001", "T001"]}, {})
    t279 = next(c for c in e.zlist("shield", 0) if e.cdef(c).id == "T279")
    seen = _drive(e, lambda ev: "T279" in _defns(ev, "hand", 0) and _quiet(ev),
                  play_key="play:T893", choose_defn="T279")
    assert "T279" in _defns(e, "hand", 0)
    assert "declare_strigger" in seen
    assert e.s.cards[t279].strigger_off is False


# ---------- 実挙動: 形B（常在 deny） ----------

def test_form_b_break_denies_non_light(rules):
    """発生源がいる時、割られた闇のシールド（T279）は宣言できない。"""
    e = setup(rules, {"bz": ["T001"]},
              {"bz": ["T894"], "shield": ["T279", "T001", "T001", "T001", "T001"]})
    seen = _attack_out(e, "T001", "T279")
    assert "T279" in _defns(e, "hand", 1)
    assert "declare_strigger" not in seen


def test_form_b_break_baseline_offers(rules):
    """対照: 発生源がいなければ同じシールドでも宣言できる。"""
    e = setup(rules, {"bz": ["T001"]},
              {"shield": ["T279", "T001", "T001", "T001", "T001"]})
    seen = _attack_out(e, "T001", "T279")
    assert "T279" in _defns(e, "hand", 1)
    assert "declare_strigger" in seen


def test_form_b_break_allows_light(rules):
    """光のシールド（T207）は not_civs に当たらず宣言できる。"""
    e = setup(rules, {"bz": ["T001"]},
              {"bz": ["T894"], "shield": ["T207", "T001", "T001", "T001", "T001"]})
    seen = _attack_out(e, "T001", "T207")
    assert "T207" in _defns(e, "hand", 1)
    assert "declare_strigger" in seen


def test_form_b_opponent_shields_unaffected(rules):
    """affects の owner: you は発生源のコントローラー側だけ。
    相手の闇シールドは、自分の発生源がいても宣言できる。"""
    e = setup(rules, {"bz": ["T894", "T001"]},
              {"shield": ["T279", "T001", "T001", "T001", "T001"]})
    seen = _attack_out(e, "T001", "T279")
    assert "T279" in _defns(e, "hand", 1)
    assert "declare_strigger" in seen


def test_form_b_effect_path_denies(rules):
    """効果で手札に加える経路（strigger 指定なしの move）でも、
    phase 1 の permits 判定で形B が効く。"""
    e = setup(rules, {"bz": ["T894"], "hand": ["T893"], "mana": ["T004"] * 4,
                      "shield": ["T279", "T001", "T001", "T001", "T001"]}, {})
    seen = _drive(e, lambda ev: "T279" in _defns(ev, "hand", 0) and _quiet(ev),
                  play_key="play:T893", choose_defn="T279")
    assert "T279" in _defns(e, "hand", 0)
    assert "declare_strigger" not in seen
