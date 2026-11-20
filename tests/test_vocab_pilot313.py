"""語彙パイロット第313弾: cost_le_count（「マナの枚数よりコストが小さい」）。

対象は dm26rp3-std010 BARUGA-雷座87 の3刷（std010 /
stdchosec010 / stdsec010、いずれも gaps は空で partial の
unsupported にだけ cost_le_count が残る監査行）。残りの条項
（NEO進化・W・ブレイカー・出た時に山札上2枚をタップして
マナへ）は partial に完成済みで、不足はメテオバーンの
「自分のマナゾーンにあるカードの枚数よりコストが小さい
クリーチャーを1体、自分のマナゾーンから出す」だけだった。

結論: **ドリフト**（新規語彙・エンジン変更なし）。

- 「Xの枚数よりコストが小さい」は第117弾 cost_lt_count の
  確立形 cost_le: {sum: [{count: {zone: mana, owner: you}},
  -1]}（「より小さい」= 枚数-1 以下）。マナ枚数で数える形も
  登録済み先例がある（dm26ex3-082 蒼龍の大地。選択時点＝
  出す前のマナ枚数で数える読みも同先例で固定済み）。
- 攻撃時メテオバーンの「置いてもよい。そうしたら」は
  dm19-007 の確立イディオム: may [move {under_of: self,
  count: 1} → graveyard, as: paid ＋ if {exists: {ref: paid}}
  → 続き]。
- マナから出すは dm26ex3-082 と同じ move {zone: mana} →
  bz, reason: put（play_free はマナ源の先例なし）。

プロト T964（std010 型）。確立形は
tests/test_vocab_pilot313_cards.py の FORM が正本。
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()
ME = "T964"


def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]


def _cids(e, zone, p=0):
    return [c for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]


def _cid(e, zone, defn, p=0):
    return next(c for c in _cids(e, zone, p) if e.s.cards[c].defn == defn)


def _run(e, handler, limit=600, done=None):
    for _ in range(limit):
        if e.s.result is not None or (done and done()):
            return
        d = e.advance()
        if d is None:
            return
        r = handler(e, d)
        if r is not None:
            e.answer(r)
            continue
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))


def _driver(evolve=True, accept=True, pick_defn="T001"):
    """T964 を出し（任意で NEO 進化）、次の自分のターンに攻撃する。
    state: played / attacked / putout_options（マナからの選択肢 cid 列）。"""
    st = {"played": False, "attacked": False, "putout_options": None,
          "opp_main": False}

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        p = d["player"]
        if d["kind"] == "main" and p == 1 and st["attacked"]:
            st["opp_main"] = True     # 攻撃が解決し切って相手のターンへ
        if d["kind"] == "main" and p == 0 and not st["played"]:
            key = f"play:{ME}:neo" if evolve else f"play:{ME}"
            if key in keys:
                st["played"] = True
                return [keys.index(key)]
        if d["kind"] == "choose_evo_source":
            for i, o in enumerate(d["options"]):
                if e.s.cards[o["cid"]].defn == "T001":
                    return [i]
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [keys.index("yes")] if accept else [keys.index("no")]
        if d["kind"] == "choose_cards" and any(
                k.startswith("mana:") for k in keys):
            st["putout_options"] = [o["cid"] for o in d["options"]]
            for i, o in enumerate(d["options"]):
                if e.s.cards[o["cid"]].defn == pick_defn:
                    return [i]
            return [0]
        if d["kind"] in ("attack", "declare_attack") and p == 0 \
                and not st["attacked"]:
            ak = f"attack:{ME}:player"
            if ak in keys:
                st["attacked"] = True
                return [keys.index(ak)]
        if d["kind"] in ("block", "declare_block") and "no_block" in keys:
            return [keys.index("no_block")]
        return None

    return handler, st


def _fixture(mana, deck):
    return setup(load_rules(),
                 {"bz": ["T001"], "hand": [ME], "mana": mana, "deck": deck},
                 {})


# ---- parse ----

def test_proto_parse():
    d = parse_card(proto_card(ME), TABLES)
    assert d.neo and d.evolve_from == {"civs": ["light", "fire", "nature"],
                                       "types": ["creature"]}
    assert "double_breaker" in d.keywords
    trigs = [a for a in d.abilities if a["kind"] == "trigger"]
    assert len(trigs) == 2


# ---- 出た時: 山札の上から2枚をタップしてマナへ ----

def test_cip_top2_to_mana_tapped():
    e = _fixture(["T001"] * 5, ["T002"] * 4 + ["T001", "T001"])
    handler, st = _driver()
    _run(e, handler,
         done=lambda: ME in _defns(e, "bz") and len(_cids(e, "mana")) == 7)
    assert st["played"]
    mana = _cids(e, "mana")
    assert len(mana) == 7                      # 5（支払い分）+ 2（CIP）
    added = [c for c in mana if e.s.cards[c].defn == "T002"]
    assert len(added) == 2                     # 山札の上から2枚
    assert all(e.s.cards[c].tapped for c in added)


# ---- メテオバーン: 燃やして、マナ枚数より小さいコストを出す ----

def test_meteor_burn_puts_out_cost_below_mana_count():
    e = _fixture(["T142", "T095", "T001", "T001", "T001"],
                 ["T002"] * 4 + ["T001", "T001"])
    base = _cid(e, "bz", "T001")
    big7 = _cid(e, "mana", "T142")             # コスト7
    big9 = _cid(e, "mana", "T095")             # コスト9
    handler, st = _driver()
    _run(e, handler,
         done=lambda: len([c for c in _cids(e, "bz")
                           if e.s.cards[c].defn == "T001"]) >= 1
         and st["putout_options"] is not None)
    assert st["attacked"]
    # マナは7枚（5+ CIP 2）→ コスト7以上は候補に出ない
    assert st["putout_options"] is not None
    assert big7 not in st["putout_options"]
    assert big9 not in st["putout_options"]
    # 候補はコスト2の T001 / T002 だけ（コスト7・9は枚数7未満でない）
    assert {e.s.cards[c].defn for c in st["putout_options"]} <= {"T001", "T002"}
    # 燃やした進化元は墓地へ、出した T001 はバトルゾーンへ
    assert base in _cids(e, "graveyard")
    assert any(e.s.cards[c].defn == "T001" for c in _cids(e, "bz"))
    assert len(_cids(e, "mana")) == 6          # 7 - 1（出した分）


def test_meteor_burn_decline_keeps_under():
    e = _fixture(["T001"] * 5, ["T002"] * 4 + ["T001", "T001"])
    base = _cid(e, "bz", "T001")
    me = None
    handler, st = _driver(accept=False)
    _run(e, handler, done=lambda: st["opp_main"])
    me = _cid(e, "bz", ME)
    assert list(e.s.cards[me].under or []) == [base]   # 下は残る
    assert base not in _cids(e, "graveyard")
    assert len(_cids(e, "mana")) == 7                  # 何も出ない


def test_meteor_burn_no_under_no_putout():
    e = _fixture(["T001"] * 5, ["T002"] * 4 + ["T001", "T001"])
    handler, st = _driver(evolve=False)                # 素出し（下なし）
    _run(e, handler, done=lambda: st["opp_main"])
    assert st["putout_options"] is None                # 出す選択は出ない
    assert sorted(_defns(e, "bz")) == ["T001", ME]     # 場は元通り
    assert len(_cids(e, "mana")) == 7


def test_meteor_burn_no_valid_target():
    # マナのクリーチャーは全てコスト7以上（CIP の2枚は呪文）。
    # マナ7枚 → コスト<7 のクリーチャーは無く、何も出ない。
    e = _fixture(["T142", "T142", "T095", "T095", "T142"],
                 ["T003"] * 6)
    base = _cid(e, "bz", "T001")
    handler, st = _driver()
    _run(e, handler, done=lambda: st["opp_main"])
    assert base in _cids(e, "graveyard")               # 燃やすのは可能
    assert st["putout_options"] is None                # 対象なし
    assert _defns(e, "bz") == [ME]
    assert len(_cids(e, "mana")) == 7
