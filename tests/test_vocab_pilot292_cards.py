"""語彙パイロット第292弾のカード適用テスト（登録形）。

ラウンド327で「破壊して払う」支払いクラスタ純粋6件を処理:
- 新規登録5件: dm22rp2x-038 ソー＝ゾー（形A）/ dm23rp2x-004
  ラーテ:ガ:フヨーキ（形B）/ dm22rp2x-015 セリヴィエット＝エリー
  （CIP＋形E）/ dm24ex1-003 ジェニー&ガ:ナテハ（形C）/
  dm26rp3-011 黎悪銃と邪煉哀の決断（形D＋モーダル本体）。
- alias 畳み込み1件: dm26rp3-sec015（011 のシークレット印刷、同一本文。
  canon は 011 のため提出は 011 のみ。validate が aliases_for で自動付与）。
- converted 10,189 / rejects 2,140、重なり0・漏れ0。
  alternative_cost_destroy / optional_cost_reduction_with_sacrifice は
  残り0件で両ファミリー解消。

ラウンド側の修正2点（提出前の実挙動プローブで検出）:
- dm24ex1-003: submit の merge_split が本文由来の CIP（見ないで選び =
  chooser: random）を別途差し込み、partial 由来（chooser 無し）と
  非同一 dict のため重複排除されず2重登録された。本文に合う
  chooser: random 形だけを残し、もう一方を converted.yaml から除去した。
- dm26rp3-011 モード3「エレメントを２つまで選び、破壊する」: 無資格の
  選択は両プレイヤーのエレメントが対象（dm23-031 等の先例で owner: any）。
  第292弾の提出形は owner 省略（= you のみ）だったため owner: any に修正。
  あわせてモード2の辞退時（up_to で0体 → entered 空束縛で delayed_trigger
  がターン終わりに発火）の実挙動も本ファイルで固定した。

プロトテスト（test_vocab_pilot292.py）とは別プロセスで実行すること
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
    ここでは直接 scenario.build を包む（第291弾 cards と同じ）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGETS = ["dm22rp2x-038", "dm23rp2x-004", "dm22rp2x-015",
           "dm24ex1-003", "dm26rp3-011"]

ALT_A = {"cost": 1,
         "do": [{"zone": "bz", "owner": "you",
                 "filter": {"types": ["creature", "tamaseed"]},
                 "count": 1, "to": "graveyard", "reason": "destroy"}]}
ALT_B = {"cost": 6,
         "do": [{"zone": "bz", "owner": "you",
                 "filter": {"types": ["creature"]},
                 "count": 2, "to": "graveyard", "reason": "destroy"}]}
ALT_C = {"cost": 2, "civs": ["darkness", "darkness"],
         "do": [{"zone": "bz", "owner": "you",
                 "filter": {"race_has": "デスパペット"},
                 "count": 3, "to": "graveyard", "reason": "destroy"}]}
ALT_D = {"cost": 5, "civs": ["light", "darkness", "nature"],
         "do": [{"zone": "bz", "owner": "you",
                 "count": 2, "to": "graveyard", "reason": "destroy"}]}

OFFICIAL_011 = (
    "自分のエレメントを２つ破壊し、[ldn05]支払ってこの呪文を唱えてもよい。\n"
    "次の中から２回選ぶ。同じものを選んでもよい。\n"
    "▶自分の山札の上から３枚を見る。その中から１枚を手札に加え、残りをタップしてマナゾーンに置く。\n"
    "▶コスト９以下の、進化ではないクリーチャーを１体、自分の手札から出す。このターンの終わりに、それを破壊する。\n"
    "▶エレメントを２つまで選び、破壊する。")

# 登録形のモーダル（モード3は owner: any に修正済み）
MODAL_011 = {"op": "modal", "count": 2, "repeat": True, "modes": [
    [{"op": "choose",
      "select": {"zone": "deck", "owner": "you", "from_top": 3,
                 "look": True, "count": "all"},
      "as": "pile"},
     {"op": "move", "select": {"ref": "pile", "count": 1},
      "to": "hand", "reason": "draw"},
     {"op": "move", "select": {"ref": "pile", "count": "all"},
      "to": "mana", "reason": "charge", "tapped": True}],
    [{"op": "play_free",
      "select": {"zone": "hand", "owner": "you",
                 "filter": {"types": ["creature"], "evolution": False,
                            "cost_le": 9},
                 "count": 1, "up_to": True},
      "as": "entered"},
     {"op": "delayed_trigger", "when": {"event": "turn_end"},
      "effect": [{"op": "destroy", "select": {"ref": "entered"}}]}],
    [{"op": "destroy",
      "select": {"zone": "bz", "owner": "any", "count": 2, "up_to": True}}],
]}

CIP_015 = {"kind": "trigger",
           "when": {"event": "move", "to": "bz", "subject": "self"},
           "effect": [{"op": "may", "body": [
               {"op": "discard",
                "select": {"zone": "hand", "owner": "you", "count": 1}},
               {"op": "discard",
                "select": {"zone": "hand", "owner": "opp",
                           "chooser": "opp", "count": 1}}]}]}
SAC_015 = {"kind": "static", "affects": "self",
           "mod": {"sac_reduce": {"amount": 2, "for": {"race_has": "アビス"}}}}

MEK_004 = {"kind": "trigger",
           "when": {"event": "summon", "subject": "self"},
           "effect": [{"op": "mekurade", "filter": {"race_has": "アビス"},
                       "cost_le": 8},
                      {"op": "mekurade", "filter": {"race_has": "アビス"},
                       "cost_le": 8}]}
SLAYER_004 = {"kind": "static",
              "affects": {"owner": "you", "zone": "bz",
                          "filter": {"types": ["creature"],
                                     "race_has": "アビス"}},
              "mod": {"grant": ["slayer"]}}

# 登録形の CIP は「見ないで選び」= chooser: random 形（submit の split 由来）。
# partial 由来の chooser 無し形は重複として除去済み。
CIP_003 = {"kind": "trigger",
           "when": {"event": "move", "to": "bz", "subject": "self"},
           "effect": [{"op": "discard",
                       "select": {"zone": "hand", "owner": "opp", "count": 2,
                                  "chooser": "random"}}]}
MEK_003 = {"kind": "trigger", "once_per_turn": True,
           "when": {"event": "move", "from": "hand", "to": "graveyard",
                    "reason": "discard", "subject": {"owner": "opp"}},
           "effect": [{"op": "mekurade",
                       "filter": {"race_has": "デスパペット"}, "cost_le": 5}]}

TEXT_038 = ("このクリーチャーを召喚する時、自分の、クリーチャー１体または"
            "タマシードを１枚、破壊してもよい。そうしたら、このクリーチャーの"
            "召喚コストを４少なくする。\n"
            "ブロッカー（このクリーチャーをタップして、相手クリーチャーの"
            "攻撃先をこのクリーチャーに変更してもよい）\n"
            "W・ブレイカー（このクリーチャーはシールドを２つブレイクする）")
TEXT_004 = ("このクリーチャーを召喚する時、自分のクリーチャーを２体破壊して"
            "もよい。そうしたら、このクリーチャーの召喚コストを３少なくする。\n"
            "W・ブレイカー\n"
            "このクリーチャーが召喚によって出た時、アビス・W・メクレイド８する。"
            "（アビス・W・メクレイド８：自分の山札の上から６枚を見る。その中から、"
            "コスト８以下のアビスを２枚まで、コストを支払わずに使う。残りを"
            "好きな順序で山札の下に置く）\n"
            "自分のアビス・クリーチャーすべてに「スレイヤー」を与える。")
TEXT_015 = ("このクリーチャーが出た時、自分の手札を１枚捨ててもよい。"
            "そうしたら、相手は自身の手札を１枚選んで捨てる。"
            "自分のアビスを召喚する時、コストを２少なくしてもよい。"
            "そうしたら、このクリーチャーを破壊する。ただし、そのアビスの"
            "コストは０以下にはならない。")
TEXT_003 = ("このクリーチャーを召喚する時、自分のデスパペットを３つ破壊して"
            "もよい。そうしたら、このクリーチャーの召喚コストを[dd02]にする。\n"
            "W・ブレイカー\n"
            "このクリーチャーが出た時、相手の手札を２枚見ないで選び、捨てさせる。\n"
            "各ターンに一度、相手が手札を捨てた時、デスパペット・メクレイド５する。")


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
    for cid in TARGETS + ["dm26rp3-sec015"]:
        assert cid not in rej, cid
    # 両ファミリー解消: 対象ギャップを含む行は rejects に残らない
    assert not [r["id"] for r in rej.values()
                if {"alternative_cost_destroy",
                    "optional_cost_reduction_with_sacrifice"}
                & set(r.get("gaps") or [])]

    c = _converted("dm22rp2x-038")
    assert c.get("abilities") in (None, [])
    assert c["keywords"] == ["blocker", "double_breaker"]
    assert c["alt_cost"] == ALT_A
    assert c["text"] == TEXT_038
    assert (c.get("source") or {}).get("aliases") == [
        "dm22rp2-038", "dm22rp2-15a", "dm22rp2x-15a"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.alt_cost == ALT_A
    assert sorted(d.keywords) == ["blocker", "double_breaker"]

    c = _converted("dm23rp2x-004")
    assert c["abilities"] == [MEK_004, SLAYER_004]
    assert c["keywords"] == ["double_breaker"]
    assert c["alt_cost"] == ALT_B
    assert c["text"] == TEXT_004
    assert (c.get("source") or {}).get("aliases") == [
        "dm23rp2-004", "dm23rp2x-04x"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.alt_cost == ALT_B and MEK_004 in d.abilities

    c = _converted("dm22rp2x-015")
    assert c["abilities"] == [CIP_015, SAC_015]
    assert c.get("keywords") in (None, [])
    assert c["text"] == TEXT_015
    assert (c.get("source") or {}).get("aliases") == [
        "dm22rp2-015", "dm22rp2-13a", "dm22rp2x-13a"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert SAC_015 in d.abilities

    c = _converted("dm24ex1-003")
    # CIP は chooser: random 形が1つだけ（二重登録の回帰防止）
    assert c["abilities"] == [CIP_003, MEK_003]
    assert c["keywords"] == ["double_breaker"]
    assert c["alt_cost"] == ALT_C
    assert c["text"] == TEXT_003
    assert (c.get("source") or {}).get("aliases") is None
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.alt_cost == ALT_C
    triggers = [a for a in d.abilities if a["kind"] == "trigger"]
    assert len(triggers) == 2          # CIP（random）＋メクレイド誘発だけ
    assert triggers[0]["effect"][0]["select"].get("chooser") == "random"

    c = _converted("dm26rp3-011")
    assert c.get("abilities") in (None, [])
    assert c["alt_cost"] == ALT_D
    assert c["spell"] == [MODAL_011]
    assert c["text"] == OFFICIAL_011
    assert (c.get("source") or {}).get("aliases") == ["dm26rp3-sec015"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.alt_cost == ALT_D
    assert d.spell[0]["op"] == "modal" and len(d.spell[0]["modes"]) == 3
    # sec015 は独立 id では登録されず、011 の alias としてのみ存在する
    assert _conv_cache.find(CONVERTED, "dm26rp3-sec015") is None


# ---------- 実挙動の共通部品（第292弾プロトと同じ型） ----------

def _bz(e, p, defn):
    return [c for c in e.zlist("bz", p) if e.s.cards[c].defn == defn
            and e.s.cards[c].controller == p]


def _in_gy(e, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist("graveyard", p))


def _in_hand(e, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist("hand", p))


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


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


def _chain(*hooks):
    def hook(e, d, keys):
        for h in hooks:
            ans = h(e, d, keys)
            if ans is not None:
                return ans
        return None
    return hook


def _play_hook(key, st):
    def hook(e, d, keys):
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("played") and key in keys:
            st["played"] = True
            return [keys.index(key)]
        return None
    return hook


def _stop_at_opp_charge(st):
    def hook(e, d, keys):
        if st.get("played") and d["kind"] == "charge" and d.get("player") == 1:
            return "stop"
        return None
    return hook


def _mode_hook(modes):
    st = {"modes": list(modes)}

    def hook(e, d, keys):
        if d["kind"] == "choose_mode" and st["modes"]:
            return [keys.index(f"mode:{st['modes'].pop(0)}")]
        return None
    return hook


MANA9_LDN = ["T030", "T008"] + ["T001"] * 7   # 光/闇/自然を満たす9枚


# ---------- dm22rp2x-038: 形A ----------

def test_038_alt_pays_one_and_destroys_own_only(rules):
    e = setup(rules, {"hand": ["dm22rp2x-038"], "mana": ["T008"] * 5,
                      "bz": ["T001"]},
              {"bz": ["T034"]})
    st = {}
    _drive(e, _chain(_play_hook("play:dm22rp2x-038:alt", st),
                     _stop_at_opp_charge(st)))
    assert st.get("played")
    assert _bz(e, 0, "dm22rp2x-038")
    assert _in_gy(e, 0, "T001")                    # 自分の生贄は破壊
    assert _bz(e, 1, "T034")                       # 相手の獣は無傷
    assert _tapped_mana(e, 0) == 1                 # 5-4=1


# ---------- dm23rp2x-004: 形B ----------

def test_004_alt_pays_six_and_destroys_two(rules):
    e = setup(rules, {"hand": ["dm23rp2x-004"], "mana": ["T008"] * 9,
                      "bz": ["T001", "T001"]})
    st = {}
    _drive(e, _chain(_play_hook("play:dm23rp2x-004:alt", st),
                     _stop_at_opp_charge(st)))
    assert st.get("played")
    assert _bz(e, 0, "dm23rp2x-004")
    assert len([c for c in e.zlist("graveyard", 0)
                if e.s.cards[c].defn == "T001"]) == 2
    assert _tapped_mana(e, 0) == 6                 # 9-3=6


# ---------- dm22rp2x-015: CIP と形E ----------

def test_015_cip_may_discard_then_opponent_discards_own_choice(rules):
    e = setup(rules, {"hand": ["dm22rp2x-015", "T002"], "mana": ["T008"] * 3},
              {"hand": ["T001", "T034"]})
    st = {}

    def opp_choice(e, d, keys):
        # 相手の捨て札は相手自身の決定（chooser: opp）として提示される
        if d["kind"] == "choose_cards" and d.get("player") == 1:
            st["opp_chose"] = True
        return None

    _drive(e, _chain(_play_hook("play:dm22rp2x-015", st), opp_choice,
                     _stop_at_opp_charge(st)))
    assert st.get("played") and st.get("opp_chose")
    assert _bz(e, 0, "dm22rp2x-015")
    assert _in_gy(e, 0, "T002")                    # 自分の捨て札（may を受けた）
    assert len(e.zlist("graveyard", 1)) == 1       # 相手は自身で選んで1枚捨てた
    # 手札は 2 - 1（捨て札）+ 1（相手ターン開始時のドロー）= 2
    assert len(e.zlist("hand", 1)) == 2


def test_015_sac_reduce_for_abyss_summon(rules):
    """自分のアビス（T858）を召喚する時、015 を生贄に -2（第292弾形E）。"""
    e = setup(rules, {"hand": ["T858"], "mana": ["T008"] * 3,
                      "bz": ["dm22rp2x-015"]})
    st = {}

    def sac(e, d, keys):
        if d["kind"] == "choose_cards" and st.get("played") \
                and not st.get("sac"):
            st["sac"] = [e.s.cards[o["cid"]].defn for o in d["options"]]
            return [0]
        return None

    _drive(e, _chain(_play_hook("play:T858", st), sac,
                     _stop_at_opp_charge(st)))
    assert st.get("played") and st.get("sac") == ["dm22rp2x-015"]
    assert _bz(e, 0, "T858")
    assert _in_gy(e, 0, "dm22rp2x-015")            # 生贄は破壊された
    assert _tapped_mana(e, 0) == 3                 # 5-2=3


# ---------- dm24ex1-003: CIP は1回だけ＋形C ----------

def test_003_cip_fires_once_random_two(rules):
    """CIP が二重登録されていないこと: 相手の手札は 4→2（4→0 にならない）。"""
    e = setup(rules, {"hand": ["dm24ex1-003"], "mana": ["T008"] * 8},
              {"hand": ["T001", "T002", "T034", "T010"]})
    st = {}
    _drive(e, _chain(_play_hook("play:dm24ex1-003", st),
                     _stop_at_opp_charge(st)))
    assert st.get("played")
    assert _bz(e, 0, "dm24ex1-003")
    # 捨てさせたのは2枚だけ（二重なら墓地が4枚になる）
    assert len(e.zlist("graveyard", 1)) == 2
    # 手札は 4 - 2（捨て札）+ 1（相手ターン開始時のドロー）= 3
    assert len(e.zlist("hand", 1)) == 3


def test_003_alt_destroys_three_despuppets_pays_dd02(rules):
    e = setup(rules, {"hand": ["dm24ex1-003"], "mana": ["T008"] * 2,
                      "bz": ["T687", "T687", "T687"]})
    st = {}
    _drive(e, _chain(_play_hook("play:dm24ex1-003:alt", st),
                     _stop_at_opp_charge(st)))
    assert st.get("played")
    assert _bz(e, 0, "dm24ex1-003")
    assert len([c for c in e.zlist("graveyard", 0)
                if e.s.cards[c].defn == "T687"]) == 3
    assert _tapped_mana(e, 0) == 2                 # [dd02]


# ---------- dm26rp3-011: モーダル本体 ----------

def test_011_mode2_declined_twice_is_safe(rules):
    """モード2を2回とも0体で辞退: entered 空束縛の delayed_trigger が
    ターン終わりに発火しても潰れず、何も破壊されない（ラウンド必須検証）。"""
    e = setup(rules, {"hand": ["dm26rp3-011", "T001"], "mana": MANA9_LDN})
    st = {}
    _drive(e, _chain(_play_hook("play:dm26rp3-011", st), _mode_hook([1, 1]),
                     _stop_at_opp_charge(st)))
    assert st.get("played")
    assert _in_gy(e, 0, "dm26rp3-011")
    assert _in_hand(e, 0, "T001")                  # 出さなかったので手札に残る
    assert not _bz(e, 0, "T001") and not _in_gy(e, 0, "T001")


def test_011_mode2_summoned_creature_destroyed_at_turn_end(rules):
    e = setup(rules, {"hand": ["dm26rp3-011", "T001"], "mana": MANA9_LDN})
    st = {}

    def pick(e, d, keys):
        if d["kind"] == "choose_cards" and st.get("played") \
                and not st.get("picked"):
            for i, o in enumerate(d["options"]):
                if e.s.cards[o["cid"]].defn == "T001" \
                        and e.s.cards[o["cid"]].zone == "hand":
                    st["picked"] = True
                    return [i]
        return None

    _drive(e, _chain(_play_hook("play:dm26rp3-011", st), _mode_hook([1, 2]),
                     pick, _stop_at_opp_charge(st)))
    assert st.get("picked")
    assert _in_gy(e, 0, "T001")                    # ターン終わりに破壊された
    assert not _bz(e, 0, "T001")


def test_011_mode3_destroys_any_elements(rules):
    """モード3は無資格 = 相手のエレメントも選べる（owner: any の回帰）。"""
    e = setup(rules, {"hand": ["dm26rp3-011"], "mana": MANA9_LDN,
                      "bz": ["T001"]},
              {"bz": ["T034"]})
    st = {}

    def pick_both(e, d, keys):
        if d["kind"] == "choose_cards" and st.get("played") \
                and not st.get("picked"):
            idx = [i for i, o in enumerate(d["options"])
                   if e.s.cards[o["cid"]].defn in ("T034", "T001")]
            if len(idx) == 2:
                st["picked"] = True
                return idx
        return None

    _drive(e, _chain(_play_hook("play:dm26rp3-011", st), _mode_hook([2, 2]),
                     pick_both, _stop_at_opp_charge(st)))
    assert st.get("picked")
    assert _in_gy(e, 1, "T034") and _in_gy(e, 0, "T001")
    assert _in_gy(e, 0, "dm26rp3-011")


def test_011_alt_cast_destroys_two_elements_pays_five(rules):
    e = setup(rules, {"hand": ["dm26rp3-011"],
                      "mana": ["T030", "T008", "T001", "T001", "T001"],
                      "bz": ["T001", "T034"]})
    st = {}
    _drive(e, _chain(_play_hook("play:dm26rp3-011:alt", st),
                     _mode_hook([2, 2]), _stop_at_opp_charge(st)))
    assert st.get("played")
    assert _in_gy(e, 0, "dm26rp3-011")
    assert _in_gy(e, 0, "T001") and _in_gy(e, 0, "T034")
    assert _tapped_mana(e, 0) == 5                 # [ldn05]
