"""語彙パイロット第291弾のカード適用テスト（登録形）。

ラウンド326で ex_life_shield_tracking 純粋3件を新規登録:
- dm23bd1-005 頂竜連結 バジュエン・ザ・ローラ: partial は abilities を
  持たない。出た時（相手のパワー3000以下のクリーチャーをすべて破壊）＋
  形A（相手のターン中、EXライフシールドが離れた時、相手のマナゾーンの
  カードをすべてタップし、次の相手のターンのはじめにアンタップしない）
  を構築。alias dm23bd1-be003 は reject 行ではなく、登録時に畳まれた。
- dm23ex2-024 頂上連結 サックーヴ・ヴァッサークァ7th: partial は
  abilities を持たない。シンパシー（表向きシールドの枚数だけ軽減、
  下限0）、攻撃時（1枚引いてもよい。その後、裁きの紋章を手札から
  コストを支払わずに唱えてもよい）、形B（離れた時、相手の獣1体を
  タップ＋凍結）を構築。
- dmrp17-s06 紫天連結 ネバーシデンド: partial の「はじめてタップした時
  アンタップする」誘発は完全なため、形C（離れた時、そのターン離れない）
  を足しただけ（submit の連結意味論で重複なし）。
- converted 10,184 / rejects 2,146、重なり0・漏れ0。
  ex_life_shield_tracking は残り0件でファミリー解消。

プロトテスト（test_vocab_pilot291.py）とは別プロセスで実行すること
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


def setup(rules, p0, p1=None, filler="T002", seed=1, deck_size=20):
    """conftest の setup と同じ薄い包み。tests.conftest を import すると
    DMSIM_SKIP_CONVERTED が再設定されて converted が読めなくなるため、
    ここでは直接 scenario.build を包む（第286弾 cards と同じ）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGETS = ["dm23bd1-005", "dm23ex2-024", "dmrp17-s06"]

TRACK = {"event": "move", "from": "shield", "subject": {"exlife_of": "self"}}

FORM_A = {"kind": "trigger", "when": TRACK, "if": {"is_turn": "opp"},
          "effect": [{"op": "tap",
                      "select": {"zone": "mana", "owner": "opp", "count": "all"},
                      "no_untap_next": True}]}

FORM_B = {"kind": "trigger", "when": TRACK,
          "effect": [{"op": "tap",
                      "select": {"zone": "bz", "owner": "opp",
                                 "filter": {"types": ["creature"]}, "count": 1},
                      "no_untap_next": True}]}

FORM_C = {"kind": "trigger", "when": TRACK,
          "effect": [{"op": "modify", "select": {"ref": "self"},
                      "mod": {"no_leave": True}, "duration": "end_of_turn"}]}

CIP_005 = {"kind": "trigger",
           "when": {"event": "move", "to": "bz", "subject": "self"},
           "effect": [{"op": "destroy",
                       "select": {"zone": "bz", "owner": "opp",
                                  "filter": {"types": ["creature"],
                                             "power_le": 3000},
                                  "count": "all"}}]}

# parse では destroy マクロが move 形に展開される
CIP_005_PARSED = {"kind": "trigger",
                  "when": {"event": "move", "to": "bz", "subject": "self"},
                  "effect": [{"op": "move",
                              "select": {"zone": "bz", "owner": "opp",
                                         "filter": {"types": ["creature"],
                                                    "power_le": 3000},
                                         "count": "all"},
                              "to": "graveyard", "reason": "destroy"}]}

SYMPATHY_024 = {"kind": "static", "affects": "self", "zone": "hand",
                "mod": {"cost": {"amount": -1,
                                 "count": {"zone": "shield", "owner": "you",
                                           "filter": {"face_up": True}}},
                        "cost_min": 0}}

ATTACK_024 = {"kind": "trigger",
              "when": {"event": "attack", "subject": "self"},
              "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]},
                         {"op": "play_free",
                          "select": {"zone": "hand", "owner": "you",
                                     "filter": {"types": ["spell"],
                                                "race_has": "裁きの紋章"},
                                     "count": 1, "up_to": True}}]}

TAP_UNTAP_S06 = {"kind": "trigger", "first_time": True,
                 "when": {"event": "tap", "subject": "self"},
                 "effect": [{"op": "untap",
                             "select": {"ref": "self", "count": 1}}]}

TEXT_005 = ("EXライフ\nスピードアタッカー\nT・ブレイカー\n"
            "このクリーチャーが出た時、相手のパワー3000以下のクリーチャーを"
            "すべて破壊する。\n"
            "相手のターン中、このクリーチャーの「EXライフ」シールドが自分の"
            "シールドゾーンを離れた時、相手のマナゾーンのカードをすべて"
            "タップする。次の相手のターンのはじめに、それらのカードは"
            "アンタップしない。")

TEXT_024 = ("シンパシー：自分のシールドゾーンにある表向きのカード"
            "（自分のシールドゾーンにある表向きのカード１枚につき、この"
            "クリーチャーの召喚コストを１少なくする。ただしコストは０以下に"
            "ならない）\nEXライフ\nW・ブレイカー\n"
            "このクリーチャーが攻撃する時、カードを１枚引いてもよい。その後、"
            "裁きの紋章を１枚、自分の手札からコストを支払わずに唱えてもよい。\n"
            "このクリーチャーの「EXライフ」シールドが自分のシールドゾーンを"
            "離れた時、相手のクリーチャーを１体選び、タップする。次の相手の"
            "ターンのはじめに、そのクリーチャーはアンタップしない。")

TEXT_S06 = ("EXライフ（このクリーチャーを出す時、自分の山札の上から１枚目を"
            "シールド化する。このクリーチャーが離れる時、かわりにそのシールドを"
            "墓地に置く）\nブロッカー\nW・ブレイカー\n"
            "各ターン、このクリーチャーがはじめてタップした時、アンタップする。\n"
            "このクリーチャーの「EXライフ」シールドが自分のシールドゾーンを"
            "離れた時、そのターン、このクリーチャーはバトルゾーンを離れない。")


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
    # ファミリー解消: ex_life_shield_tracking を含む行は rejects に残らない
    assert not [r["id"] for r in rej.values()
                if "ex_life_shield_tracking" in (r.get("gaps") or [])]

    c = _converted("dm23bd1-005")
    assert c["abilities"] == [CIP_005, FORM_A]
    assert c["keywords"] == ["ex_life", "speed_attacker", "triple_breaker"]
    assert c["text"] == TEXT_005
    assert (c.get("source") or {}).get("aliases") == ["dm23bd1-be003"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert CIP_005_PARSED in d.abilities and FORM_A in d.abilities
    assert sorted(d.keywords) == ["ex_life", "speed_attacker", "triple_breaker"]

    c = _converted("dm23ex2-024")
    assert c["abilities"] == [SYMPATHY_024, ATTACK_024, FORM_B]
    assert c["keywords"] == ["ex_life", "double_breaker"]
    assert c["text"] == TEXT_024
    assert (c.get("source") or {}).get("aliases") is None
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert SYMPATHY_024 in d.abilities and ATTACK_024 in d.abilities \
        and FORM_B in d.abilities
    assert sorted(d.keywords) == ["double_breaker", "ex_life"]

    c = _converted("dmrp17-s06")
    # partial のタップ誘発＋形C（連結による重複なし）
    assert c["abilities"] == [TAP_UNTAP_S06, FORM_C]
    assert c["keywords"] == ["ex_life", "blocker", "double_breaker"]
    assert c["text"] == TEXT_S06
    assert (c.get("source") or {}).get("aliases") is None
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert TAP_UNTAP_S06 in d.abilities and FORM_C in d.abilities
    assert sorted(d.keywords) == ["blocker", "double_breaker", "ex_life"]


# ---------- 実挙動の共通部品（第291弾プロトと同じ型） ----------

def _exlife_shield(e, p):
    return next((c for c in e.zlist("shield", p)
                 if e.s.cards[c].exlife_of is not None), None)


def _bz(e, p, defn):
    return [c for c in e.zlist("bz", p) if e.s.cards[c].defn == defn
            and e.s.cards[c].controller == p]


def _in_gy(e, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist("graveyard", p))


def _mana_states(e, p):
    return [(e.s.cards[c].tapped, e.s.cards[c].no_untap_next)
            for c in e.zlist("mana", p)]


def _drive(e, hook, limit=900):
    """hook(e, d, keys) は答えのリスト / None（既定） / "stop" を返す。"""
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        ans = hook(e, d, keys)
        if ans == "stop":
            return
        if ans is not None:
            e.answer(ans)
            continue
        kind = d["kind"]
        if kind == "pay_mana":
            e.answer([0])
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("drive did not finish")


def _play_hook(tid, st):
    def hook(e, d, keys):
        if d["kind"] == "main" and not st.get("played") and f"play:{tid}" in keys:
            st["played"] = True
            return [keys.index(f"play:{tid}")]
        return None
    return hook


def _pick_shield_hook(st, which):
    def hook(e, d, keys):
        if d["kind"] == "choose_shields" and not st.get("broke"):
            ex = _exlife_shield(e, 0)
            for i, o in enumerate(d["options"]):
                if (o.get("cid") == ex) == (which == "ex"):
                    st["broke"] = True
                    st["broken_cid"] = o["cid"]
                    return [i]
            return None
        return None
    return hook


def _chain(*hooks):
    def hook(e, d, keys):
        for h in hooks:
            ans = h(e, d, keys)
            if ans is not None:
                return ans
        return None
    return hook


MANA_005 = ["T030", "T008"] + ["T034"] * 5   # 光/闇/火を満たす7枚（コスト7）
MANA_S06 = ["T030"] + ["T034"] * 6           # 光/火を満たす7枚（コスト7）


# ---------- dm23bd1-005: 出た時 ----------

def test_005_cip_destroys_power_3000_or_less_only(rules):
    """出た時: 相手のパワー3000以下はすべて破壊、4000は残る。"""
    e = setup(rules, {"hand": ["dm23bd1-005"], "mana": MANA_005},
              {"bz": ["T001", "T004", "T010"]})
    st = {}

    def hook(e, d, keys):
        a = _play_hook("dm23bd1-005", st)(e, d, keys)
        if a is not None:
            return a
        if st.get("played") and d["kind"] == "charge" and d["player"] == 1:
            return "stop"
        return None

    _drive(e, hook)
    assert st.get("played")
    assert _bz(e, 0, "dm23bd1-005")
    assert _in_gy(e, 1, "T001") and _in_gy(e, 1, "T004")   # 2000と3000は破壊
    assert _bz(e, 1, "T010")                               # 4000は残る
    assert not _bz(e, 1, "T001") and not _bz(e, 1, "T004")


# ---------- dm23bd1-005: 形A ----------

def test_005_form_a_break_freezes_all_opponent_mana(rules):
    """相手のターンに EXライフシールドが割れる → 相手のマナすべてが
    タップ＋凍結。次の相手のターンのはじめにアンタップせず（印は消費）、
    さらに次の相手のターンのはじめに通常通りアンタップする。
    攻撃役の T010（パワー4000）は出た時の破壊を生き残る。"""
    e = setup(rules, {"hand": ["dm23bd1-005"], "mana": MANA_005},
              {"bz": ["T010"], "mana": ["T010"] * 4, "hand": ["T001"]})
    st = {"snaps": []}

    def hook(e, d, keys):
        a = _play_hook("dm23bd1-005", st)(e, d, keys)
        if a is not None:
            return a
        a = _pick_shield_hook(st, "ex")(e, d, keys)
        if a is not None:
            return a
        if d["kind"] == "attack" and d["player"] == 1 \
                and not st.get("attacked"):
            if "attack:T010:player" in keys:
                st["attacked"] = True
                return [keys.index("attack:T010:player")]
            return None
        if st.get("broke") and "just_after" not in st:
            st["just_after"] = _mana_states(e, 1)
        if st.get("broke") and d["kind"] == "charge" and d["player"] == 1:
            st["snaps"].append(_mana_states(e, 1))
            if len(st["snaps"]) >= 2:
                return "stop"
        return None

    _drive(e, hook)
    assert st.get("attacked") and st.get("broke")
    assert st["just_after"] == [(True, True)] * 4     # 全マナがタップ＋凍結
    assert st["snaps"][0] == [(True, False)] * 4      # 次の相手ターン開始: 凍結で起きない
    assert st["snaps"][1] == [(False, False)] * 4     # さらに次は通常通りアンタップ


# ---------- dm23ex2-024: 形B ----------

def test_024_form_b_destroy_replacement_taps_and_freezes(rules):
    """相手の破壊呪文 → EXライフ置換でシールドが墓地へ → 相手の獣1体を
    タップ＋凍結。凍結した獣は次の相手のターンのはじめにアンタップしない。"""
    e = setup(rules, {"hand": ["dm23ex2-024"], "mana": ["T030"] * 7},
              {"bz": ["T001", "T001"], "hand": ["T056"], "mana": ["T082"] * 3})
    st = {}

    def hook(e, d, keys):
        a = _play_hook("dm23ex2-024", st)(e, d, keys)
        if a is not None:
            return a
        if d["kind"] == "main" and d["player"] == 1 and st.get("played") \
                and not st.get("cast") and "play:T056" in keys:
            st["cast"] = True
            return [keys.index("play:T056")]
        if d["kind"] == "choose_cards" and st.get("cast") \
                and not st.get("tap_pick"):
            for i, o in enumerate(d["options"]):
                if e.cdef(o["cid"]).id == "T001":
                    st["tap_pick"] = o["cid"]
                    return [i]
            return None
        if st.get("tap_pick") and "just_after" not in st:
            c = e.s.cards[st["tap_pick"]]
            st["just_after"] = (c.tapped, c.no_untap_next)
        if st.get("tap_pick") and d["kind"] == "charge" and d["player"] == 1:
            c = e.s.cards[st["tap_pick"]]
            st["next_start"] = (c.tapped, c.no_untap_next)
            return "stop"
        return None

    _drive(e, hook)
    assert st.get("cast") and st.get("tap_pick")
    assert _bz(e, 0, "dm23ex2-024")                   # 置換で場に残った
    assert len(e.zlist("graveyard", 0)) == 1          # シールドが墓地へ
    assert st["just_after"] == (True, True)           # タップ＋凍結
    assert st["next_start"] == (True, False)          # 次の相手ターン開始でもタップしたまま
    others = [c for c in _bz(e, 1, "T001") if c != st["tap_pick"]]
    assert len(others) == 1
    assert e.s.cards[others[0]].tapped is False       # もう1体は無傷


# ---------- dmrp17-s06: 形C ----------

def test_s06_form_c_replacement_grants_no_leave(rules):
    """破壊 → EXライフ置換で残り、離れたシールドの誘発で no_leave が付く。
    同じターンの2度目の破壊は、置換ではなく no_leave が止める。"""
    e = setup(rules, {"hand": ["dmrp17-s06"], "mana": MANA_S06},
              {"bz": ["T001"], "hand": ["T056", "T056"], "mana": ["T082"] * 6})
    st = {"casts": 0}

    def hook(e, d, keys):
        a = _play_hook("dmrp17-s06", st)(e, d, keys)
        if a is not None:
            return a
        if d["kind"] == "main" and d["player"] == 1 and st.get("played") \
                and st["casts"] < 2 and "play:T056" in keys:
            if st["casts"] == 1 and "no_leave_mid" not in st:
                cid = _bz(e, 0, "dmrp17-s06")[0]
                st["no_leave_mid"] = bool(e.chars(cid)["no_leave"])
            st["casts"] += 1
            return [keys.index("play:T056")]
        if st["casts"] >= 2:
            st["seen"] = st.get("seen", 0) + 1
            if st["seen"] >= 3:
                return "stop"
        return None

    _drive(e, hook)
    assert st["casts"] == 2
    assert st["no_leave_mid"] is True                 # 1度目の解決後に no_leave が立っている
    assert _bz(e, 0, "dmrp17-s06")                    # 2度目の破壊も通らなかった
    assert len(e.zlist("graveyard", 0)) == 1          # 墓地はシールド1枚だけ
    assert len([c for c in e.zlist("graveyard", 1)
                if e.s.cards[c].defn == "T056"]) == 2
