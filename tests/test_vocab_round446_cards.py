"""再変換ラウンド446（第411弾 madness）の記録テスト。

- 新規登録1件: dmx18-047 有毒類罠顎目 ドクゲーター
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 自然 / コスト5 / パワー4000 /
  種族 ジュラシック・コマンド・ドラゴン、mana 1、
  keywords・abilities ともに無し〕に第411弾の
  確立形 abilities 2件〔第1条項: replace {zone:
  hand, optional: true, when: {event: move,
  from: hand, to: graveyard, reason: discard,
  subject: self, by: opp}, instead: [move
  {select: {ref: self, count: 1}, to: bz,
  reason: put}]}（登録済み dm26ex3-dcr005 と
  完全一致）／第2条項: trigger {when: {event:
  move, to: bz, subject: self}, effect: [choose
  {select: {zone: bz, owner: opp, filter:
  {cost_le: 4}, count: 1}, as: pick}, mana_put
  {select: {ref: pick}}]}（第389弾形のフィルタ
  違い。文面は「カード」のため types は絞らない）〕
  を足し、unsupported を外したもの。abilities は
  この2件ちょうど、keywords は無いまま）。
- 補完あり: text のみ（partial の text は断片
  「捨てられる時」のため、行の公式テキスト全文＝
  第411弾の FULL_TEXT を入れ、登録後の全文一致も
  照合済み）。
- split は None で定型所有が無く登録ブロッカーなし。
- alias 畳み込み0件（alias は無し。identity 実測で
  canon_id は対象自身、aliases_for = []。正本判定は
  通常型で対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1179 の
  notes 内参照のみ〕）。
- stale クリーンアップ0件・差し戻し1件
  （reopen〔madness〕の出力は2件。ファミリーの
  残り1件 dmx26-028 熱血提督 ザーク・タイザーは
  unsupported を残した partial のまま差し戻し、
  rejects に gaps・partial を保って残ることを
  実測確認。madness は完全解消しない）。
- converted 10,390→10,391 / rejects 1,921→1,920、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from 同期漏れ
  （第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第411弾本体と同形（対象を proto T1179 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（コスト2クリーチャー役・
自然マナ役）/ T116（コスト6役＝候補外の判別）/
T117（相手の手札を捨てさせる呪文役）/ T118
（自分の手札を捨てる呪文役）/ T189（コスト3
タマシード役＝「カード」判別）/ T008（闇マナ役）。
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
from tests.test_vocab_pilot411 import EXPANDED, FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmx18-047"
REMAINING = "dmx26-028"
GAP = "madness"
NAME = "有毒類罠顎目 ドクゲーター"


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


def test_round446_disposition():
    rej = _reject_rows()
    assert len(rej) == 1920
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10391
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == [REMAINING]            # ファミリーは解消しない
    # 差し戻し行は gaps・partial を保ったまま残る
    b = rej[REMAINING]
    assert b["reason"] == "vocab" and b["gaps"] == [GAP]
    bp = b["partial"]
    assert bp["id"] == REMAINING
    assert bp["name"] == "熱血提督 ザーク・タイザー"
    assert (bp.get("source") or {}).get("unsupported") == [
        {"need": GAP, "text": "捨てる時、かわりにバトルゾーンに出す"}]
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ジュラシック・コマンド・ドラゴン"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完は text のみ）
    # 登録形は提出形と完全一致: abilities は確立形2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("keywords")          # text 由来キーワードは union されない
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し（自動付与なし）
    d = parse_card(c, TABLES)
    assert d.abilities == EXPANDED
    assert not d.keywords
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第411弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _zone_card(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn)


def _settle(e, done, drive, max_steps=300):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    return done()


def _discard_drive(caster, victim, accept=True):
    """第411弾と同型の駆動: player 0 が caster を唱え、
    victim を捨てさせ、置換の諾否を選ぶ。"""
    st = {"played": False}

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 \
                and not st["played"]:
            k = f"play:{caster}"
            if k in keys:
                st["played"] = True
                e.answer([keys.index(k)])
                return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer(list(range(d["min"])))
            return True
        if d["kind"] == "choose_replacement":
            if accept:
                hit = [i for i, k in enumerate(keys)
                       if "replace:" in k]
                if hit:
                    e.answer([hit[0]])
                    return True
            else:
                if "pass" in keys:
                    e.answer([keys.index("pass")])
                    return True
                hit = [i for i, k in enumerate(keys)
                       if "replace:" not in k]
                if hit:
                    e.answer([hit[0]])
                    return True
        if d["kind"] == "choose_cards":
            hit = [i for i, k in enumerate(keys) if victim in k]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    return drive


def test_madness_replace_puts_into_bz(rules):
    """第1条項の実挙動: 相手の呪文（T117）で捨てられる時、
    置換を選べば墓地ではなくバトルゾーンに出る。"""
    e = _build(rules, {"hand": ["T117"], "mana": ["T008"] * 4},
               {"hand": [TARGET]})
    v = _zone_card(e, "hand", 1, TARGET)
    assert _settle(e, lambda: e.s.cards[v].zone == "bz",
                   _discard_drive("T117", TARGET, True))
    assert v in e.zlist("bz", 1)
    assert v not in e.zlist("graveyard", 1)


def test_madness_replace_is_optional(rules):
    """第1条項は任意: 置換を断れば墓地に置かれる。"""
    e = _build(rules, {"hand": ["T117"], "mana": ["T008"] * 4},
               {"hand": [TARGET]})
    v = _zone_card(e, "hand", 1, TARGET)
    assert _settle(e, lambda: e.s.cards[v].zone == "graveyard",
                   _discard_drive("T117", TARGET, False))
    assert v not in e.zlist("bz", 1)


def test_madness_not_triggered_by_own_spell(rules):
    """by: opp の判別: 自分の呪文（T118）で自分の手札から
    捨てる時は置換が発火せず、墓地に行く。"""
    e = _build(rules,
               {"hand": ["T118", TARGET], "mana": ["T008"] * 2},
               {})
    v = _zone_card(e, "hand", 0, TARGET)
    assert _settle(e, lambda: e.s.cards[v].zone == "graveyard",
                   _discard_drive("T118", TARGET, True))
    assert v not in e.zlist("bz", 0)


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _summon(rules, p1, choose_defn=None):
    """p0 が登録カードを召喚し、CIP の choose に答えて
    解決まで進める（第411弾と同型）。"""
    e = _build(rules, {"hand": [TARGET], "mana": ["T001"] * 5}, p1)
    played = False
    chose = False
    key = f"play:{TARGET}"
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and key in keys:
            played = True
            e.answer([keys.index(key)])
            continue
        if played and d["kind"] == "choose_cards":
            chose = True
            idx = [i for i, o in enumerate(d["options"])
                   if choose_defn in o["key"]]
            assert idx, f"{choose_defn} が選択肢に無い: {keys}"
            e.answer(idx[:1])
            continue
        if played and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, played, chose


def _mana_defns(e, p):
    return [e.cdef(c).id for c in e.zlist("mana", p)]


def _bz_defns(e, p):
    """バトルゾーンは共有ゾーンのため controller で絞る。"""
    return [e.cdef(c).id for c in e.zlist("bz", p)
            if e.s.cards[c].controller == p]


def test_cip_cost2_creature_to_owner_mana(rules):
    """第2条項の実挙動: 相手のコスト2クリーチャー（T001）を
    選ぶと、持ち主（相手）のマナゾーンに置かれる。"""
    e, played, chose = _summon(rules, {"bz": ["T001"]}, "T001")
    assert played
    assert chose is False           # 候補1枚では選択判断が出ず自動で決まる
    assert _mana_defns(e, 1) == ["T001"]
    assert _bz_defns(e, 1) == []
    assert TARGET in _bz_defns(e, 0)


def test_cip_tamaseed_is_a_candidate(rules):
    """「カード」の判別（types フィルタ無し）: 相手の
    タマシード（T189、コスト3）も対象になり、持ち主の
    マナゾーンに置かれる。"""
    e, played, chose = _summon(rules, {"bz": ["T189"]}, "T189")
    assert played
    assert _mana_defns(e, 1) == ["T189"]
    assert _bz_defns(e, 1) == []


def test_cip_cost6_is_not_a_candidate(rules):
    """cost_le: 4 の判別: 相手のコスト6（T116）は候補に
    ならず、バトルゾーンに留まりマナゾーンにも行かない。"""
    e, played, chose = _summon(rules, {"bz": ["T116"]})
    assert played
    assert chose is False
    assert _mana_defns(e, 1) == []
    assert _bz_defns(e, 1) == ["T116"]


def test_cip_fires_when_entering_via_madness(rules):
    """複合判別: マッドネス置換でバトルゾーンに出た時も
    第2条項は発火する。相手（p0）のコスト2（T001）が
    持ち主（p0）のマナゾーンに置かれる。"""
    e = _build(rules, {"bz": ["T001"], "hand": ["T117"],
                       "mana": ["T008"] * 4},
               {"hand": [TARGET]})
    v = _zone_card(e, "hand", 1, TARGET)
    t = _zone_card(e, "bz", 0, "T001")
    assert _settle(e, lambda: e.s.cards[t].zone == "mana",
                   _discard_drive("T117", TARGET, True))
    assert e.s.cards[v].zone == "bz"
    assert t in e.zlist("mana", 0)
    assert t not in e.zlist("bz", 0)
