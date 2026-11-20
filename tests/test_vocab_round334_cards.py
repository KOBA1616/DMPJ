"""再変換ラウンド334（第299弾 under_card_removed）の記録テスト。

- 新規登録3件: dm34-014 呪言人形ワヤ / dm34-022 神星の守護者
  アルト・コロニス / dm34-032 惑星の勇者ドリッピー。3件とも単独
  gap の純粋行で、partial（abilities 無し）に第299弾の誘発対
  （破壊側 from_under: false ／ 下カード側 from_under
  {owner: you, filter: {types: [evolution]}}）＋効果を足して登録。
  登録形は abilities == FORMS で、partial の連結残り・テキスト
  由来のキーワード追加が無いことを固定する。
- dm34-022 の効果は choose {from_top: 1, count: 1} 形（第299弾で
  実挙動固定）。dmr08-008 の choose {count: 0, up_to: true} 形は
  不発形のため使っていない（棚卸し＋修繕は別ステージ課題）。
- alias 畳み込み・stale 解消・差し戻しは0件。
- converted 10,224→10,227 / rejects 2,099→2,096、重なり0・漏れ0。
  under_card_removed は rejects に残らない。

プロトテスト（test_vocab_pilot299.py）とは別プロセスで実行する
こと（conftest の DMSIM_SKIP_CONVERTED 復活の汚染回避）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402
from test_vocab_pilot299_cards import FORMS  # noqa: E402


def setup(rules, p0, p1=None, filler="T002", seed=1, deck_size=20):
    """conftest の setup と同じ薄い包み（tests.conftest は import しない）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGETS = ["dm34-014", "dm34-022", "dm34-032"]
P1_DESTROY = {"hand": ["T056"], "mana": ["T008"] * 3}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round334_disposition():
    rej = _reject_rows()
    assert len(rej) == 2096
    for cid in TARGETS:
        c = _conv(cid)
        assert c is not None, cid                    # 登録済み
        assert cid not in rej, cid                   # reject 行は残らない
        assert not (c.get("source") or {}).get("unsupported"), cid
        assert c["abilities"] == FORMS[cid], cid     # 連結残り・追加なし
        assert not c.get("keywords"), cid            # 本文由来の追加なし
        parse_card(c, TABLES)
    # under_card_removed は解消、converted と rejects の重なり0
    assert not [r for r in rej.values()
                if "under_card_removed" in (r.get("gaps") or [])]
    ids = {x["id"] for x in _conv_cache.all_cards(CONVERTED)}
    assert len(ids) == 10227
    assert not (ids & set(rej))


# ---------- 実挙動ドライバ（第299弾のものと同形） ----------

def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _pub(e, kind, defn=None):
    return [r for r in e.s.pub if r["kind"] == kind
            and (defn is None or r.get("defn") == defn)]


def _drive(e, done, cast=None, cast_player=1, target_defn=None,
           pick_defn=None, yes=True, num_key=None, steps=400):
    st = {"cast": False}
    for _ in range(steps):
        if done(e):
            return st
        d = e.advance()
        assert d is not None, "game ended before done"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and cast and not st["cast"] \
                and d.get("player") == cast_player and f"play:{cast}" in keys:
            e.answer([keys.index(f"play:{cast}")])
            st["cast"] = True
        elif kind == "choose_cards":
            idx = None
            for want in (pick_defn, target_defn):
                if not want:
                    continue
                for o in d["options"]:
                    if e.s.cards[o["cid"]].defn == want:
                        idx = keys.index(o["key"])
                        break
                if idx is not None:
                    break
            e.answer([idx] if idx is not None else list(range(d["min"])))
        elif kind == "choose_one" and num_key is not None:
            e.answer([keys.index(num_key)])
        elif kind == "yes_no":
            want = "yes" if yes else "no"
            e.answer([keys.index(want)] if want in keys
                     else list(range(d["min"])))
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive budget exhausted")


def test_registered_014_modify_power_minus_1000(rules):
    """dm34-014（登録形）: 自分の他のクリーチャーの破壊を監視して
    相手クリーチャー1体のパワーを -1000 する（そのターンの間）。"""
    e = setup(rules, {"bz": ["dm34-014", "T001"]},
              {"bz": ["T004"], **P1_DESTROY}, filler="T002")
    tgt = next(c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T004")
    assert e.chars(tgt)["power"] == 3000
    _drive(e, lambda e: "T001" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T001")
    assert e.chars(tgt)["power"] == 2000


def test_registered_032_number_match_destroys(rules):
    """dm34-032（登録形）: 数字を選んで山札の上を表向きにし、
    コストが一致したら相手のパワー5000以下を破壊する。"""
    e = setup(rules, {"bz": ["dm34-032", "T001"]},
              {"bz": ["T004"], **P1_DESTROY}, filler="T002")
    top = e.s.zones["deck"][0][0]
    top_defn = e.s.cards[top].defn
    cost = rules.cards[top_defn].cost
    _drive(e, lambda e: "T004" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T056", target_defn="T001", pick_defn="T004",
           num_key=f"num:{cost}")
    assert _pub(e, "reveal", defn=top_defn)   # 上のカードは表向きにされた


def test_registered_022_takes_spell_from_top(rules):
    """dm34-022（登録形）: 山札の上が呪文なら、相手に見せてから
    自分の手札に加える。"""
    e = scenario.build(
        rules, {"p0": {"bz": ["dm34-022", "T001"], "deck": ["T003"] * 4},
                "p1": dict(P1_DESTROY), "filler": "T002", "seed": 1,
                "deck_exact": [True, False]})
    assert [e.s.cards[c].defn for c in e.s.zones["deck"][0]] == ["T003"] * 4
    # 手札の T003 が「ターン1のドロー1枚＋効果で加えた1枚」＝2枚になる
    _drive(e, lambda e: _defns(e, "hand").count("T003") == 2 and _quiet(e),
           cast="T056", target_defn="T001", pick_defn="T003")
    assert _pub(e, "reveal", defn="T003")     # 相手に見せた記録
    assert len(e.s.zones["deck"][0]) == 2     # ドロー1＋効果で1枚減った
