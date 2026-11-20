"""再変換ラウンド348（第313弾 cost_le_count）の記録テスト。

- 新規登録1件: dm26rp3-std010 BARUGA-雷座87(DM26RP3 STD10/)。
- alias 畳み込み4件: dm26rp3-stdchosec010 / dm26rp3-stdsec010 /
  dm25ex3-023 / dm25rp2-021 → dm26rp3-std010
  （source.aliases への記録）。
- stale クリーンアップ2件: submit では std010 の reject 行だけが
  外れたため、alias としてカバーされた stdchosec010 / stdsec010
  の reject 行を行だけ除去した（第347弾と同型）。
- 差し戻し0件。
- 正本判定は identity の実データ照合による:
  canon_id は3刷とも dm26rp3-std010、
  aliases_for（BARUGA-雷座87, dm26rp3-std010）
  = [dm25ex3-023, dm25rp2-021, dm26rp3-stdchosec010,
     dm26rp3-stdsec010]。
- 対象行は gaps が空のため reopen では外れず直接 submit
  （第323・343・347弾の先例）。
- converted 10,251→10,252 / rejects 2,069→2,066、
  canonical 重なり0・漏れ0。cost_le_count は対象3行から解消
  （ギャップ名は多重ギャップ行 dm25ex3-rp1s02 にのみ残る）。

登録形は第313弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし、abilities は [CIP誘発,
メテオバーン誘発] の2件ちょうど）:
- partial（NEO進化・W・ブレイカー・CIP「山札の上から2枚を
  タップしてマナゾーンに置く」）に、dm19-007 のメテオバーン
  イディオム（may + move {under_of: self} as: paid + if
  {exists: {ref: paid}}）の攻撃時誘発を追加し、unsupported
  を除去したもの。マナから出すコスト条件は第117弾
  cost_lt_count の確立形 cost_le: {sum: [{count: {zone: mana,
  owner: you}}, -1]}（登録先例 dm26ex3-082）。
- 登録名は公式データの表記「BARUGA-雷座87(DM26RP3 STD10/)」
  （partial の表記と一致）。text は公式本文と同一。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。
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

TARGET = "dm26rp3-std010"
PRINTINGS = ["dm26rp3-std010", "dm26rp3-stdchosec010", "dm26rp3-stdsec010"]
ALIASES = ["dm25ex3-023", "dm25rp2-021",
           "dm26rp3-stdchosec010", "dm26rp3-stdsec010"]
GAP = "cost_le_count"

TEXT = ("NEO進化：光、火、または自然のクリーチャー１体の上に置いてもよい。\n"
        "W・ブレイカー\n"
        "このクリーチャーが出た時、自分の山札の上から２枚をタップしてマナゾーンに置く。\n"
        "メテオバーン：このクリーチャーが攻撃する時、このクリーチャーの下にあるカードを１枚墓地に置いてもよい。"
        "そうしたら、自分のマナゾーンにあるカードの枚数よりコストが小さいクリーチャーを１体、自分のマナゾーンから出す。")

CIP_TRIGGER = {"kind": "trigger",
               "when": {"event": "move", "to": "bz", "subject": "self"},
               "effect": [
                   {"op": "move",
                    "select": {"zone": "deck", "owner": "you",
                               "from_top": 2},
                    "to": "mana", "reason": "put", "tapped": True}]}

METEOR_TRIGGER = {"kind": "trigger",
                  "when": {"event": "attack", "subject": "self"},
                  "effect": [
                      {"op": "may",
                       "body": [
                           {"op": "move",
                            "select": {"under_of": "self", "count": 1},
                            "to": "graveyard", "reason": "put",
                            "as": "paid"},
                           {"op": "if",
                            "cond": {"exists": {"ref": "paid"}},
                            "then": [
                                {"op": "move",
                                 "select": {"zone": "mana", "owner": "you",
                                            "filter": {
                                                "types": ["creature"],
                                                "cost_le": {"sum": [
                                                    {"count": {
                                                        "zone": "mana",
                                                        "owner": "you"}},
                                                    -1]}},
                                            "count": 1},
                                 "to": "bz", "reason": "put"}]}]}]}

FORM = {"id": TARGET,
        "name": "BARUGA-雷座87(DM26RP3 STD10/)",
        "types": ["creature"],
        "civs": ["nature"],
        "cost": 5, "power": 6000,
        "races": ["アーマード・ドラゴン", "テクノ・サムライ"],
        "mana": 1,
        "neo": True,
        "evolve_from": {"civs": ["light", "fire", "nature"],
                        "types": ["creature"]},
        "text": TEXT,
        "abilities": [CIP_TRIGGER, METEOR_TRIGGER],
        "keywords": ["double_breaker"]}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round348_disposition():
    rej = _reject_rows()
    assert len(rej) == 2066
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10252
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = set()
    for c in conv:
        aliases.update((c.get("source") or {}).get("aliases") or [])
    for t in PRINTINGS:
        assert t not in rej              # 漏れ0（3刷とも行が無い）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == ALIASES
    for a in ALIASES:
        assert a not in ids and a in aliases
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "neo", "evolve_from", "text", "abilities",
              "keywords"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2      # [CIP誘発, メテオバーン誘発]
    d = parse_card(c, TABLES)
    assert d.types == ["creature"] and d.neo
    assert sorted(d.keywords) == ["double_breaker"]
    # cost_le_count は対象3行から解消。ギャップ名は多重ギャップ行
    # dm25ex3-rp1s02（neo_summon_cost_reduction を併せ持ち、手札枚数
    # 以下のコストで実行する別用法）にのみ残る
    def _unsup(r):
        return [u.get("need") if isinstance(u, dict) else u
                for u in (((r.get("partial") or {}).get("source") or {})
                          .get("unsupported") or [])]
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == {"dm25ex3-rp1s02"}, left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

CARD = TARGET


def _build(rules, p0, p1):
    return scenario.build(
        rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]


def _cids(e, zone, p=0):
    return [c for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]


def _cid(e, zone, defn, p=0):
    return next(c for c in _cids(e, zone, p) if e.s.cards[c].defn == defn)


def _run(e, handler, limit=900, done=None):
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
    raise AssertionError("run did not finish")


def _driver(accept=True, pick_defn="T001"):
    """登録カードを NEO 進化で出し、次の自分のターンに攻撃する。
    state: played / attacked / putout_options / opp_main。"""
    st = {"played": False, "attacked": False, "putout_options": None,
          "opp_main": False}

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        p = d["player"]
        if d["kind"] == "main" and p == 1 and st["attacked"]:
            st["opp_main"] = True     # 攻撃が解決し切って相手のターンへ
        if d["kind"] == "main" and p == 0 and not st["played"]:
            key = f"play:{CARD}:neo"
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
            ak = f"attack:{CARD}:player"
            if ak in keys:
                st["attacked"] = True
                return [keys.index(ak)]
        if d["kind"] in ("block", "declare_block") and "no_block" in keys:
            return [keys.index("no_block")]
        return None

    return handler, st


def _fixture(rules, mana):
    return _build(rules,
                  {"bz": ["T001"], "hand": [CARD], "mana": mana,
                   "deck": ["T002"] * 8},
                  {"deck": ["T002"] * 6})


# ---------- 実挙動（登録形） ----------

def test_registered_cip_top2_to_mana_tapped(rules):
    """dm26rp3-std010: 出た時、山札の上から2枚をタップしてマナへ。"""
    e = _fixture(rules, ["T001"] * 5)
    handler, st = _driver()
    _run(e, handler,
         done=lambda: CARD in _defns(e, "bz") and len(_cids(e, "mana")) == 7)
    assert st["played"]
    mana = _cids(e, "mana")
    assert len(mana) == 7                      # 5 + 2（CIP）
    added = [c for c in mana if e.s.cards[c].defn == "T002"]
    assert len(added) == 2                     # 山札の上から2枚
    assert all(e.s.cards[c].tapped for c in added)


def test_registered_meteor_burn_puts_out_below_mana_count(rules):
    """メテオバーン: 下を燃やし、マナ7枚よりコストが小さい
    クリーチャーを1体マナから出す（コスト7・9は候補に出ない）。"""
    e = _fixture(rules, ["T142", "T095", "T001", "T001", "T001"])
    base = _cid(e, "bz", "T001")
    big7 = _cid(e, "mana", "T142")             # コスト7
    big9 = _cid(e, "mana", "T095")             # コスト9
    handler, st = _driver()
    _run(e, handler,
         done=lambda: st["putout_options"] is not None
         and len(_cids(e, "mana")) == 6)
    assert st["attacked"]
    assert big7 not in st["putout_options"]
    assert big9 not in st["putout_options"]
    assert {e.s.cards[c].defn for c in st["putout_options"]} <= {"T001", "T002"}
    assert base in _cids(e, "graveyard")       # 燃やした進化元は墓地へ
    assert any(e.s.cards[c].defn == "T001" for c in _cids(e, "bz"))
    assert len(_cids(e, "mana")) == 6          # 7 - 1（出した分）


def test_registered_meteor_burn_decline_keeps_under(rules):
    """メテオバーンを辞退すると下は残り、何も出ない。"""
    e = _fixture(rules, ["T001"] * 5)
    base = _cid(e, "bz", "T001")
    handler, st = _driver(accept=False)
    _run(e, handler, done=lambda: st["opp_main"])
    me = _cid(e, "bz", CARD)
    assert list(e.s.cards[me].under or []) == [base]   # 下は残る
    assert base not in _cids(e, "graveyard")
    assert len(_cids(e, "mana")) == 7                  # 何も出ない
