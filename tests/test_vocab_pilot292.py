"""語彙パイロット第292弾（2026-11-20）の検証。

「破壊して払う代替コスト」（alternative_cost_destroy 純粋3件＋
optional_cost_reduction_with_sacrifice 純粋3件、計6件）。
支払いの形そのものは既存だった:
- alt_cost {do: [...]}（第29弾）: 行動だけで払い切る形。
- alt_cost {cost, civs, do} 混合形（第258弾）: 行動の後に別額を払う形。
- mod sac_reduce（ササゲール、第201弾）: 生贄にした自分の獣のぶん軽減。

ただし実挙動を測ると2点の欠落があったため、本弾で直した:
1. alt_cost の do ステップが step の owner を読んでおらず、共有ゾーンの
   bz では相手のカードまで候補に入った（提示判定・実行の両方）。
   → _alt_step_cands で owner（省略時 you）を honor するよう統一。
2. 混合形の提示判定が cost 側しか見ておらず、do 側が払えない時も
   :alt が提示され、選ぶと実行時に潰れた。
   → 提示判定は cost 側と do 側の両方を要求するよう修正。
3. sac_reduce はディスペクター専用だった（_sac_pool の種族ゲート）。
   dm22rp2x-015 の「自分のアビスを召喚する時…そうしたら、この
   クリーチャーを破壊する」はササゲールと同文型で対象だけが違う。
   → dict 形 {amount, for} を追加（for は召喚先の印刷特性に照合）。

形:
- 形A（dm22rp2x-038）: alt {cost: 印刷-4, do: [自分の獣/タマシード1枚を破壊]}
- 形B（dm23rp2x-004）: alt {cost: 印刷-3, do: [自分の獣2体を破壊]}
- 形C（dm24ex1-003）: alt {cost: 2, civs: [dd], do: [自分のデスパペット3つを破壊]}
- 形D（dm26rp3-011/sec015）: alt {cost: 5, civs: [ldn], do: [自分のエレメント2つを破壊（フィルタなし）]}
- 形E（dm22rp2x-015）: static {affects: self, mod: {sac_reduce: {amount: 2, for: {race_has: アビス}}}}
"""
import copy

import pytest
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()
PROTOS = ("T851", "T852", "T853", "T854", "T855", "T856",
          "T857", "T858", "T859", "T860")

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
                 "filter": {"race_has": "ドール"},
                 "count": 3, "to": "graveyard", "reason": "destroy"}]}
ALT_D = {"cost": 5, "civs": ["light", "darkness", "nature"],
         "do": [{"zone": "bz", "owner": "you",
                 "count": 2, "to": "graveyard", "reason": "destroy"}]}
SAC_E = {"kind": "static", "affects": "self",
         "mod": {"sac_reduce": {"amount": 2, "for": {"race_has": "アビス"}}}}


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_parse_protos():
    for cid in PROTOS:
        parse_card(_proto_card(cid), TABLES)
    assert parse_card(_proto_card("T851"), TABLES).alt_cost == ALT_A
    assert parse_card(_proto_card("T852"), TABLES).alt_cost == ALT_B
    assert parse_card(_proto_card("T853"), TABLES).alt_cost == ALT_C
    assert parse_card(_proto_card("T854"), TABLES).alt_cost == ALT_D
    assert SAC_E in parse_card(_proto_card("T857"), TABLES).abilities


def test_validation_rejects_bad_forms():
    bad = copy.deepcopy(_proto_card("T851"))
    bad["alt_cost"]["do"][0]["owner"] = "any"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = copy.deepcopy(_proto_card("T857"))
    bad["abilities"][0]["mod"]["sac_reduce"] = {"amount": 2}   # for が無い
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = copy.deepcopy(_proto_card("T857"))
    bad["abilities"][0]["mod"]["sac_reduce"] = {"amount": 2,
                                                "for": {"bogus_key": 1}}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


# ---------- 実挙動の共通部品 ----------

def _bz(e, p, defn):
    return [c for c in e.zlist("bz", p) if e.s.cards[c].defn == defn
            and e.s.cards[c].controller == p]


def _in_gy(e, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist("graveyard", p))


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


def _play_hook(key, st):
    def hook(e, d, keys):
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("played") and key in keys:
            st["played"] = True
            st["main_keys"] = list(keys)
            return [keys.index(key)]
        return None
    return hook


def _stop_at_opp_charge(st):
    def hook(e, d, keys):
        if st.get("played") and d["kind"] == "charge" and d.get("player") == 1:
            return "stop"
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


def _first_main_keys(e, limit=200):
    """P0 の最初のメインで提示されたキー一覧を返す（何もプレイしない）。"""
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "main" and d.get("player") == 0:
            return [o["key"] for o in d["options"]]
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("no main decision")


# ---------- 形A: dm22rp2x-038 ----------

def test_form_a_alt_destroys_own_and_pays_reduced(rules):
    """生贄は自分の獣だけ（相手の獣は候補に入らないため自動解決）、
    減額後の1マナだけを払って出る。"""
    e = setup(rules, {"hand": ["T851"], "mana": ["T008"] * 5, "bz": ["T001"]},
              {"bz": ["T034"]})
    st = {}
    _drive(e, _chain(_play_hook("play:T851:alt", st), _stop_at_opp_charge(st)))
    assert st.get("played")
    assert _bz(e, 0, "T851")
    assert _in_gy(e, 0, "T001")                    # 自分の生贄は破壊された
    assert _bz(e, 1, "T034")                       # 相手の獣は無傷
    assert not _in_gy(e, 1, "T034")
    assert _tapped_mana(e, 0) == 1                 # 5-4=1 だけ払った


def test_form_a_candidates_are_own_cards_only(rules):
    """候補が確定数より多い時も、提示されるのは自分の獣とタマシードだけ。
    タマシードも生贄に選べる。"""
    e = setup(rules, {"hand": ["T851"], "mana": ["T008"] * 5,
                      "bz": ["T001", "T855"]},
              {"bz": ["T034"]})
    st = {}

    def pick(e, d, keys):
        if d["kind"] == "choose_cards" and st.get("played") \
                and "cands" not in st:
            st["cands"] = [(e.s.cards[o["cid"]].defn,
                            e.s.cards[o["cid"]].controller)
                           for o in d["options"]]
            for i, o in enumerate(d["options"]):
                if e.s.cards[o["cid"]].defn == "T855":
                    return [i]
            return None
        return None

    _drive(e, _chain(_play_hook("play:T851:alt", st), pick,
                     _stop_at_opp_charge(st)))
    assert sorted(st["cands"]) == [("T001", 0), ("T855", 0)]   # 相手の T034 は無い
    assert _in_gy(e, 0, "T855")                    # タマシードを破壊した
    assert _bz(e, 0, "T001")                       # 獣は残った
    assert _bz(e, 0, "T851")


def test_form_a_not_offered_without_own_fodder(rules):
    """自分の生贄が無ければ、相手に獣がいても :alt は提示されない
    （修正前の提示判定・候補計算は相手の獣を数えていた）。"""
    e = setup(rules, {"hand": ["T851"], "mana": ["T008"] * 5},
              {"bz": ["T034", "T034"]})
    keys = _first_main_keys(e)
    assert "play:T851" in keys                     # 通常召喚は提示される
    assert "play:T851:alt" not in keys


def test_form_a_normal_play_keeps_fodder(rules):
    """通常召喚を選べば生贄は残り、全額を払う（代替は任意）。"""
    e = setup(rules, {"hand": ["T851"], "mana": ["T008"] * 5, "bz": ["T001"]},
              {"bz": ["T034"]})
    st = {}
    _drive(e, _chain(_play_hook("play:T851", st), _stop_at_opp_charge(st)))
    assert _bz(e, 0, "T851") and _bz(e, 0, "T001")
    assert _tapped_mana(e, 0) == 5


# ---------- 形B: dm23rp2x-004 ----------

def test_form_b_alt_destroys_two_and_pays_six(rules):
    e = setup(rules, {"hand": ["T852"], "mana": ["T008"] * 9,
                      "bz": ["T001", "T856"]},
              {"bz": ["T034"]})
    st = {}
    _drive(e, _chain(_play_hook("play:T852:alt", st), _stop_at_opp_charge(st)))
    assert _bz(e, 0, "T852")
    assert _in_gy(e, 0, "T001") and _in_gy(e, 0, "T856")
    assert _bz(e, 1, "T034")
    assert _tapped_mana(e, 0) == 6                 # 9-3=6


def test_form_b_not_offered_with_one_fodder(rules):
    """自分の獣が1体だけでは2体破壊を払えない。相手の獣は数えない。"""
    e = setup(rules, {"hand": ["T852"], "mana": ["T008"] * 9, "bz": ["T001"]},
              {"bz": ["T034", "T034"]})
    keys = _first_main_keys(e)
    assert "play:T852" in keys
    assert "play:T852:alt" not in keys


# ---------- 形C: dm24ex1-003 ----------

def test_form_c_alt_destroys_three_race_and_pays_dd(rules):
    """自分のドール3つだけが数えられ（相手のドールは数えない）、
    [dd02]＝闇2マナを払う。対象外の自分の獣は残る。"""
    e = setup(rules, {"hand": ["T853"], "mana": ["T008"] * 8,
                      "bz": ["T856", "T856", "T856", "T001"]},
              {"bz": ["T856"]})
    st = {}
    _drive(e, _chain(_play_hook("play:T853:alt", st), _stop_at_opp_charge(st)))
    assert _bz(e, 0, "T853")
    assert len([c for c in e.zlist("graveyard", 0)
                if e.s.cards[c].defn == "T856"]) == 3
    assert _bz(e, 0, "T001")                       # ドールでない獣は残る
    assert _bz(e, 1, "T856")                       # 相手のドールは残る
    assert _tapped_mana(e, 0) == 2


def test_form_c_not_offered_with_two_own_dolls(rules):
    e = setup(rules, {"hand": ["T853"], "mana": ["T008"] * 8,
                      "bz": ["T856", "T856"]},
              {"bz": ["T856", "T856"]})
    keys = _first_main_keys(e)
    assert "play:T853" in keys
    assert "play:T853:alt" not in keys


# ---------- 形D: dm26rp3-011 ----------

def test_form_d_alt_destroys_any_two_elements_and_pays_five(rules):
    """フィルタなし＝自分のエレメントなら獣でもタマシードでもよい。
    相手のエレメントは候補に入らない。[ldn05] を払い、本体（2ドロー）が解決する。"""
    e = setup(rules, {"hand": ["T854"],
                      "mana": ["T030", "T008", "T001", "T034", "T010"],
                      "bz": ["T001", "T855"]},
              {"bz": ["T034", "T010"]})
    st = {}
    _drive(e, _chain(_play_hook("play:T854:alt", st), _stop_at_opp_charge(st)))
    assert st.get("played")
    assert _in_gy(e, 0, "T001") and _in_gy(e, 0, "T855")
    assert _bz(e, 1, "T034") and _bz(e, 1, "T010")  # 相手のエレメントは無傷
    assert _tapped_mana(e, 0) == 5
    assert len(e.zlist("hand", 0)) == 2             # 本体の2ドロー
    assert _in_gy(e, 0, "T854")                     # 唱えた呪文は墓地へ


def test_form_d_not_offered_with_one_element(rules):
    e = setup(rules, {"hand": ["T854"],
                      "mana": ["T030", "T008", "T001", "T034", "T010"],
                      "bz": ["T001"]},
              {"bz": ["T034", "T010", "T034"]})
    keys = _first_main_keys(e)
    assert "play:T854:alt" not in keys


# ---------- 形E: dm22rp2x-015（sac_reduce dict 形） ----------

def _sac_hook(st, accept):
    """支払い中の生贄の諮問（choose_cards）に答える。accept は何回使うか。"""
    def hook(e, d, keys):
        if d["kind"] == "choose_cards" and st.get("played"):
            n = st.get("sac_asks", 0)
            st["sac_asks"] = n + 1
            st.setdefault("sac_cands", []).append(
                [e.s.cards[o["cid"]].defn for o in d["options"]])
            if n < accept:
                return [0]
            return []                                # 辞退（min 0）
        return None
    return hook


def test_form_e_sacrifice_reduces_matching_summon(rules):
    """アビス召喚時だけ生贄が提示され、使うと -2 され生贄は破壊される。"""
    e = setup(rules, {"hand": ["T858"], "mana": ["T008"] * 3, "bz": ["T857"]},
              {})
    st = {}
    _drive(e, _chain(_play_hook("play:T858", st), _sac_hook(st, accept=1),
                     _stop_at_opp_charge(st)))
    assert st.get("played") and st.get("sac_asks") == 1
    assert st["sac_cands"] == [["T857"]]
    assert _bz(e, 0, "T858")
    assert _in_gy(e, 0, "T857")                    # 生贄は破壊された
    assert _tapped_mana(e, 0) == 3                 # 5-2=3


def test_form_e_decline_pays_full_and_keeps_fodder(rules):
    e = setup(rules, {"hand": ["T858"], "mana": ["T008"] * 5, "bz": ["T857"]},
              {})
    st = {}
    _drive(e, _chain(_play_hook("play:T858", st), _sac_hook(st, accept=0),
                     _stop_at_opp_charge(st)))
    assert st.get("sac_asks") == 1
    assert _bz(e, 0, "T858") and _bz(e, 0, "T857")  # 生贄は残った
    assert _tapped_mana(e, 0) == 5                 # 全額


def test_form_e_gate_blocks_non_matching_summon(rules):
    """対象外（アビスでない）召喚では生贄は提示されず、軽減の見積もりも
    効かない（マナ3では出せない）。提示が何も無いメインは決定自体が
    立たないため、見積もりは _play_options を直接見る（第201弾の判別法）。"""
    e = setup(rules, {"hand": ["T859"], "mana": ["T034"] * 3, "bz": ["T857"]},
              {})
    keys = [o["key"] for o in e._play_options(0)]
    assert "play:T859" not in keys                 # 5-2 と見積もられない

    e = setup(rules, {"hand": ["T859"], "mana": ["T034"] * 5, "bz": ["T857"]},
              {})
    st = {}
    _drive(e, _chain(_play_hook("play:T859", st), _sac_hook(st, accept=1),
                     _stop_at_opp_charge(st)))
    assert st.get("played")
    assert st.get("sac_asks", 0) == 0              # 諮問自体が起きない
    assert _bz(e, 0, "T859") and _bz(e, 0, "T857")
    assert _tapped_mana(e, 0) == 5


def test_form_e_floor_zero_with_two_fodder(rules):
    """2体使うと 3-4 で床の0。マナが無くても召喚でき、両方とも破壊される。"""
    e = setup(rules, {"hand": ["T860"], "mana": [], "bz": ["T857", "T857"]},
              {})
    st = {}
    _drive(e, _chain(_play_hook("play:T860", st), _sac_hook(st, accept=2),
                     _stop_at_opp_charge(st)))
    assert st.get("played") and st.get("sac_asks") == 2
    assert _bz(e, 0, "T860")
    assert len([c for c in e.zlist("graveyard", 0)
                if e.s.cards[c].defn == "T857"]) == 2
    assert _tapped_mana(e, 0) == 0
