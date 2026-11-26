"""再変換ラウンド445（第410弾 force_block）の記録テスト。

- 新規登録1件: dmr09-004 剛鉄突破 アイアンローズ
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 光 / コスト7 / パワー6000 /
  種族 アウトレイジMAX、mana 1、keywords
  [double_breaker]、abilities 無し〕に第410弾の
  確立形 abilities 2件〔第1条項: static {affects:
  {zone: bz, owner: opp, filter: {types:
  [creature]}}, mod: {grant: [blocker], require:
  [block]}}／第2条項: static {affects: self, mod:
  {power: {amount: 2000, count: {zone: bz, owner:
  opp, filter: {types: [creature]}}}}}}〕を足し、
  unsupported を外したもの。abilities はこの
  2件ちょうど、keywords は [double_breaker]
  のまま）。
- 補完なし（partial の text は公式全文と一致。
  登録後の全文一致も照合済み）。
- split の part[2] 定型所有は空のためツール側
  ブロッカーなし。
- alias 畳み込み0件（alias は無し。identity 実測で
  canon_id は対象自身、aliases_for = []。正本判定は
  通常型で対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1178 の
  notes 内参照のみ〕）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔force_block〕の出力は対象1件ちょうど）。
- converted 10,389→10,390 / rejects 1,922→1,921、
  canonical 重なり0・漏れ0。force_block は完全解消。
- 第410弾のエンジン修正（combat.py: ブロック宣言で
  タップするのは選ばれた1体だけ。強制は no_block
  選択肢を消すことで効く）が登録と同時に効く。
  require の強制自体の Rust 未実装は既存の乖離で
  本ラウンドでは触っていない。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from 同期漏れ
  （第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第410弾本体と同形（対象を proto T1178 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（攻撃役・自軍バニラ役）/
T1091（相手バニラ役）/ T1090（相手の印刷スピード
アタッカー役）。タップ状態の観測は防御側のターン
開始アンタップより前、同ターンの次の攻撃決定時点
で行う（第410弾の作法）。
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
from tests.test_vocab_pilot410 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr09-004"
GAP = "force_block"
NAME = "剛鉄突破 アイアンローズ"


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


def test_round445_disposition():
    rej = _reject_rows()
    assert len(rej) == 1921
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10390
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリーは完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"]
    assert c["civs"] == ["light"]
    assert c["cost"] == 7 and c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["アウトレイジMAX"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は確立形2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["keywords"] == ["double_breaker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し（自動付与なし）
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 3          # double_breaker 派生 static 込み
    for a in FORM:
        assert a in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第410弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, defn, p, nth=0):
    return [c for c in e.bz_tops(p) if e.cdef(c).id == defn][nth]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _attack_player(e, attacker_key):
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended before attack"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0:
            assert attacker_key in keys, keys
            e.answer([keys.index(attacker_key)])
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("attack never happened")


def _next_block_decision(e, limit=300):
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return None
        if d["kind"] == "block":
            return d
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def _next_attack_decision(e, limit=300):
    """player 0 の次の攻撃決定（同一ターンの攻撃ステップ
    継続）まで進めて返す。タップ状態の観測は防御側の
    ターン開始アンタップより前のこの時点で行う。"""
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return None
        if d["kind"] == "attack" and d.get("player") == 0:
            return d
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def _settle_until(e, done, limit=600):
    for _ in range(limit):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return done()


def test_registered_chars_discrimination(rules):
    """特性レベルの判別: 相手のクリーチャー（バニラ・
    印刷スピードアタッカーとも）は blocker と
    require [block] を得る。自分のクリーチャーと
    発生源自身は得ない。"""
    e = _build(rules,
               {"bz": [TARGET, "T001"]},
               {"bz": ["T1091", "T1090"]})
    src = _cid(e, TARGET, 0)
    own = _cid(e, "T001", 0)
    opp_v = _cid(e, "T1091", 1)
    opp_sa = _cid(e, "T1090", 1)
    for c in (opp_v, opp_sa):
        ch = e.chars(c)
        assert "blocker" in ch["keywords"]
        assert "block" in ch["require"]
    for c in (src, own):
        ch = e.chars(c)
        assert "blocker" not in ch["keywords"]
        assert "block" not in ch["require"]


def test_registered_power_scales_with_opponent_creatures(rules):
    """第2条項: パワーは相手のクリーチャー1体につき
    +2000（自分のクリーチャーは数えない）。"""
    e = _build(rules, {"bz": [TARGET]}, {})
    assert e.chars(_cid(e, TARGET, 0))["power"] == 6000
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1091"]})
    assert e.chars(_cid(e, TARGET, 0))["power"] == 8000
    e = _build(rules, {"bz": [TARGET, "T001"]},
               {"bz": ["T1091", "T1091"]})
    assert e.chars(_cid(e, TARGET, 0))["power"] == 10000


def test_registered_opponent_must_block_and_only_chosen_taps(rules):
    """第1条項の実挙動＋第410弾エンジン修正の判別:
    相手のバニラ2体は両方ともブロッカーを得て
    強制される（no_block は出ない）。ブロックするのは
    選ばれた1体だけで、選ばれなかった側はタップ
    しない（修正前は強制全員がタップしていた）。"""
    e = _build(rules,
               {"bz": [TARGET, "T002", "T002"]},
               {"bz": ["T1091", "T1091"]})
    b0 = _cid(e, "T1091", 1, 0)
    b1 = _cid(e, "T1091", 1, 1)
    _attack_player(e, "attack:T002:player")
    d = _next_block_decision(e)
    assert d is not None and d["player"] == 1
    keys = _keys(d)
    assert "no_block" not in keys
    block_opts = [i for i, o in enumerate(d["options"])
                  if o.get("cid") in (b0, b1)]
    assert len(block_opts) == 2
    chosen, other = b0, b1
    e.answer([next(i for i, o in enumerate(d["options"])
                   if o.get("cid") == chosen)])
    # 同一ターンの次の攻撃決定時点で観測する
    d = _next_attack_decision(e)
    assert d is not None
    # ブロックされたのでシールドは割れていない
    assert len(e.zlist("shield", 1)) == 5
    # 選ばれた1体はタップし、選ばれなかった強制
    # クリーチャーはタップしていない
    assert e.s.cards[chosen].tapped is True
    assert other in e.bz_tops(1)
    assert e.s.cards[other].tapped is False


def test_registered_no_source_no_block(rules):
    """対照: 登録カードが無ければ相手のバニラは
    ブロックできず、攻撃は通ってシールドが
    1枚割れる。"""
    e = _build(rules, {"bz": ["T001"]}, {"bz": ["T1091", "T1091"]})
    _attack_player(e, "attack:T001:player")
    d = _next_block_decision(e)
    assert d is None
    assert _settle_until(e, lambda: len(e.zlist("shield", 1)) == 4)


def test_registered_tapped_opponent_creature_does_not_force(rules):
    """「可能であれば」の判別: 相手のクリーチャーが
    タップ状態ならブロックできず、強制も働かない
    （攻撃は通る）。"""
    e = _build(rules,
               {"bz": [TARGET, "T001"]},
               {"bz": ["T1091"]})
    opp = _cid(e, "T1091", 1)
    e.s.cards[opp].tapped = True
    _attack_player(e, "attack:T001:player")
    d = _next_block_decision(e)
    assert d is None
    assert _settle_until(e, lambda: len(e.zlist("shield", 1)) == 4)
