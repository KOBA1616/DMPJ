"""再変換ラウンド452（第417弾 battle_win_destroy）
の記録テスト。

- 新規登録1件: dmr11-051 護神のインガ イヌハッカ
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 光/闇 / コスト3 / パワー5500 /
  種族 オラクル、mana 1〕に第417弾の確立形
  〔free_if {exists: {zone: bz, owner: you,
  filter: {race_has: ゴッド}}}（G・ゼロ。登録済み
  dm22rp2x-tf14 の条件形と同一）＋ keywords
  [blocker, cannot_attack_player]（cannot_attack_
  player は同一文面の自己制限の標準形）＋ trigger
  {when: {event: battle_win, subject: self},
  effect: [destroy {select: {ref: self}}]}
  （第413弾の確立形、登録済み dm01-026 と完全
  一致）〕を足し、unsupported を外したもの。
  abilities はこの1件ちょうど、keywords は
  そのまま、free_if は保持される。第1条項
  「マナゾーンに置く時タップして置く」は多色
  ルール405.1でエンジン core が適用済み
  （第399弾）のため text のみ）。
- 補完あり: text のみ（partial の text は断片
  「バトルに勝っても破壊される」のため、行の
  公式テキスト全文を使用。登録後の全文一致も
  照合済み）。
- split は None で定型所有なし＝ツール側
  ブロッカーなし。
- alias 畳み込み0件（alias dmr11-051m は rejects
  に独自行なし。対象 id と alias を real /
  real_akashic / real_vocab / real_zone / proto /
  converted と照合し登録なし〔proto のヒットは
  T1186 の notes 内参照のみ〕、identity 実測で
  canon_id は対象自身・alias 側の canon も
  dmr11-051、aliases_for = [dmr11-051m]。
  登録エントリの source.aliases は validate の
  自動付与）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔battle_win_destroy〕の出力は対象
  1件ちょうど＝巻き込みなし）。
- converted 10,396→10,397 / rejects
  1,915→1,914、canonical 重なり0・漏れ0。
  battle_win_destroy は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第417弾本体と同形（対象を proto T1186 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（パワー2000バニラ役）/
T1140（パワー4000ブロッカー役＝対照）/ T1187
（ゴッドのバニラ役）/ T1188（ゴッド・ノヴァ
OMG 役）/ T873（光マナ役）/ T872（闇マナ役）/
T1090（単色のマナ置き対照）。
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
from tests.test_vocab_pilot417 import (  # noqa: E402
    FORM, FREE_IF, FULL_TEXT, KEYWORDS, PARSED_TRIG)

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr11-051"
GAP = "battle_win_destroy"
NAME = "護神のインガ イヌハッカ"


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


def test_round452_disposition():
    rej = _reject_rows()
    assert len(rej) == 1914
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10397
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は登録で解消
    assert "dmr11-051m" not in rej       # alias に独自行なし
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light", "darkness"]
    assert c["cost"] == 3 and c["power"] == 5500 and c["mana"] == 1
    assert c["races"] == ["オラクル"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完は text のみ）
    # 登録形は提出形と完全一致: abilities は誘発1件ちょうど、
    # keywords はそのまま、free_if は保持される
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["keywords"] == KEYWORDS
    assert c["free_if"] == FREE_IF
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ["dmr11-051m"]  # validate の自動付与
    d = parse_card(c, TABLES)
    assert d.free_if == FREE_IF
    assert PARSED_TRIG in d.abilities
    assert len(d.abilities) == 3        # キーワード由来 static 2件＋誘発1件
    assert d.keywords == KEYWORDS
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第417弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _main_keys(e, player):
    """player の最初の main 決定の選択肢キーを返す。"""
    for _ in range(900):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player:
            return keys
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def _play_and_settle(e, player, key, done):
    """player の main で key を選び、done() になるまで進める。"""
    played = False
    for _ in range(600):
        if played and done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" \
                and d.get("player") == player and key in keys:
            played = True
            e.answer([keys.index(key)])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return done()


MANA3 = ["T873", "T872", "T873"]   # 光・闇を含む3枚（コスト3の支払い用）


def test_no_free_without_god(rules):
    """G・ゼロの判別: ゴッドがいなければ無料選択肢は
    出ず、有料だけが出る（場の非ゴッド T001 では
    条件を満たさない判別込み）。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": list(MANA3), "bz": ["T001"]},
               {})
    keys = _main_keys(e, 0)
    assert f"play:{TARGET}" in keys
    assert f"play:{TARGET}:free" not in keys


def test_free_with_god_and_no_mana_tapped(rules):
    """G・ゼロの実挙動: 自分のゴッド（T1187）がいれば
    無料選択肢が出て、無料召喚ではマナは1枚も
    タップされない。ゴッド・ノヴァ OMG（T1188）でも
    無料になる（race_has の部分一致）。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": list(MANA3), "bz": ["T1187"]},
               {})
    keys = _main_keys(e, 0)
    assert f"play:{TARGET}:free" in keys
    ok = _play_and_settle(e, 0, f"play:{TARGET}:free",
                          lambda: _in_zone(e, 0, "bz", TARGET))
    assert ok
    assert _tapped_mana(e, 0) == 0
    e2 = _build(rules,
                {"hand": [TARGET], "mana": list(MANA3), "bz": ["T1188"]},
                {})
    assert f"play:{TARGET}:free" in _main_keys(e2, 0)


def test_attack_player_denied_creature_allowed(rules):
    """相手プレイヤーを攻撃できない（cannot_attack_
    player）: permits では attack_player のみ不許可で、
    attack_creature と block は許可。攻撃選択肢でも
    タップした相手クリーチャーへの攻撃だけが出る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T001"]})
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == TARGET)
    opp = next(c for c in e.zlist("bz", 1)
               if e.s.cards[c].defn == "T001")
    assert not e.permits(cid, "attack_player")
    assert e.permits(cid, "attack_creature")
    assert e.permits(cid, "block")
    assert e._attack_options(0) == []
    e.s.mut_card(opp).tapped = True
    keys = [o["key"] for o in e._attack_options(0)]
    assert keys == [f"attack:{TARGET}:T001"]


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


def _drive_battle(e, atk_player, atk, blk):
    """第417弾本体と同型: atk がプレイヤーを攻撃し、
    相手が blk でブロックするバトルを1回行い、攻撃側の
    ターンが終わる（防御側の charge）まで進める。
    観測した hist:battle_win の最大値を併せて返す。"""
    state = {"attacked": False, "blocked": False,
             "win_seen": {0: 0, 1: 0}}
    for _ in range(4000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        for p in (0, 1):
            v = max(e.s.turn_counters.get(f"hist:battle_win:{p}") or 0,
                    e.s.prev_counters.get(f"hist:battle_win:{p}") or 0)
            state["win_seen"][p] = max(state["win_seen"][p], v)
        if state["blocked"] and d["kind"] == "charge" \
                and d.get("player") != atk_player:
            break
        if d["kind"] == "attack" and d.get("player") == atk_player \
                and not state["attacked"]:
            state["attacked"] = True
            e.answer([keys.index(f"attack:{atk}:player")])
            continue
        if d["kind"] == "block":
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blk}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
            continue
        _answer_default(e, d)
    assert state["attacked"] and state["blocked"], state
    return state


def test_block_win_destroys_self(rules):
    """自壊条項の実挙動: 登録カードがパワー2000の
    攻撃をブロックしてバトルに勝つと、バトルの後に
    自身が破壊される（攻撃側はバトルで破壊され、
    シールドは割れない）。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T001"]})
    shields_before = len(e.zlist("shield", 0))
    state = _drive_battle(e, 1, "T001", TARGET)
    assert state["win_seen"][0] == 1
    assert _in_zone(e, 1, "graveyard", "T001")
    assert _in_zone(e, 0, "graveyard", TARGET)
    assert not _in_zone(e, 0, "bz", TARGET)
    assert len(e.zlist("shield", 0)) == shields_before


def test_block_win_control_blocker_survives(rules):
    """対照: 誘発を持たないブロッカー（T1140、パワー
    4000）が同じ攻撃をブロックして勝てば生き残る。"""
    e = _build(rules, {"bz": ["T1140"]}, {"bz": ["T001"]})
    state = _drive_battle(e, 1, "T001", "T1140")
    assert state["win_seen"][0] == 1
    assert _in_zone(e, 1, "graveyard", "T001")
    assert _in_zone(e, 0, "bz", "T1140")
    assert not _in_zone(e, 0, "graveyard", "T1140")


def _charge(e, player, tid):
    """第417弾本体と同型: player の最初の charge で
    tid を選んで置く。置けたら True を返す。"""
    for _ in range(300):
        d = e.advance()
        if d is None:
            return False
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and d.get("player") == player:
            hit = [i for i, k in enumerate(keys) if tid in k]
            if hit:
                e.answer([hit[0]])
                for _ in range(4):
                    if any(e.cdef(c).id == tid
                           for c in e.zlist("mana", player)):
                        break
                    d2 = e.advance()
                    if d2 is None:
                        break
                    keys2 = [o["key"] for o in d2["options"]]
                    if "pass" in keys2:
                        e.answer([keys2.index("pass")])
                    elif "no_block" in keys2:
                        e.answer([keys2.index("no_block")])
                    elif d2["kind"] == "declare_strigger":
                        e.answer([])
                    else:
                        e.answer(list(range(d2.get("min", 0))))
                return True
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
    return False


def test_multicolor_card_enters_mana_tapped(rules):
    """第1条項「マナゾーンに置く時、このカードは
    タップして置く」は多色カードのルール（405.1）:
    光/闇の登録カードを手札からマナに置くとタップ
    状態で置かれる。対照として単色の T1090（火）は
    アンタップで置かれる。"""
    e = _build(rules, {"hand": [TARGET]}, {})
    assert _charge(e, 0, TARGET)
    mana = [c for c in e.zlist("mana", 0) if e.cdef(c).id == TARGET]
    assert len(mana) == 1
    assert e.s.cards[mana[0]].tapped
    e2 = _build(rules, {"hand": ["T1090"]}, {})
    assert _charge(e2, 0, "T1090")
    mana2 = [c for c in e2.zlist("mana", 0) if e2.cdef(c).id == "T1090"]
    assert len(mana2) == 1
    assert not e2.s.cards[mana2[0]].tapped
