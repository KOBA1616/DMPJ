"""再変換ラウンド409（第374弾 global_s_trigger_lock）の記録テスト。

- 新規登録1件: dm23rp1-t2 石像男
  （登録形は提出形と完全一致: partial の骨格
  〔闇 / コスト6 / パワー5000 / 種族 ヘドリアン、
  keywords・abilities ともに無し〕に第374弾の
  確立形〔static {affects: {zone: shield, owner:
  opp}, if: {all: [cmp count {zone: bz, owner: you,
  filter: {types: [creature], civs: [文明]}} >= 1
  ×5文明]}, mod: {deny: [s_trigger]}}〕1能力を
  足し、unsupported を外したもの。abilities は
  1件ちょうど、keywords は無いまま。text は
  partial の時点で公式全文と一致するため補完なし）。
- alias 畳み込み0件（alias dm23rp1-tf2 / dm24-020 は
  rejects に独自行が無く、登録エントリの
  source.aliases に記録されたのみ）。正本判定:
  対象 id と alias 2件を real.yaml /
  real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml と
  照合し、いずれにも登録なし（proto.yaml のヒットは
  T1122 の notes 内参照のみ）。identity 実測で
  canon(dm23rp1-t2) = dm23rp1-t2（対象 id が正本）、
  canon(dm23rp1-tf2) = canon(dm24-020) = dm23rp1-t2、
  aliases_for(石像男, dm23rp1-t2) =
  [dm23rp1-tf2, dm24-020]。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [global_s_trigger_lock] のため
  reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,353→10,354 / rejects 1,959→1,958、
  canonical 重なり0・漏れ0。global_s_trigger_lock は
  ファミリーがこの1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第374弾本体の薄い包み（対象 T1122 を登録カードに
差し替えたもの）で、tests.conftest は import しない
（第319弾以降の作法）。判別役は既存 proto を流用
（T339=光 / T079=水 / T277=火 / T001=自然 /
T1107=アタッカー / T006=S・トリガー呪文）。
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

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm23rp1-t2"
GAP = "global_s_trigger_lock"
ALIASES = ["dm23rp1-tf2", "dm24-020"]

CIVS5 = ["light", "water", "darkness", "fire", "nature"]


def _all_civs_creatures():
    return {"all": [{"cmp": [{"count": {"zone": "bz", "owner": "you",
                                        "filter": {"types": ["creature"],
                                                   "civs": [c]}}},
                             ">=", 1]}
                    for c in CIVS5]}


LOCK = {"kind": "static",
        "affects": {"zone": "shield", "owner": "opp"},
        "if": _all_civs_creatures(),
        "mod": {"deny": ["s_trigger"]}}
FORM = [LOCK]
FULL_TEXT = ("自分のクリーチャーで、すべての文明が揃っていれば、"
             "相手は自身の「S・トリガー」を使えない。")

# 文明カバー役: 登録カード自身が闇、T339=光 / T079=水 /
# T277=火 / T001=自然（いずれも能力なしクリーチャー）
FULL = [TARGET, "T339", "T079", "T277", "T001"]
MISSING = [TARGET, "T339", "T079", "T277"]     # 自然が欠ける


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


def test_round409_disposition():
    rej = _reject_rows()
    assert len(rej) == 1958
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10354
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0（aliases 欄）
    assert TARGET not in rej             # 対象行は解消
    for a in ALIASES:                    # alias は独自行が無いまま
        assert a not in rej
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # aliases 欄は使わない
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: abilities は確立形1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")         # keywords は無いまま
    assert c["text"] == FULL_TEXT        # text の補完はなし
    assert c["name"] == "石像男"
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 6 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["ヘドリアン"]
    d = parse_card(c, TABLES)
    assert LOCK in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第374弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.cdef(c).id == defn)


def test_registered_chars_deny_full_coverage(rules):
    """登録カード: 特性レベルで、自分のクリーチャーで
    全文明が揃えば相手のシールドにだけ deny
    [s_trigger] が付く（自分のシールドには付かない）。"""
    e = _build(rules, {"bz": FULL, "shield": ["T006"]},
               {"shield": ["T006"]})
    assert "s_trigger" in e.chars(_find(e, "shield", 1, "T006"))["deny"]
    assert "s_trigger" not in e.chars(_find(e, "shield", 0, "T006"))["deny"]


def test_registered_chars_no_deny_missing_civ(rules):
    """登録カード: 文明が1つ欠ければ deny は付かない。"""
    e = _build(rules, {"bz": MISSING}, {"shield": ["T006"]})
    assert "s_trigger" not in e.chars(_find(e, "shield", 1, "T006"))["deny"]


def _drive(e, attacker, player, break_defn=None, use_strigger=False):
    """player の attacker でプレイヤーを攻撃する（第374弾の作法）。"""
    log = []
    attacked = False
    for _ in range(1500):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == player and not attacked:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit:
                attacked = True
                e.answer([hit[0]])
                continue
        if kind == "choose_shields" and break_defn:
            shields = e.zlist("shield", 1 - player)
            idx = next(i for i, c in enumerate(shields)
                       if e.cdef(c).id == break_defn)
            e.answer([idx])
            continue
        if kind == "declare_strigger":
            log.append((kind, d.get("player"), keys))
            e.answer(list(range(len(keys))) if use_strigger else [])
            continue
        if kind == "choose_cards":
            hit = [i for i, k in enumerate(keys) if attacker in k]
            if hit:
                e.answer(hit[:1])
                continue
        if kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
            continue
        e.answer(list(range(d.get("min", 0))))
        if attacked and kind == "main" and d.get("player") == player:
            break
    return log


def test_registered_opponent_strigger_denied_full_coverage(rules):
    """登録カード: 全文明が揃っている間、相手のシールド
    （T006）がブレイクされても S・トリガーの宣言判断
    自体が出ず、カードはそのまま相手の手札に加わる
    （攻撃側は破壊されない）。"""
    e = _build(rules,
               {"bz": FULL + ["T1107"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T1107", 0, break_defn="T006", use_strigger=True)
    assert not [x for x in log if x[0] == "declare_strigger"]
    assert "T006" in _defns(e, "hand", 1)
    assert "T1107" in _defns(e, "bz", 0)      # 破壊されていない
    assert len(e.zlist("shield", 1)) == 4


def test_registered_opponent_strigger_usable_missing_civ(rules):
    """登録カード: 対照として、文明が欠けていれば
    ブレイクされた T006 は S・トリガーを宣言でき、
    使えば攻撃側（パワー2000）が破壊され、呪文は
    墓地に置かれる。"""
    e = _build(rules,
               {"bz": MISSING + ["T1107"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T1107", 0, break_defn="T006", use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 1 and "strigger:T006" in st[0][2]
    assert "T1107" in _defns(e, "graveyard", 0)
    assert "T006" in _defns(e, "graveyard", 1)
    assert len(e.zlist("shield", 1)) == 4
