"""再変換ラウンド330（第295弾 スーパー／ウルトラ・シールド・プラス）の記録テスト。

- 新規登録2件: dmex06-010（形A: shield_plus each）/ dm28-s01（形A。
  ラウンド328で super_shield_plus だけで差し戻された行で、進化面＋
  W・ブレイカーは銀行済みだった）。
- stale 解消1件: dmx19-s06（形B）は real.yaml に手変換済みだった
  （ウルトラシールド・プラスを modal＋put_under で表現、koba 確認
  2026-10-28）ため converted へは登録せず、reject 行の除去のみ。
  converted との二重登録はしない（ラウンド200の Fiona 教訓）。
- 差し戻し0件。ラウンド直後: converted 10,213 / rejects 2,112、
  重なり0・漏れ0。super_shield_plus は rejects に残らない（ファミリー解消）。

プロトテスト（test_vocab_pilot295.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが
汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402


def setup(rules, p0, p1=None, filler="T002", seed=1, deck_size=20):
    """conftest の setup と同じ薄い包み（tests.conftest は import しない）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

NEW = ["dmex06-010", "dm28-s01"]
CIP_ADD = {"kind": "trigger", "when": {"event": "move", "to": "bz",
                                       "subject": "self"},
           "effect": [{"op": "may",
                       "body": [{"op": "shield_plus", "each": True}]}]}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round330_disposition():
    rej = _reject_rows()
    for cid in NEW:
        c = _conv(cid)
        assert c is not None, cid                      # 新規登録された
        assert cid not in rej, cid                     # rejects に残らない
        assert "unsupported" not in (c.get("source") or {}), cid
        d = parse_card(c, TABLES)                      # 登録形が parse できる
        assert CIP_ADD in d.abilities, cid             # 第295弾の条項が1つだけ
        assert len([a for a in d.abilities
                    if a.get("kind") == "trigger"]) == 1, cid
    # dm28-s01 は進化面（第293弾形A）が銀行済みのまま効く
    d = parse_card(_conv("dm28-s01"), TABLES)
    assert d.face(None).evolve_zone == "mana"
    # dmx19-s06 は real.yaml のみの stale 解消（converted に二重登録しない）
    assert _conv("dmx19-s06") is None
    assert "dmx19-s06" not in rej
    # ファミリー解消: super_shield_plus を含む行は rejects に残らない
    assert not [r["id"] for r in rej.values()
                if "super_shield_plus" in (r.get("gaps") or [])]


# ---------- 実挙動 ----------

def _drive(e, done, cid, steps=300):
    """done(e) が真になるまで: cid のプレイを選び、yes_no は yes、
    それ以外は先頭 min 件で答える（第295弾テストと同じ作法）。"""
    for _ in range(steps):
        if done(e):
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif kind not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys)
                   if cid in k and not k.startswith("charge:")]
            if hit:
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif "pass" in keys:
            # charge は pass を選ぶ（先頭 min 件だと手札を charge し続ける）
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return done(e)


def _under_counts(e, p=0):
    return {c: len(e.s.cards[c].under) for c in e.zlist("shield", p)}


def test_form_a_registered_ex06_010_each_shield(rules):
    """dmex06-010（形A）: 出た時、各シールドの下に1枚ずつ入る。
    束の数は増えず、山札がシールドの数だけ減る。"""
    e = setup(rules, {"hand": ["dmex06-010"], "mana": ["T004"] * 9},
              {"mana": ["T001"]})
    n_shields = len(e.zlist("shield", 0))
    deck0 = len(e.zlist("deck", 0))
    assert _drive(e, lambda e: any(e.s.cards[c].defn == "dmex06-010"
                                   for c in e.zlist("bz", 0)), "dmex06-010")
    assert _drive(e, lambda e: sum(_under_counts(e).values()) == n_shields,
                  "dmex06-010")
    counts = _under_counts(e)
    assert sorted(counts.values()) == [1] * n_shields
    assert len(e.zlist("shield", 0)) == n_shields
    assert len(e.zlist("deck", 0)) == deck0 - n_shields


def test_form_a_registered_28_s01_evolve_and_each_shield(rules):
    """dm28-s01（形A）: マナ進化V（光2体）で出て、各シールドの下に
    1枚ずつ入る。進化元2体は下に残る。"""
    e = setup(rules, {"hand": ["dm28-s01"], "mana": ["T004"] * 10},
              {"mana": ["T001"]})
    n_shields = len(e.zlist("shield", 0))
    assert _drive(e, lambda e: any(e.s.cards[c].defn == "dm28-s01"
                                   for c in e.zlist("bz", 0)), "dm28-s01")
    host = next(c for c in e.zlist("bz", 0)
                if e.s.cards[c].defn == "dm28-s01")
    assert len(e.s.cards[host].under) == 2            # 進化元2体
    assert _drive(e, lambda e: sum(_under_counts(e).values()) == n_shields,
                  "dm28-s01")
    assert sorted(_under_counts(e).values()) == [1] * n_shields
