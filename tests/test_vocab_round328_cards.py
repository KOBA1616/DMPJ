"""再変換ラウンド328（第293弾「進化元のゾーン拡張」）の記録テスト。

- 新規登録18件: dm22ex2-003 / dm26ex2-027 / dm38-027 / dm28-s05 /
  dmc55-021 / dm34-002 / dm25ex1-044 / dm26ex2-mc005 / dm23bd4-017 /
  dmc63-009 / dm25ex1-023 / dm25ex1-016 / dm22ex2-4a /
  dm25ex1-010 / dm23ex3-tr07 / dm23ex3-tr02 /
  dmr20-s04 / dm26ex1-011。
- alias 畳み込み1件: dmartkiwami03-005 → dm25ex1-010。
- stale 解消2件: dmc66-008 は canon dmpcd03-b02 が変換済み（dm34-s03 と
  ともに alias へ追加）。dm26ex4-sec009 は canon dm26ex4-012 の alias に
  既存だったため reject 行の除去のみ。
- 差し戻し5件: dm28-s01 → super_shield_plus（既存ギャップ）、
  dm28-s09 → static_if_own_current_power（新規ギャップ。提出後に判明:
  ブレイカー帯の常在条件は自身の現在パワーを参照するが、常在条件の評価は
  再帰防止のため印刷特性で行われ power_of: self は印刷パワー0しか読めない。
  下のカード合計への読み替えは外部のパワー修正で乖離するため採らない。
  進化面と合計パワー常在は partial に銀行済み）、
  dm26ex2-pr003 → per_evolution_base_cost_reduction（新規ギャップ）、
  dm24bd5-012 → was_under_cards_return（既存ギャップ。提出後に判明:
  離脱誘発の under_of: self は離脱時点で under が解体され gen も進むため
  解決時に空になる。dm25rp2-033 と同じ欠落機構。進化面とパワー常在は
  partial に銀行済み。第294弾で語彙が入り、ラウンド329で登録済み）、
  dm26ex2-mc009 → exlife_shield_left_any（新規ギャップ。提出後に判明:
  「自分のEXライフシールド（どのクリーチャーのものでも）が離れた時」の
  subject 形が無い。exlife_of は特定クリーチャーへの紐付け照合のみ、
  filter の exlife は離脱後の実カードしか見ず LKI を見ない。進化GV・Ω面、
  エクストラEXライフ、G・ストライク付与は partial に銀行済み）。
- 提出時のマージ由来混入の除去1件: dm34-002 の keywords から
  meteor_burn（離脱置換キーワード。本文のメテオバーンは攻撃中止形で
  別能力）を除去。
- 登録形の修正2件（実挙動テストで検出）: dm28-s05 のターン開始誘発は
  subject: self では turn_start レコード（subject を持たない）に一致しない
  ため player: you 形へ。dm22ex2-003 の攻撃者コスト参照は attack
  レコードに attacker キーが無いため cost_of: event.subject へ。
- ラウンド直後: converted 10,207 / rejects 2,119、重なり0・漏れ0。
  第293弾の12ギャップは rejects に残らない（両ファミリー解消）。

プロトテスト（test_vocab_pilot293.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
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

NEW = ["dm22ex2-003", "dm26ex2-027", "dm38-027", "dm28-s05", "dmc55-021",
       "dm34-002", "dm25ex1-044", "dm26ex2-mc005", "dm23bd4-017",
       "dmc63-009", "dm25ex1-023", "dm25ex1-016", "dm22ex2-4a", "dm25ex1-010",
       "dm23ex3-tr07", "dm23ex3-tr02", "dmr20-s04",
       "dm26ex1-011"]
FOLDED = {"dmartkiwami03-005": "dm25ex1-010"}
STALE = {"dmc66-008": "dmpcd03-b02", "dm34-s03": "dmpcd03-b02",
         "dm26ex4-sec009": "dm26ex4-012"}
BOUNCED = {"dm28-s01": ["super_shield_plus"],
           "dm26ex2-pr003": ["per_evolution_base_cost_reduction"],
           "dm26ex2-mc009": ["exlife_shield_left_any"],
           "dm28-s09": ["static_if_own_current_power"]}
# dm24bd5-012 は本ラウンドで was_under_cards_return に差し戻されたが、
# 第294弾（was_under）で解けラウンド329で登録されたため BOUNCED から外した
FAMILY_GAPS = {"graveyard_evolution_v", "mana_evolution_v", "hand_evolution_v",
               "graveyard_evolution_gv", "mana_evolution_gv", "hand_evolution_gv",
               "shield_evolution_gv", "deck_evolution_gv", "evolution_gv_omega",
               "infinite_evolution_omega", "infinite_graveyard_evolution",
               "infinite_evolution"}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round328_disposition():
    rej = _reject_rows()
    for cid in NEW:
        c = _conv(cid)
        assert c is not None, cid                      # 新規登録された
        assert cid not in rej, cid                     # rejects に残らない
        assert "unsupported" not in (c.get("source") or {}), cid
        parse_card(c, TABLES)                          # 登録形が parse できる
    for alias, canon in {**FOLDED, **STALE}.items():
        assert _conv(alias) is None, alias             # 独立 id では登録されない
        c = _conv(canon)
        assert alias in ((c.get("source") or {}).get("aliases") or []), alias
        assert alias not in rej, alias                 # 漏れなし
    for cid, gaps in BOUNCED.items():
        assert _conv(cid) is None, cid
        assert rej[cid]["gaps"] == gaps, cid
        assert rej[cid]["reason"] == "vocab", cid
    # 第293弾ファミリー解消: 対象12ギャップを含む行は rejects に残らない
    assert not [r["id"] for r in rej.values() if FAMILY_GAPS & set(r.get("gaps") or [])]
    # dm24bd5-012 の銀行 partial はラウンド329の登録で消費された（rejects に無い）
    assert "dm24bd5-012" not in rej
    assert _conv("dm24bd5-012") is not None
    # dm26ex2-mc009 の銀行 partial: 解けた節（Ω面＋EXライフ＋G・ストライク付与）
    p = rej["dm26ex2-mc009"]["partial"]
    assert [f.get("zone") for f in p["evolve_from"]] == ["graveyard", "mana", "bz"]
    assert sorted(p["keywords"]) == ["extra_ex_life", "world_breaker"]
    assert [ab["kind"] for ab in p["abilities"]] == ["static"]
    # dm28-s09 の銀行 partial: 解けた節（「3体まで」面＋合計パワー常在）
    p = rej["dm28-s09"]["partial"]
    assert p["evolve_max"] == 3 and p["evolve_any"] is True and p["power"] == 0
    assert [ab["kind"] for ab in p["abilities"]] == ["static"]


def test_registered_key_forms():
    # 愛銀河の代替コスト（dm25ex1-050 の登録先例形）
    for cid, cost, civ in [("dm25ex1-044", 2, "darkness"), ("dm25ex1-023", 3, "water"),
                           ("dm25ex1-016", 4, "light"), ("dm25ex1-010", 3, "fire")]:
        ac = _conv(cid)["alt_cost"]
        assert ac["cost"] == cost and ac["civs"] == [civ, civ], cid
    # dm34-002: マージ由来の meteor_burn キーワード混入が除かれている
    assert _conv("dm34-002")["keywords"] == ["double_breaker"]
    # dm22ex2-4a: デッキ進化GV（stack_all）
    assert _conv("dm22ex2-4a")["deck_evolution"] == {"count": 3, "blind": True,
                                                     "stack_all": True}
    # dm26ex1-011: 超無限進化の素形＋identity alias 3件
    c = _conv("dm26ex1-011")
    assert c["evolve_any"] is True and c["evolve_from"] == {"types": ["creature"]}
    assert sorted((c.get("source") or {}).get("aliases") or []) == \
        ["dm23rp1-tr3", "dmex01-022", "dmex08-283"]
    # dm25ex1-016: シールド進化GVの進化元は「カード」全般（空フィルタ）
    assert _conv("dm25ex1-016")["evolve_from"] == {}
    # dm28-s05: ターン開始誘発は player: you 形（turn_start レコードに
    # subject は無く、subject: self は永遠に一致しない）
    w = _conv("dm28-s05")["abilities"][0]["when"]
    assert w == {"event": "turn_start", "player": "you"}
    # dm22ex2-003: 攻撃したドラゴンのコスト参照は event.subject
    # （attack レコードに attacker キーは無い）
    s = json.dumps(_conv("dm22ex2-003")["abilities"], ensure_ascii=False)
    assert "event.subject" in s and "event.attacker" not in s


# ---------- 実挙動 ----------

def _drive(e, hook, limit=1200):
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
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif kind == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("drive did not finish")


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tops(e, p):
    return [c for c in e.zlist("bz", p)
            if e.s.cards[c].controller == p and e.s.cards[c].top_of < 0]


def test_011_mega_meteo_burn_10_wins(rules):
    """dm26ex1-011: 進化元10体を積み、攻撃時に10枚墓地へ置くと勝利する。"""
    e = setup(rules, {"hand": ["dm26ex1-011"], "bz": ["T001"] * 10,
                      "mana": ["T030", "T008"] + ["T034"] * 6},
              {"bz": []})
    st = {}

    def hook(e, d, keys):
        if d["kind"] == "main" and "play:dm26ex1-011" in keys and not st.get("played"):
            st["played"] = True
            return [keys.index("play:dm26ex1-011")]
        if d["kind"] == "choose_evo_source":
            return list(range(len(d["options"])))       # 10体すべてを進化元に
        if d["kind"] == "attack" and e.s.turn == 3:
            k = "attack:dm26ex1-011:player"
            if k in keys:
                return [keys.index(k)]
        if e.s.result is not None:
            return "stop"
        return None

    _drive(e, hook)
    assert e.s.result is not None and e.s.result["winner"] == 0


def test_s05_turn_start_only_on_own_turn(rules):
    """dm28-s05: 自分のターンのはじめにだけ、相手が自軍の場/マナから
    1枚選んで墓地に置く。相手のターンのはじめには誘発しない。"""
    e = setup(rules, {"bz": ["dm28-s05"]},
              {"bz": ["T001"], "mana": ["T001", "T001"]})
    seen = {"turn2_max": 0, "final": 0}

    def hook(e, d, keys):
        gy = len(e.zlist("graveyard", 1))
        if e.s.turn == 2:
            seen["turn2_max"] = max(seen["turn2_max"], gy)
        seen["final"] = gy
        if e.s.turn >= 3 and gy >= 2:
            return "stop"
        return None

    _drive(e, hook)
    assert seen["turn2_max"] == 1     # 自分ターン開始で1枚、相手ターン開始では増えない
    assert seen["final"] == 2         # 次の自分ターン開始でもう1枚


def test_003_dragon_attack_summons_from_graveyard(rules):
    """dm22ex2-003: 自分のドラゴンが攻撃した時、攻撃したドラゴンより
    コストが1小さい闇のクリーチャーを墓地から出せる。"""
    e = setup(rules, {"bz": ["dm22ex2-003"], "graveyard": ["dm03-027"]}, {"bz": []})
    st = {}

    def hook(e, d, keys):
        if d["kind"] == "attack" and not st.get("attacked"):
            k = "attack:dm22ex2-003:player"
            if k in keys:
                st["attacked"] = True
                return [keys.index(k)]
        if d["kind"] == "choose_cards" and not st.get("summoned"):
            for i, o in enumerate(d["options"]):
                if e.s.cards[o["cid"]].defn == "dm03-027":
                    st["summoned"] = True
                    return [i]
        if st.get("summoned"):
            return "stop"
        return None

    _drive(e, hook)
    assert "dm03-027" in _defns(e, "bz", 0)


def test_003_non_dragon_attack_does_not_trigger(rules):
    """ドラゴンでない自軍の攻撃では誘発しない。"""
    e = setup(rules, {"bz": ["dm22ex2-003", "T001"], "graveyard": ["dm03-027"]},
              {"bz": []})
    st = {}

    def hook(e, d, keys):
        if d["kind"] == "attack" and not st.get("attacked"):
            k = "attack:T001:player"
            if k in keys:
                st["attacked"] = True
                return [keys.index(k)]
        if st.get("attacked") and e.s.turn >= 2:
            return "stop"
        return None

    _drive(e, hook)
    assert "dm03-027" in _defns(e, "graveyard", 0)
    assert "dm03-027" not in _defns(e, "bz", 0)
