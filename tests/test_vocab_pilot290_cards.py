"""語彙パイロット第290弾のカード適用テスト（登録形）。

ラウンド325で win_prevention 純粋3件を新規登録:
- dmrp06-001 帰還の精霊シュマヌマージ: partial は abilities を持たない。
  形A（自分のクリーチャーの数が相手より多ければ負けない常在型 no_lose）
  ＋形D（相手の呪文の効果またはクリーチャーの能力で自分のカードが山札の
  一番下に置かれた時、1枚引いてもよい）を構築。text・keywords は
  partial のまま。
- dmx11-001 十弐制覇 鬼「王者」: 形B（タップされている間、負けない
  常在型 no_lose）を追加。partial の evolve_from は {types: [creature]}
  だけで公式全文の「ハンターとエイリアンを種族に持つクリーチャー」の
  条件が欠けていたため {races_all: [ハンター, エイリアン]} に補正。
- dmr20-038 完全防御革命: partial の text は unsupported 節だけに
  切れていたため reject 行の公式全文に戻し、spell に形E（選んだ
  クリーチャーがバトルに勝った時アンタップする遅延誘発）、abilities に
  形C（クリーチャーによる攻撃以外の方法で相手が勝つ時、手札から捨てて
  置き換える敗北置換）を構築。
- 3件とも alias は無し（identity で canon は自 ID、aliases は空）。
- converted 10,181 / rejects 2,149、重なり0・漏れ0。win_prevention は
  残り0件でファミリー解消。

プロトテスト（test_vocab_pilot290.py）とは別プロセスで実行すること
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
    ここでは直接 scenario.build を包む（第286弾 cards と同じ）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGETS = ["dmrp06-001", "dmx11-001", "dmr20-038"]

FORM_A = {"kind": "static",
          "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                                    "filter": {"types": ["creature"]}}},
                          ">",
                          {"count": {"zone": "bz", "owner": "opp",
                                     "filter": {"types": ["creature"]}}}]},
          "no_lose": True}

FORM_B = {"kind": "static",
          "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
          "no_lose": True}

FORM_C = {"kind": "replace", "zone": "hand", "optional": True,
          "when": {"event": "lose", "reason": ["deck_out", "state", "effect"]},
          "instead": [{"op": "move", "select": {"ref": "self"},
                       "to": "graveyard", "reason": "discard"}]}

FORM_D = {"kind": "trigger",
          "when": {"event": "move", "to": "deck", "position": "bottom",
                   "subject": {"owner": "you"},
                   "cause": {"by": "opp", "kind": ["spell", "ability"]}},
          "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]}

FORM_E_SPELL = [
    {"op": "choose",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": 1},
     "as": "pick"},
    {"op": "delayed_trigger",
     "when": {"event": "battle_win", "subject": {"ref": "pick"}},
     "duration": "end_of_turn",
     "effect": [{"op": "untap", "select": {"ref": "pick"}}]},
]

TEXT_001 = ("ブロッカー\nW・ブレイカー\n"
            "バトルゾーンにある自分のクリーチャーの数が相手より多ければ、自分はゲームに負けず、相手はゲームに勝てない。\n"
            "相手の呪文の効果またはクリーチャーの能力によって、自分のカードが山札の一番下に置かれた時、カードを１枚引いてもよい。")

TEXT_X11 = ("進化-自分の、ハンターとエイリアンを種族に持つクリーチャー１体の上に置く。\n"
            "W・ブレイカー(このクリーチャーはシールドを２枚ブレイクする)\n"
            "このクリーチャーがタップされている間、自分はゲームに負けず、相手は勝てない。")

TEXT_038 = ("自分のクリーチャーを１体選ぶ。このターン、そのクリーチャーがバトルに勝った時、アンタップする。"
            "相手が、クリーチャーによる攻撃以外の方法でゲームに勝つ時、かわりに自分の手札にあるこのカードを捨ててもよい。")


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
    # ファミリー解消: win_prevention を含む行は rejects に残らない
    assert not [r["id"] for r in rej.values()
                if "win_prevention" in (r.get("gaps") or [])]

    c = _converted("dmrp06-001")
    assert c["abilities"] == [FORM_A, FORM_D]
    assert c["keywords"] == ["blocker", "double_breaker"]
    assert c["text"] == TEXT_001
    assert "unsupported" not in (c.get("source") or {})
    assert (c.get("source") or {}).get("aliases") is None
    d = parse_card(c, TABLES)
    assert any(ab.get("no_lose") is True for ab in d.abilities)
    assert any(ab.get("when", {}).get("position") == "bottom"
               for ab in d.abilities)

    c = _converted("dmx11-001")
    assert c["abilities"] == [FORM_B]
    assert c["keywords"] == ["double_breaker"]
    assert c["evolve_from"] == {"races_all": ["ハンター", "エイリアン"]}
    assert c["text"] == TEXT_X11
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert any(ab.get("no_lose") is True for ab in d.abilities)

    c = _converted("dmr20-038")
    assert c["abilities"] == [FORM_C]
    assert c["spell"] == FORM_E_SPELL
    assert not c.get("keywords")
    assert c["text"] == TEXT_038
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    reps = [ab for ab in d.abilities if ab.get("kind") == "replace"]
    assert len(reps) == 1
    assert reps[0]["when"]["reason"] == ["deck_out", "state", "effect"]
    assert reps[0].get("zone") == "hand"


# ---------- 駆動ヘルパ（第290弾プロトと同じ型） ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive(e, on_dec, limit=600):
    for _ in range(limit):
        if e.s.result is not None:
            return
        d = e.advance()
        if d is None:
            return
        r = on_dec(e, d)
        if r == "stop":
            return
        if r:
            continue
        keys = _keys(d)
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def _hand_n(e, p):
    return len(e.zlist("hand", p))


def _in_gy(e, defn, p):
    return any(e.cdef(c).id == defn for c in e.zlist("graveyard", p))


# ---------- 形A: dmrp06-001（数の条件つき no_lose） ----------

def test_001_immune_when_outnumbering(rules):
    e = setup(rules, {"bz": ["dmrp06-001", "T001", "T001"]}, {"bz": ["T001"]})
    for reason in ("deck_out", "direct_attack", "effect", "state"):
        assert e._lose_immune(0, reason) is True
        assert e._lose_immune(1, reason) is False   # 相手は守られない


def test_001_not_immune_when_not_outnumbering(rules):
    e = setup(rules, {"bz": ["dmrp06-001", "T001"]}, {"bz": ["T001", "T001"]})
    assert e._lose_immune(0, "deck_out") is False   # 同数では守られない
    e = setup(rules, {"bz": ["dmrp06-001"]}, {"bz": ["T001", "T001"]})
    assert e._lose_immune(0, "effect") is False     # 少なければ守られない


# ---------- 形D: dmrp06-001（相手の効果で一番下に置かれた時） ----------

def _opp_act(e, defn, choose_defn):
    """相手（P1）が defn を使い choose_defn を対象に取るまで進める。
    P0 の yes_no（形D の「引いてもよい」）を見たら記録して引く。"""
    seen = {"yes_no": False, "played": False}

    def on_dec(e, d):
        keys = _keys(d)
        if d["kind"] == "yes_no" and d.get("player") == 0:
            seen["yes_no"] = True
            e.answer([0])   # 引く
            return True
        if d["kind"] == "main" and d.get("player") == 1 \
                and f"play:{defn}" in keys:
            seen["played"] = True
            e.answer([keys.index(f"play:{defn}")])
            return True
        if d["kind"] == "pay_mana":
            e.answer([0])
            return True
        if d["kind"] == "choose_cards":
            for i, o in enumerate(d["options"]):
                if e.cdef(o["cid"]).id == choose_defn:
                    e.answer([i])
                    return True
            e.answer(list(range(d.get("min", 0))))
            return True
        if seen["played"] and d["kind"] in ("main", "charge", "attack") \
                and d.get("player") == 1:
            return "stop"
        return False

    _drive(e, on_dec)
    assert seen["played"]
    return seen


def test_001_form_d_opponent_spell_bottom_draws(rules):
    e = setup(rules, {"bz": ["dmrp06-001", "T001"]},
              {"bz": ["T001"], "hand": ["T841"], "mana": ["T010"] * 4})
    hand0 = _hand_n(e, 0)
    seen = _opp_act(e, "T841", "T001")
    assert seen["yes_no"] is True
    assert _hand_n(e, 0) == hand0 + 1                    # 1枚引いた
    deck0 = list(e.zlist("deck", 0))
    assert e.cdef(deck0[-1]).id == "T001"                # 一番下に置かれた


def test_001_form_d_opponent_ability_bottom_draws(rules):
    e = setup(rules, {"bz": ["dmrp06-001", "T001"]},
              {"bz": ["T001"], "hand": ["T843"], "mana": ["T010"] * 5})
    hand0 = _hand_n(e, 0)
    seen = _opp_act(e, "T843", "T001")
    assert seen["yes_no"] is True          # クリーチャーの能力でも発火する
    assert _hand_n(e, 0) == hand0 + 1


# ---------- 形B: dmx11-001（タップ中だけ no_lose） ----------

def test_x11_immune_only_while_tapped(rules):
    e = setup(rules, {"bz": ["dmx11-001"]}, {})
    assert e._lose_immune(0, "deck_out") is False
    assert e._lose_immune(0, "direct_attack") is False
    cid = next(c for c in e.zlist("bz", 0) if e.cdef(c).id == "dmx11-001")
    e.s.cards[cid].tapped = True
    assert e._lose_immune(0, "deck_out") is True
    assert e._lose_immune(0, "direct_attack") is True
    assert e._lose_immune(1, "deck_out") is False


# ---------- 形C: dmr20-038（手札からの敗北置換） ----------

def _cast_lose_and_answer(e, accept):
    """T845（効果で自分が負ける）を唱え、lose_replace の諮問に答える。
    戻り値: lose_replace 決定を見たか。"""
    seen = {"v": False}

    def on_dec(e, d):
        keys = _keys(d)
        if seen["v"]:
            return "stop"          # 置換の諮問に答えた後の最初の決定で止める
        if d["kind"] == "main" and d.get("player") == 0 and "play:T845" in keys:
            e.answer([keys.index("play:T845")])
            return True
        if d["kind"] == "pay_mana":
            e.answer([0])
            return True
        if d["kind"] == "lose_replace":
            seen["v"] = True
            if accept:
                e.answer([next(i for i, k in enumerate(keys)
                               if k.startswith("lose_replace:dmr20-038"))])
            else:
                e.answer([keys.index("decline")])
            return True
        return False

    _drive(e, on_dec)
    return seen["v"]


def test_038_form_c_accept_discards_and_survives(rules):
    e = setup(rules, {"hand": ["dmr20-038", "T845"], "mana": ["T008"]},
              {"bz": ["T001"]})
    assert _cast_lose_and_answer(e, accept=True)
    assert e.s.result is None                    # 敗北は置換された
    assert _in_gy(e, "dmr20-038", 0)             # かわりに手札のこのカードを捨てた
    assert not any(e.cdef(c).id == "dmr20-038" for c in e.zlist("hand", 0))


def test_038_form_c_decline_loses(rules):
    e = setup(rules, {"hand": ["dmr20-038", "T845"], "mana": ["T008"]},
              {"bz": ["T001"]})
    assert _cast_lose_and_answer(e, accept=False)
    assert e.s.result is not None
    assert e.s.result["winner"] == 1 and e.s.result["reason"] == "effect"


def test_038_form_c_candidates_by_reason(rules):
    e = setup(rules, {"hand": ["dmr20-038"]}, {"bz": ["T001"]})
    assert e._lose_candidates(0, "direct_attack") == []   # 攻撃による敗北は対象外
    for reason in ("deck_out", "state", "effect"):
        cands = e._lose_candidates(0, reason)
        assert len(cands) == 1
        assert e.cdef(cands[0][0]).id == "dmr20-038"
    assert e._lose_candidates(1, "effect") == []          # 相手の敗北は守らない


# ---------- 形E: dmr20-038（バトルに勝った時アンタップ） ----------

def _form_e(rules, attack_player):
    e = setup(rules, {"bz": ["T001", "T827"], "hand": ["dmr20-038"],
                      "mana": ["T034"] * 3},
              {"bz": ["T002"]})
    t001 = next(c for c in e.zlist("bz", 0) if e.cdef(c).id == "T001")
    t002 = next(c for c in e.zlist("bz", 1) if e.cdef(c).id == "T002")
    st = {"chose": False, "cast": False, "attacked": False, "done": False}

    def on_dec(e, d):
        keys = _keys(d)
        if not st["chose"]:
            if d["kind"] == "main" and d.get("player") == 0 \
                    and "play:dmr20-038" in keys:
                e.answer([keys.index("play:dmr20-038")])
                return True
            if d["kind"] == "pay_mana":
                e.answer([0])
                return True
            if d["kind"] == "choose_cards":
                for i, o in enumerate(d["options"]):
                    if o["cid"] == t001:
                        e.answer([i])
                        st["chose"] = True
                        return True
                e.answer(list(range(d.get("min", 0))))
                return True
            return False
        if not st["cast"]:
            st["cast"] = True        # 解決後の決定に戻った
            if not attack_player:
                e.s.cards[t002].tapped = True   # 攻撃できるようタップさせる
        if not st["attacked"]:
            if d["kind"] == "attack" and d.get("player") == 0:
                want = "attack:T001:player" if attack_player \
                    else "attack:T001:T002"
                if want in keys:
                    st["attacked"] = True
                    e.answer([keys.index(want)])
                    return True
                if "pass" in keys:
                    e.answer([keys.index("pass")])
                    return True
            return False
        if d["kind"] in ("main", "charge", "attack") and d.get("player") == 0:
            st["done"] = True
            return "stop"
        return False

    _drive(e, on_dec)
    assert st["cast"] and st["attacked"] and st["done"]
    return e, t001, t002


def test_038_form_e_untaps_after_battle_win(rules):
    e, t001, t002 = _form_e(rules, attack_player=False)
    assert e.s.cards[t002].zone == "graveyard"   # バトルに負けた側は破壊される
    assert e.s.cards[t001].tapped is False       # 勝ったのでアンタップした


def test_038_form_e_no_battle_no_untap(rules):
    e, t001, _ = _form_e(rules, attack_player=True)
    assert e.s.cards[t001].tapped is True        # バトルしていないのでタップしたまま
