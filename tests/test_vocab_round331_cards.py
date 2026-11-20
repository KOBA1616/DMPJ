"""再変換ラウンド331（第296弾 「S・トリガーは使えない」）の記録テスト。

- 新規登録4件: dm26rp2-066 / dmx18-003 / dmr13-003 / dmrp01-s03。
- 差し戻し1件: dmx21-064（公式データのカード名・種族欠落により
  data_incomplete。提出形は partial に銀行済み）。
- stale 解消1件: dmx22b-023（正本 dm26ex4-cho049 が変換済み）。
  あわせて正本 cho049 と別変換エントリ dm03-042 の戻す move に
  strigger: "off" を外科的に付与（修繕前は宣言諮問が出ていた）。
- ラウンド直後: converted 10,217 / rejects 2,107、重なり0・漏れ0。
  shield_trigger_restriction / s_trigger_disable は rejects に残らない。

プロトテスト（test_vocab_pilot296.py）とは別プロセスで実行すること
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

NEW = ["dm26rp2-066", "dmx18-003", "dmr13-003", "dmrp01-s03"]


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round331_disposition():
    rej = _reject_rows()
    for cid in NEW:
        c = _conv(cid)
        assert c is not None, cid
        assert cid not in rej, cid
        assert not (c.get("source") or {}).get("unsupported"), cid
        parse_card(c, TABLES)
    assert rej["dmx21-064"]["gaps"] == ["data_incomplete"]
    assert "dmx22b-023" not in rej and _conv("dmx22b-023") is None
    assert not [r["id"] for r in rej.values()
                if set(r.get("gaps") or []) &
                {"shield_trigger_restriction", "s_trigger_disable"}]


# ---------- 実挙動ドライバ ----------

def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _drive(e, stop, play_key=None, attack_key=None, prefer=(), limit=1500):
    """stop(e) まで進める。現れた Decision の kind 列を返す。
    choose_cards は prefer の defn を優先して選ぶ。"""
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
            e.answer([])          # 宣言しない（機会の有無だけを見る）
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


def test_registered_066_cip_no_strigger(rules):
    """dm26rp2-066（登録形）: CIP で手札に加えた T279 は宣言できない。"""
    e = setup(rules, {"hand": ["dm26rp2-066"], "mana": ["T008"] * 2,
                      "shield": ["T279", "T001", "T001", "T001", "T001"]},
              {"mana": ["T001"]})
    t279 = next(c for c in e.zlist("shield", 0) if e.cdef(c).id == "T279")
    seen = _drive(e, lambda ev: "T279" in _defns(ev, "hand", 0) and _quiet(ev),
                  play_key="play:dm26rp2-066", prefer=("T279",))
    assert "T279" in _defns(e, "hand", 0)
    assert "declare_strigger" not in seen
    assert e.s.cards[t279].strigger_off is True


def test_registered_s03_shield_count_cip(rules):
    """dmrp01-s03（登録形）: CIP は置く前の自分のシールド数と同じ枚数を
    山札の上からシールド化する（count の式は置く前に評価される）。"""
    e = setup(rules, {"hand": ["dmrp01-s03"], "mana": ["T004"] * 7},
              {"mana": ["T001"]})
    n0 = len(e.zlist("shield", 0))
    assert n0 >= 1
    mark = {}

    def stop(ev):
        if any(ev.s.cards[c].defn == "dmrp01-s03" for c in ev.zlist("bz", 0)):
            mark.setdefault("deck", len(ev.zlist("deck", 0)))
            return len(ev.zlist("shield", 0)) == 2 * n0 and _quiet(ev)
        return False

    _drive(e, stop, play_key="play:dmrp01-s03")
    assert len(e.zlist("shield", 0)) == 2 * n0       # n0 枚が新たに置かれた
    assert len(e.zlist("deck", 0)) == mark["deck"] - n0


def test_registered_s03_form_b_denies(rules):
    """dmrp01-s03（登録形）の常在 deny: 自分の光でないシールド（T279）が
    割られても S・トリガーを宣言できない。"""
    e = setup(rules, {"bz": ["T001"]},
              {"bz": ["dmrp01-s03"],
               "shield": ["T279", "T001", "T001", "T001", "T001"]})
    seen = _drive(e, lambda ev: "T279" in _defns(ev, "hand", 1) and _quiet(ev),
                  attack_key="attack:T001:player", prefer=("T279",))
    assert "T279" in _defns(e, "hand", 1)
    assert "declare_strigger" not in seen


def test_registered_18_003_attack_form(rules):
    """dmx18-003（登録形）: 攻撃時、シールドを手札に加えてもよい（宣言は
    できない）。加えた場合、相手のパワー6000以下を1体破壊する。"""
    e = setup(rules, {"hand": ["dmx18-003"], "mana": ["T034"] * 5,
                      "shield": ["T279", "T001", "T001", "T001", "T001"]},
              {"bz": ["T004"], "mana": ["T001"],
               "shield": ["T001"] * 5})
    seen = _drive(
        e, lambda ev: "T004" in _defns(ev, "graveyard", 1)
        and "T279" in _defns(ev, "hand", 0) and _quiet(ev),
        play_key="play:dmx18-003",
        attack_key="attack:dmx18-003:player", prefer=("T279", "T004"))
    assert "T279" in _defns(e, "hand", 0)
    assert "T004" in _defns(e, "graveyard", 1)
    assert "declare_strigger" not in seen


def test_registered_13_003_gate_form(rules):
    """dmr13-003（登録形）: CIP ゲート形で手札に戻した T279 は宣言でき
    ない。シールド化した分と合わせてシールド総数は変わらない。"""
    e = setup(rules, {"hand": ["dmr13-003"], "mana": ["T010"] * 7,
                      "shield": ["T279", "T001", "T001", "T001", "T001"]},
              {"mana": ["T001"]})
    n0 = len(e.zlist("shield", 0))
    seen = _drive(e, lambda ev: "T279" in _defns(ev, "hand", 0) and _quiet(ev),
                  play_key="play:dmr13-003", prefer=("T279",))
    assert "T279" in _defns(e, "hand", 0)
    assert len(e.zlist("shield", 0)) == n0           # -1（回収）+1（シールド化）
    assert "declare_strigger" not in seen


def test_repaired_emerald_no_strigger(rules):
    """修繕した正本 dm26ex4-cho049 と dm03-042（登録形）: 手札に戻した
    T279 はどちらも宣言できない。"""
    for cid in ("dm26ex4-cho049", "dm03-042"):
        e = setup(rules, {"hand": [cid, "T001"], "mana": ["T010"] * 3,
                          "shield": ["T279", "T001", "T001", "T001", "T001"]},
                  {"mana": ["T001"]})
        seen = _drive(e, lambda ev: "T279" in _defns(ev, "hand", 0)
                      and _quiet(ev),
                      play_key=f"play:{cid}", prefer=("T279",))
        assert "T279" in _defns(e, "hand", 0), cid
        assert "declare_strigger" not in seen, cid
