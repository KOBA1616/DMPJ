"""再変換ラウンド341（第306弾 same_name_sweep）の記録テスト。

- 新規登録1件: dm17-004 エクスプロード・カタストロフィー。
  alias 畳み込み・stale クリーンアップ・差し戻しは0件。
- 正本判定は identity の実データ照合による: canon_id は
  dm17-004 自身＝独立正本、aliases_for は空（alias なし）。
- converted 10,243→10,244 / rejects 2,078→2,077、
  canonical 重なり0・漏れ0。same_name_sweep は解消。
  evolution_cross_gear のギャップ名自体は他ギャップ併記の
  dmc66-034（dynamic_name_reference_filter）/ dm17-s04
  （reveal_and_cast_free）の2行に残る。

登録形は第306弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし、abilities は [静的型, 一掃誘発]
の2件ちょうど）:
- partial ＋ types [cross_gear, evolution] ＋ evolve_from
  {civs: [darkness, fire]} ＋ 一掃誘発（battle_win ＋
  subject: crossed、敗者の名前は {name: {name_of:
  event.opponent}}、手札 look は choose {count: all} の束縛、
  一掃は複数ゾーン select ＋ count: all の move to deck
  position: bottom）。text は reject 行の正式本文。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。相手側の同名カード等は第306弾プロト（T940–T944）を
使い、ギアだけ登録カード dm17-004 に替える。
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

GEAR = "dm17-004"
OFFICIAL_TEXT = (
    "このクロスギアはマナゾーンにタップして置かれる。\n"
    "進化-自分の闇または火のクロスギア１枚の上に置く。\n"
    "これをクロスしたクリーチャーは、タップされていないクリーチャーを攻撃できる。\n"
    "これをクロスしたクリーチャーがバトルに勝った時、相手の手札を見る。"
    "相手は自分自身の手札、マナゾーン、墓地、バトルゾーンから、"
    "このバトルで負けたクリーチャーと同じ名前の自分自身のカードをすべて山札の一番下に置く。"
)

STATIC = {"kind": "static", "affects": "crossed",
          "mod": {"allow": [{"action": "attack_creature",
                             "other": {"tapped": False}}]}}

SWEEP_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "battle_win", "subject": "crossed"},
    "effect": [
        {"op": "choose",
         "select": {"zone": "hand", "owner": "opp", "count": "all"},
         "as": "seen"},
        {"op": "move",
         "select": {"zone": ["hand", "mana", "graveyard", "bz"],
                    "owner": "opp",
                    "filter": {"name": {"name_of": "event.opponent"}},
                    "count": "all"},
         "to": "deck", "position": "bottom", "reason": "put"},
    ],
}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round341_disposition():
    rej = _reject_rows()
    assert len(rej) == 2077
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10244
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv(GEAR)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert GEAR not in rej               # 漏れ0
    assert (c.get("source") or {}).get("aliases") is None
    assert c["types"] == ["cross_gear", "evolution"]
    assert c["evolve_from"] == {"civs": ["darkness", "fire"]}
    assert c["civs"] == ["darkness", "fire"]
    assert c["cost"] == 3 and c["mana"] == 1
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    assert c["abilities"] == [STATIC, SWEEP_TRIGGER]
    assert c["text"] == OFFICIAL_TEXT
    d = parse_card(c, TABLES)
    assert d.types == ["cross_gear", "evolution"]
    # same_name_sweep は解消。evolution_cross_gear は併記2行のみ
    sweep = {rid for rid, r in rej.items()
             if "same_name_sweep" in (r.get("gaps") or [])}
    assert sweep == set(), sweep
    evo = {rid for rid, r in rej.items()
           if "evolution_cross_gear" in (r.get("gaps") or [])}
    assert evo == {"dmc66-034", "dm17-s04"}, evo


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

MANA = ["T008", "T034", "T001"]          # dm17-004（コスト3・闇/火）


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


def _gear_handler(attack_key):
    st = {"played": False, "crossed": False, "attacked": False}

    def handler(e, d):
        p = d["player"]
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and p == 0:
            if not st["played"] and f"play:{GEAR}" in keys:
                st["played"] = True
                return [keys.index(f"play:{GEAR}")]
            if st["played"] and not st["crossed"]:
                ck = [k for k in keys if k.startswith(f"cross:{GEAR}:")]
                if ck:
                    st["crossed"] = True
                    return [keys.index(ck[0])]
        if d["kind"] == "choose_evo_source":
            for i, o in enumerate(d["options"]):
                if o.get("defn") == "T940":
                    return [i]
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [0]
        if d["kind"] in ("block", "declare_block") and "no_block" in keys:
            return [keys.index("no_block")]
        if d["kind"] in ("attack", "declare_attack") \
                and attack_key and not st["attacked"]:
            if attack_key in keys:
                st["attacked"] = True
                return [keys.index(attack_key)]
        if d["kind"] == "choose_cards":
            return list(range(d["min"]))
        return None

    return handler, st


def _opp_full():
    return {"bz": ["T942", "T943"], "hand": ["T942", "T943"],
            "mana": ["T942", "T943"], "graveyard": ["T942"],
            "deck": ["T002"] * 6}


# ---------- 実挙動（登録形） ----------

def test_registered_sweep_on_battle_win(rules):
    """dm17-004: クロスした獣がバトルに勝つと同名を全て山札の下へ。"""
    e = _build(rules, {"bz": ["T940", "T941"], "hand": [GEAR],
                       "mana": MANA, "deck": ["T002"] * 6},
               _opp_full())
    host = _cid(e, "bz", 0, "T941")
    gear = _cid(e, "hand", 0, GEAR)
    handler, st = _gear_handler("attack:T941:T942")
    _run(e, handler,
         done=lambda: _defns(e, "deck", 1).count("T942") == 4)
    # タップされていないクリーチャーを攻撃できた（ギアの常在型）
    assert st["attacked"] and st["crossed"]
    assert e.s.cards[gear].crossed[0] == host
    # 相手の同名カードは4ゾーンからすべて消えた
    for zone in ("hand", "mana", "graveyard", "bz"):
        assert "T942" not in _defns(e, zone, 1), zone
    # 別名カードは残る
    assert "T943" in _defns(e, "bz", 1)
    assert "T943" in _defns(e, "hand", 1)
    assert "T943" in _defns(e, "mana", 1)
    # 行き先は相手の山札の一番下（末尾4枚）。
    # 内訳: 手札1・マナ1・墓地1（元から）＋敗者自身（墓地経由）= 4枚
    deck = _defns(e, "deck", 1)
    assert deck.count("T942") == 4
    assert deck[-4:] == ["T942"] * 4
    # 勝った宿主は場に残る
    assert "T941" in _defns(e, "bz", 0)


def test_registered_no_sweep_on_battle_lose(rules):
    """dm17-004: 宿主がバトルに負けた時は一掃しない。"""
    opp = _opp_full()
    opp["bz"] = ["T944", "T943"]
    e = _build(rules, {"bz": ["T940", "T941"], "hand": [GEAR],
                       "mana": MANA, "deck": ["T002"] * 6}, opp)
    handler, st = _gear_handler("attack:T941:T944")
    _run(e, handler,
         done=lambda: "T941" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    # 宿主が負けたので一掃は起きない（相手の同名は各ゾーンに残る）
    assert "T942" in _defns(e, "hand", 1)
    assert "T942" in _defns(e, "mana", 1)
    assert "T942" in _defns(e, "graveyard", 1)
    assert "T942" not in _defns(e, "deck", 1)
