"""再変換ラウンド422（第387弾 attack_count_this_turn）の記録テスト。

- 新規登録1件: dm25ex3-rp4s04 楽蛇の虚 フミガルド
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 火 / コスト5 / パワー6000 /
  デーモン・コマンド、mana 1、keywords
  [speed_attacker, double_breaker]、abilities
  [declare, replace] は構築済み〕に第387弾の
  確立形 static〔hand 常在型 {cost: {amount: -2,
  count: {turn_count: {kind: attack, owner: any,
  distinct: true}}}, cost_min: 1}〕を条項順の
  先頭へ1件足し、unsupported を外したもの。
  abilities は [static, declare, replace] の
  3件ちょうど、keywords は2件のまま。補完なし:
  partial の text は公式テキスト全文のまま）。
- 第1条項の体数読みは公式QA 47928（2025.12.19）で
  確定。turn_count の distinct: true は第387弾で
  追加した新規語彙で、本カードが初の登録カード。
- 正本判定は通常型: identity 実測で canon_id は
  対象 id 自身が正本。alias 3件（dm25ex3-rp4sec05 /
  dm25rp4-s04 / dm25rp4-sec05）はいずれも rejects に
  独自行が無く、登録形の source.aliases に入っている
  （validate が identity.aliases_for から自動付与）。
  alias 畳み込み0件・stale クリーンアップ0件・
  差し戻し0件。
- よく似た別 gap の attack_count_this_turn_condition
  （dm25ex3-014）は別ファミリーで対象外のまま。
- converted 10,366→10,367 / rejects 1,946→1,945、
  canonical 重なり0・漏れ0。attack_count_this_turn は
  完全解消（ファミリーはこの1件のみ）。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  dmrp08-023 の登録形の見直し・schema.py の
  turn_count への from 同期漏れ（第387弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第387弾本体と同形（対象を proto T1150 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第387弾の proto を流用: T1151（同一クリーチャーの
2回攻撃役）/ T001・T1139（別個体のアタッカー役）、
マナ役は T277。
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
from tests.test_vocab_pilot387 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm25ex3-rp4s04"
GAP = "attack_count_this_turn"
NAME = "楽蛇の虚 フミガルド"
ALIASES = ["dm25ex3-rp4sec05", "dm25rp4-s04", "dm25rp4-sec05"]


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


def test_round422_disposition():
    rej = _reject_rows()
    assert len(rej) == 1945
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10367
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == set()                  # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 5 and c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["デーモン・コマンド"]
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形3能力ちょうど（条項順）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 3
    assert not c.get("aliases")
    # alias 3件は source.aliases に入っている
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 5   # 3能力＋キーワード2件の展開
    # 類似 gap の別ファミリーには触っていない
    assert rej["dm25ex3-014"]["gaps"] == ["attack_count_this_turn_condition"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第387弾本体と同形、対象は登録カード） ----------

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


def _hand_cid(e, defn=TARGET):
    return next(c for c in e.zlist("hand", 0)
                if e.s.cards[c].defn == defn)


def test_registered_pay_cost_progression(rules):
    # 登録カード: 攻撃が無い間は素のコスト5、別個体の
    # 攻撃が進むごとに体数ぶん軽減される（1体→3、2体→1）。
    e = _build(rules, {"bz": ["T001", "T1139"], "hand": [TARGET]}, {})
    cid = _hand_cid(e)
    assert e.chars_ro(cid)["pay_cost"] == 5
    readings = []
    queue = ["attack:T001:player", "attack:T1139:player"]
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "declare_attack":
            hist = list(e.s.turn_counters.get("hist:attackers:0", []))
            readings.append((hist, e.chars_ro(cid)["pay_cost"]))
            e.answer([])   # 宣言は見送る
            continue
        if d["kind"] == "attack" and d.get("player") == 0 and queue:
            want = queue.pop(0)
            assert want in keys, keys
            e.answer([keys.index(want)])
            continue
        if d["kind"] == "charge" and d.get("player") == 1:
            break
        _answer_default(e, d)
    assert len(readings) == 2
    (h1, p1), (h2, p2) = readings
    assert len(h1) == 1 and p1 == 3          # 1体目の攻撃中: -2
    assert len(h2) == 2 and len(set(h2)) == 2 and p2 == 1   # 2体で -4


def test_registered_pay_cost_same_creature_twice(rules):
    # 公式QA 47928 の状況を登録カードで: 同じクリーチャーが
    # 攻撃→アンタップ→再攻撃しても体数は1体のまま
    # （pay_cost は 5-2=3。distinct でなければ 1 になる判別）。
    e = _build(rules, {"bz": ["T1151"], "hand": [TARGET]}, {})
    cid = _hand_cid(e)
    attacks = 0
    seen = None
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "declare_attack":
            e.answer([])
            continue
        if d["kind"] == "attack" and d.get("player") == 0:
            if "attack:T1151:player" in keys and attacks < 2:
                attacks += 1
                e.answer([keys.index("attack:T1151:player")])
                continue
            seen = (list(e.s.turn_counters.get("hist:attackers:0", [])),
                    e.chars_ro(cid)["pay_cost"])
            break
        _answer_default(e, d)
    assert attacks == 2
    assert seen is not None
    hist, pay = seen
    assert len(hist) == 2 and hist[0] == hist[1]   # 記録は同一 cid が2件
    assert pay == 3                                # 数えは1体ぶんだけ


def test_registered_ddd_declare_pays_reduced_cost(rules):
    # 実挙動: 2体目の攻撃で D・D・D を宣言すると、軽減後の
    # コスト1だけを払って登録カードが出る。
    e = _build(rules, {"bz": ["T001", "T1139"], "hand": [TARGET],
                       "mana": ["T277"] * 9}, {})
    queue = ["attack:T001:player", "attack:T1139:player"]
    declares = 0
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "declare_attack":
            declares += 1
            if declares == 2:
                idx = [i for i, k in enumerate(keys)
                       if k.startswith(f"declare:{TARGET}")]
                assert idx, keys
                e.answer([idx[0]])
            else:
                e.answer([])
            continue
        if d["kind"] == "attack" and d.get("player") == 0 and queue:
            want = queue.pop(0)
            assert want in keys, keys
            e.answer([keys.index(want)])
            continue
        if d["kind"] == "charge" and d.get("player") == 1:
            break
        _answer_default(e, d)
    assert declares >= 2
    assert any(e.s.cards[c].defn == TARGET for c in e.zlist("bz", 0))
    tapped = sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped)
    assert tapped == 1
