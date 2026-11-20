"""再変換ラウンド347（第312弾 ex_life_shield_leave_trigger）の記録テスト。

- 新規登録1件: dm26ex4-003 切札接続 ドールバロム。
- alias 畳み込み1件: dm26ex4-sec004 → dm26ex4-003
  （source.aliases への記録。submit では sec004 の reject 行が
  外れなかったため、登録で alias としてカバーされた stale 行として
  行だけを除去した。第328・330・331弾の stale クリーンアップと同型）
- stale クリーンアップ1件（上記 sec004 行）/ 差し戻し0件。
- 正本判定は identity の実データ照合による:
  canon_id(dm26ex4-sec004) = dm26ex4-003、
  aliases_for（切札接続 ドールバロム, dm26ex4-003）
  = [dm26ex4-sec004]。
- 対象行は gaps が空のため reopen では外れず直接 submit
  （第323・343弾の先例）。
- converted 10,250→10,251 / rejects 2,071→2,069、
  canonical 重なり0・漏れ0。ex_life_shield_leave_trigger は解消。

登録形は第312弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし、abilities は [CIP誘発, 離脱誘発]
の2件ちょうどで両誘発の effect は同一モーダル）:
- partial（NEO進化・EXライフ・T・ブレイカー・CIP 誘発＋
  モーダル3択）に第2誘発 {event: move, from: shield,
  subject: {exlife_of: self}}（第190弾実装・第291弾登録先例）
  を追加し、unsupported を除去したもの。
- text は reject 行の正式本文と同一。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。相手のブレイク呪文役は第312弾プロト T850 を使う。
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

TARGET = "dm26ex4-003"
ALIAS = "dm26ex4-sec004"
GAP = "ex_life_shield_leave_trigger"

TEXT = ("NEO進化：闇のクリーチャー１体の上に置いてもよい。\n"
        "EXライフT・ブレイカー\n"
        "このクリーチャーが出た時またはこのクリーチャーの「EXライフ」シールドが離れた時、"
        "次の中から１回選ぶ。\n"
        "▶相手は自身の手札を表向きにし、その中から闇ではないカードをすべて捨てる。\n"
        "▶闇ではないクリーチャーをすべて破壊する。\n"
        "▶相手のマナゾーンにある闇ではないカードはすべて、"
        "次の自分のターンのはじめまでアンタップしない。")

MODAL = {"op": "modal", "modes": [
    [{"op": "discard",
      "select": {"zone": "hand", "owner": "opp", "chooser": "opp",
                 "filter": {"not_civs": ["darkness"]}, "count": "all"}}],
    [{"op": "destroy",
      "select": {"zone": "bz", "owner": "any",
                 "filter": {"types": ["creature"],
                            "not_civs": ["darkness"]},
                 "count": "all"}}],
    [{"op": "modify",
      "select": {"zone": "mana", "owner": "opp",
                 "filter": {"not_civs": ["darkness"]}, "count": "all"},
      "mod": {"deny": ["untap_at_start"]},
      "duration": "until_next_own_turn_start"}]]}

CIP_TRIGGER = {"kind": "trigger",
               "when": {"event": "move", "to": "bz", "subject": "self"},
               "effect": [MODAL]}

LEAVE_TRIGGER = {"kind": "trigger",
                 "when": {"event": "move", "from": "shield",
                          "subject": {"exlife_of": "self"}},
                 "effect": [MODAL]}

FORM = {"id": TARGET,
        "name": "切札接続 ドールバロム",
        "types": ["creature"],
        "civs": ["darkness"],
        "cost": 10, "power": 15000,
        "races": ["ディスペクター", "デスパペット", "デーモン・コマンド"],
        "mana": 1,
        "neo": True,
        "evolve_from": {"civs": ["darkness"], "types": ["creature"]},
        "text": TEXT,
        "abilities": [CIP_TRIGGER, LEAVE_TRIGGER],
        "keywords": ["ex_life", "triple_breaker"]}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round347_disposition():
    rej = _reject_rows()
    assert len(rej) == 2069
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10251
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = set()
    for c in conv:
        aliases.update((c.get("source") or {}).get("aliases") or [])
    c = _conv(TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert TARGET not in rej             # 漏れ0
    # sec004 は独立エントリではなく alias として畳み込み、
    # reject 行も除去済み（stale クリーンアップ）
    assert ALIAS not in ids and ALIAS not in rej
    assert (c.get("source") or {}).get("aliases") == [ALIAS]
    assert ALIAS in aliases
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "neo", "evolve_from", "text", "abilities",
              "keywords"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2      # [CIP誘発, 離脱誘発]
    assert c["abilities"][0]["effect"] == c["abilities"][1]["effect"]
    d = parse_card(c, TABLES)
    assert d.types == ["creature"] and d.neo
    assert sorted(d.keywords) == ["ex_life", "triple_breaker"]
    # ex_life_shield_leave_trigger は解消（unsupported 側も含め残らない）
    def _unsup(r):
        return ((r.get("partial") or {}).get("source") or {}) \
            .get("unsupported") or []
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

CARD = TARGET
BREAK_SPELL = "T850"


def _build(rules, p0, p1):
    return scenario.build(
        rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]


def _cid(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn
                and (zone != "bz" or e.s.cards[c].controller == p))


def _exlife_shield(e, p):
    return next((c for c in e.zlist("shield", p)
                 if e.s.cards[c].exlife_of is not None), None)


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
        elif kind in ("block", "declare_block"):
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("drive did not finish")


def _hook(st, modes, base_defn="T008", break_shield=None):
    """登録カードを出し、モード列を答え、相手のブレイク呪文と
    シールド選択（break_shield: "ex" / "normal" / None）に応じる。"""
    def hook(e, d, keys):
        p = d["player"]
        if d["kind"] == "main" and p == 0 and not st.get("played") \
                and f"play:{CARD}" in keys:
            st["played"] = True
            return [keys.index(f"play:{CARD}")]
        if d["kind"] == "choose_evo_source":
            for i, o in enumerate(d["options"]):
                if o.get("cid") == st.get("base"):
                    return [i]
            return None
        if d["kind"] == "yes_no":
            return [0]
        if d["kind"] == "choose_mode":
            i = st.get("modes_seen", 0)
            st["modes_seen"] = i + 1
            if i < len(modes):
                return [keys.index(f"mode:{modes[i]}")]
            return [0]
        if d["kind"] == "main" and p == 1 and st.get("played") \
                and not st.get("cast") and f"play:{BREAK_SPELL}" in keys:
            st["cast"] = True
            return [keys.index(f"play:{BREAK_SPELL}")]
        if d["kind"] == "choose_shields" and break_shield \
                and not st.get("broke"):
            ex = _exlife_shield(e, 0)
            for i, o in enumerate(d["options"]):
                if (o.get("cid") == ex) == (break_shield == "ex"):
                    st["broke"] = True
                    return [i]
            return None
        if st.get("modes_seen", 0) >= st.get("stop_after", 10 ** 9) \
                and p == 0 and d["kind"] in ("charge", "main"):
            return "stop"
        return None
    return hook


def _setup_played(rules, p1, modes):
    e = _build(rules,
               {"hand": [CARD], "bz": ["T008"], "mana": ["T008"] * 10,
                "deck": ["T002"] * 6},
               p1)
    st = {"base": _cid(e, "bz", 0, "T008"), "stop_after": len(modes)}
    return e, st


# ---------- 実挙動（登録形） ----------

def test_registered_cip_mode_destroy(rules):
    """dm26ex4-003: 出た時 mode 1 で闇ではないクリーチャーを
    すべて破壊する（自軍の自然獣も巻き込む。闇は残る）。"""
    e = _build(rules,
               {"hand": [CARD], "bz": ["T008", "T001"],
                "mana": ["T008"] * 10, "deck": ["T002"] * 6},
               {"bz": ["T001", "T008"], "deck": ["T002"] * 6})
    st = {"base": _cid(e, "bz", 0, "T008"), "stop_after": 1}
    _drive(e, _hook(st, [1]))
    assert st.get("played") and st.get("modes_seen") == 1
    assert CARD in _defns(e, "bz", 0)
    assert "T001" in _defns(e, "graveyard", 0)   # 自軍の自然獣も破壊
    assert "T001" in _defns(e, "graveyard", 1)   # 相手の自然獣も破壊
    assert "T001" not in _defns(e, "bz", 0)
    assert "T001" not in _defns(e, "bz", 1)
    assert "T008" in _defns(e, "bz", 1)          # 闇獣は残る


def test_registered_shield_leave_break_mode_discard(rules):
    """dm26ex4-003: EXライフシールドがブレイクで離れる →
    離脱誘発 mode 0 で相手は闇ではない手札をすべて捨てる。"""
    e, st = _setup_played(rules,
                          {"hand": [BREAK_SPELL, "T001", "T008"],
                           "mana": ["T008"] * 3, "deck": ["T002"] * 6},
                          modes=[2, 0])
    _drive(e, _hook(st, [2, 0], break_shield="ex"))
    assert st.get("cast") and st.get("broke") and st.get("modes_seen") == 2
    assert CARD in _defns(e, "bz", 0)            # 本体は場に残る
    assert "T001" not in _defns(e, "hand", 1)    # 自然は捨てられた
    assert "T008" in _defns(e, "hand", 1)        # 闇は残る
    assert "T001" in _defns(e, "graveyard", 1)


def test_registered_normal_shield_break_does_not_fire(rules):
    """dm26ex4-003: 普通のシールドが割れても離脱誘発は発火しない。"""
    e, st = _setup_played(rules,
                          {"hand": [BREAK_SPELL, "T001"],
                           "mana": ["T008"] * 3, "deck": ["T002"] * 6},
                          modes=[2])
    _drive(e, _hook(st, [2], break_shield="normal"))
    assert st.get("cast") and st.get("broke")
    assert st.get("modes_seen") == 1             # CIP の1回だけ
    assert _exlife_shield(e, 0) is not None      # EXライフシールドは残存
