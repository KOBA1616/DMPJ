"""再変換ラウンド426（第391弾 battle_duration）の記録テスト。

- 新規登録1件: dmd15-005 ギャノバズガ・ドラゴン
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 火 / コスト5 / パワー4000 /
  種族 アーマード・ドラゴン、mana 1、
  keywords 無し〕に第391弾の確立形 static
  〔affects {zone: bz, owner: you, filter:
  {types: [creature], civs: [fire]}}, mod:
  {battle_power: {amount: 3000}}〕1件を足し、
  unsupported を外したもの。abilities は
  この1件ちょうど、keywords は無いまま。
  **補完あり**: partial の text は条項の断片
  （「バトルする時、そのバトルの終わりまで」）
  のため、text には行の公式テキスト全文を入れた）。
- 正本判定は通常型: identity 実測で canon_id は
  対象 id 自身が正本、alias は無い。alias
  畳み込み0件・stale クリーンアップ0件・
  差し戻し0件。
- reopen（battle_duration）の出力は対象1件
  ちょうど（対象行は reason == "vocab" で
  gaps = [battle_duration]）。
  battle_duration は完全解消。
- converted 10,370→10,371 / rejects 1,942→1,941
  （reopen −1 のみ）、canonical 重なり0・漏れ0。
- 確立形は第122弾の battle_power（バトル中だけの
  パワー修整）の他者付与形で、登録先例
  dmrp15-040 / dmr17-054 と同型。他者付与経路は
  第342弾で実装済み。新規フィールドではないが、
  回帰に test_data_audit を含めて確認済み。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ
  （第387弾で観察）は本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第391弾本体と同形（発生源を proto T1156 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第391弾の proto T1157（火・2000）/ T1140
（火・4000ブロッカー）/ T1155（光・6000
ブロッカー）を流用。
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
from tests.test_vocab_pilot391 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmd15-005"
GAP = "battle_duration"
NAME = "ギャノバズガ・ドラゴン"


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


def test_round426_disposition():
    rej = _reject_rows()
    assert len(rej) == 1941
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10371
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == set()                  # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["アーマード・ドラゴン"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 1
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第391弾本体と同形、発生源は登録カード） ----------

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


def _cid(e, p, card_id):
    return next(c for c in e.zlist("bz", p)
                if e.cdef(c).id == card_id)


def _drive_battle(e, attack_key, block_id=None, done=None, limit=400):
    """attack_key で攻撃し、block_id があればそのカードで
    ブロックさせる。done() が真になるまで進める。"""
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
            if block_id:
                hit = [i for i, k in enumerate(keys)
                       if k.startswith(f"bz:{block_id}")]
                if hit:
                    e.answer([hit[0]])
                    continue
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
                continue
        _answer_default(e, d)
    return done() if done else False


def test_registered_grant_attacking_side(rules):
    """登録カード: 攻撃側への付与 — 自分の火獣（2000）が
    プレイヤーを攻撃し、パワー4000ブロッカーにブロック
    される。+3000 で 5000 になって勝つ。"""
    e = _build(rules, {"bz": [TARGET, "T1157"]}, {"bz": ["T1140"]})
    beast = _cid(e, 0, "T1157")
    wall = _cid(e, 1, "T1140")
    ok = _drive_battle(
        e, "attack:T1157:player", block_id="T1140",
        done=lambda: e.s.cards[wall].zone == "graveyard")
    assert ok, "登録カードの battle_power +3000 付与が効かなかった"
    assert e.s.cards[wall].zone == "graveyard"
    assert e.s.cards[beast].zone == "bz"


def test_registered_source_itself_battles(rules):
    """登録カード: 発生源自身も「自分の火のクリーチャー」に
    含まれる — 登録カード自身（4000）がプレイヤーを攻撃し、
    パワー6000ブロッカーにブロックされる。+3000 で 7000 に
    なって勝つ。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1155"]})
    src = _cid(e, 0, TARGET)
    wall = _cid(e, 1, "T1155")
    ok = _drive_battle(
        e, f"attack:{TARGET}:player", block_id="T1155",
        done=lambda: e.s.cards[wall].zone == "graveyard")
    assert ok, "登録カード自身が battle_power +3000 を受けなかった"
    assert e.s.cards[wall].zone == "graveyard"
    assert e.s.cards[src].zone == "bz"


def test_registered_grant_defending_side(rules):
    """登録カード: 守備側への付与＋相手の火は対象外 —
    相手の火（4000）がタップした自分の火獣（2000）を
    攻撃する。守備側は +3000 で 5000 になって勝ち、
    攻撃側の火は owner: you（発生源から見て相手）の
    ため +3000 を受けない。"""
    e = _build(rules, {"bz": ["T1140"]}, {"bz": [TARGET, "T1157"]})
    atk = _cid(e, 0, "T1140")
    beast = _cid(e, 1, "T1157")
    e.s.cards[beast].tapped = True
    ok = _drive_battle(
        e, "attack:T1140:T1157", block_id=None,
        done=lambda: e.s.cards[atk].zone == "graveyard")
    assert ok, "守備側の火への +3000 が効かなかった／相手の火が +3000 を受けた"
    assert e.s.cards[atk].zone == "graveyard"
    assert e.s.cards[beast].zone == "bz"
