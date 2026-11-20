"""再変換ラウンド342（第307弾 exlife_shield_left_any）の記録テスト。

- 新規登録1件: dm26ex2-mc009 不敬合成王 ロマティックダム・
  アルキング。alias 畳み込み・stale クリーンアップ・差し戻し
  は0件（alias 3件は登録カードの source.aliases への記録で、
  いずれも reject 行は元々無し）。
- 正本判定は identity の実データ照合による: canon_id は
  dm26ex2-mc009 自身＝独立正本、alias 3件（dm22ex2-8a /
  dm22ex2-8b / dm22ex2-s15）の canon_id はいずれも
  dm26ex2-mc009 で、aliases_for とも一致する。
- converted 10,244→10,245 / rejects 2,077→2,076、
  canonical 重なり0・漏れ0。exlife_shield_left_any は解消。
  （alias∩rejects の既存 stale 9件は本ラウンド対象外で残る。）

登録形は第307弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし、abilities は [G・ストライク
常在型, 誘発] の2件ちょうど）:
- partial そのもの＋誘発 {event: move, from: shield,
  subject: {owner: you, exlife_of: any}}（第307弾で
  when.subject の exlife_of に "any" を追加。移動記録の
  LKI が保持する移動前の紐付けの有無だけを見る）。
  text は reject 行の正式本文（partial の text と同一）。
- ラウンド328で提出後に登録を取り消した条項がこれで解けた。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。進化GV・Ω の3ゾーン重ねは第293弾の形、シールド
ブレイクの駆動役は第291弾プロト T850、進化元は第307弾
プロト T946 を使う。
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

CARD = "dm26ex2-mc009"
ALIASES = ["dm22ex2-8a", "dm22ex2-8b", "dm22ex2-s15"]
OFFICIAL_TEXT = (
    "進化GV・Ω：自分の墓地、マナゾーン、バトルゾーンからクリーチャーを１体ずつ選び、このクリーチャーをその上に重ねつつ出す。\n"
    "エクストラEXライフ（このクリーチャーを出す時、自分の山札の上から２枚をシールド化する。このクリーチャーが離れる時、かわりにそのシールドのうち１つを墓地に置く）\n"
    "ワールド・ブレイカー\n"
    "自分の「EXライフ」シールドが離れた時、このクリーチャーの下にあるカードを１枚、墓地に置く。それが進化ではないクリーチャーなら、自分の墓地から出す。\n"
    "自分のシールドゾーンにあるディスペクター・カードすべてに「G・ストライク」を与える。"
)

STATIC = {"kind": "static",
          "affects": {"zone": "shield", "owner": "you",
                      "filter": {"race_has": "ディスペクター"}},
          "mod": {"grant": ["g_strike"]}}

TRIGGER = {"kind": "trigger",
           "when": {"event": "move", "from": "shield",
                    "subject": {"owner": "you", "exlife_of": "any"}},
           "effect": [
               {"op": "move",
                "select": {"under_of": "self", "count": 1},
                "to": "graveyard", "reason": "put", "as": "buried"},
               {"op": "if",
                "cond": {"exists": {"ref": "buried",
                                    "filter": {"types": ["creature"],
                                               "not_types": ["evolution"]}}},
                "then": [{"op": "play_free",
                          "select": {"ref": "buried"}}]},
           ]}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round342_disposition():
    rej = _reject_rows()
    assert len(rej) == 2076
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10245
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv(CARD)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert CARD not in rej               # 漏れ0
    # alias は登録カードの source.aliases への記録のみ。
    # 独立エントリにも rejects にも無い
    assert (c.get("source") or {}).get("aliases") == ALIASES
    for a in ALIASES:
        assert a not in ids and a not in rej
    assert c["types"] == ["creature", "evolution"]
    assert c["keywords"] == ["extra_ex_life", "world_breaker"]
    assert [z.get("zone") for z in c["evolve_from"]] == \
        ["graveyard", "mana", "bz"]
    assert c["cost"] == 9 and c["power"] == 25000
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    assert c["abilities"] == [STATIC, TRIGGER]
    assert c["text"] == OFFICIAL_TEXT
    d = parse_card(c, TABLES)
    assert d.types == ["creature", "evolution"]
    assert d.keywords == ["extra_ex_life", "world_breaker"]
    trigs = [a for a in d.abilities if a.get("kind") == "trigger"]
    assert trigs == [TRIGGER]
    statics = [a for a in d.abilities if a.get("kind") == "static"]
    # world_breaker の展開分＋G・ストライク付与の2件
    assert len(statics) == 2
    assert STATIC in statics
    # exlife_shield_left_any は解消
    holders = {rid for rid, r in rej.items()
               if "exlife_shield_left_any" in (r.get("gaps") or [])}
    assert holders == set(), holders


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

MANA = ["T946", "T030", "T030", "T034", "T008",
        "T001", "T010", "T034", "T008", "T030"]


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
                and e.s.cards[c].controller == p)


def _tops(e, p):
    return [c for c in e.zlist("bz", p)
            if e.s.cards[c].controller == p
            and e.s.cards[c].top_of < 0]


def _linked_shield(e, p, creature_cid):
    for c in e.zlist("shield", p):
        lo = e.s.cards[c].exlife_of
        if lo is not None and lo[0] == creature_cid:
            return c
    return None


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
        if d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))


def _driver(st, base_cids, shield_pick):
    """CARD を進化GVで出し、相手が T850 で shield_pick の
    シールドを割るまで進めるハンドラ。"""
    def handler(e, d):
        p = d["player"]
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and p == 0 and not st.get("played"):
            k = next((k for k in keys if k.startswith(f"play:{CARD}")),
                     None)
            if k is not None:
                st["played"] = True
                return [keys.index(k)]
        if d["kind"] == "main" and p == 1 and st.get("played") \
                and not st.get("cast"):
            if "play:T850" in keys:
                st["cast"] = True
                return [keys.index("play:T850")]
        if d["kind"] == "choose_evo_source":
            for i, o in enumerate(d["options"]):
                if o.get("cid") in base_cids:
                    return [i]
            return list(range(d["min"]))
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [0]
        if d["kind"] == "choose_shields" and not st.get("picked"):
            want = shield_pick(e)
            if want is not None:
                for i, o in enumerate(d["options"]):
                    if o.get("cid") == want:
                        st["picked"] = want
                        return [i]
        if d["kind"] in ("block", "declare_block") \
                and "no_block" in keys:
            return [keys.index("no_block")]
        if d["kind"] == "choose_cards":
            return list(range(d["min"]))
        return None
    return handler


def _setup_game(rules):
    e = _build(rules,
               {"hand": [CARD], "graveyard": ["T946"], "bz": ["T946"],
                "mana": MANA, "deck": ["T002"] * 8},
               {"hand": ["T850"], "mana": ["T082"],
                "deck": ["T002"] * 8})
    bases = {_cid(e, "graveyard", 0, "T946"),
             _cid(e, "mana", 0, "T946"),
             _cid(e, "bz", 0, "T946")}
    return e, bases


# ---------- 実挙動（登録形） ----------

def test_registered_fires_on_own_exlife_shield(rules):
    """dm26ex2-mc009: 自分のEXライフシールドが離れると、下の
    カード1枚が墓地経由で場に戻る。"""
    e, bases = _setup_game(rules)
    st = {}

    def pick(e):
        w = _cid(e, "bz", 0, CARD)
        return _linked_shield(e, 0, w)

    def done():
        if CARD not in _defns(e, "bz", 0):
            return False
        w = e.s.cards[_cid(e, "bz", 0, CARD)]
        tops = _tops(e, 0)
        return len(w.under) == 2 and len(tops) == 2

    _run(e, _driver(st, bases, pick), done=done)
    assert st.get("played") and st.get("cast") and st.get("picked")
    w = e.s.cards[_cid(e, "bz", 0, CARD)]
    # 進化GV: 墓地・マナ・バトルゾーンから1体ずつ重なっていた
    # （誘発で1枚外れて残り2枚）
    assert len(w.under) == 2
    assert set(w.under) <= bases
    # 外れた進化元（進化でないクリーチャー）は墓地から場に戻った
    returned = [c for c in _tops(e, 0)
                if e.s.cards[c].defn == "T946"]
    assert len(returned) == 1
    assert "T946" not in _defns(e, "graveyard", 0)
    # 割れたEXライフシールドは手札へ
    assert e.s.cards[st["picked"]].zone == "hand"


def test_registered_normal_shield_does_not_fire(rules):
    """dm26ex2-mc009: EXライフでない普通のシールドが離れても
    発火しない。"""
    e, bases = _setup_game(rules)
    st = {}

    def pick(e):
        for c in e.zlist("shield", 0):
            if e.s.cards[c].exlife_of is None:
                return c
        return None

    def done():
        return bool(st.get("picked")) \
            and e.s.cards[st["picked"]].zone == "hand" \
            and e.s.turn >= 3

    _run(e, _driver(st, bases, pick), done=done)
    assert st.get("played") and st.get("cast") and st.get("picked")
    w = e.s.cards[_cid(e, "bz", 0, CARD)]
    assert len(w.under) == 3               # 下のカードは動かない
    assert set(w.under) == bases
    assert len(_tops(e, 0)) == 1           # 場に戻るカードは無い
    assert "T946" not in _defns(e, "graveyard", 0)
