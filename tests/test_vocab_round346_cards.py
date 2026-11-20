"""再変換ラウンド346（第311弾 reveal_and_cast_free）の記録テスト。

- 新規登録1件: dm17-s04 ネオウェーブ・カタストロフィー。
  alias 畳み込み・stale クリーンアップ・差し戻しは0件。
- 正本判定は identity の実データ照合による: canon_id は
  dm17-s04 自身＝独立正本、aliases_for は空（alias なし）。
- converted 10,249→10,250 / rejects 2,072→2,071、
  canonical 重なり0・漏れ0。reveal_and_cast_free は解消し、
  evolution_cross_gear の併記は dmc66-034 の1行だけが残る。
- reopen（evolution_cross_gear + reveal_and_cast_free）は
  対象1件だけを外した（dmc66-034 は相方
  dynamic_name_reference_filter が残るため外れない）。

登録形は第311弾の確立形 FORM と完全一致（submit の連結・
merge_split 由来の混入なし、abilities は [ブロッカー常在型,
攻撃誘発] の2件ちょうど）:
- partial のブロッカー常在型 ＋ types [cross_gear, evolution]
  ＋ evolve_from {civs: [light, water]} ＋ 攻撃誘発
  （choose {from_top: 3, look, count: all, reveal: true,
  as: pile} → choose {ref: pile, filter: {types: [spell],
  keyword: s_trigger}, count: all, up_to: true, as: casts}
  → repeat {over: casts} の play_free → move {ref: pile}
  を山札の一番下へ order: choose）。unsupported は除去。
- text は reject 行の正式本文（\\n 区切り）と同一。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。進化元・宿主・呪文役は第311弾プロト T959 / T001 /
T960 / T961 / T962 を使う。build の山札は deck spec の末尾が
一番上（第305弾の確認どおり）で、先攻1ターン目はドローしない
（500.6）ため束はターン1のまま検証できる。
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

TARGET = "dm17-s04"

TEXT = ("このクロスギアはマナゾーンにタップして置かれる。\n"
        "進化-自分の光または水のクロスギア１枚の上に置く。\n"
        "これをクロスしたクリーチャーは「ブロッカー」を得る。\n"
        "これをクロスしたクリーチャーが攻撃する時、自分の山札の上から３枚を表向きにする。"
        "その中から、「S・トリガー」付き呪文を好きなだけ選び、コストを支払わずに唱えてもよい。"
        "その後、唱えなかったカードを自分の山札の一番下に好きな順番で戻す。")

BLOCKER_STATIC = {"kind": "static", "affects": "crossed",
                  "mod": {"grant": ["blocker"]}}

ATTACK_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "crossed"},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "from_top": 3,
                    "look": True, "count": "all"},
         "reveal": True, "as": "pile"},
        {"op": "choose",
         "select": {"ref": "pile",
                    "filter": {"types": ["spell"], "keyword": "s_trigger"},
                    "count": "all", "up_to": True},
         "as": "casts"},
        {"op": "repeat", "over": "casts", "as": "it",
         "body": [{"op": "play_free", "select": {"ref": "it"}}]},
        {"op": "move",
         "select": {"ref": "pile", "zone": "deck", "count": "all"},
         "to": "deck", "position": "bottom", "order": "choose",
         "reason": "put"},
    ],
}

FORM = {"id": TARGET,
        "name": "ネオウェーブ・カタストロフィー",
        "types": ["cross_gear", "evolution"],
        "civs": ["light", "water"],
        "cost": 5, "mana": 1,
        "evolve_from": {"civs": ["light", "water"]},
        "text": TEXT,
        "abilities": [BLOCKER_STATIC, ATTACK_TRIGGER]}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round346_disposition():
    rej = _reject_rows()
    assert len(rej) == 2071
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10250
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv(TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert TARGET not in rej             # 漏れ0
    assert not (c.get("source") or {}).get("aliases")   # alias なし
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "mana",
              "evolve_from", "text", "abilities"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2      # [ブロッカー常在型, 攻撃誘発]
    assert not c.get("keywords")
    d = parse_card(c, TABLES)
    assert d.types == ["cross_gear", "evolution"]
    assert d.evolve_from == {"civs": ["light", "water"]}
    # reveal_and_cast_free は解消、evolution_cross_gear は
    # dmc66-034 の1行だけが残る
    rcf = {rid for rid, r in rej.items()
           if "reveal_and_cast_free" in (r.get("gaps") or [])}
    assert rcf == set(), rcf
    evo = {rid for rid, r in rej.items()
           if "evolution_cross_gear" in (r.get("gaps") or [])}
    assert evo == {"dmc66-034"}, evo


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

GEAR = TARGET
HOST = "T001"
MANA10 = ["T030"] * 5 + ["T010"] * 5
# 山札 spec は末尾が一番上: 上から T960 / T962 / T961
DECK_PILE = ["T002"] * 6 + ["T961", "T962", "T960"]


def _build(rules, deck=DECK_PILE):
    return scenario.build(
        rules, {"p0": {"bz": ["T959", HOST], "hand": [GEAR],
                       "mana": MANA10, "deck": deck},
                "p1": {"deck": ["T002"] * 6},
                "filler": "T001", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]


def _cid(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn
                and (zone != "bz" or e.s.cards[c].controller == p))


def _run(e, casts=None, order=None, cross=True, limit=600):
    """ギアを出し（任意でクロスし）宿主でプレイヤーを攻撃し、
    誘発を解決し切って相手の最初の決定まで進める。
    casts: 唱える呪文の defn 列。order: 山札の下へ戻す順序。"""
    st = {"played": False, "crossed": False, "attacked": False}
    kinds = []
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kinds.append(d["kind"])
        keys = [o["key"] for o in d["options"]]
        p = d["player"]
        if st["attacked"] and p == 1:
            return kinds
        if d["kind"] == "main" and p == 0:
            if not st["played"] and f"play:{GEAR}" in keys:
                e.answer([keys.index(f"play:{GEAR}")])
                st["played"] = True
                continue
            if cross and st["played"] and not st["crossed"]:
                ck = [k for k in keys if k.startswith(f"cross:{GEAR}:")]
                if ck:
                    e.answer([keys.index(ck[0])])
                    st["crossed"] = True
                    continue
        if d["kind"] == "choose_evo_source":
            idx = next(i for i, o in enumerate(d["options"])
                       if e.s.cards[o["cid"]].defn == "T959")
            e.answer([idx])
            continue
        if d["kind"] == "pay_mana":
            if not st.get("pay1"):
                # 1回目の支払いは水に寄せ、クロス（もう一度5マナ）の
                # ために光マナを残す（第311弾の発見）
                st["pay1"] = True
                idx = max(range(len(d["options"])),
                          key=lambda i: d["options"][i]["key"].count("T010"))
                e.answer([idx])
            else:
                e.answer([0])
            continue
        if d["kind"] in ("attack", "declare_attack") and p == 0 \
                and (st["crossed"] or not cross) and not st["attacked"]:
            ak = f"attack:{HOST}:player"
            if ak in keys:
                e.answer([keys.index(ak)])
                st["attacked"] = True
                continue
        if d["kind"] == "choose_cards":
            want = list(casts or [])
            ans = []
            for dn in want:
                ans += [i for i, o in enumerate(d["options"])
                        if e.s.cards[o["cid"]].defn == dn]
            e.answer(ans)
            continue
        if d["kind"] == "order_cards":
            want = list(order or [])
            used = set()
            ans = []
            for dn in want:
                idx = next(i for i, o in enumerate(d["options"])
                           if i not in used
                           and e.s.cards[o["cid"]].defn == dn)
                used.add(idx)
                ans.append(idx)
            e.answer(ans)
            continue
        if d["kind"] in ("block", "declare_block") and "no_block" in keys:
            e.answer([keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
            continue
        e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


# ---------- 実挙動（登録形） ----------

def test_registered_cast_both_strigger_spells(rules):
    """dm17-s04: 上3枚 [ST光, 通常, ST水] から ST 呪文2枚とも
    唱え、残り1枚は山札の一番下へ。宿主はブロッカーを得る。"""
    e = _build(rules)
    assert _defns(e, "deck", 0)[:3] == ["T960", "T962", "T961"]
    _run(e, casts=["T960", "T961"])
    assert sorted(_defns(e, "graveyard", 0)) == ["T960", "T961"]
    deck = _defns(e, "deck", 0)
    assert deck[-1] == "T962"
    assert "T962" not in _defns(e, "hand", 0)
    reveals = [r for r in e.s.pub if r["kind"] == "reveal"]
    assert len(reveals) == 3
    # 呪文の効果（マナ全アンタップ）が解けている
    assert not [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    host = _cid(e, "bz", 0, HOST)
    assert "blocker" in e.chars_ro(host)["keywords"]


def test_registered_cast_one_with_order(rules):
    """dm17-s04: 1枚だけ唱え、残り2枚は指定した順で山札の下へ。"""
    e = _build(rules)
    _run(e, casts=["T961"], order=["T962", "T960"])
    assert _defns(e, "graveyard", 0) == ["T961"]
    deck = _defns(e, "deck", 0)
    assert deck[-2:] == ["T962", "T960"]   # 指定順の最後が一番下


def test_registered_no_trigger_when_not_crossed(rules):
    """dm17-s04: クロスしていなければ攻撃しても誘発しない。"""
    e = _build(rules)
    _run(e, cross=False)
    assert _defns(e, "deck", 0)[:3] == ["T960", "T962", "T961"]
    assert _defns(e, "graveyard", 0) == []
    assert not [r for r in e.s.pub if r["kind"] == "reveal"]
