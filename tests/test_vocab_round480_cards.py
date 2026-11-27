"""再変換ラウンド480（第446弾 blocker_cost_restriction）の記録テスト。

- 新規登録1件: dmr05-105 ヌケッピ・サンナン
  （提出形は partial の骨格〔text 公式全文、
  keywords [hunting]、abilities 未構築〕に
  第446弾の確立形 abilities 1件〔static
  {affects: self, mod: {deny: [{action:
  be_blocked, other: {cost_le: 6}}]}}〕を足し、
  unsupported を外したもの。登録形は提出形と
  完全一致〔source 以外の全フィールド〕、
  abilities は static 1件ちょうど、keywords
  [hunting]、text は公式全文）。
- 補完あり: abilities のみ（text・keywords は
  partial の時点で公式全文・完備）。
- alias 畳み込み0件（alias 無し。正本判定: 対象
  id を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1237 の notes 内参照のみ〕、
  identity 実測で canon_id は対象自身・
  aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔blocker_cost_restriction〕の出力は
  対象1件ちょうど＝巻き込みなし。
  blocker_cost_restriction は完全解消）。
- converted 10,426→10,427 / rejects 1,885→1,884、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from 同期
  漏れ（第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第446弾本体と同形（対象を proto T1237 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T309（コスト6ブロッカー・
パワー5000＝境界）/ T120（コスト7ブロッカー・
パワー9000）/ T797（コスト2・パワー2500＝
ハンティング判別）/ T040（コスト7・パワー6000
＝被攻撃判別）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402
from tests.test_vocab_pilot446_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot446 import NAME, TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr05-105"
GAP = "blocker_cost_restriction"


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


def test_round480_disposition():
    rej = _reject_rows()
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 1
    assert c["abilities"][0]["kind"] == "static"
    assert c["keywords"] == ["hunting"]
    assert c["text"] == TEXT             # text は公式全文
    assert not (c.get("source") or {}).get("unsupported")
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    d = parse_card(c, TABLES)
    assert d.name == NAME
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第446弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif d["kind"] in ("declare_strigger", "declare_sback"):
        e.answer([])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _drive(e, attacks=(), blocker=None, stop=None, limit=1500):
    st = {"done": [], "block_logs": []}
    queue = list(attacks)
    for _ in range(limit):
        if stop and stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "block":
            st["block_logs"].append(list(keys))
            if blocker:
                hit = [i for i, k in enumerate(keys)
                       if k and k.startswith(f"bz:{blocker}")]
                if hit:
                    e.answer([hit[0]])
                    continue
            e.answer([keys.index("no_block")])
            continue
        if queue and d["kind"] == "attack" and queue[0] in keys:
            e.answer([keys.index(queue[0])])
            st["done"].append(queue.pop(0))
            continue
        _answer_default(e, d)
    raise AssertionError("driver limit reached")


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    # bz は共有ゾーンなのでコントローラーまで見て引く
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == p)


def _zone(e, cid):
    return e.s.cards[cid].zone


# ---------- 登録カード dmr05-105（ブロック制限） ----------

def test_registered_cost6_blocker_cannot_block(rules):
    """登録カード: 境界のコスト6ブロッカー T309
    （パワー5000）はブロックできない。block 決定の
    選択肢に bz:T309 が現れず、攻撃が通って
    シールドが1枚割れる。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T309"]})
    src = _cid(e, 0, TARGET)
    blk = _cid(e, 1, "T309")
    st = _drive(e, attacks=[f"attack:{TARGET}:player"],
                stop=lambda: len(e.zlist("shield", 1)) == 4)
    assert st["done"] == [f"attack:{TARGET}:player"]
    assert all(not any(k and k.startswith("bz:T309") for k in ks)
               for ks in st["block_logs"])
    assert _zone(e, src) == "bz"
    assert _zone(e, blk) == "bz"
    assert not e.s.cards[blk].tapped


def test_registered_cost7_blocker_can_block(rules):
    """登録カード: コスト7ブロッカー T120
    （パワー9000）はブロックできる: 選択肢に
    bz:T120 が現れ、ブロックするとバトル
    （ハンティングで3000 vs 9000）で登録カードは
    破壊され、シールドは減らない。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T120"]})
    src = _cid(e, 0, TARGET)
    blk = _cid(e, 1, "T120")
    st = _drive(e, attacks=[f"attack:{TARGET}:player"], blocker="T120",
                stop=lambda: _zone(e, src) == "graveyard")
    assert st["done"] == [f"attack:{TARGET}:player"]
    assert any(any(k and k.startswith("bz:T120") for k in ks)
               for ks in st["block_logs"])
    assert _zone(e, blk) == "bz"
    assert len(e.zlist("shield", 1)) == 5


def test_registered_hunting_power_in_battle(rules):
    """登録カード: ハンティングの判別 — タップした
    T797（パワー2500）を攻撃すると、バトル中の
    パワーは 2000＋1000（自分のハンター＝自身）
    ＝3000 になり T797 を破壊して場に残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T797"]})
    src = _cid(e, 0, TARGET)
    tgt = _cid(e, 1, "T797")
    e.s.cards[tgt].tapped = True
    st = _drive(e, attacks=[f"attack:{TARGET}:T797"],
                stop=lambda: _zone(e, tgt) == "graveyard")
    assert st["done"] == [f"attack:{TARGET}:T797"]
    assert _zone(e, src) == "bz"


def test_registered_can_be_attacked_normally(rules):
    """登録カード: deny は be_blocked だけなので、
    登録カードは通常どおり攻撃される: プレイヤーを
    攻撃してタップした登録カードを、コスト7の
    T040 が攻撃でき、バトル（6000 vs バトル中
    3000）で登録カードは破壊される。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T040"]})
    src = _cid(e, 0, TARGET)
    atk = _cid(e, 1, "T040")
    st = _drive(e, attacks=[f"attack:{TARGET}:player",
                            f"attack:T040:{TARGET}"],
                stop=lambda: _zone(e, src) == "graveyard")
    assert st["done"] == [f"attack:{TARGET}:player",
                          f"attack:T040:{TARGET}"]
    assert _zone(e, atk) == "bz"
