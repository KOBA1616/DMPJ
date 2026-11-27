"""再変換ラウンド477（第443弾 no_untap_until_next_own_turn_start）の記録テスト。

- 新規登録1件: dm26rp1-s002 世界のY チャクラ・
  デル・フィン（提出形は partial〔クリーチャー /
  光 / コスト3 / パワー4000 / 種族 アポロニア・
  ドラゴン/超化獣、mana 1、keywords [z_rush]、
  text 公式全文（通常面）、abilities 4件構築済み〕
  に第443弾の確立形 abilities 1件〔第2条項
  trigger {when: {event: move, to: shield,
  subject: {owner: you}}, effect: [choose
  {select: {zone: bz, owner: opp, filter:
  {types: [creature]}, count: 1}, as: t},
  tap {select: {ref: t, count: all}},
  modify {select: {ref: t, count: all},
  mod: {deny: [untap_at_start]},
  duration: until_next_own_turn_start}]}〕を
  第1条項（CIP シールド化 trigger）の直後に挿入し、
  hyper: true フィールドを足し、unsupported を
  外したもの。登録形は提出形と完全一致〔source
  以外の全フィールドを照合〕、abilities は5件
  ちょうど〔順序: ハイパー時パワー static /
  CIP trigger / 第2条項 trigger / ハイパー時
  grant static / ハイパー時 deny cast static〕、
  keywords [z_rush] のまま、hyper: true 保持、
  text は公式全文）。
- 補完あり: abilities（第2条項の trigger 1件）
  ＋hyper: true フィールド（partial に欠落。
  登録済み超化獣はすべてカードフィールド
  hyper: true を持ち、無いと {hyper: true}
  条件が満たされない）。
- alias 畳み込み0件（alias dm26rp1-sec003 は
  独自行が無く、登録エントリの source.aliases
  に validate が自動付与したのみ。正本判定:
  対象 id と alias を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1233 の
  notes 内参照のみ〕、identity 実測で canon_id
  は対象自身、aliases_for = [dm26rp1-sec003]）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔no_untap_until_next_own_turn_start〕
  の出力は対象1件ちょうど＝巻き込みなし。
  no_untap_until_next_own_turn_start は完全解消）。
- converted 10,422→10,423 / rejects 1,889→1,888、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from 同期
  漏れ（第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第443弾本体と同形（対象を proto T1233 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001 / T008（相手クリーチャー役）。
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
from tests.test_vocab_pilot443_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot443 import FULL_TEXT, NAME  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm26rp1-s002"
ALIAS = "dm26rp1-sec003"
GAP = "no_untap_until_next_own_turn_start"


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


def test_round477_disposition():
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
    # abilities は5件ちょうど（順序も照合）
    assert len(c["abilities"]) == 5
    order = [(a["kind"], (a.get("when") or {}).get("to"))
             for a in c["abilities"]]
    assert order == [("static", None), ("trigger", "bz"),
                     ("trigger", "shield"), ("static", None),
                     ("static", None)]
    assert c["keywords"] == ["z_rush"]   # keywords そのまま
    assert c.get("hyper") is True        # hyper: true 保持
    assert c["text"] == FULL_TEXT        # text は公式全文（通常面）
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]
    assert canon_id(TARGET) == TARGET
    assert canon_id(ALIAS) == TARGET
    assert aliases_for(NAME, TARGET) == [ALIAS]
    assert ALIAS not in rej              # alias の独自行は無い
    d = parse_card(c, TABLES)
    assert d.name == NAME and d.power == 4000
    assert len(d.abilities) == 5
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第443弾本体と同形、対象は登録カード） ----------

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


def _drive(e, choose_target=None, after=None,
           stop=None, limit=1200):
    st = {"charges": {0: 0, 1: 0}, "chose": 0}
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "charge":
            st["charges"][d["player"]] += 1
        if stop is not None and stop(e, d, st):
            return st
        if d["kind"] == "choose_cards" \
                and d.get("player") == 0 \
                and choose_target is not None:
            idx = next(i for i, o in enumerate(d["options"])
                       if o.get("cid") == choose_target)
            e.answer([idx])
            st["chose"] += 1
        else:
            _answer_default(e, d)
        if after is not None:
            after(e, d, st)
    raise AssertionError("driver limit reached")


def _inject_once(fn, kind, player):
    state = {"done": False}

    def after(e, d, st):
        if not state["done"] and d["kind"] == kind \
                and d.get("player") == player:
            state["done"] = True
            fn(e)
    after.state = state
    return after


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == p)


def _shieldize_inject(e, player=0):
    top = e.zlist("deck", player)[0]
    e._push(e.ev_task([{"ev": "move",
                        "subject": e.s.ref(top),
                        "to": "shield", "reason": "put"}]))


def _at_charge(player, turn):
    def stop(e, d, st):
        return d["kind"] == "charge" \
            and d.get("player") == player \
            and e.s.turn == turn
    return stop


def test_clause2_flow_resolved_on_own_turn(rules):
    """登録カード: 自分のターン中にシールド化 →
    相手の T001 を選んでタップ＋アンタップ否定。
    相手ターン1のはじめにはアンタップせず、自分の
    ターン2のはじめで期限が切れ、相手ターン2の
    はじめに通常どおりアンタップする。選ばなかった
    T008 は無影響。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T002", "T002"]},
               {"bz": ["T001", "T008"]})
    tgt = _cid(e, 1, "T001")
    other = _cid(e, 1, "T008")
    inj = _inject_once(lambda eng: _shieldize_inject(eng, 0),
                       "charge", 0)
    st = _drive(e, choose_target=tgt, after=inj,
                stop=_at_charge(1, 2))
    assert inj.state["done"]
    assert st["chose"] == 1
    assert e.s.cards[tgt].tapped
    assert e.permits(tgt, "untap_at_start") is False
    assert not e.s.cards[other].tapped
    assert e.permits(other, "untap_at_start") is True
    st = _drive(e, choose_target=tgt, stop=_at_charge(0, 3))
    assert e.permits(tgt, "untap_at_start") is True
    assert e.s.cards[tgt].tapped
    st = _drive(e, choose_target=tgt, stop=_at_charge(1, 4))
    assert not e.s.cards[tgt].tapped


def test_clause2_flow_resolved_on_opponent_turn(rules):
    """登録カード: 相手のターン中にシールド化 →
    第2条項が解決しても期限は「次の自分のターンの
    はじめまで」なので、自分のターン開始で deny は
    消え、相手は次の自分のターンのはじめに通常
    どおりアンタップする（フリーズ形との判別）。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T002", "T002"]},
               {"bz": ["T001", "T008"], "hand": ["T002"],
               "mana": ["T002", "T002"]})
    tgt = _cid(e, 1, "T001")
    inj = _inject_once(lambda eng: _shieldize_inject(eng, 0),
                       "main", 1)
    st = _drive(e, choose_target=tgt, after=inj,
                stop=_at_charge(0, 3))
    assert inj.state["done"]
    assert st["chose"] == 1
    assert e.s.cards[tgt].tapped
    assert e.permits(tgt, "untap_at_start") is True
    st = _drive(e, choose_target=tgt, stop=_at_charge(1, 4))
    assert not e.s.cards[tgt].tapped


def test_clause2_already_tapped_target_still_denied(rules):
    """登録カード: すでにタップしているクリーチャーを
    選んでも「アンタップしない」は付く。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T002", "T002"]},
               {"bz": ["T001", "T008"]})
    tgt = _cid(e, 1, "T001")
    e.s.cards[tgt].tapped = True
    inj = _inject_once(lambda eng: _shieldize_inject(eng, 0),
                       "charge", 0)
    st = _drive(e, choose_target=tgt, after=inj,
                stop=_at_charge(1, 2))
    assert inj.state["done"]
    assert st["chose"] == 1
    assert e.s.cards[tgt].tapped
    assert e.permits(tgt, "untap_at_start") is False


def test_clause2_no_opponent_creature(rules):
    """登録カード: 相手のクリーチャーがいなければ
    第2条項は空転し、ゲームは通常どおり進む。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T002", "T002"]},
               {"bz": []})
    inj = _inject_once(lambda eng: _shieldize_inject(eng, 0),
                       "charge", 0)
    st = _drive(e, after=inj, stop=_at_charge(1, 2))
    assert inj.state["done"]
    assert st["chose"] == 0
    assert len(e.zlist("shield", 0)) == 6


def test_cip_shieldize_chains_into_clause2(rules):
    """登録カードが出た時、第1条項で自分の山札の
    上1枚がシールド化され、それ自体が第2条項を
    誘発させる: シールドが6枚になり、相手の T001 が
    タップされアンタップ否定が付く（期限切れ後は
    通常どおりアンタップする）。"""
    e = _build(rules, {"hand": [TARGET]},
               {"bz": ["T001", "T008"], "hand": ["T002"],
                "mana": ["T002", "T002"]})
    src = next(c for c in e.zlist("hand", 0)
               if e.s.cards[c].defn == TARGET)
    tgt = _cid(e, 1, "T001")

    def enter(eng):
        eng._push(eng.ev_task([{"ev": "move",
                                "subject": eng.s.ref(src),
                                "to": "bz", "reason": "summon"}]))
    inj = _inject_once(enter, "main", 1)
    st = _drive(e, choose_target=tgt, after=inj,
                stop=_at_charge(0, 3))
    assert inj.state["done"]
    assert st["chose"] == 1
    assert len(e.zlist("shield", 0)) == 6
    assert e.s.cards[tgt].tapped
    st = _drive(e, choose_target=tgt, stop=_at_charge(1, 4))
    assert not e.s.cards[tgt].tapped
