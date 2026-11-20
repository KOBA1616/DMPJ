"""再変換ラウンド354（第319弾 destroy_self_after_attacking）の記録テスト。

- 新規登録2件: dm22rp1-038 レター＝ジェンゲガー /
  dm22rp2x-061 ディッシュ＝ウィッシュ。
- alias は登録エントリの source.aliases への記録のみ
  （038: promoy21-052、061: dm22rp2-061 / dm22rp2-20a /
  dm22rp2x-20a / promoy21-069。alias 側の reject 行は
  元々無かった）。正本判定は identity の canon_id
  実測で2件とも自 ID。
- stale クリーンアップ0件・差し戻し0件。
- 対象2行は gaps = [destroy_self_after_attacking] のため
  reopen で外してから submit（reopen の出力は対象2件
  ちょうどだった）。
- converted 10,260→10,262 / rejects 2,057→2,055、
  canonical 重なり0・漏れ0。destroy_self_after_attacking
  はファミリーがこの2件だけだったため完全に解消。

登録形は第319弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし）: 自壊条項は旧近似形
（when: turn_end ＋ during_attack、発火しない死に形）
ではなく、攻撃（061 はブロックも）誘発 →
delayed_trigger {attack_end} の確立形。
dm22rp1-038 の残りの条項（自分のターンの終わりに
山札の上から1枚目を墓地に置き、それがアビスなら
1枚引く）は本ラウンドで構築した: turn_end 誘発
{player: you} ＋ move {from_top: 1, as: milled} ＋
if {count {ref: milled, filter: race_has アビス}
== 1} → draw 1（判定は dm23rp2x-037 の登録先例と
同形）。提出前に全アビス／全非アビス山札で実挙動を
検証済みで、本ファイルでも登録カード自身で固定する。

実挙動は登録カード自身で固定する。ドライバは
scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

GAP = "destroy_self_after_attacking"

DESTROY_SELF = {"op": "destroy", "select": {"ref": "self"}}
TRIGGER_A = {"kind": "trigger",
             "when": {"event": "attack", "subject": "self"},
             "effect": [{"op": "delayed_trigger",
                         "when": {"event": "attack_end",
                                  "subject": "self"},
                         "duration": "during_attack",
                         "effect": [DESTROY_SELF]}]}
TRIGGER_B_BLOCK = {"kind": "trigger",
                   "when": {"event": "block", "subject": "self"},
                   "effect": [{"op": "delayed_trigger",
                               "when": {"event": "attack_end",
                                        "target": "self"},
                               "duration": "during_attack",
                               "effect": [DESTROY_SELF]}]}
TURN_END_038 = {"kind": "trigger",
                "when": {"event": "turn_end", "player": "you"},
                "effect": [
                    {"op": "move",
                     "select": {"zone": "deck", "owner": "you",
                                "from_top": 1, "count": "all"},
                     "to": "graveyard", "reason": "put",
                     "as": "milled"},
                    {"op": "if",
                     "cond": {"cmp": [{"count": {"ref": "milled",
                                                 "filter": {"race_has": "アビス"}}},
                                      "==", 1]},
                     "then": [{"op": "draw", "count": 1}]}]}

TEXT_038 = ("ブロッカー（このクリーチャーをタップして、相手クリーチャーの攻撃先を"
            "このクリーチャーに変更してもよい）\n"
            "このクリーチャーが攻撃する時、攻撃の後、このクリーチャーを破壊する。\n"
            "自分のターンの終わりに、自分の山札の上から１枚目を墓地に置く。"
            "それがアビスなら、カードを１枚引く。")
TEXT_061 = ("S・トリガー（このクリーチャーをシールドゾーンから手札に加える時、"
            "コストを支払わずにすぐ召喚してもよい）\n"
            "ブロッカー（このクリーチャーをタップして、相手クリーチャーの攻撃先を"
            "このクリーチャーに変更してもよい）\n"
            "このクリーチャーが攻撃する時またはブロックした時、その攻撃の後、"
            "このクリーチャーを破壊する。")

FORMS = {
    "dm22rp1-038": {"name": "レター＝ジェンゲガー",
                    "types": ["creature"], "civs": ["darkness"],
                    "cost": 3, "power": 2000,
                    "races": ["アビスロイヤル"], "mana": 1,
                    "text": TEXT_038, "keywords": ["blocker"],
                    "abilities": [TRIGGER_A, TURN_END_038],
                    "aliases": ["promoy21-052"], "proto": "T979"},
    "dm22rp2x-061": {"name": "ディッシュ＝ウィッシュ",
                     "types": ["creature"], "civs": ["darkness"],
                     "cost": 2, "power": 5000,
                     "races": ["アビスロイヤル"], "mana": 1,
                     "text": TEXT_061,
                     "keywords": ["s_trigger", "blocker"],
                     "abilities": [TRIGGER_A, TRIGGER_B_BLOCK],
                     "aliases": ["dm22rp2-061", "dm22rp2-20a",
                                 "dm22rp2x-20a", "promoy21-069"],
                     "proto": "T980"},
}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _unsup(r):
    return [u.get("need") if isinstance(u, dict) else u
            for u in (((r.get("partial") or {}).get("source") or {})
                      .get("unsupported") or [])]


def test_round354_disposition():
    rej = _reject_rows()
    assert len(rej) == 2055
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10262
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, spec in FORMS.items():
        # 漏れ0: 正本は登録され reject 行に残っていない
        assert tid in ids and tid not in rej, tid
        for a in spec["aliases"]:
            assert a not in ids and a not in rej, a
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
        assert (c.get("source") or {}).get("aliases") == spec["aliases"], tid
        # 登録形の完全一致（連結・merge_split 由来の混入なし）
        for k in ("name", "types", "civs", "cost", "power", "races",
                  "mana", "text", "keywords", "abilities"):
            assert c.get(k) == spec[k], (tid, k)
        assert len(c["abilities"]) == 2, tid
        # 自壊誘発は対応プロトの abilities と完全一致
        d = parse_card(c, TABLES)
        proto = parse_card(proto_card(spec["proto"]), TABLES)
        for ab in proto.abilities:
            assert ab in d.abilities, tid
    # destroy_self_after_attacking は完全に解消（ファミリーはこの2件だけ）
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1, deck_exact=None):
    spec = {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
            "deck_size": 20}
    if deck_exact is not None:
        spec["deck_exact"] = deck_exact
    return scenario.build(rules, spec)


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive(e, attacker=None, blocker=None, stop_when=None, limit=1500):
    """第319弾本体と同じ汎用ドライバ。attacker（defn）で
    プレイヤーを攻撃し、blocker（defn）のブロック肢が
    現れたらブロックする。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(limit):
        if stop_when is not None and stop_when(e):
            break
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if blocker and k.startswith(f"bz:{blocker}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_registered_038_attack_destroys_self(rules):
    """登録形A: dm22rp1-038 が攻撃すると、攻撃の後に破壊される。"""
    e = _build(rules, {"bz": ["dm22rp1-038"]}, {})
    st = _drive(e, attacker="dm22rp1-038")
    assert st["attacked"]
    assert "dm22rp1-038" in _defns(e, "graveyard", 0)
    assert "dm22rp1-038" not in _defns(e, "bz", 0)


def test_registered_061_attack_destroys_self(rules):
    """登録形B（攻撃）: dm22rp2x-061 が攻撃すると、攻撃の後に破壊される。"""
    e = _build(rules, {"bz": ["dm22rp2x-061"]}, {})
    st = _drive(e, attacker="dm22rp2x-061")
    assert st["attacked"]
    assert "dm22rp2x-061" in _defns(e, "graveyard", 0)
    assert "dm22rp2x-061" not in _defns(e, "bz", 0)


def test_registered_061_block_destroys_self(rules):
    """登録形B（ブロック）: dm22rp2x-061 がブロックし、バトルに
    勝っても、その攻撃の後に破壊される。"""
    e = _build(rules, {"bz": ["dm22rp2x-061"]}, {"bz": ["T001"]})
    st = _drive(e, attacker="T001", blocker="dm22rp2x-061",
                stop_when=lambda e: "dm22rp2x-061" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    assert "T001" in _defns(e, "graveyard", 1)   # 攻撃側はバトルで落ちる
    assert "dm22rp2x-061" in _defns(e, "graveyard", 0)
    assert "dm22rp2x-061" not in _defns(e, "bz", 0)


def _turn_boundary_deltas(e):
    """ターン1最後の決定時点 → ターン2最初の決定時点の
    (手札, 山札, 墓地) デルタ。ターン終了条項には選択が
    無いので、境界をまたぐ変化はその条項の効果そのもの。"""
    snaps = []
    for _ in range(800):
        d = e.advance()
        assert d is not None, "game ended"
        snaps.append((e.s.turn, (len(e.zlist("hand", 0)),
                                  len(e.zlist("deck", 0)),
                                  _defns(e, "graveyard", 0))))
        if e.s.turn >= 2:
            break
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
    last1 = [s for s in snaps if s[0] == 1][-1][1]
    first2 = [s for s in snaps if s[0] == 2][0][1]
    return last1, first2


def test_registered_038_turn_end_mills_abyss_and_draws(rules):
    """登録形（ターン終了条項・アビス）: 山札が全てアビスなら、
    ターンの終わりに1枚墓地に置き、1枚引く。"""
    e = _build(rules,
               {"bz": ["dm22rp1-038"],
                "deck": ["dm22rp1-038"] * 3},
               {}, deck_exact=[True, False])
    (h1, dk1, _), (h2, dk2, gy2) = _turn_boundary_deltas(e)
    assert gy2 == ["dm22rp1-038"]        # mill した1枚だけが墓地へ
    assert h2 - h1 == 1                  # アビスなので1枚引く
    assert dk1 - dk2 == 2                # 山札は mill 1 + draw 1


def test_registered_038_turn_end_mills_non_abyss_no_draw(rules):
    """登録形（ターン終了条項・非アビス）: 山札が非アビスなら、
    墓地に置くだけで引かない。"""
    e = _build(rules,
               {"bz": ["dm22rp1-038"], "deck": ["T002"] * 3},
               {}, deck_exact=[True, False])
    (h1, dk1, _), (h2, dk2, gy2) = _turn_boundary_deltas(e)
    assert gy2 == ["T002"]
    assert h2 - h1 == 0                  # 引かない
    assert dk1 - dk2 == 1                # 山札は mill 1 のみ
