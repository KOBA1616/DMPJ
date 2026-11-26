"""再変換ラウンド453（第418弾 all_civilizations_mana）
の記録テスト。

- 新規登録1件: dm26sd1-u010 怪盗妖精カサブランカ /
  「信じていたのに裏切られるなんて！」（ツインパクト。
  登録形は提出形と完全一致: partial の骨格は使わず、
  faces 構造＋第418弾の確立形で組んだもの
  〔クリーチャー面（自然 / コスト3 / パワー2000 /
  種族 スノーフェアリー）: trigger（move to bz,
  subject: self → move {select: {zone: deck,
  owner: you, from_top: 1}, to: mana, reason: put}）
  （第376弾・登録済み dmex14-083 等の形）＋ static
  {affects: {zone: mana, owner: you}, mod:
  {add_civs: [light, water, darkness, fire,
  nature]}}（第376弾の確立形、登録済み dmex01-014
  と同文・同形）＋ trigger {when: {event: move,
  from: hand, to: mana, subject: {owner: you}},
  effect: [untap {select: {ref: event.subject}}]}
  （登録済み dm24bd5-033 の監視誘発から first_time と
  multicolor フィルタを外し、文面どおり from: hand
  を付加した形）／呪文面（水 / コスト6）: keywords
  [s_trigger] ＋ spell [bounce {select: {zone: bz,
  owner: any, filter: {types: [creature],
  cost_ge: 5}, count: all}}]〕。クリーチャー面の
  abilities は3件ちょうど、呪文面の spell は1 op、
  呪文面 keywords [s_trigger] は保持される）。
- 補完あり: faces 構造＋text（partial は骨格のみで
  faces 無し・text は第2条項の断片のため、両面とも
  公式全文を使用し、最上位 text は両面を「 ／ 」で
  連結。登録後の全文一致も照合済み）。
- split は None で定型所有なし＝ツール側
  ブロッカーなし。
- alias 畳み込み0件（alias 3件 dm24bd5-010 /
  dm25ex3-tf27 / dm25rp4-t09 は rejects に独自行
  なし。対象 id と alias 3件を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし、identity 実測で canon_id は
  対象自身・alias 側の canon も dm26sd1-u010、
  aliases_for = 3件。登録エントリの source.aliases
  は提出形の3件がそのまま保持）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔all_civilizations_mana〕の出力は対象
  1件ちょうど＝巻き込みなし）。
- converted 10,397→10,398 / rejects
  1,914→1,913、canonical 重なり0・漏れ0。
  all_civilizations_mana は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第418弾本体と同形（対象を proto T1189 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（自然バニラ・マナ役）/
T002（フィラー）/ T030（光水の多色＝タップ入り
判別役）/ T277（火・コスト2＝支払い判別役）/
T1139（コスト5・パワー6000役）/ T008（コスト2・
闇役）。
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
from tests.test_vocab_pilot418 import (  # noqa: E402
    CREATURE_ABILITIES, FULL_TEXT, NAME, PARSED_SPELL, SPELL)

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm26sd1-u010"
GAP = "all_civilizations_mana"
ALIASES = ["dm24bd5-010", "dm25ex3-tf27", "dm25rp4-t09"]


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


def test_round453_disposition():
    rej = _reject_rows()
    assert len(rej) == 1913
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10398
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は登録で解消
    for a in ALIASES:
        assert a not in rej              # alias に独自行なし
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["mana"] == 1
    assert c["text"] == FULL_TEXT        # 公式全文（両面「 ／ 」連結）
    f0, f1 = c["faces"]
    assert f0["types"] == ["creature"] and f0["civs"] == ["nature"]
    assert f0["cost"] == 3 and f0["power"] == 2000
    assert f0["races"] == ["スノーフェアリー"]
    # 登録形は提出形と完全一致: クリーチャー面の
    # abilities は3件ちょうど、呪文面の spell は1 op、
    # 呪文面 keywords [s_trigger] が保持される
    assert f0["abilities"] == CREATURE_ABILITIES
    assert len(f0["abilities"]) == 3
    assert f1["types"] == ["spell"] and f1["civs"] == ["water"]
    assert f1["cost"] == 6
    assert f1["spell"] == SPELL
    assert len(f1["spell"]) == 1
    assert f1["keywords"] == ["s_trigger"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert sorted(src.get("aliases") or []) == sorted(ALIASES)
    d = parse_card(c, TABLES)
    pf0, pf1 = d.faces
    assert len(pf0.abilities) == 3
    for a in CREATURE_ABILITIES:
        assert a in pf0.abilities
    assert pf1.spell == PARSED_SPELL
    assert pf1.keywords == ["s_trigger"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第418弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1, filler="T002"):
    return scenario.build(rules, {"p0": p0, "p1": p1, "filler": filler,
                                  "seed": 1, "deck_size": 20})


def _in_zone(e, p, zone, defn):
    return [c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn]


def _step_default(e, d):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "pay_mana":
        e.answer(list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    elif "no_block" in keys:
        e.answer([keys.index("no_block")])
    elif d["kind"] == "declare_strigger":
        e.answer([])
    else:
        e.answer(list(range(d.get("min", 0))))


def _play_creature_face(e, done, limit=600):
    played = False
    for _ in range(limit):
        if played and done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and f"play:{TARGET}:0" in keys:
            played = True
            e.answer([keys.index(f"play:{TARGET}:0")])
            continue
        _step_default(e, d)
    return done()


def test_cip_puts_deck_top_to_mana(rules):
    """第1条項の実挙動: 登録カードが出た時、山札の
    上から1枚がマナゾーンに置かれる（マナ+1・山札-1）。"""
    e = _build(rules, {"hand": [TARGET], "mana": ["T001", "T001", "T001"]},
               {})
    deck0, mana0 = len(e.zlist("deck", 0)), len(e.zlist("mana", 0))
    ok = _play_creature_face(e, lambda: bool(_in_zone(e, 0, "bz", TARGET)))
    assert ok
    assert len(e.zlist("mana", 0)) == mana0 + 1
    assert len(e.zlist("deck", 0)) == deck0 - 1


def test_cip_move_does_not_trigger_clause3(rules):
    """from: hand の判別: 第1条項で山札からマナに
    置かれた多色カード（フィラー T030）は 405.1 で
    タップして置かれ、第3条項ではアンタップされない
    （手札からではないため）。"""
    e = _build(rules, {"hand": [TARGET], "mana": ["T001", "T001", "T001"]},
               {}, filler="T030")
    ok = _play_creature_face(e, lambda: bool(_in_zone(e, 0, "bz", TARGET)))
    assert ok
    moved = _in_zone(e, 0, "mana", "T030")
    assert len(moved) == 1
    assert e.s.cards[moved[0]].tapped is True


def test_mana_all_civs_chars(rules):
    """第2条項の特性判別: 登録カードがいれば自分の
    マナの自然カードはすべての文明を持ち、いなければ
    自然のみ。"""
    e = _build(rules, {"bz": [TARGET], "mana": ["T001"]}, {})
    cid = _in_zone(e, 0, "mana", "T001")[0]
    assert sorted(e.chars(cid)["civs"]) == [
        "darkness", "fire", "light", "nature", "water"]
    e2 = _build(rules, {"mana": ["T001"]}, {})
    cid2 = _in_zone(e2, 0, "mana", "T001")[0]
    assert sorted(e2.chars(cid2)["civs"]) == ["nature"]


def _main_keys(e, player):
    for _ in range(300):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player:
            return keys
        _step_default(e, d)
    return None


def test_pay_fire_cost_with_nature_mana(rules):
    """第2条項の支払い判別: 登録カードがいれば自然
    マナだけで火コスト（T277）を支払える。対照では
    支払えない。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T277"],
                       "mana": ["T001", "T001"]}, {})
    assert "play:T277" in _main_keys(e, 0)
    e2 = _build(rules, {"hand": ["T277"], "mana": ["T001", "T001"]}, {})
    assert "play:T277" not in _main_keys(e2, 0)


def _charge_and_read(e, player, tid):
    """player の最初の charge で tid を置き、同ターン内に
    収まる範囲で誘発解決まで進めてから tapped を読む
    （第418弾本体と同形）。"""
    for _ in range(300):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and d.get("player") == player:
            hit = [i for i, k in enumerate(keys) if tid in k]
            if not hit:
                _step_default(e, d)
                return None
            turn = e.s.turn
            e.answer([hit[0]])
            for _ in range(40):
                if e.s.turn != turn:
                    break
                d2 = e.advance()
                if d2 is None:
                    break
                _step_default(e, d2)
                if e.s.turn != turn:
                    break
            m = _in_zone(e, player, "mana", tid)
            return e.s.cards[m[0]].tapped if m else None
        _step_default(e, d)
    return None


def test_charge_multicolor_untapped_by_clause3(rules):
    """第3条項の実挙動: 登録カードがいれば、手札から
    マナに置いた多色カード（T030、405.1 でタップして
    置かれる）は誘発でアンタップされる。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T030"]}, {})
    assert _charge_and_read(e, 0, "T030") is False


def test_charge_multicolor_control_stays_tapped(rules):
    """対照: 登録カードがなければ、多色カードは
    タップしたまま置かれる。"""
    e = _build(rules, {"hand": ["T030"]}, {})
    assert _charge_and_read(e, 0, "T030") is True


def test_opponent_charge_not_untapped(rules):
    """subject {owner: you} の判別: 相手が手札から
    マナに置いた多色カードはアンタップされない。"""
    e = _build(rules, {"bz": [TARGET]}, {"hand": ["T030"]})
    assert _charge_and_read(e, 1, "T030") is True


def test_spell_face_bounces_all_cost_ge_5(rules):
    """呪文面の実挙動: 登録カードの呪文面を実行すると、
    コスト5以上のクリーチャーは両プレイヤーとも
    すべて持ち主の手札に戻り、コスト2は残る。"""
    e = _build(rules,
               {"hand": [TARGET],
                "mana": ["T030", "T001", "T001", "T001", "T001", "T001"],
                "bz": ["T1139", "T001"]},
               {"bz": ["T1139", "T008"]})
    cast = False
    for _ in range(600):
        if cast and not _in_zone(e, 0, "bz", "T1139"):
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and f"play:{TARGET}:1" in keys:
            cast = True
            e.answer([keys.index(f"play:{TARGET}:1")])
            continue
        _step_default(e, d)
    assert cast
    assert not _in_zone(e, 0, "bz", "T1139")
    assert _in_zone(e, 0, "hand", "T1139")
    assert _in_zone(e, 0, "bz", "T001")          # コスト2は残る
    assert not _in_zone(e, 1, "bz", "T1139")
    assert _in_zone(e, 1, "hand", "T1139")
    assert _in_zone(e, 1, "bz", "T008")          # 相手のコスト2も残る
