"""再変換ラウンド356（第321弾 trigger_when_unblocked）の記録テスト。

- 新規登録2件: dm19-050 大鉄漢シルバスターズ /
  dm19-069 食いしん坊チャロック。
- alias 畳み込み0件（両行とも partial に aliases 記録は
  無く、id は提出前に real / proto / converted のいずれにも
  無いことを確認済み）。stale クリーンアップ0件・
  差し戻し0件。
- 対象2行は gaps = [trigger_when_unblocked] のため reopen で
  外してから submit（reopen の出力は対象2件ちょうど）。
- converted 10,264→10,266 / rejects 2,053→2,051、
  canonical 重なり0・漏れ0。trigger_when_unblocked は
  ファミリーがこの2件だけだったため完全に解消。

登録形は第321弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし）:
- 形A（050）: trigger {event: attack_end, subject: self,
  target: player, blocked: false} → may [draw 1]。
- 形B（069）: 同じ when → may [move {zone: deck,
  from_top: 1} to mana, reason: put]。
keywords は両件とも [dynamo]。

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

GAP = "trigger_when_unblocked"

TRIGGER_UNBLOCKED_DRAW = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]}
TRIGGER_UNBLOCKED_MANA = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "move",
         "select": {"zone": "deck", "owner": "you", "from_top": 1},
         "to": "mana", "reason": "put"}]}]}

DYNAMO_TEXT = ("ダイナモ(バトルが始まる時、あるいはこの"
               "クリーチャーで攻撃できる時、このクリーチャーを"
               "タップしてもよい。そうした場合、そのターンの"
               "終わりまで、このクリーチャーのパワーと能力を"
               "バトルゾーンにある自分の他のダイナモ１体に加える)")

FORMS = {
    "dm19-050": {"name": "大鉄漢シルバスターズ",
                 "types": ["creature"], "civs": ["water"],
                 "cost": 3, "power": 1000,
                 "races": ["グレートメカオー", "ダイナモ"],
                 "mana": 1, "keywords": ["dynamo"],
                 "text": DYNAMO_TEXT + "\nこのクリーチャーが相手"
                         "プレイヤーを攻撃してブロックされなかった時、"
                         "カードを１枚引いてもよい。",
                 "abilities": [TRIGGER_UNBLOCKED_DRAW],
                 "proto": "T984"},
    "dm19-069": {"name": "食いしん坊チャロック",
                 "types": ["creature"], "civs": ["nature"],
                 "cost": 3, "power": 2000,
                 "races": ["ドリームメイト", "ダイナモ"],
                 "mana": 1, "keywords": ["dynamo"],
                 "text": DYNAMO_TEXT + "\nこのクリーチャーが相手"
                         "プレイヤーを攻撃してブロックされなかった時、"
                         "自分の山札の上から１枚目を自分のマナゾーンに"
                         "置いてもよい。",
                 "abilities": [TRIGGER_UNBLOCKED_MANA],
                 "proto": "T985"},
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


def test_round356_disposition():
    rej = _reject_rows()
    assert len(rej) == 2051
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10266
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, spec in FORMS.items():
        assert tid in ids and tid not in rej, tid
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
        assert not (c.get("source") or {}).get("aliases"), tid
        for k in ("name", "types", "civs", "cost", "power", "races",
                  "mana", "text", "abilities"):
            assert c.get(k) == spec[k], (tid, k)
        assert c.get("keywords") == spec.get("keywords"), tid
        assert len(c["abilities"]) == len(spec["abilities"]), tid
        d = parse_card(c, TABLES)
        proto = parse_card(proto_card(spec["proto"]), TABLES)
        assert d.abilities == proto.abilities, tid
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _attack_player(e, attacker_defn):
    for _ in range(20):
        d = e.advance()
        assert d is not None, "game ended before attack"
        if d["kind"] in ("attack", "declare_attack"):
            keys = _keys(d)
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker_defn}:player"]
            if hit:
                e.answer([hit[0]])
                return
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d.get("min", 0))))
    raise AssertionError("attack decision did not appear")


def _drive_combat(e, block=False, max_steps=200):
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return d
        keys = _keys(d)
        if d["kind"] in ("block", "declare_block"):
            guard = next((i for i, k in enumerate(keys)
                          if k != "no_block"), None)
            if block and guard is not None:
                e.answer([guard])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("combat did not settle")


def test_registered_050_unblocked_draws(rules):
    """登録形A: dm19-050 がブロックされずに攻撃すると、
    攻撃の終わりに1枚引く。"""
    e = _build(rules, {"bz": ["dm19-050"]}, {})
    e.s.cards[_bz(e, 0, "dm19-050")].entered_turn = -1
    before = len(e.zlist("hand", 0))
    _attack_player(e, "dm19-050")
    _drive_combat(e)
    assert len(e.zlist("hand", 0)) == before + 1


def test_registered_050_blocked_no_draw(rules):
    """登録形Aの判別: ブロックされた攻撃では引かない。"""
    e = _build(rules, {"bz": ["dm19-050"]}, {"bz": ["T004"]})
    e.s.cards[_bz(e, 0, "dm19-050")].entered_turn = -1
    before = len(e.zlist("hand", 0))
    _attack_player(e, "dm19-050")
    _drive_combat(e, block=True)
    assert len(e.zlist("hand", 0)) == before


def test_registered_069_unblocked_mana_charge(rules):
    """登録形B: dm19-069 がブロックされずに攻撃すると、
    攻撃の終わりに山札の上1枚をマナゾーンに置く。"""
    e = _build(rules, {"bz": ["dm19-069"]}, {})
    e.s.cards[_bz(e, 0, "dm19-069")].entered_turn = -1
    before = len(e.s.zones["mana"][0])
    deck_before = len(e.zlist("deck", 0))
    _attack_player(e, "dm19-069")
    _drive_combat(e)
    assert len(e.s.zones["mana"][0]) == before + 1
    assert len(e.zlist("deck", 0)) == deck_before - 1


def test_registered_069_blocked_no_mana_charge(rules):
    """登録形Bの判別: ブロックされた攻撃では置かない。"""
    e = _build(rules, {"bz": ["dm19-069"]}, {"bz": ["T004"]})
    e.s.cards[_bz(e, 0, "dm19-069")].entered_turn = -1
    before = len(e.s.zones["mana"][0])
    _attack_player(e, "dm19-069")
    _drive_combat(e, block=True)
    assert len(e.s.zones["mana"][0]) == before
