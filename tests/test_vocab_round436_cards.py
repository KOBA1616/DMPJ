"""再変換ラウンド436（第401弾 block_break）の記録テスト。

- 新規登録1件: dm33-001 超神龍レイ・ソレイユ
  （登録形は提出形と完全一致: partial の骨格
  〔進化クリーチャー / 光 / コスト4 / パワー6000 /
  種族 アポロニア・ドラゴン、mana 1、keywords
  [blocker]〕に第401弾の確立形 static {affects:
  {zone: bz, owner: you, filter: {types:
  [creature]}}, mod: {gain: [trigger {when:
  {event: block, subject: self}, effect: [break
  {player: opp, count: 1}]}]}} を足し、unsupported
  を外したもの。abilities はこの1件ちょうど
  〔parse 後の blocker 派生 static を除く〕、
  keywords は [blocker] のまま。**補完あり:
  types と evolve_from のみ** — types は
  [creature, evolution]、evolve_from は
  {types: [creature], keyword: blocker}
  （第372弾・登録先例 dm32-011 と同文・同形）。
  text は partial の時点で公式全文と一致し
  補完なし（登録後の全文一致も照合済み））。
- alias 畳み込み0件（alias は無い。正本判定は
  通常型: 対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1168 の
  notes 内参照のみ〕、identity 実測で canon_id は
  対象自身、aliases_for = []）。stale
  クリーンアップ0件・差し戻し0件（reopen
  〔block_break〕の出力は対象1件ちょうど）。
- converted 10,380→10,381 / rejects 1,932→1,931、
  canonical 重なり0・漏れ0。block_break は
  完全解消。
- 確立形は登録先例 dmd26-015（静的効果の gain で
  誘発を付与）＋第326弾形B（gain した誘発が
  break を解決）の合成で追加語彙なし。新規
  フィールドではないが、回帰に test_data_audit
  と第326・372弾本体を含めて確認済み。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）は本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第401弾本体と同形（対象を proto T1168 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第401弾の proto を流用: T1117（ブロッカー進化元
役＋光マナ役）/ T004（ブロッカー役）/ T001
（攻撃役）/ T1118（パワー7000の攻撃役）/ T1107
（ブロッカーを持たない進化元対照）。
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
from tests.test_vocab_pilot401 import EVOLVE_FROM, FORM, FULL_TEXT, GAINED_TRIGGER  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm33-001"
GAP = "block_break"
NAME = "超神龍レイ・ソレイユ"


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


def test_round436_disposition():
    rej = _reject_rows()
    assert len(rej) == 1931
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10381
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # block_break は完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    # 補完あり: types と evolve_from
    assert c["types"] == ["creature", "evolution"]
    assert c["evolve_from"] == EVOLVE_FROM
    assert c["civs"] == ["light"]
    assert c["cost"] == 4 and c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["アポロニア・ドラゴン"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    assert c["keywords"] == ["blocker"]
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("aliases")        # alias は無い
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 2         # blocker 派生 static ＋ 確立形
    assert d.abilities[1] == FORM[0]
    assert d.evolve_from == EVOLVE_FROM
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第401弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive(e, attacker=None, attacker_player=1, blocker=None,
           play=None, pick=None, stop=None, limit=900):
    """汎用ドライバ（第401弾本体と同型）。"""
    state = {"attacked": False, "played": False}
    plays = [play] if play else []
    for _ in range(limit):
        if stop is not None and stop():
            return state
        d = e.advance()
        if d is None:
            return state
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and d.get("player") == 0 and plays:
            hit = next((k for k in plays if k in keys), None)
            if hit is not None:
                plays.remove(hit)
                state["played"] = True
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("attack", "declare_attack"):
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and d["player"] == attacker_player \
                    and not state["attacked"]:
                state["attacked"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("block", "declare_block"):
            hit = [i for i, k in enumerate(keys)
                   if blocker and k.startswith(f"bz:{blocker}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_shields":
            e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


def _triggers(e, p, defn):
    cid = next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)
    return [ab for _, ab in e.abilities(cid, "trigger")]


def test_registered_granted_trigger_only_on_own_creatures(rules):
    """特性判別: 登録カードがいる間、自分の
    クリーチャーは全員（発生源自身を含む）が
    「ブロックした時」の誘発を持ち、相手の
    クリーチャーは持たない。"""
    e = _build(rules, {"bz": [TARGET, "T004"]}, {"bz": ["T001"]})
    assert _triggers(e, 0, "T004") == [GAINED_TRIGGER]
    assert _triggers(e, 0, TARGET) == [GAINED_TRIGGER]
    assert _triggers(e, 1, "T001") == []


def test_registered_block_by_other_creature_breaks_one_shield(rules):
    """実挙動: 自分の他のクリーチャー（T004）が
    ブロックすると、そのクリーチャーが相手の
    シールドを1枚ブレイクする。バトル自体も通常
    どおり行われる（T004 3000 が T001 2000 を倒す）。"""
    e = _build(rules, {"bz": [TARGET, "T004"]},
               {"bz": ["T001"], "shield": ["T007"] * 5})
    st = _drive(e, attacker="T001", attacker_player=1,
                blocker="T004",
                stop=lambda: "T001" in _defns(e, "graveyard", 1))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4        # 1枚ブレイク
    assert _defns(e, "hand", 1).count("T007") == 1
    assert "T004" in _defns(e, "bz", 0)          # バトルに勝つ
    assert TARGET in _defns(e, "bz", 0)


def test_registered_break_before_battle_even_if_blocker_dies(rules):
    """実挙動（タイミング判別）: ブロッカー（T004、
    3000）がパワー7000（T1118）にブロックしてバトルで
    落ちても、ブレイクはブロック宣言時に先に起きる。"""
    e = _build(rules, {"bz": [TARGET, "T004"]},
               {"bz": ["T1118"], "shield": ["T007"] * 5})
    st = _drive(e, attacker="T1118", attacker_player=1,
                blocker="T004",
                stop=lambda: "T004" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4        # 先にブレイク
    assert _defns(e, "hand", 1).count("T007") == 1
    assert "T1118" in _defns(e, "bz", 1)         # 攻撃側は残る


def test_registered_source_itself_blocks_and_breaks(rules):
    """実挙動: 発生源自身（登録カード）がブロック
    しても誘発する（「自分のクリーチャー」には
    自身も含む）。"""
    e = _build(rules, {"bz": [TARGET]},
               {"bz": ["T001"], "shield": ["T007"] * 5})
    st = _drive(e, attacker="T001", attacker_player=1,
                blocker=TARGET,
                stop=lambda: "T001" in _defns(e, "graveyard", 1))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4
    assert _defns(e, "hand", 1).count("T007") == 1
    assert TARGET in _defns(e, "bz", 0)


def test_registered_opponent_block_breaks_nothing(rules):
    """判別: 相手のクリーチャーがブロックしても、
    どちらのシールドも割れない（付与は自分の
    クリーチャーだけ）。自分の T001 はバトルで落ちる。"""
    e = _build(rules, {"bz": [TARGET, "T001"]}, {"bz": ["T004"]})
    st = _drive(e, attacker="T001", attacker_player=0,
                blocker="T004",
                stop=lambda: "T001" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    assert len(e.zlist("shield", 0)) == 5
    assert len(e.zlist("shield", 1)) == 5
    assert "T004" in _defns(e, "bz", 1)


def test_registered_evolution_onto_blocker_base(rules):
    """実挙動: 登録カードはブロッカーを持つ
    クリーチャー（T1117）の上に進化して出る。"""
    e = _build(rules,
               {"bz": ["T1117"], "hand": [TARGET],
                "mana": ["T1117"] * 5},
               {})
    _drive(e, play=f"play:{TARGET}", pick="T1117",
           stop=lambda: TARGET in _defns(e, "bz", 0))
    assert TARGET in _defns(e, "bz", 0)
    cid = next(c for c in e.bz_tops(0) if e.cdef(c).id == TARGET)
    assert e.chars(cid)["power"] == 6000


def test_registered_no_evolution_onto_non_blocker_base(rules):
    """判別: ブロッカーを持たないクリーチャー
    （T1107）の上には進化できない。main の選択肢に
    play が現れず、手札に留まる。"""
    e = _build(rules,
               {"bz": ["T1107"], "hand": [TARGET],
                "mana": ["T1117"] * 5},
               {})
    offered = {"play": False}
    for _ in range(300):
        if e.s.turn >= 5:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == 0:
            if f"play:{TARGET}" in keys:
                offered["play"] = True
            if "pass" in keys:
                e.answer([keys.index("pass")])
                continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert not offered["play"]
    assert TARGET in _defns(e, "hand", 0)
    assert TARGET not in _defns(e, "bz", 0)
