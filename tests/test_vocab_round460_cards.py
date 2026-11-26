"""再変換ラウンド460（第425弾 battle_power_filter）の
記録テスト。

- 新規登録1件: dmr08-009 巨体の守護者ランチュン
  （partial の骨格〔クリーチャー / 光 / コスト3 /
  パワー4000 / 種族 ガーディアン、mana 1、keywords
  [blocker, cannot_attack_player]〕に第425弾の
  確立形 ability 1件〔static {affects: self, mod:
  {battle_power: {amount: 2000, opponent_filter:
  {cost_le: 6}}}}〕（第122弾の battle_power
  {amount, opponent_filter} のフィルタ差し替え版。
  第377弾 civs 版・第378弾 power_ge 版と同型の
  ドリフト）を足し、unsupported を外したもの。
  登録形は提出形と完全一致、abilities はこの
  static 1件ちょうど、keywords は [blocker,
  cannot_attack_player] のまま）。
- 補完なし（partial の text は公式全文、登録後も
  照合済み）。
- split はキーワードのみ定型所有で part[2] は空
  ＝ツール側ブロッカーなし。
- alias 畳み込み0件（alias 無し。正本判定は通常型:
  対象 id を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1201 の notes 内参照のみ〕、
  identity 実測で canon_id は対象自身、
  aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔battle_power_filter〕の出力は対象1件
  ちょうど＝巻き込みなし）。
- converted 10,404→10,405 / rejects
  1,907→1,906、canonical 重なり0・漏れ0。
  battle_power_filter は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第425弾本体と同形（対象を proto T1201 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1202（コスト5／パワー5000:
上限以下で +2000 が付く役）/ T1203（コスト7／
パワー5000: 上限超えで加算が付かない対照役）。
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
from tests.test_vocab_pilot425 import FULL_TEXT, STATIC  # noqa: E402
from tests.test_vocab_pilot425_cards import SUBMIT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr08-009"
GAP = "battle_power_filter"
NAME = "巨体の守護者ランチュン"


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


def test_round460_disposition():
    rej = _reject_rows()
    assert len(rej) == 1906
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10405
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["mana"] == 1
    assert c["text"] == FULL_TEXT        # 公式全文
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    # 登録後は abilities が static 1件ちょうど・
    # keywords [blocker, cannot_attack_player] のまま
    assert c["abilities"] == [STATIC]
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["blocker", "cannot_attack_player"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities
    assert d.keywords == ["blocker", "cannot_attack_player"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第425弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _blocked_battle(e, attacker_p, attacker, blocker):
    """attacker_p の attacker がプレイヤーを攻撃し、相手が
    blocker でブロックする。バトルが終わって attacker_p の
    次の charge が来たら戻る。"""
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == attacker_p \
                and state.get("blocked"):
            return state
        if d["kind"] == "attack" and d.get("player") == attacker_p \
                and not state.get("attacked"):
            tgt = [k for k in keys if k == f"attack:{attacker}:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blocker}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("battle never finished")


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tops(e, p):
    return [e.s.cards[c].defn for c in e.bz_tops(p)]


def test_block_beats_cost5_with_bonus(rules):
    # コスト5・パワー5000のアタッカーをブロック:
    # 素4000では負けるが +2000=6000 で勝つ（登録カード自身）
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1202"]})
    state = _blocked_battle(e, 1, "T1202", TARGET)
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1202" in _defns(e, "graveyard", 1)
    assert TARGET in _tops(e, 0)


def test_block_loses_to_cost7_without_bonus(rules):
    # コスト7・パワー5000のアタッカーをブロック:
    # コスト上限を超えるので加算は付かず 4000<5000 で負ける
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1203"]})
    state = _blocked_battle(e, 1, "T1203", TARGET)
    assert state.get("attacked") and state.get("blocked"), state
    assert TARGET in _defns(e, "graveyard", 0)
    assert "T1203" in _tops(e, 1)


def _attack_creature_battle(e, target):
    """p1 の target がプレイヤーを攻撃してタップした後、
    p0 の登録カードがそのタップした target を攻撃する。
    バトルが終わって p1 の次の charge が来たら戻る。"""
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1 \
                and state.get("battled"):
            return state
        if d["kind"] == "attack" and d.get("player") == 1 \
                and not state.get("p1_attacked"):
            tgt = [k for k in keys if k == f"attack:{target}:player"]
            if tgt:
                state["p1_attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "attack" and d.get("player") == 0 \
                and state.get("p1_attacked") and not state.get("battled"):
            tgt = [k for k in keys if k == f"attack:{TARGET}:{target}"]
            if tgt:
                state["battled"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("battle never finished")


def test_attack_beats_cost5_with_bonus(rules):
    # 攻撃側でも「バトル中」は効く（battle_power は only
    # 無しで両バトルに効く）: タップしたコスト5・
    # パワー5000 を攻撃し、+2000=6000 で勝つ
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1202"]})
    state = _attack_creature_battle(e, "T1202")
    assert state.get("p1_attacked") and state.get("battled"), state
    assert "T1202" in _defns(e, "graveyard", 1)
    assert TARGET in _tops(e, 0)


def test_attack_loses_to_cost7_without_bonus(rules):
    # タップしたコスト7・パワー5000 を攻撃: 加算は
    # 付かず 4000<5000 で負ける
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1203"]})
    state = _attack_creature_battle(e, "T1203")
    assert state.get("p1_attacked") and state.get("battled"), state
    assert TARGET in _defns(e, "graveyard", 0)
    assert "T1203" in _tops(e, 1)


def test_no_bonus_outside_battle(rules):
    # バトル中でなければパワーは素の 4000 のまま
    # （battle_power はバトル中専用の修整）
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1202"]})
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == TARGET)
    assert e.chars(cid)["power"] == 4000
