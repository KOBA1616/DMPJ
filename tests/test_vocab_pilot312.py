"""語彙パイロット第312弾: ex_life_shield_leave_trigger
（「EXライフ」シールドが離れた時にも選ぶモーダル）。

対象は dm26ex4-003 / dm26ex4-sec004 切札接続 ドールバロム 2件
（同一カードの2刷。行の gaps は空で、ギャップ名は
partial.source.unsupported = ["ex_life_shield_leave_trigger"] にのみある
NEO 期の行）。partial は CIP 誘発＋モーダル3択まで完成済みで、
欠けているのは「このクリーチャーの『EXライフ』シールドが離れた時」
にも同じモーダルが発火する第2誘発だけだった。

結論: **ドリフト**（新規語彙・エンジン変更なし）。離脱誘発の形は
第190弾で実装され第291弾で登録先例のある
{event: move, from: shield, subject: {exlife_of: self}}。
本弾では dm26ex4-003 型のプロト T963（EXライフ＋CIPモーダル＋
離脱モーダル）で、CIP 経路・ブレイク経路・破壊置換経路と
モーダル3択すべての実挙動を固定する。

モーダルの検証ポイント:
- mode 0（相手は闇ではない手札をすべて捨てる）: discard マクロ＋
  select {chooser: opp, count: all, filter: {not_civs: [darkness]}}。
  全対象が捨てられるため公開情報は墓地で確定し、闇カードは伏せたまま残る。
- mode 1（闇ではないクリーチャーをすべて破壊）: destroy
  {count: all, owner: any}。自軍の闇でない獣も巻き込む（本文どおり）。
- mode 2（相手の闇でないマナは次の自分のターンのはじめまで
  アンタップしない）: modify {deny: [untap_at_start],
  duration: until_next_own_turn_start}。自分のターンに発火すれば
  相手の次のターン開始のアンタップを止める（本弾で固定）。
  相手のターンに発火した場合は、相手の次のアンタップが
  自分の次のターン開始より後になるため、文面どおり制限は
  そこで切れる（duration の解決は core._duration が
  until_turn_start:{you} に固定する既存意味論）。
"""
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
PROTO = "T963"

MODAL = {"op": "modal", "modes": [
    [{"op": "discard",
      "select": {"chooser": "opp", "count": "all",
                 "filter": {"not_civs": ["darkness"]},
                 "owner": "opp", "zone": "hand"}}],
    [{"op": "destroy",
      "select": {"count": "all",
                 "filter": {"not_civs": ["darkness"], "types": ["creature"]},
                 "owner": "any", "zone": "bz"}}],
    [{"op": "modify",
      "select": {"count": "all", "filter": {"not_civs": ["darkness"]},
                 "owner": "opp", "zone": "mana"},
      "mod": {"deny": ["untap_at_start"]},
      "duration": "until_next_own_turn_start"}]]}

CIP_TRIGGER = {"kind": "trigger",
               "when": {"event": "move", "to": "bz", "subject": "self"},
               "effect": [MODAL]}

LEAVE_TRIGGER = {"kind": "trigger",
                 "when": {"event": "move", "from": "shield",
                          "subject": {"exlife_of": "self"}},
                 "effect": [MODAL]}


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _exlife_shield(e, p):
    return next((c for c in e.zlist("shield", p)
                 if e.s.cards[c].exlife_of is not None), None)


def _bz(e, p, defn):
    return [c for c in e.zlist("bz", p) if e.s.cards[c].defn == defn
            and e.s.cards[c].controller == p]


def _zone_defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


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
        if d["kind"] == "main" and not st.get("played") \
                and f"play:{tid}" in keys:
            st["played"] = True
            return [keys.index(f"play:{tid}")]
        return None
    return hook


def _mode_hook(st, modes):
    """choose_mode を modes の列順に答え、回数を数える。"""
    def hook(e, d, keys):
        if d["kind"] == "choose_mode":
            i = st.get("modes_seen", 0)
            st["modes_seen"] = i + 1
            if i < len(modes):
                return [keys.index(f"mode:{modes[i]}")]
            return [0]
        return None
    return hook


def _pick_shield_hook(st, which):
    def hook(e, d, keys):
        if d["kind"] == "choose_shields" and not st.get("broke"):
            ex = _exlife_shield(e, 0)
            for i, o in enumerate(d["options"]):
                if (o.get("cid") == ex) == (which == "ex"):
                    st["broke"] = True
                    return [i]
            return None
        return None
    return hook


def _cast_hook(tid, st):
    def hook(e, d, keys):
        if d["kind"] == "main" and d["player"] == 1 and st.get("played") \
                and not st.get("cast") and f"play:{tid}" in keys:
            st["cast"] = True
            return [keys.index(f"play:{tid}")]
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


def _stop_next_own(st, after_modes):
    def hook(e, d, keys):
        if st.get("modes_seen", 0) >= after_modes \
                and d["player"] == 0 and d["kind"] in ("charge", "main"):
            return "stop"
        return None
    return hook


# ---------- parse ----------

def test_parse_protos():
    d = parse_card(_proto_card(PROTO), TABLES)
    trigs = [a for a in d.abilities if a["kind"] == "trigger"]
    assert len(trigs) == 2
    assert trigs[0]["when"] == CIP_TRIGGER["when"]
    assert trigs[1]["when"] == LEAVE_TRIGGER["when"]
    # 2つの誘発の効果は同一モーダル（parse 後の形で一致）
    assert trigs[0]["effect"] == trigs[1]["effect"]
    modal = trigs[0]["effect"][0]
    assert modal["op"] == "modal" and len(modal["modes"]) == 3
    # マクロ展開: discard → move (reason: discard)、destroy → move (reason: destroy)
    assert modal["modes"][0][0]["op"] == "move"
    assert modal["modes"][0][0]["reason"] == "discard"
    assert modal["modes"][1][0]["op"] == "move"
    assert modal["modes"][1][0]["reason"] == "destroy"
    m3 = modal["modes"][2][0]
    assert m3["op"] == "modify" and m3["mod"] == {"deny": ["untap_at_start"]}
    assert m3["duration"] == "until_next_own_turn_start"
    assert "ex_life" in d.keywords


# ---------- CIP 経路 ----------

def test_cip_mode_destroy_all_non_darkness(rules):
    """出た時 mode 1: 闇ではないクリーチャーをすべて破壊（自軍も巻き込む）。
    闇のクリーチャーは残る。"""
    e = setup(rules, {"hand": [PROTO], "mana": ["T008"] * 5, "bz": ["T001"]},
              {"bz": ["T001", "T008"]})
    st = {}
    hook = _chain(_play_hook(PROTO, st), _mode_hook(st, [1]),
                  _stop_next_own(st, 1))
    _drive(e, hook)
    assert st.get("played") and st.get("modes_seen") == 1
    assert _bz(e, 0, PROTO)
    assert "T001" in _zone_defns(e, "graveyard", 0)   # 自軍の自然獣も破壊
    assert "T001" in _zone_defns(e, "graveyard", 1)   # 相手の自然獣も破壊
    assert not _bz(e, 0, "T001") and not _bz(e, 1, "T001")
    assert _bz(e, 1, "T008")                          # 闇獣は残る


def test_cip_mode_freeze_blocks_next_opponent_untap(rules):
    """出た時 mode 2: 相手の闇でないマナは次の相手のターンのはじめに
    アンタップしない。闇マナは通常通りアンタップする。"""
    e = setup(rules, {"hand": [PROTO], "mana": ["T008"] * 5},
              {"mana": ["T001", "T001", "T008"], "hand": ["T001"]})
    for c in e.zlist("mana", 1):
        e.s.cards[c].tapped = True
    st = {}

    def stop(e, d, keys):
        if st.get("modes_seen", 0) >= 1 and d["player"] == 1 \
                and d["kind"] == "charge":
            return "stop"
        return None

    hook = _chain(_play_hook(PROTO, st), _mode_hook(st, [2]), stop)
    _drive(e, hook)
    assert st.get("played") and st.get("modes_seen") == 1
    states = {e.s.cards[c].defn: e.s.cards[c].tapped
              for c in e.zlist("mana", 1)}
    assert states == {"T001": True, "T008": False}  # 自然は凍結、闇は起きた
    assert len([c for c in e.zlist("mana", 1)
                if e.s.cards[c].defn == "T001"]) == 2


# ---------- シールド離脱経路: ブレイク ----------

def test_shield_leave_break_mode_discard(rules):
    """相手のブレイク呪文で EXライフシールドが離れる → mode 0:
    相手は闇ではない手札をすべて捨て、闇カードは手札に残る。"""
    e = setup(rules, {"hand": [PROTO], "mana": ["T008"] * 5},
              {"hand": ["T850", "T001", "T008"], "mana": ["T008"]})
    st = {}
    hook = _chain(_play_hook(PROTO, st), _mode_hook(st, [2, 0]),
                  _cast_hook("T850", st), _pick_shield_hook(st, "ex"),
                  _stop_next_own(st, 2))
    _drive(e, hook)
    assert st.get("cast") and st.get("broke") and st.get("modes_seen") == 2
    assert _bz(e, 0, PROTO)                            # 本体は場に残る
    assert _zone_defns(e, "hand", 1) == ["T008"]       # 闇だけ残った
    assert "T001" in _zone_defns(e, "graveyard", 1)    # 自然は捨てられた
    assert "T850" in _zone_defns(e, "graveyard", 1)


def test_normal_shield_break_does_not_fire(rules):
    """EXライフでない普通のシールドが割れてもモーダルは発火しない。"""
    e = setup(rules, {"hand": [PROTO], "mana": ["T008"] * 5},
              {"hand": ["T850", "T001"], "mana": ["T008"]})
    st = {}
    hook = _chain(_play_hook(PROTO, st), _mode_hook(st, [2]),
                  _cast_hook("T850", st), _pick_shield_hook(st, "normal"),
                  _stop_next_own(st, 1))
    _drive(e, hook)
    assert st.get("cast") and st.get("broke")
    assert st.get("modes_seen") == 1                   # CIP の1回だけ
    assert "T001" in _zone_defns(e, "hand", 1)         # 捨てられていない
    assert _exlife_shield(e, 0) is not None            # EXライフシールドは残存


# ---------- シールド離脱経路: 破壊置換 ----------

def test_shield_leave_destroy_replacement_mode_destroy(rules):
    """相手の破壊呪文 → EXライフ置換でシールドが墓地へ（本体は残る）
    → mode 1: 闇ではないクリーチャーをすべて破壊する。"""
    e = setup(rules, {"hand": [PROTO], "mana": ["T008"] * 5},
              {"hand": ["T056"], "mana": ["T008"] * 3,
               "bz": ["T001", "T008"]})
    st = {}

    # T056 の破壊対象は、相手のクリーチャーが T963 だけのため
    # 選択決定が出ず自動で T963 に定まる（ask の一意自動決定）
    hook = _chain(_play_hook(PROTO, st), _mode_hook(st, [2, 1]),
                  _cast_hook("T056", st), _stop_next_own(st, 2))
    _drive(e, hook)
    assert st.get("cast") and st.get("modes_seen") == 2
    assert _bz(e, 0, PROTO)                            # 置換で場に残った
    assert len(e.zlist("graveyard", 0)) == 1           # 墓地はシールド1枚だけ
    assert "T001" in _zone_defns(e, "graveyard", 1)    # 相手の自然獣は破壊
    assert _bz(e, 1, "T008")                           # 闇獣は残る
