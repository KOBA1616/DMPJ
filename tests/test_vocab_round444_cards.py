"""再変換ラウンド444（第409弾 enters_tapped_grant）の記録テスト。

- 新規登録1件: dm26ex3-010 永遠のリュウセイ・カイザー
  （登録形は提出形と完全一致〔差分は validate が
  identity.aliases_for から自動付与した
  source.aliases のみ〕: partial の骨格
  〔クリーチャー / 火 / コスト8 / パワー8000 /
  種族 レッド・コマンド・ドラゴン / ハンター、
  mana 1、keywords [double_breaker]、abilities は
  第1条項の static 1件が構築済み〕に第409弾の
  確立形 abilities 3件〔第1条項: static
  {affects: {owner: you, filter: {types:
  [creature]}}, mod: {grant: [speed_attacker]}}
  （partial 構築済み）／第2条項: static {affects:
  {zone: bz, owner: opp, filter: {types:
  [creature]}}, mod: {grant: [enters_tapped]}}
  （登録済み dmc52-007・第340弾と完全一致）／
  第3条項: replace {zone: hand, optional: true,
  when: {event: move, from: hand, to: graveyard,
  reason: discard, subject: self, by: opp},
  instead: [move {select: {ref: self, count: 1},
  to: bz, reason: put}]}（同一文面の登録済み
  dm26ex3-dcr005 と完全一致）〕を足し、
  unsupported を外したもの。abilities はこの
  3件ちょうど、keywords は [double_breaker]
  のまま）。
- 補完なし（partial の text は公式全文と一致。
  登録後の全文一致も照合済み）。
- split の part[2] 定型所有（第1条項の static）は
  提出形と完全一致のため merge_split の dedupe で
  二重付着せず、登録後の abilities が3件ちょうど
  であることを実測確認済み。
- alias 畳み込み0件（alias 11件 dm23bd4-015 /
  dm26sd1-j002f / dmbd05-003 / dmbd09-006 /
  dmd13-009 / dmd20-016 / dmex15-a029 /
  dmex17-cho19 / dmr02-s03 / dmx22b-094 /
  promoy15-051 は rejects に独自行が無く、
  登録エントリの source.aliases に validate が
  自動付与。正本判定は通常型で対象 id と
  alias 11件を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1177 の notes 内参照のみ〕、
  identity 実測で canon_id は対象・全 alias とも
  dm26ex3-010）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔enters_tapped_grant〕の出力は対象
  1件ちょうど）。
- converted 10,388→10,389 / rejects 1,923→1,922、
  canonical 重なり0・漏れ0。enters_tapped_grant は
  完全解消。
- 第2条項は keyword フィルタを含まないため
  第398弾の base 照合の制限は及ばず、相手の
  進化クリーチャーもタップして出る。第3条項は
  zone: hand 宣言の置換のため第386弾の発生源
  走査制限（bz 起点のみ）は及ばない。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第409弾本体と同形（対象を proto T1177 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（バニラ役・自然マナ役）/
T1090（印刷スピードアタッカー役・火マナ役）/
T1091（バニラ役）/ T1145・T1146（進化・進化元役）/
T117（相手の手札を捨てさせる呪文役）/ T118
（自分の手札を捨てる呪文役）/ T008（闇マナ役）。
バトルゾーンは共有ゾーンなので所有は bz_tops(p)
で見る。
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
from tests.test_vocab_pilot409 import FORM, FULL_TEXT, GRANT_SA  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm26ex3-010"
GAP = "enters_tapped_grant"
NAME = "永遠のリュウセイ・カイザー"
ALIASES = ["dm23bd4-015", "dm26sd1-j002f", "dmbd05-003",
           "dmbd09-006", "dmd13-009", "dmd20-016",
           "dmex15-a029", "dmex17-cho19", "dmr02-s03",
           "dmx22b-094", "promoy15-051"]


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


def test_round444_disposition():
    rej = _reject_rows()
    assert len(rej) == 1922
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10389
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリーは完全解消
    for a in ALIASES:
        assert a not in rej              # alias に独自行は無い（漏れ0）
        assert a not in ids
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"]
    assert c["civs"] == ["fire"]
    assert c["cost"] == 8 and c["power"] == 8000 and c["mana"] == 1
    assert c["races"] == ["レッド・コマンド・ドラゴン", "ハンター"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は確立形3件ちょうど
    # （split の part[2] 定型所有分の重複は無い）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 3
    assert sum(1 for a in c["abilities"] if a == GRANT_SA) == 1
    assert c["keywords"] == ["double_breaker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 4          # double_breaker 派生 static 込み
    for a in FORM:
        assert a in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第409弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


def _zone_card(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn)


def _play(e, player, play_key, pick=None, limit=600):
    """player の main で play_key を使い、対象カードが
    バトルゾーンに出るまで進める汎用ドライバ
    （第409弾本体と同形）。"""
    defn = play_key.split(":", 1)[1]
    for _ in range(limit):
        if any(e.s.cards[c].defn == defn
               for c in e.zlist("bz", player)):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player \
                and play_key in keys:
            e.answer([keys.index(play_key)])
            continue
        if pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("play never happened")


def _drive(e, player, play=None, attack=None):
    """player の最初の main のターンだけを対象に進める
    ドライバ（第409弾本体と同形）。"""
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
        if kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def test_registered_chars_discrimination(rules):
    """特性レベルの判別: 第1条項は自分のクリーチャー
    すべて（発生源自身を含む）に speed_attacker を
    付け、第2条項は相手のクリーチャーすべて
    （バニラ・印刷スピードアタッカーとも）に
    enters_tapped を付ける（自分のクリーチャーには
    付けない）。"""
    e = _build(rules,
               {"bz": [TARGET, "T001"]},
               {"bz": ["T1091", "T1090"]})
    src = _cid(e, TARGET, 0)
    own = _cid(e, "T001", 0)
    opp_v = _cid(e, "T1091", 1)
    opp_sa = _cid(e, "T1090", 1)
    assert "speed_attacker" in e.chars(src)["keywords"]
    assert "speed_attacker" in e.chars(own)["keywords"]
    assert "enters_tapped" in e.chars(opp_v)["keywords"]
    assert "enters_tapped" in e.chars(opp_sa)["keywords"]
    assert "enters_tapped" not in e.chars(own)["keywords"]
    assert "enters_tapped" not in e.chars(src)["keywords"]


def test_registered_opponent_vanilla_enters_tapped(rules):
    """第2条項の実挙動: 相手のバニラ（T1091）は
    登録カードがいる場にタップして出る。"""
    e = _build(rules, {"bz": [TARGET]},
               {"hand": ["T1091"], "mana": ["T1091", "T1091"]})
    _play(e, 1, "play:T1091")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1091")].tapped is True


def test_registered_opponent_evolution_enters_tapped(rules):
    """第2条項は進化クリーチャーにも及ぶ: 相手の
    進化（T1145）もタップして出る（keyword フィルタを
    含まないため第398弾の制限は及ばない）。"""
    e = _build(rules, {"bz": [TARGET]},
               {"bz": ["T1146"], "hand": ["T1145"],
                "mana": ["T1146", "T001", "T001"]})
    _play(e, 1, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1145")].tapped is True


def test_registered_own_creature_enters_untapped(rules):
    """owner: opp の判別: 自分のクリーチャーは
    登録カードがいてもタップせずに出る。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1091"],
                       "mana": ["T1091", "T1091"]},
               {})
    _play(e, 0, "play:T1091")
    assert e.s.cards[_zone_card(e, "bz", 0, "T1091")].tapped is False


def test_registered_no_source_opponent_enters_untapped(rules):
    """対照: 登録カードが無ければ相手のクリーチャーも
    タップせずに出る。"""
    e = _build(rules, {},
               {"hand": ["T1091"], "mana": ["T1091", "T1091"]})
    _play(e, 1, "play:T1091")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1091")].tapped is False


def test_registered_granted_speed_attacker_can_attack_on_entry_turn(rules):
    """第1条項の実挙動: 登録カードがいれば、自分の
    バニラ（T001）も出たターンにプレイヤーを
    攻撃できる（シールド1枚減る）。"""
    e = _build(rules,
               {"bz": [TARGET], "hand": ["T001"],
                "mana": ["T001", "T001"]},
               {"bz": ["T1091"]})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T001", attack="T001")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 1


def test_registered_no_source_vanilla_cannot_attack_on_entry_turn(rules):
    """対照: 登録カードが無ければ、出たターンのバニラは
    攻撃できない。"""
    e = _build(rules,
               {"hand": ["T001"], "mana": ["T001", "T001"]},
               {"bz": ["T1091"]})
    seen = _drive(e, player=0, play="T001", attack="T001")
    assert seen["played"]
    assert not seen["attacked"]


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
    """第409弾本体と同型の駆動: player 0 が caster を
    唱え、victim を捨てさせ、置換の諾否を選ぶ。"""
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


def test_registered_madness_replace_puts_into_bz(rules):
    """第3条項の実挙動: 相手の呪文（T117）で
    捨てられる時、置換を選べば墓地ではなく
    バトルゾーンに出る（by: opp）。"""
    e = _build(rules, {"hand": ["T117"], "mana": ["T008"] * 4},
               {"hand": [TARGET]})
    v = _zone_card(e, "hand", 1, TARGET)
    assert _settle(e, lambda: e.s.cards[v].zone == "bz",
                   _discard_drive("T117", TARGET, True))
    assert v in e.zlist("bz", 1)
    assert v not in e.zlist("graveyard", 1)


def test_registered_madness_replace_is_optional(rules):
    """第3条項は任意: 置換を断れば墓地に置かれる。"""
    e = _build(rules, {"hand": ["T117"], "mana": ["T008"] * 4},
               {"hand": [TARGET]})
    v = _zone_card(e, "hand", 1, TARGET)
    assert _settle(e, lambda: e.s.cards[v].zone == "graveyard",
                   _discard_drive("T117", TARGET, False))
    assert v not in e.zlist("bz", 1)


def test_registered_madness_not_triggered_by_own_spell(rules):
    """by: opp の判別: 自分の呪文（T118）で自分の
    手札から捨てる時は置換が発火せず、墓地に行く。"""
    e = _build(rules,
               {"hand": ["T118", TARGET], "mana": ["T008"] * 2},
               {})
    v = _zone_card(e, "hand", 0, TARGET)
    assert _settle(e, lambda: e.s.cards[v].zone == "graveyard",
                   _discard_drive("T118", TARGET, True))
    assert v not in e.zlist("bz", 0)
