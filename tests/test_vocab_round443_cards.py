"""再変換ラウンド443（第408弾 enters_tapped_rule）の記録テスト。

- 新規登録1件: dmex11-005 その子供、凶暴につき
  （登録形は提出形と完全一致〔差分は validate が
  identity.aliases_for から自動付与した
  source.aliases のみ〕: partial の骨格
  〔クリーチャー / 火 / コスト4 / パワー4000 /
  種族 ヒューマノイド / チルドレン、mana 1、
  keywords・abilities ともに無し〕に第408弾の
  確立形 static 3件〔付与: affects {zone: bz,
  owner: you, filter: {types: [creature],
  cost_le: 3}}, mod: {grant: [speed_attacker]}／
  タップ入り（進化）: affects {zone: bz, owner:
  opp, filter: {types: [evolution]}}, mod:
  {grant: [enters_tapped]}／タップ入り
  （スピードアタッカー）: affects {zone: bz,
  owner: opp, filter: {types: [creature],
  keyword: speed_attacker}}, mod: {grant:
  [enters_tapped]}〕を足し、unsupported を
  外したもの。abilities はこの3件ちょうど、
  keywords は無いまま）。
- 補完あり: text のみ（partial の text は断片
  「タップしてバトルゾーンに出る」のため、行の
  公式テキスト全文を入れた。登録後の全文一致も
  照合済み）。
- alias 畳み込み0件（alias 3件 dmr08s-004 /
  dmx24-009 / promoy11-066 は rejects に独自行が
  無く、登録エントリの source.aliases に validate
  が自動付与。正本判定は通常型で対象 id と
  alias 3件を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1176 の notes 内参照のみ〕、
  identity 実測で canon_id は対象・全 alias とも
  dmex11-005）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔enters_tapped_rule〕の出力は対象
  1件ちょうど）。
- converted 10,387→10,388 / rejects 1,924→1,923、
  canonical 重なり0・漏れ0。enters_tapped_rule は
  完全解消。
- 登録後も既知の制限（付与されたスピード
  アタッカーは base 照合のため第3件の keyword
  フィルタに掛からない）は残る。keyword フィルタを
  使う登録済み静的効果と共有するエンジン全体の
  規約で、解消は専用ステージ判断（本ラウンドでは
  扱わない）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第408弾本体と同形（対象を proto T1176 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（コスト2バニラ役・自然
マナ役）/ T1090（印刷スピードアタッカー役・火
マナ役）/ T1091（バニラ役）/ T1145（進化役）/
T1146（進化元役）/ T314（スピードアタッカー
自己付与役）。バトルゾーンは共有ゾーンなので
所有は bz_tops(p) で見る。
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
from tests.test_vocab_pilot408 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex11-005"
GAP = "enters_tapped_rule"
NAME = "その子供、凶暴につき"
ALIASES = ["dmr08s-004", "dmx24-009", "promoy11-066"]


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


def test_round443_disposition():
    rej = _reject_rows()
    assert len(rej) == 1923
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10388
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
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ヒューマノイド", "チルドレン"]
    assert c["text"] == FULL_TEXT        # 公式全文（text のみ補完）
    # 登録形は提出形と完全一致: abilities は確立形 static 3件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 3
    assert not c.get("keywords")
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 3
    for a in FORM:
        assert a in d.abilities
    assert not d.keywords
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第408弾本体と同形、対象は登録カード） ----------

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
    （第408弾本体と同形）。"""
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
    ドライバ（第408弾本体と同形）。"""
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


def test_registered_chars_grant_and_tap_discrimination(rules):
    """特性レベルの判別: 第1条項は自分のコスト3以下に
    だけ speed_attacker を付け（発生源自身はコスト4で
    対象外、相手には付けない）、第3件は相手の印刷
    スピードアタッカーに enters_tapped を付ける
    （相手のバニラには付けない）。"""
    e = _build(rules,
               {"bz": [TARGET, "T001"]},
               {"bz": ["T001", "T1090"]})
    src = _cid(e, TARGET, 0)
    own = _cid(e, "T001", 0)
    opp_v = _cid(e, "T001", 1)
    opp_sa = _cid(e, "T1090", 1)
    assert "speed_attacker" in e.chars(own)["keywords"]
    assert "speed_attacker" not in e.chars(src)["keywords"]
    assert "speed_attacker" not in e.chars(opp_v)["keywords"]
    assert "enters_tapped" in e.chars(opp_sa)["keywords"]
    assert "enters_tapped" not in e.chars(opp_v)["keywords"]
    assert "enters_tapped" not in e.chars(own)["keywords"]


def test_registered_granted_speed_attacker_limitation(rules):
    """既知の制限の固定: 付与されたスピードアタッカー
    （T314 の自己付与）は base 照合のため第3件の
    keyword フィルタに掛からず、enters_tapped は
    付かない。登録後も残るエンジン全体の規約
    （第398・408弾 docs 参照）。"""
    e = _build(rules,
               {"bz": [TARGET]},
               {"bz": ["T314"]})
    granted = _cid(e, "T314", 1)
    ch = e.chars(granted)
    assert "speed_attacker" in ch["keywords"]   # 付与自体は有効
    assert "enters_tapped" not in ch["keywords"]


def test_registered_own_low_cost_can_attack_on_entry_turn(rules):
    """第1条項の実挙動: 登録カードがいれば、自分の
    コスト2バニラ（T001）も出たターンにプレイヤーを
    攻撃できる（シールド1枚減る）。"""
    e = _build(rules,
               {"bz": [TARGET], "hand": ["T001"],
                "mana": ["T001", "T001"]},
               {"bz": ["T1091"]})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T001", attack="T001")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 1


def test_registered_control_without_source_cannot_attack_on_entry_turn(rules):
    """対照: 登録カードが無ければ、出たターンの
    バニラは攻撃できない。"""
    e = _build(rules,
               {"hand": ["T001"], "mana": ["T001", "T001"]},
               {"bz": ["T1091"]})
    seen = _drive(e, player=0, play="T001", attack="T001")
    assert seen["played"]
    assert not seen["attacked"]


def test_registered_opponent_evolution_enters_tapped(rules):
    """第2条項（進化側）の実挙動: 相手の進化
    クリーチャー（T1145）は登録カードがいる場に
    タップして出る。"""
    e = _build(rules, {"bz": [TARGET]},
               {"bz": ["T1146"], "hand": ["T1145"],
                "mana": ["T1146", "T001", "T001"]})
    _play(e, 1, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1145")].tapped is True


def test_registered_own_evolution_enters_untapped(rules):
    """owner: opp の判別: 自分の進化クリーチャーは
    登録カードがいてもタップせずに出る。"""
    e = _build(rules, {"bz": [TARGET, "T1146"], "hand": ["T1145"],
                       "mana": ["T1146", "T001", "T001"]},
               {})
    _play(e, 0, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 0, "T1145")].tapped is False


def test_registered_opponent_speed_attacker_enters_tapped(rules):
    """第2条項（スピードアタッカー側）の実挙動:
    相手の印刷スピードアタッカー（T1090）は
    タップして出る。"""
    e = _build(rules, {"bz": [TARGET]},
               {"hand": ["T1090"], "mana": ["T1090", "T1090"]})
    _play(e, 1, "play:T1090")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1090")].tapped is True


def test_registered_opponent_vanilla_enters_untapped(rules):
    """判別: 相手のバニラ（T1091）はどちらのフィルタ
    にも掛からず、タップせずに出る。"""
    e = _build(rules, {"bz": [TARGET]},
               {"hand": ["T1091"], "mana": ["T1091", "T1091"]})
    _play(e, 1, "play:T1091")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1091")].tapped is False


def test_registered_own_speed_attacker_enters_untapped(rules):
    """owner: opp の判別: 自分のスピードアタッカーは
    登録カードがいてもタップせずに出る。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1090"],
                       "mana": ["T1090", "T1090"]},
               {})
    _play(e, 0, "play:T1090")
    assert e.s.cards[_zone_card(e, "bz", 0, "T1090")].tapped is False
