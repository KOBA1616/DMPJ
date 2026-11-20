"""再変換ラウンド337（第302弾 gachinko_break_count）の記録テスト。

- 新規登録3件: dm26rp2-tr009（ツインパクト。クリーチャー面に形B）/
  dmex12-009（形B）= R.S.F.K. の別々の正本2印刷と、dmr05-v02
  鬼無双 カイザー「勝」（形A）。identity では tr009 と dmex12-009 は
  互いに canon ではなく（canon_id は各自）、独立に登録した。
- alias は partial の source.aliases 由来（tr009: dm22bd3-008 /
  dm22ex1-030 / dmart19-004、dmex12-009: dmr08-004 / dmx22b-079）。
  いずれも独立エントリではなく reject 行も元々無い。
- 差し戻し・stale 解消・converted 是正は0件。
- converted 10,232→10,235 / rejects 2,090→2,087、重なり0・漏れ0。
  gachinko_break_count は rejects から解消。

登録形の要点（第302弾で実挙動固定した形どおり）:
- 形B（R.S.F.K.）: attack 誘発 [gachinko {until_lose, stoppable,
  as: wins}, break {player: opp, count: {var: wins}}]（効果ブレイク。
  公式QA qa/42524・2023.5.17 の一連のQAで裏取り済み）。
- 形A（カイザー）: partial の repeat {times: {var: wins}} の body に
  modify {breaks_add: 1}（end_of_turn）を本文の順序どおり挿入。
- submit の連結・merge_split 由来の混入が無いことを、登録形の
  abilities・keywords の完全一致で固定する。

converted 側センサス（ラウンド169の誤読の有無）: 本ラウンドの
登録前に gachinko と breaks_add を併せ持つ converted カードは
0件で、誤読は登録されていなかった。登録後に該当するのは形Aの
本物 dmr05-v02 だけであることもここで固定する。

実挙動は登録カード自身で固定する。山札は build がシャッフルする
ため、ガチンコの公開は均一デッキ（勝ち札 T201 コスト9 / 負け札
T002 コスト2）で脚本する。継続確認は投げる前の yes_no で、
yes=0 / no=1（ops.op_gachinko）。ドライバは scenario.build の
薄い包みで、tests.conftest は import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TR009 = "dm26rp2-tr009"
EX12 = "dmex12-009"
V02 = "dmr05-v02"
TARGETS = (TR009, EX12, V02)
ALIASES = {TR009: ["dm22bd3-008", "dm22ex1-030", "dmart19-004"],
           EX12: ["dmr08-004", "dmx22b-079"],
           V02: []}

FORM_B = {"kind": "trigger",
          "when": {"event": "attack", "subject": "self"},
          "effect": [
              {"op": "gachinko", "until_lose": True, "stoppable": True,
               "as": "wins"},
              {"op": "break", "player": "opp", "count": {"var": "wins"}}]}
BREAKS_STEP = {"op": "modify", "select": {"ref": "self"},
               "mod": {"breaks_add": 1}, "duration": "end_of_turn"}
FORM_A_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "effect": [
        {"op": "gachinko", "until_lose": True, "stoppable": True,
         "as": "wins"},
        {"op": "repeat", "times": {"var": "wins"}, "body": [
            {"op": "modify", "select": {"ref": "self"},
             "mod": {"power": 6000}, "duration": "end_of_turn"},
            BREAKS_STEP,
            {"op": "destroy",
             "select": {"zone": "bz", "owner": "opp", "count": 1,
                        "chooser": "opp",
                        "filter": {"types": ["creature"],
                                   "keyword": "blocker"}}}]}]}
SPELL_FACE = [
    {"op": "gachinko", "times": 1, "as": "wins"},
    {"op": "if", "cond": {"cmp": [{"var": "wins"}, ">=", 1]},
     "then": [{"op": "draw", "count": 1}]}]


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round337_disposition():
    rej = _reject_rows()
    assert len(rej) == 2087
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10235
    assert not (ids & set(rej))          # canonical 重なり0
    for tid in TARGETS:
        c = _conv(tid)
        assert c is not None, tid
        assert not (c.get("source") or {}).get("unsupported"), tid
        assert (c.get("source") or {}).get("aliases") == \
            (ALIASES[tid] or None), tid
        parse_card(c, TABLES)
        assert tid not in rej, tid       # 漏れ0
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    tr = _conv(TR009)
    assert tr["faces"][0]["abilities"] == [FORM_B]
    assert tr["faces"][0]["keywords"] == ["speed_attacker"]
    assert tr["faces"][1]["spell"] == SPELL_FACE
    assert tr["faces"][1]["keywords"] == ["charger"]
    ex = _conv(EX12)
    assert ex["abilities"] == [FORM_B]
    assert ex["keywords"] == ["speed_attacker"]
    v02 = _conv(V02)
    assert v02["abilities"] == [FORM_A_TRIGGER]
    assert v02["keywords"] == ["double_breaker"]
    # alias は独立エントリではなく reject 行も無い
    for tid, als in ALIASES.items():
        for a in als:
            assert _conv(a) is None, a
            assert a not in rej, a
    # ファミリー解消
    holders = {rid for rid, r in rej.items()
               if "gachinko_break_count" in (r.get("gaps") or [])}
    assert holders == set(), holders
    # converted 側センサス: ラウンド337の登録前に gachinko と
    # breaks_add を併せ持つカードは0件で、ラウンド169の誤読は
    # converted に登録されていなかった。登録後は形Aの本物である
    # dmr05-v02（本文に「さらに」がある正当な加算）だけが該当する。
    both = [c["id"] for c in conv
            if "gachinko" in json.dumps(c, ensure_ascii=False)
            and "breaks_add" in json.dumps(c, ensure_ascii=False)]
    assert both == [V02], both
    assert "さらに" in _conv(V02)["text"]


# ---------- 実挙動ドライバ ----------

def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _attacker_cid(e, defn):
    for c in e.zlist("bz", 0):
        card = e.s.cards[c]
        if card.defn == defn and card.controller == 0 and card.top_of < 0:
            return c
    return None


def _build(rules, p0, p1, winner=True):
    d0, d1 = (["T201"] * 6, ["T002"] * 6) if winner \
        else (["T002"] * 6, ["T201"] * 6)
    spec0 = dict(p0)
    spec0["deck"] = d0
    spec1 = dict(p1)
    spec1["deck"] = d1
    return scenario.build(
        rules, {"p0": spec0, "p1": spec1, "filler": "T001", "seed": 1,
                "deck_exact": [True, True]})


def _drive(e, attack, yes_no=(), block_with=None, breaks_log=None,
           steps=600):
    st = {"attacked": False, "yn": list(yes_no)}
    for _ in range(steps):
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "choose_shields" and breaks_log is not None:
            cid = _attacker_cid(e, attack)
            breaks_log.append({
                "count": d.get("min"),
                "shields": len(e.zlist("shield", 1)),
                "power": e.chars_ro(cid)["power"] if cid is not None
                else None})
            e.answer(list(range(d["min"])))
        elif kind == "attack" and not st["attacked"]:
            want = f"attack:{attack}:player"
            if want in keys:
                st["attacked"] = True
                e.answer([keys.index(want)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "yes_no":
            e.answer([st["yn"].pop(0) if st["yn"] else 0])
        elif kind == "block":
            hit = None
            if block_with:
                hit = next((i for i, k in enumerate(keys)
                            if k.startswith("bz:" + block_with)), None)
            if hit is not None:
                e.answer([hit])
            else:
                e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return st


# ---------- 形B（登録形）: dmex12-009 / dm26rp2-tr009 ----------

def test_registered_ex12_form_b_two_wins(rules):
    """2勝 → 誘発中の効果ブレイク2枚が先に着地し、その後で攻撃自身の
    ブレイク1枚（第302弾の判別どおり）。"""
    e = _build(rules, {"bz": [EX12]}, {})
    log = []
    _drive(e, EX12, yes_no=[0, 0, 1], breaks_log=log)
    assert [(x["count"], x["shields"]) for x in log] == [(2, 5), (1, 3)]
    assert len(e.zlist("shield", 1)) == 2


def test_registered_ex12_form_b_blocked_after_effect_break(rules):
    """ブロックされても効果ブレイクの1枚は割れたまま（攻撃のブレイク
    への加算ではないことの判別）。"""
    e = _build(rules, {"bz": [EX12]}, {"bz": ["T004"]})
    log = []
    _drive(e, EX12, yes_no=[0, 1], block_with="T004", breaks_log=log)
    assert [(x["count"], x["shields"]) for x in log] == [(1, 5)]
    assert len(e.zlist("shield", 1)) == 4
    assert "T004" in _defns(e, "graveyard", 1)   # 3000 は 5000 に負ける
    assert EX12 in _defns(e, "bz")


def test_registered_tr009_form_b_one_win(rules):
    """ツインパクトのクリーチャー面も形B: 1勝 → 効果1枚＋攻撃1枚。"""
    e = _build(rules, {"bz": [TR009]}, {})
    log = []
    _drive(e, TR009, yes_no=[0, 1], breaks_log=log)
    assert [(x["count"], x["shields"]) for x in log] == [(1, 5), (1, 4)]
    assert len(e.zlist("shield", 1)) == 3


# ---------- 形A（登録形）: dmr05-v02 ----------

def test_registered_v02_form_a_two_wins(rules):
    """2勝 → 誘発中は割らず、攻撃のブレイクが W・ブレイカー2＋勝ち数
    2 = 4枚に増える。パワーは +6000×2、ブロッカー破壊も2回。"""
    base = _conv(V02)["power"]
    e = _build(rules, {"bz": [V02]}, {"bz": ["T004", "T004"]})
    log = []
    _drive(e, V02, yes_no=[0, 0, 1], breaks_log=log)
    assert [(x["count"], x["shields"]) for x in log] == [(4, 5)]
    assert log[0]["power"] == base + 12000
    assert _defns(e, "graveyard", 1).count("T004") == 2
    assert len(e.zlist("shield", 1)) == 1


def test_registered_v02_form_a_lose_immediately(rules):
    """即負け → 増幅なしの通常 W・ブレイカー2枚だけ。"""
    base = _conv(V02)["power"]
    e = _build(rules, {"bz": [V02]}, {}, winner=False)
    log = []
    _drive(e, V02, yes_no=[0], breaks_log=log)
    assert [(x["count"], x["shields"]) for x in log] == [(2, 5)]
    assert log[0]["power"] == base
    assert len(e.zlist("shield", 1)) == 3
