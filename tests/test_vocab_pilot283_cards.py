"""語彙パイロット第283弾のカード適用テスト（登録形）。

ラウンド318で eternal_kappa の8件を処理:
- 新規登録3件:
  - dm23ex3-s06 「使命」の頂天 グレイテスト・グレート: 残りギャップ
    look_put_any_number_rest_to_hand は既存の pile 束縛＋play_free
    （count: any）＋残りを手札の形で表せるため登録。
  - dm24bd6-002 「祝福」の頂天 ウェディング: each_opponent_shieldize は
    chooser: opp の move to shield（dm24ex3-023 の「相手は自身の〜を選ぶ」
    先例）で表せるため登録。
  - dm24sp2-003 「戦鬼」の頂天 ベートーベン: tapped_self_cannot_be_attacked
    は dmrp22-043 と同一文の常在型（if: exists {ref: self, filter:
    {tapped: true}} → deny attack_player）で表せるため登録。partial の
    マッハファイター展開形は1件に整理し、出た時能力は reason: summon と
    reveal: true を補い、残りは ref＋count: all の形に再構築した
    （partial の count: rest はエンジンに実装が無い）。
- 差し戻し5件（eternal_kappa 条項はキーワードとして partial に格納し、
  ギャップから外した）:
  - dm23ex3-or1（残り use_opponent_etb_abilities。負ける時形の置換能力も
    partial に格納）
  - dm23ex3-027（残り even_shield_or_cost_attack_permission）
  - dm24bd6-011（残り reveal_until、entered_turn_attack_player）
  - dm24bd6-024（残り battle_by_cost）
  - dm24rp3-td01（残り cast_opponent_graveyard_spells_then_bottom）
- converted 10,157 / rejects 2,176、重複0・漏れ0。eternal_kappa ギャップは
  残り0件でファミリー解消。

プロトテスト（test_vocab_pilot283.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ["dm23ex3-s06", "dm24bd6-002", "dm24sp2-003"]
REMAINING_GAPS = {
    "dm23ex3-or1": ["use_opponent_etb_abilities"],
    "dm23ex3-027": ["even_shield_or_cost_attack_permission"],
    "dm24bd6-011": ["reveal_until", "entered_turn_attack_player"],
    "dm24bd6-024": ["battle_by_cost"],
    "dm24rp3-td01": ["cast_opponent_graveyard_spells_then_bottom"],
}
BANKED = sorted(REMAINING_GAPS)

EXPECTED_KAPPA = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                             "filter": {"face_down": True}}}, ">=", 3]},
    "instead": [{"op": "flip_up",
                 "select": {"zone": "mana", "owner": "you",
                            "filter": {"face_down": True}, "count": 3}}],
}

EXPECTED_LOSE = {
    "kind": "replace", "optional": True,
    "when": {"event": "lose"},
    "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                             "filter": {"face_down": True}}}, ">=", 3]},
    "instead": [{"op": "flip_up",
                 "select": {"zone": "mana", "owner": "you",
                            "filter": {"face_down": True}, "count": 3}}],
}


def _setup(rules, p0, p1=None, **kw):
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001",
                         "seed": 1, "deck_size": 20, **kw})


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if r["id"] == cid:
                return r
    raise KeyError(cid)


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, zone, p, defn):
    cids = e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)
    return next(c for c in cids if e.cdef(c).id == defn)


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _face_down_count(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].face_down)


def _set_face_down(e, p, n):
    """マナゾーンの先頭 n 枚を裏向きにする（第283弾プロトと同じ直接設定）。"""
    for c in e.zlist("mana", p)[:n]:
        e.s.cards[c].face_down = True


class _Driver:
    """汎用ドライバ（第276弾のものに choose_replacement 受諾を足したもの）。

    play: main 決定で (e, d) -> 答えのリストか None を返すフック。
    choose_defn: choose_cards ではその defn のカードを1枚選ぶ。
    choose: choose_cards で (e, d) -> 答えか None を返すフック（対象選択用）。
    attack_log: (turn, player, keys) を全攻撃決定について記録する。
    """

    def __init__(self, play=None, choose_defn=None, choose=None, pre=None):
        self.play = play
        self.choose_defn = choose_defn
        self.choose = choose
        self.pre = pre
        self.attack_log = []
        self.seen = []

    def run(self, e, stop, limit=1200):
        for _ in range(limit):
            if e.s.result is not None:
                return
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen.append(kind)
            if self.pre is not None:
                self.pre(e, d)
            if kind == "choose_replacement":
                hit = [i for i, k in enumerate(keys) if k.startswith("replace:")]
                assert hit, "置換の諮問に replace 選択肢が無い"
                e.answer(hit[:1])
                if stop(e):
                    return
                continue
            if kind == "choose_cards" and self.choose is not None:
                ans = self.choose(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "choose_cards" and self.choose_defn is not None:
                hit = [i for i, o in enumerate(d["options"])
                       if e.cdef(o["cid"]).id == self.choose_defn]
                if hit:
                    e.answer(hit[:1])
                    if stop(e):
                        return
                    continue
            if kind == "main" and self.play is not None:
                ans = self.play(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "attack":
                self.attack_log.append((e.s.turn, d["player"], list(keys)))
            if kind == "declare_strigger":
                e.answer([])
            elif kind == "declare_sback":
                e.answer([])
            elif kind == "choose_breaker":
                e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
            elif kind == "choose_shields":
                e.answer(list(range(d.get("min", 0))))
            elif kind == "pay_mana":
                e.answer([0])
            elif kind == "yes_no":
                e.answer([keys.index("yes")])
            elif kind == "order_pending":
                e.answer([0])
            elif kind == "block":
                if "no_block" in keys:
                    e.answer([keys.index("no_block")])
                else:
                    e.answer(list(range(d.get("min", 0))))
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            if stop(e):
                return
        raise AssertionError("limit reached")


def _play_once(key):
    seen = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None

    return play


def _choose_targets(*defns):
    """choose_cards で、指定した defn のカードを順に選ぶフック。"""
    queue = list(defns)

    def choose(e, d):
        if not queue:
            return None
        for i, o in enumerate(d["options"]):
            if e.cdef(o["cid"]).id == queue[0]:
                queue.pop(0)
                return [i]
        return None

    return choose


def _kappa_expansions(card_dict):
    d = parse_card(copy.deepcopy(card_dict), TABLES)
    return [ab for ab in d.abilities if ab.get("keyword") == "eternal_kappa"]


# ---------- 登録形 ----------

def test_registered_forms():
    for cid in REGISTERED:
        c = _converted(cid)
        parse_card(copy.deepcopy(c), TABLES)
        assert "unsupported" not in (c.get("source") or {}), cid
        assert c["crystal_soul"] == 3, cid
        kabs = _kappa_expansions(c)
        assert len(kabs) == 1, cid
        assert {k: kabs[0][k] for k in EXPECTED_KAPPA} == EXPECTED_KAPPA, cid
        try:
            _reject(cid)
            raise AssertionError(f"{cid} が rejects に残っている")
        except KeyError:
            pass

    c = _converted("dm23ex3-s06")
    assert c["name"] == "「使命」の頂天 グレイテスト・グレート"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 11 and c["power"] == 12000
    assert c["races"] == ["ゼニス・セレス"]
    assert c["keywords"] == ["triple_breaker", "eternal_kappa"]
    assert (c["source"] or {}).get("aliases") == ["dm23ex3-sp4"]
    assert c["abilities"] == [
        {"kind": "static",
         "affects": {"owner": "you", "filter": {"types": ["creature"]}},
         "mod": {"grant": ["speed_attacker"]}},
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "subject": "self",
                  "reason": "summon"},
         "effect": [
             {"op": "choose",
              "select": {"zone": "deck", "owner": "you", "from_top": 3,
                         "look": True, "count": "all"},
              "as": "pile"},
             {"op": "play_free",
              "select": {"ref": "pile",
                         "filter": {"types": ["creature"], "cost_le": 7},
                         "count": "any"}},
             {"op": "move", "select": {"ref": "pile", "count": "all"},
              "to": "hand", "reason": "draw"}]},
    ]

    c = _converted("dm24bd6-002")
    assert c["name"] == "「祝福」の頂天 ウェディング"
    assert c["types"] == ["creature"]
    assert c["civs"] == ["light", "darkness", "fire"]
    assert c["cost"] == 12 and c["power"] == 15500
    assert c["races"] == ["ゼニス・セレス"]
    assert c["keywords"] == ["blocker", "speed_attacker", "triple_breaker",
                             "eternal_kappa"]
    assert c["abilities"] == [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "subject": "self",
                  "reason": "summon"},
         "effect": [
             {"op": "move",
              "select": {"zone": "bz", "owner": "opp", "chooser": "opp",
                         "filter": {"types": ["creature"]}, "count": 2},
              "to": "shield", "reason": "charge"},
             {"op": "move",
              "select": {"zone": "hand", "owner": "opp", "chooser": "opp",
                         "count": 2},
              "to": "shield", "reason": "charge"}]},
        {"kind": "trigger",
         "when": {"event": "attack", "subject": "self"},
         "effect": [
             {"op": "move",
              "select": {"zone": "shield", "owner": "opp", "chooser": "opp",
                         "count": 1},
              "to": "graveyard", "reason": "put"}]},
    ]

    c = _converted("dm24sp2-003")
    assert c["name"] == "「戦鬼」の頂天 ベートーベン"
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 13 and c["power"] == 19000
    assert c["races"] == ["ゼニス・セレス"]
    assert c["keywords"] == ["quad_breaker", "eternal_kappa"]
    assert (c["source"] or {}).get("aliases") == ["dm23ex3-s08", "dm23ex3-sp5"]
    assert c["abilities"] == [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [{"op": "modify", "select": {"ref": "self"},
                     "mod": {"allow": [{"action": "attack_creature",
                                        "other": {"tapped": False}}]},
                     "duration": "end_of_turn"}]},
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "subject": "self",
                  "reason": "summon"},
         "effect": [
             {"op": "choose",
              "select": {"zone": "deck", "owner": "you", "from_top": 3,
                         "look": True, "count": "all"},
              "as": "pile"},
             {"op": "may", "body": [
                 {"op": "choose",
                  "select": {"ref": "pile", "filter": {"types": ["creature"]},
                             "count": "any"},
                  "reveal": True, "as": "take"},
                 {"op": "move", "select": {"ref": "take", "count": "all"},
                  "to": "hand", "reason": "draw"}]},
             {"op": "move", "select": {"ref": "pile", "count": "all"},
              "to": "mana", "reason": "put", "face_down": True}]},
        {"kind": "static",
         "affects": {"owner": "opp", "zone": "bz",
                     "filter": {"types": ["creature"]}},
         "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
         "mod": {"deny": ["attack_player"]}},
    ]


def test_banked_rows():
    """差し戻し5件: rejects に残り、eternal_kappa はギャップから外れ、
    partial にキーワード（or1 は負ける時形も）として格納されている。"""
    for cid in BANKED:
        row = _reject(cid)
        assert "eternal_kappa" not in row["gaps"], cid
        assert sorted(row["gaps"]) == sorted(REMAINING_GAPS[cid]), cid
        partial = row["partial"]
        assert "eternal_kappa" in (partial.get("keywords") or []), cid
        kabs = _kappa_expansions(partial)
        assert len(kabs) == 1, cid
        assert {k: kabs[0][k] for k in EXPECTED_KAPPA} == EXPECTED_KAPPA, cid
        assert _conv_cache.find(CONVERTED, cid) is None, cid
    or1 = _reject("dm23ex3-or1")["partial"]
    assert or1["abilities"] == [EXPECTED_LOSE]


# ---------- 実挙動 ----------

def test_registered_s06_cip_puts_cheap_creature_rest_to_hand():
    """dm23ex3-s06: 召喚によって出た時、上から3枚（T001=コスト2獣 /
    T003=呪文 / T052=コスト8獣）を見て、コスト7以下のクリーチャー
    （T001）だけを出し、残りは手札に加える。"""
    e = _setup(load_rules(),
               {"hand": ["dm23ex3-s06"], "mana": ["T034"] * 11,
                "shield": ["T002"] * 5, "deck": ["T003", "T052", "T001", "T003"]},
               {"bz": ["T001"], "deck": ["T002"] * 12},
               filler="T002", deck_size=0)
    drv = _Driver(play=_play_once("play:dm23ex3-s06"), choose_defn="T001")
    drv.run(e, lambda ev: "T001" in _defns(ev, "bz", 0)
            and "T003" in _defns(ev, "hand", 0) and _quiet(ev))
    assert "dm23ex3-s06" in _defns(e, "bz", 0)
    assert "T001" in _defns(e, "bz", 0)          # コスト7以下は出す
    assert "T052" not in _defns(e, "bz", 0)      # コスト8は出せない
    assert "T052" in _defns(e, "hand", 0)        # 残りは手札へ
    assert "T003" in _defns(e, "hand", 0)


def test_registered_bd6002_cip_shieldize_by_opponent_choice():
    """dm24bd6-002: 召喚によって出た時、各相手（この対局では相手）は自身の
    クリーチャー2体と自身の手札2枚を選び、シールド化する。"""
    e = _setup(load_rules(),
               {"hand": ["dm24bd6-002"],
                "mana": ["T030"] * 10 + ["T008", "T034"]},
               {"bz": ["T001", "T001", "T001"], "hand": ["T001", "T003"]})
    hand0 = len(e.zlist("hand", 1))
    shield0 = len(e.zlist("shield", 1))
    drv = _Driver(play=_play_once("play:dm24bd6-002"))
    drv.run(e, lambda ev: "dm24bd6-002" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 1)) == shield0 + 4 and _quiet(ev))
    assert _defns(e, "bz", 1).count("T001") == 1     # 3体中2体がシールド化
    assert len(e.zlist("shield", 1)) == shield0 + 4  # 獣2＋手札2
    assert len(e.zlist("hand", 1)) == hand0 - 2      # 手札から2枚


def test_registered_sp2003_cip_take_and_face_down_mana():
    """dm24sp2-003: 召喚によって出た時、上から3枚（T001 / T004 / T003）を
    見て、T001を表向きにして手札に加え、残りは裏向きでマナゾーンへ。"""
    e = _setup(load_rules(),
               {"hand": ["dm24sp2-003"], "mana": ["T001"] * 13,
                "shield": ["T002"] * 5, "deck": ["T003", "T004", "T001", "T003"]},
               {"bz": ["T001"], "deck": ["T002"] * 12},
               filler="T002", deck_size=0)
    drv = _Driver(play=_play_once("play:dm24sp2-003"), choose_defn="T001")
    drv.run(e, lambda ev: "T001" in _defns(ev, "hand", 0)
            and len(ev.zlist("mana", 0)) == 15 and _quiet(ev))
    assert "dm24sp2-003" in _defns(e, "bz", 0)
    assert "T001" in _defns(e, "hand", 0)            # 表向きにして手札へ
    assert "T004" not in _defns(e, "hand", 0)
    for defn in ("T004", "T003"):                    # 残りは裏向きでマナへ
        cid = _cid(e, "mana", 0, defn)
        assert e.s.cards[cid].face_down is True
    assert _face_down_count(e, 0) == 2


def test_registered_sp2003_tapped_protects_player():
    """dm24sp2-003 がタップしていれば、相手のクリーチャーは自分（プレイヤー）
    を攻撃できない。ただしタップしているこのクリーチャー自体は攻撃できる。"""
    e = _setup(load_rules(),
               {"bz": ["dm24sp2-003"]},
               {"bz": ["T001"]})
    def _tap_bee(e, d):   # 相手ターン（2ターン目）の決定前にタップする
        # （自ターンに触ると攻撃選択肢の再計算で回答インデックスがずれる）
        if e.s.turn < 2:
            return
        bee = _cid(e, "bz", 0, "dm24sp2-003")
        if bee is not None:
            e.s.cards[bee].tapped = True
    drv = _Driver(pre=_tap_bee)
    drv.run(e, lambda ev: any(p == 1 for _, p, _ in drv.attack_log))
    keys = next(k for _, p, k in drv.attack_log if p == 1)
    assert "attack:T001:player" not in keys          # プレイヤーは攻撃できない
    assert "attack:T001:dm24sp2-003" in keys         # 本体は攻撃できる


def test_registered_sp2003_untapped_allows_player_attack():
    """対照: dm24sp2-003 がアンタップなら、相手はプレイヤーを攻撃できる。"""
    e = _setup(load_rules(),
               {"bz": ["dm24sp2-003"]},
               {"bz": ["T001"]})
    drv = _Driver()
    drv.run(e, lambda ev: any(p == 1 for _, p, _ in drv.attack_log))
    keys = next(k for _, p, k in drv.attack_log if p == 1)
    assert "attack:T001:player" in keys


def test_registered_bd6002_eternal_kappa_replaces_destroy():
    """dm24bd6-002（登録形）: 破壊される時、裏向きマナ3枚を表向きにして
    バトルゾーンに残る。"""
    e = _setup(load_rules(),
               {"bz": ["dm24bd6-002"], "mana": ["T001"] * 6},
               {"hand": ["T056"], "mana": ["T008"] * 3})
    _set_face_down(e, 0, 3)
    assert _face_down_count(e, 0) == 3
    drv = _Driver(play=_play_once("play:T056"),
                  choose=_choose_targets("dm24bd6-002"))
    drv.run(e, lambda ev: "dm24bd6-002" in _defns(ev, "bz", 0)
            and _face_down_count(ev, 0) == 0 and _quiet(ev))
    assert "dm24bd6-002" in _defns(e, "bz", 0)
    assert "dm24bd6-002" not in _defns(e, "graveyard", 0)
    assert _face_down_count(e, 0) == 0
    assert drv.seen.count("choose_replacement") == 1
