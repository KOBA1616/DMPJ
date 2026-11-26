"""再変換ラウンド459（第424弾 entry_turn_attack）の
記録テスト。

- 新規登録1件: dmbd07-a-006 ガンバＧ/
  ガガン・ガン・ガガン（ツインパクト。登録形は
  提出形と完全一致: partial の骨格（クリーチャー面
  のみ）は使わず、faces 構造＋第424弾の確立形で
  組んだもの〔クリーチャー面（ゼロ / コスト6 /
  パワー6000 / 種族 ジョーカーズ）: keywords
  [double_breaker] ＋ static {affects: self,
  if: {exists: {ref: self, filter:
  {entered_this_turn: true}}}, mod:
  {player_rush: true}}（第261弾の player_rush の
  self 形。登録済み promoy17-sp4d01 と同一文面・
  同形。第392弾の「確立形が未確認」という見送りは
  登録先例の見落としだった）／呪文面（ゼロ /
  コスト2）: spell [move {select: {zone:
  graveyard, owner: you, filter: {race_has:
  ジョーカーズ}, count: 1}, to: mana,
  reason: put}]（登録済み dm23bd5-042 の呪文形。
  文面どおり必須1枚で up_to 無し、種別指定が無い
  ため types フィルタ無し）〕。クリーチャー面の
  abilities は1件ちょうど、呪文面の spell は
  1 op）。
- 補完あり: faces 構造＋text＋keywords（partial は
  クリーチャー面の骨格のみで faces・keywords 無し、
  text は第2条項の断片のため、両面とも公式全文を
  使用し、最上位 text は両面を「 ／ 」で連結。
  面名は公式名を / で分けた ガンバＧ ／
  ガガン・ガン・ガガン。呪文面の文明は公式データで
  空文字だが、同 product（bd07）のツインパクトで
  明示される場合はクリーチャー面と同一
  （dmbd07-b-010）のため両面とも zero とする。
  登録後の全文一致も照合済み）。
- split は None で定型所有なし＝ツール側
  ブロッカーなし。
- alias 畳み込み0件（alias 3件 dmsd04-002 /
  promoy17-035 / promoy17-sp4d02 は rejects に
  独自行なし。対象 id と alias 3件を real /
  real_akashic / real_vocab / real_zone / proto /
  converted と照合し登録なし〔proto のヒットは
  T1200 の notes 内参照のみ〕、identity 実測で
  canon_id は対象自身・alias 側の canon も
  dmbd07-a-006、aliases_for = 3件。登録エントリの
  source.aliases は提出形の3件がそのまま保持）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔entry_turn_attack〕の出力は対象1件
  ちょうど＝巻き込みなし）。
- converted 10,403→10,404 / rejects
  1,908→1,907、canonical 重なり0・漏れ0。
  entry_turn_attack は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第424弾本体と同形（対象を proto T1200 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1175（ゼロ・ジョーカーズ役＝
マナ役・墓地のジョーカーズ役）/ T1091（通常
クリーチャー役・対照役）。
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
from tests.test_vocab_pilot424 import (  # noqa: E402
    FULL_TEXT, NAME, SPELL, STATIC)
from tests.test_vocab_pilot424_cards import (  # noqa: E402
    CREATURE_TEXT, SPELL_TEXT, SUBMIT)

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmbd07-a-006"
GAP = "entry_turn_attack"
ALIASES = ["dmsd04-002", "promoy17-035", "promoy17-sp4d02"]


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


def test_round459_disposition():
    rej = _reject_rows()
    assert len(rej) == 1907
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10404
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
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
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    f0, f1 = c["faces"]
    assert f0["name"] == "ガンバＧ"
    assert f0["types"] == ["creature"] and f0["civs"] == ["zero"]
    assert f0["cost"] == 6 and f0["power"] == 6000
    assert f0["races"] == ["ジョーカーズ"]
    assert f0["text"] == CREATURE_TEXT
    # 登録形は提出形と完全一致: クリーチャー面の
    # abilities は static 1件ちょうど、keywords は
    # [double_breaker]、呪文面の spell は move 1件
    assert f0["abilities"] == [STATIC]
    assert len(f0["abilities"]) == 1
    assert f0["keywords"] == ["double_breaker"]
    assert f1["name"] == "ガガン・ガン・ガガン"
    assert f1["types"] == ["spell"] and f1["civs"] == ["zero"]
    assert f1["cost"] == 2 and f1["text"] == SPELL_TEXT
    assert f1["spell"] == SPELL
    assert len(f1["spell"]) == 1
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert sorted(src.get("aliases") or []) == sorted(ALIASES)
    d = parse_card(c, TABLES)
    pf0, pf1 = d.faces
    assert STATIC in pf0.abilities
    # double_breaker はキーワード展開で static が1件増える
    assert len(pf0.abilities) == 2
    assert pf0.keywords == ["double_breaker"]
    assert pf1.spell == SPELL
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第424弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1, filler="T002"):
    return scenario.build(rules, {"p0": p0, "p1": p1, "filler": filler,
                                  "seed": 1, "deck_size": 20})


def _in_zone(e, p, zone, defn):
    return [c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn]


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


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


def test_chars_player_rush_only_on_entry_turn(rules):
    """特性レベルの判別（登録カード自身）: 出たターン
    だけ player_rush が付き、攻撃選択肢はプレイヤー
    への攻撃のみ（タップしている相手クリーチャーが
    いてもクリーチャーへの攻撃は提示されない＝
    召喚酔いはバイパスしない）。前ターンからいれば
    player_rush は付かず、クリーチャーへの攻撃が
    提示される。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1091"]})
    src = _cid(e, TARGET, 0)
    opp = _cid(e, "T1091", 1)
    e.s.mut_card(opp).tapped = True
    e.s.mut_card(src).entered_turn = e.s.turn
    assert e.chars(src)["player_rush"] is True
    keys = [o["key"] for o in e._attack_options(0)]
    assert f"attack:{TARGET}:player" in keys
    assert not [k for k in keys if k.startswith(f"attack:{TARGET}:T")]
    e.s.mut_card(src).entered_turn = e.s.turn - 1
    assert e.chars(src)["player_rush"] is False
    keys = [o["key"] for o in e._attack_options(0)]
    assert f"attack:{TARGET}:T1091" in keys


def _drive(e, player, play=None, attack=None):
    """player の最初の main のターンだけを対象に進める
    ドライバ（第424弾本体と同形）。"""
    seen = {"attack_keys": [], "played": False,
            "attacked": False, "target_turn": None}
    for _ in range(600):
        if seen["target_turn"] is not None \
                and e.s.turn > seen["target_turn"] + 1:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind in ("charge", "main", "attack") \
                and pl == player and seen["target_turn"] is None:
            seen["target_turn"] = e.s.turn
        if kind == "main" and pl == player and play \
                and not seen["played"]:
            hit = [i for i, k in enumerate(keys)
                   if k == f"play:{play}"]
            if hit:
                seen["played"] = True
                seen["target_turn"] = e.s.turn
                e.answer([hit[0]])
                continue
        if kind == "attack" and pl == player \
                and e.s.turn == seen["target_turn"]:
            seen["attack_keys"].extend(keys)
            hit = [i for i, k in enumerate(keys)
                   if attack and k == f"attack:{attack}:player"]
            if hit and not seen["attacked"]:
                seen["attacked"] = True
                e.answer([hit[0]])
                continue
        _step_default(e, d)
    return seen


def test_summon_and_break_two_shields_same_turn(rules):
    """実挙動（登録カード自身）: 召喚したターンに相手
    プレイヤーを攻撃でき、W・ブレイカーでシールドが
    2枚減る。"""
    e = _build(rules,
               {"hand": [TARGET],
                "mana": ["T1175", "T1175", "T1175",
                         "T1175", "T1175", "T1175"]},
               {})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play=f"{TARGET}:0", attack=TARGET)
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 2


def test_control_vanilla_cannot_attack_on_entry_turn(rules):
    """対照: 通常クリーチャーは出たターンに攻撃
    できない（player_rush の判別）。"""
    e = _build(rules,
               {"hand": ["T1091"], "mana": ["T1091", "T1091"]},
               {"bz": ["T1091"]})
    seen = _drive(e, player=0, play="T1091", attack="T1091")
    assert seen["played"]
    assert not seen["attacked"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1091:")]


def _cast_spell_face(e, done, limit=600):
    cast = False
    for _ in range(limit):
        if cast and done():
            return True
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
    return done()


def test_spell_face_moves_jokers_from_graveyard_to_mana(rules):
    """呪文面の実挙動（登録カード自身）: 墓地の
    ジョーカーズ（T1175）が1枚マナゾーンに置かれ、
    ジョーカーズでないカード（T1091）は墓地に残る。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": ["T1175", "T1175"],
                "graveyard": ["T1175", "T1091"]},
               {})
    ok = _cast_spell_face(
        e, lambda: len(_in_zone(e, 0, "mana", "T1175")) == 3)
    assert ok
    assert not _in_zone(e, 0, "graveyard", "T1175")
    assert _in_zone(e, 0, "graveyard", "T1091")


def test_spell_face_without_jokers_moves_nothing(rules):
    """呪文面の判別（登録カード自身）: 墓地に
    ジョーカーズが無ければ何も置かれず、呪文は
    通常どおり墓地に置かれる。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": ["T1175", "T1175"],
                "graveyard": ["T1091"]},
               {})
    ok = _cast_spell_face(
        e, lambda: bool(_in_zone(e, 0, "graveyard", TARGET)))
    assert ok
    assert len(_in_zone(e, 0, "mana", "T1175")) == 2
    assert _in_zone(e, 0, "graveyard", "T1091")
