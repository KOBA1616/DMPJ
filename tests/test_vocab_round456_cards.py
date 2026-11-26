"""再変換ラウンド456（第421弾 move_to_deck_bottom_trigger）
の記録テスト。

- 新規登録1件: dmex04-025 ヤッタレ総長
  （partial の骨格〔クリーチャー / 火 / コスト3 /
  パワー3000 / 種族 ジョーカーズ、mana 1〕に
  第421弾の確立形 abilities 2件〔(1) static
  {affects: {owner: you, zone: hand, filter:
  {types: [creature], race_has: ジョーカーズ,
  cost_ge: 7}}, mod: {cost_may: {amount: 1,
  min: 1}}}（partial 構築済み）／(2) trigger
  {when: {event: move, from: bz, to: deck,
  position: bottom, subject: {owner: you}},
  effect: [draw {count: 1}]}（第290弾の position
  照合＋登録済み dmrp06-001 形Dから cause を外し
  from: bz を足しドローを必須とした形）〕を足し、
  unsupported を外したもの。登録形は提出形と
  完全一致、abilities は2件ちょうど）。
- 補完なし: partial の text は公式全文で、登録後の
  text も公式全文と完全一致を照合済み。
- split は None で定型所有なし＝ツール側
  ブロッカーなし。
- alias 畳み込み0件（alias 3件 dmex02-041 /
  dmrp04s-050 / promoy16-087 は rejects に
  独自行なし、登録エントリの source.aliases に
  収載。正本判定は通常型で対象 id と alias 3件を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1192 の notes 内参照のみ〕、identity
  実測で canon_id は対象自身、alias 側の canon も
  dmex04-025、aliases_for = 3件）。
- stale クリーンアップ0件・差し戻し0件:
  reopen（move_to_deck_bottom_trigger）の出力は
  対象1件ちょうど（巻き込みなし）。
- converted 10,400→10,401 / rejects
  1,911→1,910、canonical 重なり0・漏れ0。
  move_to_deck_bottom_trigger は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第421弾本体と同形（対象を proto T1192 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T844（自分の呪文で自分の獣を
一番下へ＝駆動役）/ T842（相手の呪文で一番上へ
＝位置の対照役）/ T841（相手の呪文で自分の獣を
一番下へ＝原因の判別役）/ T1193（墓地から一番下
＝from 判別役）/ T1194（自分の獣2体を一度に
一番下＝枚数判別役）/ T1185（コスト7ジョーカーズ
＝第1条項の対象役）/ T001（自然バニラ＝移動対象役）/
T008（闇マナ役）/ T009（水マナ役）。
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
from tests.test_vocab_pilot421 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex04-025"
GAP = "move_to_deck_bottom_trigger"
NAME = "ヤッタレ総長"
ALIASES = ["dmex02-041", "dmrp04s-050", "promoy16-087"]


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


def test_round456_disposition():
    rej = _reject_rows()
    assert len(rej) == 1910
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10401
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    for a in ALIASES:
        assert a not in rej              # alias に独自行なし
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 3 and c["power"] == 3000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は2件
    # ちょうど（static＋trigger）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES
    d = parse_card(c, TABLES)
    for ab in FORM:
        assert ab in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第421弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "pay_mana":
        e.answer([0])
    elif d["kind"] == "choose_shields":
        e.answer(list(range(d["min"])))
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _counts(e):
    return (len(e.zlist("hand", 0)), len(e.zlist("deck", 0)),
            len(e.zlist("bz", 0)))


def _resolve_cast(e, caster, spell, choose=None):
    st = {}
    for _ in range(6000):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if not st.get("cast"):
            if d["kind"] == "main" and d.get("player") == caster \
                    and f"play:{spell}" in keys:
                st["before"] = _counts(e)
                st["cast"] = True
                e.answer([keys.index(f"play:{spell}")])
            else:
                _answer_default(e, d)
            continue
        if d["kind"] == "charge" and d.get("player") == 1 - caster:
            st["after"] = _counts(e)
            return st["before"], st["after"]
        if d["kind"] == "choose_cards" and choose is not None:
            e.answer(choose(keys))
            continue
        _answer_default(e, d)
    raise AssertionError(f"cast not resolved: {st}")


MANA_D = ["T008"] * 5   # 闇マナ役（T844 / T1193 の支払い用）
MANA_W = ["T009"] * 5   # 水マナ役（T841 / T842 / T1194 の支払い用）


def test_own_spell_bottom_draws(rules):
    # 第2条項（登録カード自身）: 自分の呪文で自分の獣を
    # 山札の一番下に置くと1枚引く。
    e = _build(rules,
               {"bz": [TARGET, "T001"], "hand": ["T844"],
                "mana": MANA_D},
               {"bz": []})
    before, after = _resolve_cast(e, 0, "T844")
    assert before == (1, 15, 2)
    assert after == (1, 15, 1)


def test_self_bottom_draws(rules):
    # 公式 QA 32439（登録カード自身）: 発生源自身が
    # 一番下に置かれた時も引ける（lki 発生源経路）。
    e = _build(rules,
               {"bz": [TARGET], "hand": ["T844"], "mana": MANA_D},
               {"bz": []})
    before, after = _resolve_cast(e, 0, "T844")
    assert before == (1, 15, 1)
    assert after == (1, 15, 0)


def test_top_does_not_draw(rules):
    # 対照: 一番「上」に置いた時は引けない（position 判別）。
    e = _build(rules,
               {"bz": [TARGET, "T001"], "mana": MANA_D},
               {"bz": [], "hand": ["T842"], "mana": MANA_W})
    before, after = _resolve_cast(e, 1, "T842")
    assert before == (0, 15, 2)
    assert after == (1, 15, 1)


def test_graveyard_bottom_does_not_draw(rules):
    # 対照: 墓地から一番下に置いた時は引けない（from: bz 判別）。
    e = _build(rules,
               {"bz": [TARGET], "graveyard": ["T001"],
                "hand": ["T1193"], "mana": MANA_D},
               {"bz": []})
    before, after = _resolve_cast(e, 0, "T1193")
    assert before == (1, 15, 1)
    assert after == (0, 16, 1)


def test_opponent_spell_bottom_draws(rules):
    # 原因の判別: 相手の呪文で自分の獣が一番下に
    # 置かれた時も引く（cause 無し）。
    e = _build(rules,
               {"bz": [TARGET, "T001"], "mana": MANA_D},
               {"bz": [], "hand": ["T841"], "mana": MANA_W})
    before, after = _resolve_cast(e, 1, "T841")
    assert before == (0, 15, 2)
    assert after == (2, 14, 1)


def test_two_cards_two_draws(rules):
    # 枚数の判別（公式 QA 31661 と同じ機構）: 自分の獣
    # 2体を一度に一番下に置くと2枚引く。発生源は場に残す。
    e = _build(rules,
               {"bz": [TARGET, "T001", "T001"], "hand": ["T1194"],
                "mana": MANA_W},
               {"bz": []})
    before, after = _resolve_cast(
        e, 0, "T1194",
        choose=lambda keys: [i for i, k in enumerate(keys)
                             if "T001" in k])
    assert before == (1, 15, 3)
    assert after == (2, 15, 1)


def test_clause1_cost_may_reduction(rules):
    # 第1条項（登録カード自身）: 発生源がいれば、コスト7の
    # ジョーカーズをマナ6枚（1軽減）で召喚できる。
    e = _build(rules,
               {"bz": [TARGET], "hand": ["T1185"],
                "mana": ["T001"] * 6},
               {"bz": []})
    st = {}
    for _ in range(6000):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("played"):
            assert "play:T1185" in keys, keys
            st["played"] = True
            e.answer([keys.index("play:T1185")])
            continue
        if st.get("played") and d["kind"] == "choose_cards" \
                and "reduce" in keys:
            st["reduce_offered"] = True
            e.answer([keys.index("reduce")])
            continue
        if st.get("played") and any(
                e.s.cards[c].defn == "T1185"
                for c in e.zlist("bz", 0)):
            tapped = sum(1 for c in e.zlist("mana", 0)
                         if e.s.cards[c].tapped)
            assert st.get("reduce_offered") is True
            assert tapped == 6
            return
        _answer_default(e, d)
    raise AssertionError(f"summon not finished: {st}")


def test_clause1_no_source_no_reduction(rules):
    # 対照: 発生源がいなければ、コスト7はマナ6枚では
    # 召喚できない。
    e = _build(rules,
               {"bz": [], "hand": ["T1185"], "mana": ["T001"] * 6},
               {"bz": []})
    for _ in range(6000):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "main" and d.get("player") == 0:
            assert "play:T1185" not in _keys(d)
            return
        _answer_default(e, d)
    raise AssertionError("main not reached")
