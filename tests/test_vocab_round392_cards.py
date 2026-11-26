"""再変換ラウンド392（第357弾 return_any_number）の記録テスト。

- 新規登録1件: dmex08-049 十極 ジョバンチュ / Genesis of
  Drillball（ツインパクト。登録形は提出形と完全一致:
  クリーチャー面は第357弾の確立形1能力＋keywords
  [blocker, cannot_attack_player]、呪文面は spell 2 op）。
- alias 畳み込み0件（converted の登録エントリに aliases
  なし。対象 id は real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / converted.yaml の
  いずれにも無く、proto.yaml のヒットは T1073 の notes 内
  参照のみ）。stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [return_any_number] のため reopen で
  外してから submit（reopen の出力は対象1件ちょうど）。
- converted 10,336→10,337 / rejects 1,976→1,975、
  canonical 重なり0・alias 重なり0・漏れ0。
  return_any_number はファミリーがこの1件だけだったため
  完全に解消。
- dm02-046 の stale 行（destroy_self_after_attacking_player）
  は判断待ちのため本ラウンドでも触っていない。

呪文面の検証（ラウンド392で実施）:
「次の自分のターンのはじめまで、手札に加える自分の
シールドカードすべてに『S・トリガー』を与える」は
shield_grant 系に近いが、既存語彙で正確に表せることを
確認した。根拠: キーワード s_trigger の定義そのものが
static {zone: shield, affects: self, mod: {allow:
[s_trigger]}}（data/rules/keywords.yaml）であり、宣言判定
（combat の h_break phase 1）はカードがシールドゾーンに
ある間に chars の allow を見る。したがって呪文の解決で
modify {select: {zone: shield, owner: you}, mod: {allow:
[s_trigger]}, dynamic: true, duration:
until_next_own_turn_start} の継続的効果を作れば、
(1) その時点で置かれたばかりの2枚を含む全シールド、
(2) 窓の間に後からシールドゾーンに入ったカード、
のどちらにも宣言許可が及び、自分の次のターン開始で
失効する。対照的に、印（strigger_on）方式は解決時に
現存するカードへの付与でしかなく失効も無いため不採用、
move 誘発型の遅延誘発は宣言判定（移動前）より後に
発火するため間に合わず不採用。本ファイルの実挙動
テストで (1)(2) と失効を登録カード自身で固定する。

実挙動は登録カード自身で固定する。ドライバは
scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。フィクスチャは
proto T1074（コスト9）/ T1075（コスト8）/ T001。
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

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex08-049"

CREATURE_FORM = [{"kind": "trigger",
                  "when": {"event": "turn_end", "player": "you"},
                  "effect": [
                      {"op": "choose",
                       "select": {"zone": "graveyard", "owner": "you",
                                  "filter": {"cost_le": 9, "cost_ge": 9},
                                  "count": "any"},
                       "as": "pick"},
                      {"op": "move",
                       "select": {"ref": "pick", "count": "all"},
                       "to": "hand", "reason": "return"}]}]
SPELL_FORM = [{"op": "move",
               "select": {"zone": "deck", "owner": "you", "from_top": 2},
               "to": "shield", "reason": "put"},
              {"op": "modify",
               "select": {"zone": "shield", "owner": "you"},
               "mod": {"allow": ["s_trigger"]},
               "dynamic": True,
               "duration": "until_next_own_turn_start"}]


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


def test_round392_disposition():
    rej = _reject_rows()
    assert len(rej) == 1975
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10337
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias 畳み込み0件
    assert not (c.get("source") or {}).get("unsupported")
    f0, f1 = c["faces"]
    assert f0["name"] == "十極 ジョバンチュ"
    assert f0["keywords"] == ["blocker", "cannot_attack_player"]
    assert f0["abilities"] == CREATURE_FORM
    assert f0["cost"] == 3 and f0["power"] == 4000
    assert f0["races"] == ["エンジェル・コマンド", "侵略者", "ナイト"]
    assert f1["name"] == "Genesis of Drillball"
    assert f1["types"] == ["spell"] and f1["cost"] == 9
    assert f1["spell"] == SPELL_FORM
    d = parse_card(c, TABLES)
    assert [f.name for f in d.faces] == ["十極 ジョバンチュ",
                                         "Genesis of Drillball"]
    left = {rid for rid, r in rej.items()
            if "return_any_number" in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T001", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _boring(d):
    if d["kind"] in ("charge", "main", "attack"):
        keys = [o["key"] for o in d["options"]]
        for want in ("pass", "end_turn", "end_attack", "end_phase"):
            if want in keys:
                return [keys.index(want)]
        return [0]
    return [0]


def _drive(e, handler=None, until=None, kinds=None, limit=1500):
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        if until is not None and d["kind"] in ("main", "charge", "attack") and until():
            return
        if kinds is not None:
            kinds.append(d["kind"])
        ans = handler(d) if handler else None
        e.answer(ans if ans is not None else _boring(d))
    raise AssertionError("did not settle")


def _to_main(e, player):
    for _ in range(600):
        d = e.advance()
        if d is None:
            raise AssertionError("game ended before main")
        if d["kind"] == "main" and d["player"] == player:
            return d
        e.answer(_boring(d))
    raise AssertionError("main not reached")


def _shield_idx(e, d, cid):
    for i, o in enumerate(d["options"]):
        if o.get("cid") == cid:
            return i
    return e.zlist("shield", e.s.cards[cid].owner).index(cid)


def _attack_handler(e, shield_cid, declare_keys=None):
    def h(d):
        if d["kind"] == "attack" and d["player"] == 1:
            ks = [o["key"] for o in d["options"]]
            if "attack:T001:player" in ks:
                return [ks.index("attack:T001:player")]
            return None
        if d["kind"] == "choose_shields":
            return [_shield_idx(e, d, shield_cid)]
        if d["kind"] == "declare_strigger":
            if declare_keys is not None:
                declare_keys.extend(o["key"] for o in d["options"])
                return list(range(len(d["options"])))
            return []
        return None
    return h


def _cast_spell_face(e):
    """登録カードの呪文面を唱え、シールドが7枚になるまで進める。
    唱える前にあったシールドの cid 集合を返す。"""
    before = set(e.zlist("shield", 0))
    d = _to_main(e, 0)
    keys = [o["key"] for o in d["options"]]
    assert f"play:{TARGET}:1" in keys
    e.answer([keys.index(f"play:{TARGET}:1")])
    _drive(e, until=lambda: len(e.zlist("shield", 0)) == 7)
    assert TARGET in _defns(e, "graveyard", 0)   # 唱えた後は墓地へ
    return before


# ---------- クリーチャー面の実挙動 ----------

def test_registered_creature_face_returns_cost9_at_turn_end(rules):
    """登録カード（クリーチャー面）が場にいる時、自分の
    ターンの終わりに墓地のコスト9を好きな枚数戻せる。
    コスト8は選べない（第357弾の確立形の登録形での再演）。"""
    e = _build(rules, {"bz": [TARGET],
                       "graveyard": ["T1074", "T1074", "T1075"]}, {})
    start = e.s.turn
    fired = 0
    for _ in range(1500):
        if e.s.turn >= start + 1:
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_cards":
            fired += 1
            e.answer([i for i, o in enumerate(d["options"])
                      if o["key"].split(":")[1] == "T1074"])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert fired == 1
    assert _defns(e, "hand", 0).count("T1074") == 2
    assert _defns(e, "graveyard", 0) == ["T1075"]


# ---------- 呪文面の実挙動 ----------

def test_registered_spell_face_grants_strigger_to_new_shields(rules):
    """呪文面を唱えると山札の上2枚が新しいシールドになり、
    その2枚（S・トリガーを持たないフィラー）でも相手の
    攻撃でブレイクされた時に S・トリガーを宣言でき、
    コストなしで召喚できる。"""
    e = _build(rules, {"hand": [TARGET], "mana": ["T1074"] * 9},
               {"bz": ["T001"]})
    before = _cast_spell_face(e)
    new_shields = [c for c in e.zlist("shield", 0) if c not in before]
    assert len(new_shields) == 2
    ces = [ce for ce in e.s.continuous
           if ce["mod"].get("allow") == ["s_trigger"]]
    assert len(ces) == 1 and ces[0]["duration"] == "until_turn_start:0"
    target = new_shields[0]
    seen = []
    h = _attack_handler(e, target, declare_keys=seen)
    _drive(e, h, until=lambda: e.s.cards[target].zone == "bz")
    assert "strigger:T001" in seen
    assert e.s.cards[target].zone == "bz"


def test_registered_spell_face_grant_expires_at_next_own_turn_start(rules):
    """付与は次の自分のターンのはじめまで: 失効した後は
    S・トリガーを持たないシールドを割られても宣言できず、
    手札に加わるだけ。"""
    e = _build(rules, {"hand": [TARGET], "mana": ["T1074"] * 9,
                       "shield": ["T264", "T001", "T001", "T001", "T001"]},
               {"bz": ["T001"]})
    _cast_spell_face(e)
    # 相手ターンは攻撃させずにやり過ごす
    _drive(e, until=lambda: e.s.active == 0 and e.s.turn >= 2)
    ces = [ce for ce in e.s.continuous
           if ce["mod"].get("allow") == ["s_trigger"]]
    assert ces == []
    t264 = next(c for c in e.zlist("shield", 0)
                if e.s.cards[c].defn == "T264")
    assert e._permits_face(t264, "s_trigger", None) is False
    seen = []
    h = _attack_handler(e, t264, declare_keys=seen)
    _drive(e, h, until=lambda: e.s.cards[t264].zone == "hand")
    assert e.s.cards[t264].zone == "hand"
    assert "strigger:T264" not in seen
