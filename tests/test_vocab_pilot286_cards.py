"""語彙パイロット第286弾のカード適用テスト（登録形）。

ラウンド321で choose_restriction 純粋4件を新規登録:
- dmr18-054 アクア特攻兵 デコイ: partial は abilities を持たず text も
  節だけに切れていた。text を reject 行の公式全文に戻し、形A
  （マナ武装3の条件つき常在型 must_be_chosen）を追加。
- dmrp06-029 ギギギのギタロー: partial は abilities を持たず text も
  切れていた。全文に戻し、形B（出た時、そのターン modify で
  must_be_chosen を付与）を追加。
- dm26rp2-033 救済のラクシャ ミルク: shield_go キーワードはそのまま、
  形C（無条件常在型）を追加。破壊されると shield_go の必須置換で
  表向きシールド化する（墓地には行かない）。
- dm26ex3-088 雨森まもり: 第186弾で解けた置換2件（スーパーガードマン、
  破壊時シールド化）はそのまま、形Cを追加。
- 4件とも alias は無し（identity.aliases_for は空）。
- converted 10,167 / rejects 2,166、重なり0・漏れ0。choose_restriction
  は残り0件でファミリー解消。

プロトテスト（test_vocab_pilot286.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402


def setup(rules, p0, p1=None, filler="T001", seed=1, deck_size=20):
    """conftest の setup と同じ薄い包み。tests.conftest を import すると
    DMSIM_SKIP_CONVERTED が再設定されて converted が読めなくなるため、
    ここでは直接 scenario.build を包む（第285弾 cards と同じ）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGETS = ["dmr18-054", "dmrp06-029", "dm26rp2-033", "dm26ex3-088"]

FORM_A = {"kind": "static", "affects": "self",
          "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                                    "filter": {"civs": ["water"]}}}, ">=", 3]},
          "mod": {"must_be_chosen": True}}

FORM_B = {"kind": "trigger",
          "when": {"event": "move", "to": "bz", "subject": "self"},
          "effect": [{"op": "modify", "select": {"ref": "self"},
                      "mod": {"must_be_chosen": True},
                      "duration": "end_of_turn"}]}

FORM_C = {"kind": "static", "affects": "self", "mod": {"must_be_chosen": True}}

REPLACE_BATTLE = {
    "kind": "replace",
    "when": {"event": "battle",
             "subject": {"owner": "you", "filter": {"types": ["creature"]},
                         "other": True}},
    "instead": [{"op": "battle_substitute", "tap": True}],
}

REPLACE_SHIELD = {
    "kind": "replace",
    "optional": True,
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "subject": "self"},
    "instead": [{"op": "move", "select": {"ref": "self"},
                 "to": "shield", "reason": "charge"}],
}

TEXT_054 = ("マナ武装 ３-相手が自分のクリーチャーを選ぶ時、自分のマナゾーンに"
            "水のカードが３枚以上あれば、相手は《アクア特攻兵 デコイ》以外"
            "選べない。（ただし、自分の他のクリーチャーを攻撃またはブロック"
            "してもよい）")

TEXT_029 = ("このクリーチャーがバトルゾーンに出た時、そのターン、相手が"
            "自分のクリーチャーを選ぶ時、相手は可能ならこのクリーチャーを"
            "選ぶ。（ただし、自分の他のクリーチャーを攻撃またはブロック"
            "してもよい）")

TEXT_033 = ("相手がクリーチャーを選ぶなら、可能ならこのクリーチャーを選ぶ。\n"
            "{SG} シールド・ゴー（このクリーチャーが破壊された時、自分の墓地から"
            "表向きでシールド化する。このクリーチャーが表向きでシールドゾーンを"
            "離れる時、かわりに墓地に置く）")

TEXT_088 = ("{GS} G・ストライク（このカードを自分のシールドゾーンから手札に"
            "加える時、表向きにし、相手のクリーチャーを１体選んでもよい。"
            "このターン、そのクリーチャーは攻撃できない）\n"
            "ブロッカー\n"
            "スーパーガードマン（自分の他のクリーチャーがバトルする時、かわりに"
            "このクリーチャーをタップしてバトルさせてもよい）\n"
            "Q・ブレイカー\n"
            "相手がクリーチャーを選ぶなら、可能ならこのクリーチャーを選ぶ。\n"
            "このクリーチャーが破壊される時、墓地に置くかわりにシールド化してもよい。")


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


# ---------- 登録形 ----------

def test_registered_forms():
    rej = _reject_rows()
    for cid in TARGETS:
        assert cid not in rej, cid
        _converted(cid)
    # ファミリー解消: choose_restriction を含む行は rejects に残らない
    assert not [r["id"] for r in rej.values()
                if "choose_restriction" in (r.get("gaps") or [])]

    c = _converted("dmr18-054")
    assert c["abilities"] == [FORM_A]
    assert c["text"] == TEXT_054
    assert not c.get("keywords")
    assert "unsupported" not in (c.get("source") or {})
    assert (c.get("source") or {}).get("aliases") is None
    d = parse_card(c, TABLES)
    assert d.abilities == [FORM_A]

    c = _converted("dmrp06-029")
    assert c["abilities"] == [FORM_B]
    assert c["text"] == TEXT_029
    assert not c.get("keywords")
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.abilities == [FORM_B]

    c = _converted("dm26rp2-033")
    assert c["abilities"] == [FORM_C]
    assert c["keywords"] == ["shield_go"]
    assert c["text"] == TEXT_033
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.keywords == ["shield_go"]
    # shield_go の展開（置換2件）の後ろに形Cが付く
    assert len(d.abilities) == 3 and d.abilities[-1] == FORM_C

    c = _converted("dm26ex3-088")
    assert c["abilities"] == [REPLACE_BATTLE, REPLACE_SHIELD, FORM_C]
    assert sorted(c["keywords"]) == ["blocker", "g_strike", "quad_breaker"]
    assert c["text"] == TEXT_088
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert FORM_C in d.abilities
    assert sum(1 for a in d.abilities if a["kind"] == "replace") == 2
    assert sorted(d.keywords) == ["blocker", "g_strike", "quad_breaker"]


# ---------- 実挙動の共通部品（第286弾プロトと同じ型） ----------

def _in_gy(e, defn, player=0):
    return any(e.s.cards[c].defn == defn for c in e.zlist("graveyard", player))


def _in_bz(e, defn, player=0):
    return any(e.s.cards[c].defn == defn and e.s.cards[c].controller == player
               for c in e.zlist("bz", player))


def _shield_cards(e, defn, player=0):
    return [c for c in e.zlist("shield", player) if e.cdef(c).id == defn]


def _cast(e, caster, spell, target=None, limit=200):
    """caster が spell を唱える。target は (defn, controller)。
    戻り値: 対象選択で提示されたキー一覧 or None（候補が1体に絞られ
    自動解決された場合）。置換の諮問は decline する。"""
    offered = None
    started = False
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not started and d["kind"] == "main" and d.get("player") == caster \
                and f"play:{spell}" in keys:
            started = True
            e.answer([keys.index(f"play:{spell}")])
            continue
        if started:
            if d["kind"] == "choose_replacement":
                if "decline" in keys:
                    e.answer([keys.index("decline")])
                else:
                    e.answer(list(range(d["min"])))
                continue
            if d["kind"] == "choose_cards" and offered is None:
                offered = list(keys)
                ans = None
                if target is not None:
                    for i, o in enumerate(d["options"]):
                        c = e.s.cards[o["cid"]]
                        if e.cdef(o["cid"]).id == target[0] \
                                and c.controller == target[1]:
                            ans = [i]
                            break
                e.answer(ans if ans is not None else list(range(d["min"])))
                continue
            if d["kind"] in ("attack", "charge"):
                break
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return offered


# ---------- 形A: dmr18-054 ----------

def test_054_restricts_when_armed(rules):
    """水マナ3枚以上で武装: 相手の単体破壊は dmr18-054 に自動で決まる。"""
    e = setup(rules, {"bz": ["dmr18-054", "T001"], "mana": ["T010"] * 3},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    offered = _cast(e, 1, "T056")
    assert offered is None                    # 候補が1体に絞られ自動解決
    assert _in_gy(e, "dmr18-054")
    assert _in_bz(e, "T001")


def test_054_inactive_below_three_water(rules):
    """水マナ2枚では武装せず、相手は自由に選べる（対照）。"""
    e = setup(rules, {"bz": ["dmr18-054", "T001"],
                      "mana": ["T010", "T010", "T001"]},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    offered = _cast(e, 1, "T056", target=("T001", 0))
    assert offered is not None
    assert any("dmr18-054" in k for k in offered) \
        and any("T001" in k for k in offered)
    assert _in_gy(e, "T001")
    assert _in_bz(e, "dmr18-054")


# ---------- 形B: dmrp06-029 ----------

def _cid_of(e, defn, controller=0):
    for c in e.zlist("bz", controller):
        card = e.s.cards[c]
        if card.controller == controller and e.cdef(c).id == defn:
            return c
    raise AssertionError(defn)


def _summon_029(e, limit=300):
    """P0 が手札から dmrp06-029 を召喚し、解決直後の決定で止める
    （第286弾プロトの _summon_821 と同じ観測点）。"""
    played = False
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and "play:dmrp06-029" in keys:
            played = True
            e.answer([keys.index("play:dmrp06-029")])
            continue
        if played and d["kind"] != "pay_mana":
            return
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("summon did not resolve")


def test_029_grants_on_entry_turn_only(rules):
    """出たターンだけ chars に must_be_chosen が立つ。ターンが回ると切れる。"""
    # ゼロ文明のカードの支払いには zero 文明のマナが1枚要る（エンジンの
    # civ_ok は need の各文明を別々のマナで満たす）ため、マナに同カードを
    # 1枚置いて残り3枚を T001 で揃える（合計値4＝コスト4）。
    e = setup(rules, {"bz": ["T001"], "hand": ["dmrp06-029"],
                      "mana": ["dmrp06-029", "T001", "T001", "T001"]},
              {"bz": ["T001"]}, filler="T002")
    _summon_029(e)
    cid = _cid_of(e, "dmrp06-029")
    assert e.chars(cid)["must_be_chosen"] is True
    for _ in range(300):
        if e.s.turn >= 2:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.turn >= 2
    assert e.chars(cid)["must_be_chosen"] is False


def _strigger_scenario(e, limit=600):
    """P0 が dmrp06-029 を召喚してから T001 でプレイヤーを攻撃し、
    P1 のシールド（全て T006）を割る。P1 が S・トリガーを宣言して唱え、
    対象選択が提示されたらそのキー一覧を返す（自動解決なら None）。"""
    played = False
    attacked = False
    declared = False
    offered = None
    for _ in range(limit):
        if declared and _in_gy(e, "T006", 1):
            return offered
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and d.get("player") == 0 and not played:
            played = True
            if "play:dmrp06-029" in keys:
                e.answer([keys.index("play:dmrp06-029")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if kind == "pay_mana":
            e.answer([0])
            continue
        if kind == "attack" and d.get("player") == 0 and not attacked:
            attacked = True
            if "attack:T001:player" in keys:
                e.answer([keys.index("attack:T001:player")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if kind == "choose_shields":
            e.answer(list(range(d.get("min", 0))))
            continue
        if kind == "declare_strigger":
            hit = None
            for i, o in enumerate(d["options"]):
                if (o.get("cid") is not None and e.cdef(o["cid"]).id == "T006") \
                        or "T006" in o["key"]:
                    hit = i
                    break
            if hit is not None:
                declared = True
                e.answer([hit])
            else:
                e.answer([])
            continue
        if kind == "choose_cards" and declared and offered is None:
            offered = list(keys)
            e.answer(list(range(d["min"])))
            continue
        if kind == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("S-trigger scenario did not finish")


def test_029_restricts_opponent_strigger_choice(rules):
    """出たターン: 自分の攻撃で割った相手の S・トリガー（T006）の
    対象選択は dmrp06-029 に自動で決まり、攻撃した T001 は無事。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["dmrp06-029"],
                      "mana": ["dmrp06-029", "T001", "T001", "T001"]},
              {"shield": ["T006"] * 5}, filler="T002")
    offered = _strigger_scenario(e)
    assert offered is None                    # 候補が1体に絞られ自動解決
    assert _in_gy(e, "dmrp06-029")
    assert _in_bz(e, "T001")


# ---------- 形C: dm26rp2-033 / dm26ex3-088 ----------

def test_033_restricts_and_shield_go(rules):
    """無条件常在型: 相手の単体破壊は dm26rp2-033 に自動で決まる。
    破壊された 033 は shield_go の必須置換で表向きシールド化する。"""
    e = setup(rules, {"bz": ["dm26rp2-033", "T001"], "mana": ["T001"] * 3},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    offered = _cast(e, 1, "T056")
    assert offered is None
    assert _in_bz(e, "T001")
    assert not _in_bz(e, "dm26rp2-033")
    assert not _in_gy(e, "dm26rp2-033")
    shields = _shield_cards(e, "dm26rp2-033", 0)
    assert len(shields) == 1
    assert e.s.cards[shields[0]].face_up is True


def test_088_restricts_choice(rules):
    """無条件常在型: chars に印が立ち、相手の単体破壊は dm26ex3-088 に
    自動で決まる（破壊時シールド化の置換は decline して墓地に行く）。"""
    e = setup(rules, {"bz": ["dm26ex3-088", "T001"], "mana": ["T001"] * 3},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    assert e.chars(_cid_of(e, "dm26ex3-088"))["must_be_chosen"] is True
    offered = _cast(e, 1, "T056")
    assert offered is None
    assert _in_gy(e, "dm26ex3-088")
    assert _in_bz(e, "T001")
