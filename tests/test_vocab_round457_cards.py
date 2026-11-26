"""再変換ラウンド457（第422弾 block_event_target）
の記録テスト。

- 新規登録1件: dmrp12-046 凶鬼79号 ジュージュ
  （partial の骨格〔クリーチャー / 闇 / コスト6 /
  パワー2000 / 種族 マフィ・ギャング、mana 1、
  keywords [s_trigger, blocker]〕に第422弾の
  確立形 abilities 2件〔(1) trigger {when:
  {event: block, subject: self}, effect:
  [modify {select: {ref: event.attacker},
  mod: {power: -9000}, duration: end_of_turn}]}
  （第401弾のブロック誘発＋第388弾の event 参照。
  対象は event.opponent ではなく event.attacker
  ＝block レコードの attacker キー、登録済み
  dmr16g-015 の先例）／(2) trigger {when:
  {event: turn_end}, if: {exists: {ref: self,
  filter: {tapped: true}}}, effect: [destroy
  {select: {ref: self}}]}（登録済み dmrp15-069
  の登録形そのもの）〕を足し、unsupported を
  外したもの。登録形は提出形と完全一致、
  abilities は2件ちょうど、keywords は
  [s_trigger, blocker] のまま。登録形では
  第2条項の destroy が parse で move
  {to: graveyard, reason: destroy} に正規化
  されることを照合済み）。
- 補完なし: partial の text は公式全文で、登録後の
  text も公式全文と完全一致を照合済み。
- split はキーワードのみ定型所有で part[2] は空
  ＝ツール側ブロッカーなし。
- alias 畳み込み0件（alias 無し。正本判定は通常型
  で対象 id を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1195 の notes 内参照のみ〕、
  identity 実測で canon_id は対象自身、
  aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件:
  reopen（block_event_target）の出力は対象1件
  ちょうど（巻き込みなし）。
- converted 10,401→10,402 / rejects
  1,910→1,909、canonical 重なり0・漏れ0。
  block_event_target は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第422弾本体と同形（対象を proto T1195 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1196（パワー5000）/ T1197
（パワー12000）/ T1198（パワー10000）/ T1126
（パワー8000ブロッカー＝第3条項の不発判別役）/
T001（パワー2000バニラ＝非対象・対照役）。
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
from tests.test_vocab_pilot422 import FORM, FULL_TEXT, PARSED_FORM  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmrp12-046"
GAP = "block_event_target"
NAME = "凶鬼79号 ジュージュ"


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


def test_round457_disposition():
    rej = _reject_rows()
    assert len(rej) == 1909
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10402
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 6 and c["power"] == 2000 and c["mana"] == 1
    assert c["races"] == ["マフィ・ギャング"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は2件
    # ちょうど、keywords はそのまま
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["keywords"] == ["s_trigger", "blocker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    for ab in PARSED_FORM:               # destroy は move に正規化
        assert ab in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第422弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "pay_mana":
        e.answer([0])
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


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _drive(e, attacker=None, blocker=None, stop=None, limit=600):
    st = {"attacked": False}
    for _ in range(limit):
        if stop and stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if attacker and not st["attacked"] and d["kind"] == "attack" \
                and attacker in keys:
            e.answer([keys.index(attacker)])
            st["attacked"] = True
            continue
        if d["kind"] == "block" and blocker:
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"bz:{blocker}")]
            if hit:
                e.answer([hit[0]])
                continue
        _answer_default(e, d)
    return st


def test_block_destroys_5000_attacker(rules):
    # 第3条項（登録カード自身）: パワー5000のアタッカーを
    # ブロックすると -9000 でパワー0以下になり破壊される。
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1196"]})
    atk = _cid(e, 1, "T1196")
    st = _drive(e, attacker="attack:T1196:player", blocker=TARGET,
                stop=lambda: e.s.cards[atk].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[atk].zone == "graveyard"


def test_block_reduces_12000_and_restores(rules):
    # 第3条項の対象と duration（登録カード自身）:
    # パワー12000は -9000 で 3000 になって勝ち、同じ
    # ターンの間は 3000 のまま。ブロックしていない
    # 相手の獣は修整を受けず、ターンが終われば戻る。
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1197", "T001"]})
    atk = _cid(e, 1, "T1197")
    blk = _cid(e, 0, TARGET)
    other = _cid(e, 1, "T001")
    st = _drive(e, attacker="attack:T1197:player", blocker=TARGET,
                stop=lambda: e.s.cards[blk].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[atk].zone == "bz"
    assert e.chars_ro(atk)["power"] == 3000
    assert e.chars_ro(other)["power"] == 2000
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "attack" and d.get("player") == 1:
            break
        _answer_default(e, d)
    assert e.chars_ro(atk)["power"] == 12000


def test_block_10000_attacker_loses_and_blocker_destroyed_at_turn_end(rules):
    # 第3+4条項の合成判別（登録カード自身）: パワー
    # 10000は -9000 で 1000 になって負け、ブロッカーは
    # タップしたまま生き残るが、ターンの終わりに
    # 第4条項で破壊される。
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1198"]})
    atk = _cid(e, 1, "T1198")
    blk = _cid(e, 0, TARGET)
    st = _drive(e, attacker="attack:T1198:player", blocker=TARGET,
                stop=lambda: e.s.cards[atk].zone == "graveyard"
                and e.s.cards[blk].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[atk].zone == "graveyard"
    assert e.s.cards[blk].zone == "graveyard"


def test_clause4_attacking_unblocked_destroyed_at_turn_end(rules):
    # 第4条項の単独判別（登録カード自身）: プレイヤーを
    # 攻撃してタップした発生源は、自分のターンの
    # 終わりに破壊される。
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    src = _cid(e, 0, TARGET)
    st = _drive(e, attacker=f"attack:{TARGET}:player",
                stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[src].zone == "graveyard"


def test_clause4_untapped_survives(rules):
    # 対照（登録カード自身）: タップしていなければ、
    # ターンの終わりを2回跨いでも破壊されない。
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    src = _cid(e, 0, TARGET)
    seen = {"n": 0}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "attack" and d.get("player") == 0:
            seen["n"] += 1
            if seen["n"] >= 2:
                break
        _answer_default(e, d)
    assert seen["n"] >= 2
    assert e.s.cards[src].zone == "bz"
    assert not e.s.cards[src].tapped


def test_no_reduction_when_attacking(rules):
    # 第3条項の不発判別（登録カード自身）: 発生源が
    # 攻撃側の時は発火せず、パワー8000ブロッカーは
    # 修整を受けない。
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1126"]})
    src = _cid(e, 0, TARGET)
    wall = _cid(e, 1, "T1126")
    st = _drive(e, attacker=f"attack:{TARGET}:player", blocker="T1126",
                stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[src].zone == "graveyard"
    assert e.s.cards[wall].zone == "bz"
    assert e.chars_ro(wall)["power"] == 8000
