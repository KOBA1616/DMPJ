"""再変換ラウンド479（第445弾 fury_charge）の記録テスト。

- 新規登録1件: dmx12b-015 Tatsurion（提出形は
  partial の骨格〔text 公式全文、keywords
  [double_breaker]、abilities 未構築〕に第445弾の
  確立形 abilities 1件〔trigger {when: {event:
  move, to: bz, subject: self}, effect: [modify
  {select: {ref: self}, mod: {allow: [{action:
  attack_creature, other: {tapped: true}}]},
  duration: end_of_turn}]}〕を足し、unsupported を
  外したもの。登録形は提出形と完全一致〔source
  以外の全フィールド〕、abilities は trigger
  1件ちょうど、keywords [double_breaker]、text は
  公式全文）。
- 補完あり: abilities のみ（text・keywords は
  partial の時点で公式全文・完備）。
- alias 畳み込み0件（alias 無し。正本判定: 対象
  id を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1236 の notes 内参照のみ〕、
  identity 実測で canon_id は対象自身・
  aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔fury_charge〕の出力は対象1件ちょうど
  ＝巻き込みなし。fury_charge は完全解消）。
- converted 10,425→10,426 / rejects 1,886→1,885、
  canonical 重なり0・漏れ0。
- 本ラウンドは第445弾のエンジン修正
  （combat._attack_options）を含むバッチのため、
  回帰には第410弾本体と第445弾本体のマッハ
  ファイター判別を含めた（docs 記録参照）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from 同期
  漏れ（第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第445弾本体と同形（対象を proto T1236 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（アンタップ＝出たターン
攻撃不可）/ T008（タップ＝出たターン攻撃可・
パワー1000）。
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
from tests.test_vocab_pilot445_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot445 import NAME, TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmx12b-015"
GAP = "fury_charge"


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


def test_round479_disposition():
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
    assert c["abilities"][0]["kind"] == "trigger"
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == TEXT             # text は公式全文
    assert not (c.get("source") or {}).get("unsupported")
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    d = parse_card(c, TABLES)
    assert d.name == NAME
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第445弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif d["kind"] in ("declare_strigger", "declare_sback"):
        e.answer([])
    elif d["kind"] == "pay_mana":
        e.answer([0])
    elif d["kind"] == "yes_no":
        e.answer([keys.index("no")] if "no" in keys else [0])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _drive(e, play=None, attacks=(), arrange=None, stop=None,
           limit=3000):
    st = {"played": False, "attack_options": [], "done": []}
    queue = list(attacks)
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if arrange:
            arrange(e, d)
        if d["kind"] == "attack":
            st["attack_options"].append((d.get("player"), e.s.turn, keys))
        if stop and stop(e, d, st):
            return st
        if play and not st["played"] and d["kind"] == "main" \
                and d.get("player") == 0 and f"play:{play}" in keys:
            e.answer([keys.index(f"play:{play}")])
            st["played"] = True
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


def _tap(e, p, defn):
    e.s.cards[_cid(e, p, defn)].tapped = True


def _atk_keys(st, player, turn, attacker):
    out = []
    for p, t, keys in st["attack_options"]:
        if p == player and t == turn:
            out += [k for k in keys
                    if k and k.startswith(f"attack:{attacker}:")]
    return out


def _first_attack_stop(player, turn):
    def stop(e, d, st):
        return d["kind"] == "attack" and d.get("player") == player \
            and e.s.turn == turn
    return stop


# ---------- 登録カード dmx12b-015（フュリー・チャージ） ----------

def test_registered_entry_turn_attacks_tapped_only(rules):
    """登録カード: 出たターンにタップした T008 だけを
    攻撃でき、アンタップの T001 とプレイヤーは
    攻撃できない（エンジン修正が登録カードでも効く）。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": ["T1234"] * 6},
               {"bz": ["T001", "T008"]})
    _tap(e, 1, "T008")
    st = _drive(e, play=TARGET, stop=_first_attack_stop(0, 1))
    assert st["played"]
    assert _atk_keys(st, 0, 1, TARGET) == [f"attack:{TARGET}:T008"]


def test_registered_entry_turn_battle_destroys_tapped(rules):
    """登録カード: 出たターンにタップした T008 を攻撃
    するとバトルで破壊し、本体は場に残る（6000 vs 1000）。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": ["T1234"] * 6},
               {"bz": ["T001", "T008"]})
    _tap(e, 1, "T008")
    t008 = _cid(e, 1, "T008")

    def stop(eng, d, st):
        return eng.s.cards[t008].zone == "graveyard"

    st = _drive(e, play=TARGET, attacks=[f"attack:{TARGET}:T008"],
                stop=stop)
    assert st["done"] == [f"attack:{TARGET}:T008"]
    assert e.s.cards[t008].zone == "graveyard"
    assert e.s.cards[_cid(e, 0, TARGET)].zone == "bz"


def test_registered_entry_turn_no_legal_target(rules):
    """登録カード: 出たターンにタップした相手クリー
    チャーがいなければ、攻撃選択肢は一切出ない
    （プレイヤーも不可）。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": ["T1234"] * 6},
               {"bz": ["T001"]})

    def stop(eng, d, st):
        return d["kind"] == "charge" and d.get("player") == 1

    st = _drive(e, play=TARGET, stop=stop)
    assert st["played"]
    assert _atk_keys(st, 0, 1, TARGET) == []
    assert e.s.cards[_cid(e, 0, TARGET)].zone == "bz"
    assert e.s.cards[_cid(e, 1, "T001")].zone == "bz"


def test_registered_next_turn_is_normal_creature(rules):
    """登録カード: 翌ターン以降は通常のクリーチャー
    （プレイヤーとタップした T008 は攻撃できるが、
    アンタップの T001 は攻撃できない＝modify 切れで
    対象は広がらない）。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": ["T1234"] * 6},
               {"bz": ["T001", "T008"]})

    def arrange(eng, d):
        # 相手ターン中、T008 をタップ状態に保つ
        # （タップは charge / main の判断でのみ行う＝第442弾の作法）
        if eng.s.active == 1 and d["kind"] in ("charge", "main"):
            _tap(eng, 1, "T008")

    st = _drive(e, play=TARGET, arrange=arrange,
                stop=_first_attack_stop(0, 3))
    keys = _atk_keys(st, 0, 3, TARGET)
    assert f"attack:{TARGET}:player" in keys
    assert f"attack:{TARGET}:T008" in keys
    assert f"attack:{TARGET}:T001" not in keys
