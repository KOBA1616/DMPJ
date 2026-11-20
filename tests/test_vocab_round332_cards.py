"""再変換ラウンド332（第297弾 「ブレイクしたシールドは墓地に置く」）の記録テスト。

- 新規登録6件: dm25ex2-018（形A）/ dmr04-018（形B）/ dm26ex4-002（形A、
  partial の無い行を公式全文から全構築）/ dm26sd1-g005（形A。パワー
  アタッカーは split 由来の power_when 常在形が正本）/ dmex17-w06（形A）/
  dm24bd6-037（形C）。
- 差し戻し0件。converted 10,217→10,223 / rejects 2,107→2,101、
  重なり0・漏れ0。
- break_replacement_graveyard / break_to_graveyard は rejects に残らない。
  shield_break_to_graveyard は promoy11-011 のみ残る（ガチンコ・ジャッジに
  勝ったターンだけ与えられる形で本弾の家族とは別機構。ギャップ名の
  誤ラベルとして記録のみ）。
- 任意の銀行行 dm26ex4-sec005 / dm26ex4-025 は対象外とした
  （sec005 は submit の原文コーパスに無い印刷、025 は「相手が選んだ時」
  節の検証が別途必要なため見送り）。

プロトテスト（test_vocab_pilot297.py）とは別プロセスで実行すること
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

NEW = ["dm25ex2-018", "dmr04-018", "dm26ex4-002",
       "dm26sd1-g005", "dmex17-w06", "dm24bd6-037"]
INSTEAD = [{"op": "move", "select": {"ref": "event.shield", "count": 1},
            "to": "graveyard", "reason": "put"}]


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round332_disposition():
    rej = _reject_rows()
    for cid in NEW:
        c = _conv(cid)
        assert c is not None, cid
        assert cid not in rej, cid
        assert not (c.get("source") or {}).get("unsupported"), cid
        parse_card(c, TABLES)
    left = {g: [r["id"] for r in rej.values() if g in (r.get("gaps") or [])]
            for g in ("break_replacement_graveyard", "break_to_graveyard",
                      "shield_break_to_graveyard")}
    assert left["break_replacement_graveyard"] == []
    assert left["break_to_graveyard"] == []
    assert left["shield_break_to_graveyard"] == ["promoy11-011"]


# ---------- 実挙動ドライバ（ラウンド331と同形） ----------

def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _drive(e, stop, play_key=None, attack_key=None, prefer=(), limit=1500):
    seen = []
    played = {"done": False}
    for _ in range(limit):
        if stop(e):
            return seen
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind == "declare_strigger":
            e.answer([])
        elif kind == "main" and play_key and not played["done"]:
            hit = [i for i, k in enumerate(keys)
                   if play_key in k and not k.startswith("charge:")]
            if hit:
                played["done"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "attack" and attack_key:
            hit = [i for i, k in enumerate(keys) if k == attack_key]
            if hit:
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_cards":
            hit = []
            for want in prefer:
                hit = [i for i, o in enumerate(d["options"])
                       if e.cdef(o["cid"]).id == want]
                if hit:
                    break
            if hit:
                e.answer(hit[:max(d.get("min", 1), 1)])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_shields":
            want_n = d.get("max", d.get("min", 1))
            pref = [i for i, o in enumerate(d["options"])
                    if any(e.cdef(o["cid"]).id == w for w in prefer)]
            rest = [i for i in range(len(d["options"])) if i not in pref]
            e.answer((pref + rest)[:want_n])
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif kind == "order_pending":
            e.answer([0])
        elif kind == "block":
            e.answer([keys.index("no_block")] if "no_block" in keys
                     else list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


def test_registered_w06_break_to_graveyard(rules):
    """dmex17-w06（登録形・形A）: ブレイクした T279 は手札でなく墓地に
    置かれ、S・トリガー宣言の諮問自体が出ない。"""
    e = setup(rules, {"bz": ["dmex17-w06"]},
              {"shield": ["T279", "T001", "T001", "T001", "T001"]})
    seen = _drive(e, lambda ev: "T279" in _defns(ev, "graveyard", 1)
                  and _quiet(ev),
                  attack_key="attack:dmex17-w06:player", prefer=("T279",))
    assert "T279" in _defns(e, "graveyard", 1)
    assert "T279" not in _defns(e, "hand", 1)
    assert "declare_strigger" not in seen


def test_registered_018_form_b(rules):
    """dmr04-018（登録形・形B）: 相手の手札が0枚ならブレイクしたシールドは
    墓地へ、1枚あれば通常どおり手札へ（置換は効かない）。"""
    e = setup(rules, {"bz": ["dmr04-018"]},
              {"shield": ["T279", "T001", "T001", "T001", "T001"]})
    _drive(e, lambda ev: "T279" in _defns(ev, "graveyard", 1) and _quiet(ev),
           attack_key="attack:dmr04-018:player", prefer=("T279",))
    assert "T279" in _defns(e, "graveyard", 1)

    e = setup(rules, {"bz": ["dmr04-018"]},
              {"hand": ["T002"],
               "shield": ["T279", "T001", "T001", "T001", "T001"]})
    _drive(e, lambda ev: "T279" in _defns(ev, "hand", 1) and _quiet(ev),
           attack_key="attack:dmr04-018:player", prefer=("T279",))
    assert "T279" in _defns(e, "hand", 1)
    assert "T279" not in _defns(e, "graveyard", 1)


def test_registered_002_cip_and_cost(rules):
    """dm26ex4-002（登録形）: 相手のエレメントが2文明（火・水）なら召喚
    コストは 13-4=9。召喚によって出た時、無色ではないクリーチャーは
    すべてシールド化され（自他の T001 / T034 / T010）、自分の無色
    クリーチャー（このカード自身）1体につき相手の手札1枚がシールド化
    される。"""
    e = setup(rules,
              {"hand": ["dm26ex4-002"], "mana": ["T001"] * 9, "bz": ["T001"]},
              {"bz": ["T034", "T010"], "hand": ["T002", "T003"],
               "mana": ["T001"]})
    sh0 = {p: len(e.zlist("shield", p)) for p in (0, 1)}

    def stop(ev):
        # 相手の手札枚数は選択解決の直後に相手のドローで戻ってしまい
        # 決定境界では観測できないため、手札1枚分を含むシールド増分
        # （場の獣2体＋手札1枚＝+3）で止める。
        return ("dm26ex4-002" in _defns(ev, "bz", 0)
                and len(ev.zlist("shield", 1)) == sh0[1] + 3 and _quiet(ev))

    _drive(e, stop, play_key="play:dm26ex4-002")
    assert "dm26ex4-002" in _defns(e, "bz", 0)          # 9マナで召喚できた
    assert "T001" in _defns(e, "shield", 0)             # 自分の有色獣も対象
    assert "T034" in _defns(e, "shield", 1)
    assert "T010" in _defns(e, "shield", 1)
    assert len(e.zlist("shield", 0)) == sh0[0] + 1
    assert len(e.zlist("shield", 1)) == sh0[1] + 3      # 獣2体＋手札1枚


def test_registered_002_cost_needs_nine(rules):
    """dm26ex4-002（登録形）: マナ8枚では（軽減後コスト9に届かず）
    main の選択肢に play が出ない。"""
    e = setup(rules,
              {"hand": ["dm26ex4-002"], "mana": ["T001"] * 8},
              {"bz": ["T034", "T010"], "mana": ["T001"]})
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main":
            assert not [k for k in keys if "play:dm26ex4-002" in k], keys
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("main decision not reached")
