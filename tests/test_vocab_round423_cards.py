"""再変換ラウンド423（第388弾 battle_opponent_reference）の記録テスト。

- 新規登録1件: dm24rp4-065 カンテ＝ランタン
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 闇 / コスト2 / パワー1000 /
  アビスロイヤル、mana 1、keywords・abilities
  ともに無し〕に第388弾の確立形2能力〔攻撃側
  trigger {battle_start, subject: self} → modify
  {ref: event.opponent, power: -3000,
  duration: during_attack}、守備側 trigger
  {battle_start, opponent: self} → modify
  {ref: event.subject, power: -3000,
  duration: during_attack}〕を足し、unsupported を
  外したもの。abilities はこの2件ちょうど、
  keywords は無いまま。補完あり: partial の text は
  条項の断片のみのため、text には行の公式テキスト
  全文を入れた）。
- 正本判定は通常型: identity 実測で canon_id は
  対象 id 自身が正本、alias は無い。alias
  畳み込み0件・stale クリーンアップ0件・
  差し戻し0件。
- ファミリーのもう1件 dmr01-049 は対象外:
  reopen の出力は対象1件ちょうどだった（dmr01-049
  の行には reason が無く、reopen の reason: vocab
  条件に該当しないため外れなかった。第388弾の
  見込み＝2件とは異なる実測）。差し戻しは不要で、
  dmr01-049 は gaps = [battle_opponent_reference]・
  partial 無しの元の形のまま rejects に残る。
  battle_opponent_reference は完全解消しない
  （1件残る）。
- converted 10,367→10,368 / rejects 1,945→1,944
  （reopen −1 のみ）、canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ
  （第387弾で観察）は本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第388弾本体と同形（対象を proto T1152 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第388弾の proto を流用: T1153（パワー3500
ブロッカー／アタッカー）。
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
from tests.test_vocab_pilot388 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm24rp4-065"
OTHER = "dmr01-049"
GAP = "battle_opponent_reference"
NAME = "カンテ＝ランタン"


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


def test_round423_disposition():
    rej = _reject_rows()
    assert len(rej) == 1944
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10368
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == {OTHER}                # ファミリーは解消せず1件残る
    # dmr01-049 は元の形のまま（gaps・text のみ、partial 無し）
    assert rej[OTHER]["gaps"] == [GAP]
    assert "partial" not in rej[OTHER]
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 2 and c["power"] == 1000 and c["mana"] == 1
    assert c["races"] == ["アビスロイヤル"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形2能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 2
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第388弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")] if "yes" in keys
                 else list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _drive_battle(e, attack_key, block_defn=None, done=None, limit=400):
    for _ in range(limit):
        if done and done():
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if done and done():
            return True
        if d["kind"] == "attack" and attack_key in keys:
            e.answer([keys.index(attack_key)])
            continue
        if d["kind"] == "block":
            if block_defn:
                hit = [i for i, k in enumerate(keys)
                       if k.startswith(f"bz:{block_defn}")]
                if hit:
                    e.answer([hit[0]])
                    continue
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
                continue
        _answer_default(e, d)
    return done() if done else False


def test_registered_attacking_side_wins_against_3500(rules):
    # 登録カードの攻撃側: カンテ（1000）がプレイヤーを攻撃し、
    # パワー3500ブロッカーにブロックされる。-3000 で相手は
    # 500 になりカンテが勝つ（修整が無ければカンテが負ける判別）。
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1153"]})
    kante = _cid(e, 0, TARGET)
    wall = _cid(e, 1, "T1153")
    ok = _drive_battle(
        e, f"attack:{TARGET}:player", block_defn="T1153",
        done=lambda: e.s.cards[wall].zone == "graveyard")
    assert ok, "登録カードの -3000 が効かず、3500ブロッカーを破壊できなかった"
    assert e.s.cards[wall].zone == "graveyard"
    assert e.s.cards[kante].zone == "bz"


def test_registered_defending_side_wins_against_3500(rules):
    # 登録カードの守備側: タップしたカンテがパワー3500に
    # 攻撃される。opponent: self の誘発で攻撃側は 500 に
    # なりカンテが勝つ（修整が無ければカンテが負ける判別）。
    e = _build(rules, {"bz": ["T1153"]}, {"bz": [TARGET]})
    atk = _cid(e, 0, "T1153")
    kante = _cid(e, 1, TARGET)
    e.s.cards[kante].tapped = True
    ok = _drive_battle(
        e, f"attack:T1153:{TARGET}", block_defn=None,
        done=lambda: e.s.cards[atk].zone == "graveyard")
    assert ok, "登録カードの守備側 -3000 が効かず、3500のアタッカーを破壊できなかった"
    assert e.s.cards[atk].zone == "graveyard"
    assert e.s.cards[kante].zone == "bz"
