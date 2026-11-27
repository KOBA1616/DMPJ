"""再変換ラウンド481（第447弾 attack_target_power_filter）の記録テスト。

- 新規登録1件: dmr15-030 勇気伝承 ゲット Jr.
  （提出形は partial の骨格〔名称・文明・コスト2・
  パワー2000・種族 ヒューマノイド爆・マナ1〕に
  公式全文の text と第447弾の確立形 abilities
  2件〔マナ武装 3: static {affects: self, if:
  {cmp: [count mana fire >= 3]}, mod: {deny:
  [{action: be_attacked, other: {cost_le: 4}}]}}／
  マナ武装 5: static {affects: self, if: {cmp:
  [count mana fire >= 5]}, mod: {power_when:
  {amount: 4000, when: attacking}, grant:
  [double_breaker]}}〕を足し、unsupported を
  外したもの。登録形は提出形と完全一致
  〔source 以外の全フィールド〕、abilities は
  static 2件ちょうど、keywords は無し、text は
  公式全文）。
- 補完あり: text（公式全文。partial の text は
  第1条項の断片のみ）＋abilities（static 2件とも）。
- alias 畳み込み0件（alias は dmr15-030d /
  promoy13-066 の2件で rejects に独自行なし、
  登録エントリの source.aliases にのみ収載。
  正本判定: 対象 id と alias 2件を real /
  real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし、identity
  実測で canon は両 alias とも対象自身、
  aliases_for = [dmr15-030d, promoy13-066]）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔attack_target_power_filter〕の出力は
  対象1件ちょうど＝巻き込みなし。
  attack_target_power_filter は完全解消）。
- converted 10,427→10,428 / rejects 1,884→1,883、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from 同期
  漏れ（第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第447弾本体と同形（対象を proto T1238 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T282（自然 / コスト4・
パワー3000＝境界の攻撃役／バトル相手）/
T468（火＝マナ役）。
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
from tests.test_vocab_pilot447_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot447 import NAME, TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr15-030"
GAP = "attack_target_power_filter"
ALIASES = ["dmr15-030d", "promoy13-066"]


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


def test_round481_disposition():
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
    assert len(c["abilities"]) == 2
    assert all(a["kind"] == "static" for a in c["abilities"])
    assert not c.get("keywords")         # keywords は付いていない
    assert c["text"] == TEXT             # text は公式全文
    assert not (c.get("source") or {}).get("unsupported")
    assert c["source"]["aliases"] == ALIASES
    assert canon_id(TARGET) == TARGET
    for a in ALIASES:
        assert canon_id(a) == TARGET
    assert aliases_for(NAME, TARGET) == ALIASES
    d = parse_card(c, TABLES)
    assert d.name == NAME
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第447弾本体と同形、対象は登録カード） ----------

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


def _drive(e, attacks=(), arrange=None, stop=None, limit=1500):
    st = {"done": [], "attack_options": []}
    queue = list(attacks)
    for _ in range(limit):
        if stop and stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if arrange:
            arrange(e, d)
        if d["kind"] == "attack":
            st["attack_options"].append((d.get("player"), keys))
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


def _tap_on_turn(e, p, defn):
    def arrange(eng, d):
        if eng.s.active == p and d["kind"] in ("charge", "main"):
            for c in eng.zlist("bz", p):
                if eng.s.cards[c].defn == defn \
                        and eng.s.cards[c].controller == p:
                    eng.s.cards[c].tapped = True
    return arrange


def _attack_keys(st, player, attacker):
    out = []
    for p, keys in st["attack_options"]:
        if p == player:
            out += [k for k in keys
                    if k and k.startswith(f"attack:{attacker}:")]
    return out


FIRE_MANA = "T468"   # 火（マナ役）


# ---------- 登録カード dmr15-030（マナ武装 3 / 5） ----------

def test_registered_mana3_cost4_attacker_cannot_attack(rules):
    """登録カード: 火マナ3枚（境界）でコスト4の
    T282 は登録カードを攻撃できない。攻撃判断の
    選択肢に attack:T282:dmr15-030 が現れず、
    プレイヤーへの攻撃は通常どおりできて
    シールドが1枚割れる。登録カードは場に残る。"""
    e = _build(rules,
               {"bz": [TARGET], "mana": [FIRE_MANA] * 3},
               {"bz": ["T282"]})
    src = _cid(e, 0, TARGET)
    st = _drive(e, attacks=["attack:T282:player"],
                arrange=_tap_on_turn(e, 0, TARGET),
                stop=lambda: len(e.zlist("shield", 0)) <= 4)
    assert st["done"] == ["attack:T282:player"]
    keys = _attack_keys(st, 1, "T282")
    assert "attack:T282:player" in keys
    assert f"attack:T282:{TARGET}" not in keys
    assert len(e.zlist("shield", 0)) == 4
    assert _zone(e, src) == "bz"


def test_registered_mana2_cost4_attacker_can_attack(rules):
    """登録カード: 火マナ2枚（条件未達）では
    コスト4の T282 が登録カードを攻撃でき、
    バトル（3000 vs 2000）で登録カードは
    破壊される。"""
    e = _build(rules,
               {"bz": [TARGET], "mana": [FIRE_MANA] * 2},
               {"bz": ["T282"]})
    src = _cid(e, 0, TARGET)
    atk = _cid(e, 1, "T282")
    st = _drive(e, attacks=[f"attack:T282:{TARGET}"],
                arrange=_tap_on_turn(e, 0, TARGET),
                stop=lambda: _zone(e, src) == "graveyard")
    assert st["done"] == [f"attack:T282:{TARGET}"]
    assert _zone(e, atk) == "bz"


def test_registered_mana5_power_attacker_and_double_breaker(rules):
    """登録カード: 火マナ5枚でパワーアタッカー
    +4000 を得て、タップした T282（3000）を
    バトル中6000で破壊して場に残り、翌ターンの
    プレイヤー攻撃でシールドを2つブレイクする
    （W・ブレイカー）。"""
    e = _build(rules,
               {"bz": [TARGET], "mana": [FIRE_MANA] * 5},
               {"bz": ["T282"]})
    src = _cid(e, 0, TARGET)
    tgt = _cid(e, 1, "T282")
    e.s.cards[tgt].tapped = True
    st = _drive(e, attacks=[f"attack:{TARGET}:T282",
                            f"attack:{TARGET}:player"],
                stop=lambda: len(e.zlist("shield", 1)) <= 3)
    assert st["done"] == [f"attack:{TARGET}:T282",
                          f"attack:{TARGET}:player"]
    assert _zone(e, tgt) == "graveyard"
    assert _zone(e, src) == "bz"
    assert len(e.zlist("shield", 1)) == 3


def test_registered_mana4_no_power_attacker(rules):
    """登録カード: 火マナ4枚（第2条項は未達）では
    パワーアタッカーを得ず、タップした T282
    （3000）とのバトルは 2000 で負けて登録
    カードは破壊される。"""
    e = _build(rules,
               {"bz": [TARGET], "mana": [FIRE_MANA] * 4},
               {"bz": ["T282"]})
    src = _cid(e, 0, TARGET)
    tgt = _cid(e, 1, "T282")
    e.s.cards[tgt].tapped = True
    st = _drive(e, attacks=[f"attack:{TARGET}:T282"],
                stop=lambda: _zone(e, src) == "graveyard")
    assert st["done"] == [f"attack:{TARGET}:T282"]
    assert _zone(e, tgt) == "bz"


def test_registered_mana4_single_break(rules):
    """登録カード: 火マナ4枚では W・ブレイカーも
    得ず、プレイヤー攻撃のブレイクは1枚だけ。"""
    e = _build(rules,
               {"bz": [TARGET], "mana": [FIRE_MANA] * 4},
               {"bz": ["T001"]})
    src = _cid(e, 0, TARGET)
    st = _drive(e, attacks=[f"attack:{TARGET}:player"],
                stop=lambda: len(e.zlist("shield", 1)) <= 4)
    assert st["done"] == [f"attack:{TARGET}:player"]
    assert len(e.zlist("shield", 1)) == 4
    assert _zone(e, src) == "bz"
