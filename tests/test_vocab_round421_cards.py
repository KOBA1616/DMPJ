"""再変換ラウンド421（第386弾 graveyard_replacement）の記録テスト。

- 新規登録1件: dm26ex4-cho046 夜露死苦 キャロル
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 水・火 / コスト3 / パワー2000 /
  種族 アウトレイジ、mana 1、keywords・abilities
  ともに無し〕に第386弾の確立形1能力〔replace
  {when: {event: move, to: graveyard, subject:
  self}, if: {all: [exists マナ水, exists マナ火]},
  instead: [move {ref: subject} → hand]}〕
  ＝登録済み dm23ex1-062（同名カードの別刷り）の
  登録形と完全一致を足し、unsupported を外した
  もの。abilities はこの1件ちょうど、keywords は
  無いまま。補完あり: partial の text は条項の
  断片のみのため、登録形では text に行の公式
  テキスト全文が入っている）。
- 正本判定: 新規登録として扱った。identity 実測で
  canon_id(dm26ex4-cho046) = dm26ex4-cho046（対象
  id 自身が最新版の正本）。dm23ex1-062 は converted
  の独立エントリとして登録済みだが、その source.
  aliases は [dmex03-029, dmex13-056, dmx14-031,
  promoy12-031] の4件で対象 id を含まず、対象は
  どの converted エントリからもカバーされていない。
  dm02-046 型の stale は、正本 dmsd16-013 が登録
  済みでその aliases に dm02-046 が含まれ行が重複
  していたケースであり本件と異なる（stale として
  消すと正本 id が converted のどこにも無い漏れに
  なる）。登録形の source.aliases は validate が
  identity.aliases_for から自動付与した5件
  （dm23ex1-062 を含む）。dm23ex1-062 の独立
  エントリとの id∩aliases 重なりが生じるが、同種の
  重なりは既存データに多数ある（ラウンド415で
  確認）ほか、AliasDict は ID として存在する alias
  を別名解決から除外するため無害。alias 畳み込み
  0件・stale クリーンアップ0件。
- 差し戻し1件: dm25ex2-cho021 悠久を統べる者
  フォーエバー・プリンセス。gaps ⊆ 条件で reopen
  の出力は対象と合わせて2件ちょうど。本カードは
  instead の形が異なり第1条項も未構築のため
  対象外で、submit に unsupported を残した partial
  を含めて差し戻した。gaps = [graveyard_
  replacement] と partial を保って rejects に
  残っている（漏れなし）。graveyard_replacement
  はこの1件が残るため完全解消しない。
- converted 10,365→10,366 / rejects 1,947→1,946
  （reopen −2・差し戻し +1 の差し引き）、canonical
  重なり0・漏れ0。
- 既知の制限: 置換の発生源走査規則により本形は
  bz 起点でのみ発火し、手札・山札起点では発火
  しない（dm23ex1-062 も同一。第386弾で記録し
  専用ステージ送り。本ラウンドでは扱わない）。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第386弾本体と同形（発生源を proto T1149 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第386弾の proto を流用: T1105（火・パワー4000
ブロッカー＝ハンター役）/ T079（水・マナ役）/
T277（火・マナ役）。
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
from tests.test_vocab_pilot386 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm26ex4-cho046"
OTHER = "dm25ex2-cho021"
GAP = "graveyard_replacement"
NAME = "夜露死苦 キャロル"
ALIASES = ["dm23ex1-062", "dmex03-029", "dmex13-056",
           "dmx14-031", "promoy12-031"]


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


def test_round421_disposition():
    rej = _reject_rows()
    assert len(rej) == 1946
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10366
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["water", "fire"]
    assert c["cost"] == 3 and c["power"] == 2000 and c["mana"] == 1
    assert c["races"] == ["アウトレイジ"]
    assert not c.get("keywords")         # keywords は無いまま
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形 replace 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    # source.aliases は validate が identity から自動付与した5件
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    # 差し戻した対象外は gaps を保って残っている
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == {OTHER}, left         # ファミリーは1件残る
    assert rej[OTHER]["partial"]["keywords"] == [
        "speed_attacker", "double_breaker"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第386弾本体と同形、発生源は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_destroyed_in_battle(e, target=TARGET, hunter="T1105"):
    """target（p1）がプレイヤーを攻撃してタップした後、
    p0 の hunter にクリーチャー攻撃されてバトルで破壊
    される経路（第386弾本体の作法）。choose_replacement
    の諮問が出たら置換を選ぶ。"""
    state = {"charged": False, "hunted": False, "hunt_turn": None}
    for _ in range(1500):
        if state["hunted"] and e.s.turn >= state["hunt_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == 1:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{target}:player"]
            if hit and not state["charged"]:
                state["charged"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "attack" and d.get("player") == 0:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{hunter}:{target}"]
            if hit and state["charged"] and not state["hunted"]:
                state["hunted"] = True
                state["hunt_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            # target はブロック可能なので、プレイヤー攻撃は
            # ブロックせず通す（ブロックされるとハンター役が
            # バトルで破壊してしまい経路が変わる）
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_replacement":
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"replace:{target}:")]
            assert hit, keys
            e.answer([hit[0]])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_registered_destroy_returns_to_hand_with_water_and_fire_mana(rules):
    """実挙動: 登録カードは、自分のマナゾーンに水と火が
    あればバトルで破壊される代わりに手札に戻る
    （墓地には行かない）。"""
    e = _build(rules, {"bz": ["T1105"]},
               {"bz": [TARGET], "mana": ["T079", "T277"]})
    st = _drive_destroyed_in_battle(e)
    assert st["charged"] and st["hunted"]
    assert TARGET in _defns(e, "hand", 1)
    assert TARGET not in _defns(e, "graveyard", 1)
    assert TARGET not in _defns(e, "bz", 1)


def test_registered_destroy_goes_to_graveyard_with_water_only(rules):
    """対照: マナが水だけでは条件が外れ（火が無い）、
    置換は適用されず破壊され墓地に行く。"""
    e = _build(rules, {"bz": ["T1105"]},
               {"bz": [TARGET], "mana": ["T079"]})
    st = _drive_destroyed_in_battle(e)
    assert st["charged"] and st["hunted"]
    assert TARGET in _defns(e, "graveyard", 1)
    assert TARGET not in _defns(e, "hand", 1)


def test_registered_destroy_goes_to_graveyard_with_fire_only(rules):
    """対照: マナが火だけでは条件が外れ（水が無い）、
    置換は適用されず破壊され墓地に行く。"""
    e = _build(rules, {"bz": ["T1105"]},
               {"bz": [TARGET], "mana": ["T277"]})
    st = _drive_destroyed_in_battle(e)
    assert st["charged"] and st["hunted"]
    assert TARGET in _defns(e, "graveyard", 1)
    assert TARGET not in _defns(e, "hand", 1)
