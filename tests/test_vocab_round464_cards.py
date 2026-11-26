"""再変換ラウンド464（第429弾
drew_this_turn_condition）の記録テスト。

- 新規登録1件: dmx22b-038 天災超邪 クロスファイア
  2nd（partial の骨格〔クリーチャー / 水・火 /
  コスト7 / パワー7000 / 種族 アウトレイジMAX、
  mana 1〕に keywords [speed_attacker,
  double_breaker] と free_if {all: [{cmp:
  [{turn_count: {kind: draw, owner: you}}, ">=",
  6]}, {not: {exists: {zone: bz, owner: you,
  filter: {name: 天災超邪 クロスファイア
  2nd}}}}]}（第429弾のドリフト。第412弾の
  free_if turn_count cmp と登録済み dmex08-226 /
  dm25ex3-rp4tr6 の同名不在条件の合成）を足し、
  unsupported を外したもの。登録形は提出形と
  完全一致〔source 以外の全フィールドを照合〕、
  abilities は無く、keywords はそのまま、
  free_if は保持されている）。
- 補完あり: text（公式全文。partial の text は
  断片）＋keywords＋free_if。登録後の text の
  全文一致も照合済み。
- alias 畳み込み0件（別刷り dmr11-017 /
  promoy12-063 は rejects に独自行なし、登録
  エントリの source.aliases にのみ収載・独立
  エントリにはならない。正本判定は通常型で対象
  id と別刷り2件を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1208 の
  notes 内参照のみ〕、identity 実測で canon_id
  は対象自身、別刷りの canon も対象、
  aliases_for = [dmr11-017, promoy12-063]）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔drew_this_turn_condition〕の出力は
  対象1件ちょうど＝巻き込みなし。split は None
  で定型所有なし）。
- converted 10,409→10,410 / rejects
  1,902→1,901、canonical 重なり0・漏れ0。
  drew_this_turn_condition は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第429弾本体と同形（対象を proto T1208 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T003（水呪文・2ドロー役）/
T705（水呪文・1ドロー役＝境界判別）/ T009
（水マナ役）/ T1207（火マナ役）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402
from tests.test_vocab_pilot429_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot429 import FREE_IF, FULL_TEXT, KEYWORDS  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmx22b-038"
ALIASES = ["dmr11-017", "promoy12-063"]
GAP = "drew_this_turn_condition"


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round464_disposition():
    rej = _reject_rows()
    assert len(rej) == 1901
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10410
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert not c.get("abilities")        # abilities は無い
    assert c["keywords"] == KEYWORDS
    assert c["free_if"] == FREE_IF       # free_if が保持されている
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES
    for a in ALIASES:
        assert a not in rej
        assert _conv_cache.find(CONVERTED, a) is None
    d = parse_card(c, TABLES)
    assert d.free_if == FREE_IF
    assert d.keywords == KEYWORDS
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第429弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _in_bz(e, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist("bz", p))


def _main_keys(e, player, casts):
    casts = list(casts)
    for _ in range(900):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player:
            if casts:
                k = f"play:{casts[0]}"
                assert k in keys, f"{k} not in {keys}"
                casts.pop(0)
                e.answer([keys.index(k)])
                continue
            return keys
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def _play_and_settle(e, player, key, done):
    played = False
    for _ in range(600):
        if played and done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" \
                and d.get("player") == player and key in keys:
            played = True
            e.answer([keys.index(key)])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return done()


def _second_main_keys(e, casts):
    casts = list(casts)
    mains = 0
    for _ in range(1500):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == 0:
            mains += 1
            if mains >= 2:
                if casts:
                    k = f"play:{casts[0]}"
                    assert k in keys, f"{k} not in {keys}"
                    casts.pop(0)
                    e.answer([keys.index(k)])
                    continue
                return keys
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def test_no_free_without_draws(rules):
    """0枚引いた状態では無料選択肢は出ず、有料だけが出る。"""
    e = _build(rules, {"hand": [TARGET], "mana": ["T009"] * 7 + ["T1207"] * 7}, {})
    keys = _main_keys(e, 0, [])
    assert f"play:{TARGET}" in keys
    assert f"play:{TARGET}:free" not in keys


def test_no_free_at_five_draws(rules):
    """2ドロー×2＋1ドロー＝5枚では閾値6に届かず、
    無料選択肢は出ない（有料は残る）。"""
    e = _build(rules,
               {"hand": [TARGET, "T003", "T003", "T705"],
                "mana": ["T009"] * 7 + ["T1207"] * 7},
               {})
    keys = _main_keys(e, 0, ["T003", "T003", "T705"])
    assert f"play:{TARGET}" in keys
    assert f"play:{TARGET}:free" not in keys
    assert _tapped_mana(e, 0) == 5


def test_free_at_six_draws(rules):
    """2ドロー×3＝6枚で無料選択肢が出る。無料で召喚すると
    マナは呪文の6枚分しかタップされない。"""
    e = _build(rules,
               {"hand": [TARGET, "T003", "T003", "T003"],
                "mana": ["T009"] * 7 + ["T1207"] * 7},
               {})
    keys = _main_keys(e, 0, ["T003", "T003", "T003"])
    assert f"play:{TARGET}:free" in keys
    assert _tapped_mana(e, 0) == 6
    ok = _play_and_settle(e, 0, f"play:{TARGET}:free",
                          lambda: _in_bz(e, 0, TARGET))
    assert ok
    assert _tapped_mana(e, 0) == 6     # 無料召喚で追加タップなし


def test_no_free_when_same_name_in_bz(rules):
    """6枚引いても、自分の同名がすでにバトルゾーンに
    あれば無料選択肢は出ない（not exists の判別）。"""
    e = _build(rules,
               {"hand": [TARGET, "T003", "T003", "T003"],
                "mana": ["T009"] * 7 + ["T1207"] * 7, "bz": [TARGET]},
               {})
    keys = _main_keys(e, 0, ["T003", "T003", "T003"])
    assert f"play:{TARGET}" in keys
    assert f"play:{TARGET}:free" not in keys


def test_turn_draw_counts_on_second_turn(rules):
    """自分の2ターン目: ターンドロー1枚＋2ドロー×2＋
    1ドロー＝6枚で無料選択肢が出る（ターンドローも
    「このターン引いた枚数」に含まれることの判別）。"""
    e = _build(rules,
               {"hand": [TARGET, "T003", "T003", "T705"],
                "mana": ["T009"] * 7 + ["T1207"] * 7},
               {})
    keys = _second_main_keys(e, ["T003", "T003", "T705"])
    assert keys is not None
    assert f"play:{TARGET}:free" in keys
