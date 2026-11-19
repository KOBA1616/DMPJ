"""語彙パイロット第288弾のカード適用テスト（登録形）。

ラウンド323で civilization_match 純粋3件を新規登録し、ファミリー解消:
- dm27-026 暗黒螺旋: partial（text は公式全文、keywords に s_trigger）に
  形Aの呪文効果を追加。相手が手札を1枚選んで捨て（chooser: opp、as で
  束縛）、捨てたカードの文明と同じ文明のカードが自分のマナゾーンにあれば、
  相手は自分のマナゾーンからカードを1枚選び、墓地に置く。
- dm27-047 デビル・スモーク: partial の text は節の途中まで切れていたため
  reject 行の公式全文に戻し、形Bの呪文効果を追加。相手のタップされて
  いないクリーチャーを1体破壊し、その文明と同じ文明のカードが自分の
  マナゾーンにあれば、カードを1枚引いてもよい（不一致では諮問自体が
  起きない）。
- dmr21-002 ワルスラ・プリンスS: reject 行は partial が null で reason も
  無いため reopen では外れず、submit の直接経路で登録。公式データ
  （by_product/r21）から全構築（水・コスト6・パワー6000・種族
  マジック・コマンド/イニシャルズ・mana 1・W・ブレイカー）し、形C
  （自分の他のクリーチャーを召喚した時、そのクリーチャーを破壊しても
  よい。そうしたら上1枚を公開し、同じ文明のクリーチャーなら出す、
  他は手札へ）を追加。
- 3件とも canon は自 ID で alias は無し。
- converted 10,175 / rejects 2,155、重なり0・漏れ0。civilization_match
  は残り0件でファミリー解消。

プロトテスト（test_vocab_pilot288.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402


def setup(rules, p0, p1=None, filler="T002", seed=1, deck_size=20):
    """conftest の setup と同じ薄い包み。tests.conftest を import すると
    DMSIM_SKIP_CONVERTED が再設定されて converted が読めなくなるため、
    ここでは直接 scenario.build を包む（第287弾 cards と同じ）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


def setup_exact(rules, p0, p1=None, filler="T002"):
    """山札の中身を spec の deck リストだけにする（deck_exact）。
    山札の並びは seed でシャッフルされるため、テストは実状態を読む。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": 1, "deck_size": 20,
                         "deck_exact": [True, True]})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGETS = ["dm27-026", "dm27-047", "dmr21-002"]

FORM_A_OPS = [
    {"op": "move",
     "select": {"zone": "hand", "owner": "opp", "chooser": "opp", "count": 1},
     "to": "graveyard", "reason": "discard", "as": "dropped"},
    {"op": "if",
     "cond": {"exists": {"zone": "mana", "owner": "you",
                         "filter": {"civs": {"civs_of": "dropped"}}}},
     "then": [{"op": "move",
               "select": {"zone": "mana", "owner": "opp", "chooser": "opp",
                          "count": 1},
               "to": "graveyard", "reason": "put"}]},
]

FORM_B_OPS = [
    {"op": "move",
     "select": {"zone": "bz", "owner": "opp",
                "filter": {"types": ["creature"], "tapped": False}, "count": 1},
     "to": "graveyard", "reason": "destroy", "as": "victim"},
    {"op": "if",
     "cond": {"exists": {"zone": "mana", "owner": "you",
                         "filter": {"civs": {"civs_of": "victim"}}}},
     "then": [{"op": "may",
               "body": [{"op": "draw", "count": 1}]}]},
]

FORM_C = {"kind": "trigger",
          "when": {"event": "move", "to": "bz", "reason": "summon",
                   "subject": {"owner": "you", "other": True,
                               "filter": {"types": ["creature"]}}},
          "effect": [
              {"op": "may",
               "body": [
                   {"op": "move",
                    "select": {"ref": "event.subject"},
                    "to": "graveyard", "reason": "destroy", "as": "sac"},
                   {"op": "if",
                    "cond": {"exists": {"ref": "sac", "zone": "graveyard"}},
                    "then": [
                        {"op": "choose",
                         "select": {"zone": "deck", "owner": "you",
                                    "from_top": 1},
                         "reveal": True, "as": "top"},
                        {"op": "if",
                         "cond": {"exists": {"ref": "top",
                                             "filter": {
                                                 "types": ["creature"],
                                                 "civs": {"civs_of": "sac"}}}},
                         "then": [{"op": "move", "select": {"ref": "top"},
                                   "to": "bz", "reason": "put"}],
                         "else": [{"op": "move", "select": {"ref": "top"},
                                   "to": "hand", "reason": "draw"}]}]}]}]}

TEXT_026 = ("S・トリガー\n"
            "相手は自分自身の手札を１枚選んで捨てる。そのカードの文明と"
            "同じ文明のカードが自分のマナゾーンに１枚でもあれば、相手は"
            "自分自身のマナゾーンからカードを１枚選び、墓地に置く。")

TEXT_047 = ("相手のタップされていないクリーチャーを１体破壊する。"
            "そのクリーチャーの文明と同じ文明のカードが自分のマナゾーンに"
            "１枚でもあれば、カードを１枚引いてもよい。")

TEXT_002 = ("W・ブレイカー自分の他のクリーチャーを召喚した時、その"
            "クリーチャーを破壊してもよい。そうしたら、自分の山札の上から"
            "１枚目を表向きにする。それが、破壊したクリーチャーと同じ文明を"
            "持つクリーチャーなら、バトルゾーンに出す。そうでなければ、"
            "自分の手札に加える。")


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


# ---------- 登録形 ----------

def test_registered_forms():
    rej = _reject_rows()
    for cid in TARGETS:
        assert cid not in rej, cid
        _converted(cid)
    # ファミリー解消: civilization_match を含む行は rejects に残らない
    assert not [r["id"] for r in rej.values()
                if "civilization_match" in (r.get("gaps") or [])]

    c = _converted("dm27-026")
    assert c["spell"] == FORM_A_OPS
    assert c["keywords"] == ["s_trigger"]
    assert not c.get("abilities")
    assert c["text"] == TEXT_026
    assert "unsupported" not in (c.get("source") or {})
    assert (c.get("source") or {}).get("aliases") is None
    d = parse_card(c, TABLES)
    assert d.spell == FORM_A_OPS
    assert "s_trigger" in d.keywords

    c = _converted("dm27-047")
    assert c["spell"] == FORM_B_OPS
    assert not c.get("keywords")
    assert not c.get("abilities")
    assert c["text"] == TEXT_047
    assert "unsupported" not in (c.get("source") or {})
    assert (c.get("source") or {}).get("aliases") is None
    d = parse_card(c, TABLES)
    assert d.spell == FORM_B_OPS

    c = _converted("dmr21-002")
    assert c["abilities"] == [FORM_C]
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == TEXT_002
    assert c["civs"] == ["water"] and c["cost"] == 6 and c["power"] == 6000
    assert c["races"] == ["マジック・コマンド", "イニシャルズ"]
    assert c["mana"] == 1
    assert "unsupported" not in (c.get("source") or {})
    assert (c.get("source") or {}).get("aliases") is None
    d = parse_card(c, TABLES)
    assert [a for a in d.abilities if a["kind"] == "trigger"] == [FORM_C]
    assert "double_breaker" in d.keywords


# ---------- 実挙動の共通部品（第288弾プロトと同じ型） ----------

def _zone(e, player, zone):
    lst = list(e.zlist(zone, player))
    if zone == "bz":   # バトルゾーンは共有リストなので controller で絞る
        lst = [c for c in lst if e.s.cards[c].controller == player]
    return lst


def _defn(e, cid):
    return e.cdef(cid).id


def _zone_of(e, cid):
    return e.s.cards[cid].zone


def _drive(e, on_decision, limit=900):
    """汎用ドライバ。on_decision の戻り値:
    "stop" = ここで止める / "ok" = ハンドラが回答済み / None = 汎用回答。"""
    for _ in range(limit):
        if e.s.result is not None:
            return "result"
        d = e.advance()
        if d is None:
            return "done"
        r = on_decision(e, d)
        if r == "stop":
            return "stopped"
        if r == "ok":
            continue
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("driver limit reached")


def _play_and_pay(play_key, player=0):
    played = []

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == player \
                and play_key in keys:
            played.append(True)
            e.answer([keys.index(play_key)])
            return "ok"
        if played and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        return None

    return handler, played


def _pick_defn(want_defn, player):
    """choose_cards で want_defn のカードを選ぶハンドラ部品。"""
    def handler(e, d):
        if d["kind"] == "choose_cards" and d.get("player") == player:
            for i, o in enumerate(d["options"]):
                if o.get("cid") is not None and _defn(e, o["cid"]) == want_defn:
                    e.answer([i])
                    return "ok"
        return None
    return handler


def _yes_no(answer_yes, seen):
    def handler(e, d):
        if d["kind"] == "yes_no":
            seen.append(d)
            keys = [o["key"] for o in d["options"]]
            if "yes" in keys:
                e.answer([keys.index("yes" if answer_yes else "no")])
            else:
                e.answer([0] if answer_yes else [len(keys) - 1])
            return "ok"
        return None
    return handler


def _chain(*handlers, stop=None):
    def on_dec(e, d):
        for h in handlers:
            r = h(e, d)
            if r:
                return r
        if stop and stop(e, d):
            return "stop"
        return None
    return on_dec


def _stop_at_charge(player):
    def stop(e, d):
        return d["kind"] == "charge" and d.get("player") == player
    return stop


# ---------- 形A: dm27-026 暗黒螺旋 ----------

def _cast_026(rules, p0_mana, p1_hand, discard_defn):
    e = setup(rules, {"hand": ["dm27-026"], "mana": p0_mana},
              {"hand": p1_hand, "mana": ["T001", "T001"]})
    handler, played = _play_and_pay("play:dm27-026")
    seen_choose = []

    def watch(e, d):
        if d["kind"] == "choose_cards":
            seen_choose.append((d.get("player"),
                                [_defn(e, o["cid"]) for o in d["options"]
                                 if o.get("cid") is not None]))
        return None

    on_dec = _chain(watch, handler, _pick_defn(discard_defn, 1),
                    stop=_stop_at_charge(1))
    _drive(e, on_dec)
    assert played
    return e, seen_choose


def test_026_match_mana_to_graveyard(rules):
    # 自分のマナに火がある。相手が火のカードを捨てる → 相手のマナが墓地へ
    e, seen = _cast_026(rules, ["T008", "T034", "T001", "T001", "T001"],
                        ["T034", "T010"], "T034")
    assert len(_zone(e, 1, "mana")) == 1
    gy = [_defn(e, c) for c in _zone(e, 1, "graveyard")]
    assert gy.count("T034") == 1 and gy.count("T001") == 1
    # 選択は2回とも相手（捨て札とマナ）
    assert [p for p, _ in seen] == [1, 1]


def test_026_no_match(rules):
    # 自分のマナに火が無い → 第2文は不発。相手のマナは不変
    e, seen = _cast_026(rules, ["T008", "T010", "T010", "T001", "T001"],
                        ["T034", "T001"], "T034")
    assert len(_zone(e, 1, "mana")) == 2
    assert [_defn(e, c) for c in _zone(e, 1, "graveyard")] == ["T034"]
    assert len(seen) == 1   # 捨て札の選択だけ


# ---------- 形B: dm27-047 デビル・スモーク ----------

def _cast_047(rules, p0_mana, p1_bz, draw_answer=None):
    e = setup(rules, {"hand": ["dm27-047"], "mana": p0_mana}, {"bz": p1_bz})
    handler, played = _play_and_pay("play:dm27-047")
    seen_yes_no = []
    parts = [handler]
    if draw_answer is not None:
        parts.append(_yes_no(draw_answer, seen_yes_no))
    else:
        def watch(e, d):
            if d["kind"] == "yes_no":
                seen_yes_no.append(d)
                return "stop"
            return None
        parts.append(watch)
    _drive(e, _chain(*parts, stop=_stop_at_charge(1)))
    assert played
    return e, seen_yes_no


def test_047_match_and_draw(rules):
    e, seen = _cast_047(rules, ["T008", "T034", "T001", "T001", "T001"],
                        ["T034"], draw_answer=True)
    assert len(seen) == 1
    assert _defn(e, _zone(e, 1, "graveyard")[0]) == "T034"
    assert len(_zone(e, 0, "hand")) == 1   # 引いた1枚だけが手札にある


def test_047_match_and_decline(rules):
    e, seen = _cast_047(rules, ["T008", "T034", "T001", "T001", "T001"],
                        ["T034"], draw_answer=False)
    assert len(seen) == 1
    assert len(_zone(e, 0, "hand")) == 0


def test_047_no_match_no_offer(rules):
    e, seen = _cast_047(rules, ["T008", "T034", "T010", "T010", "T034"],
                        ["T001"], draw_answer=None)
    assert seen == []                       # 諮問自体が起きない
    assert _defn(e, _zone(e, 1, "graveyard")[0]) == "T001"
    assert len(_zone(e, 0, "hand")) == 0


# ---------- 形C: dmr21-002 ワルスラ・プリンスS ----------

def _summon_with_002(rules, deck, answer_yes=True):
    # p1 の山札に filler と同じ defn（T002）を使うと deck_exact が
    # filler とみなして取り除き山札0枚になるため、別の defn を使う
    e = setup_exact(rules, {"bz": ["dmr21-002"], "hand": ["T001"],
                            "mana": ["T001", "T001"], "deck": deck},
                    {"deck": ["T827"] * 3})
    handler, played = _play_and_pay("play:T001")
    seen_yes_no = []
    snap = []

    def watch(e, d):
        if played and not snap:
            snap.append(list(_zone(e, 0, "deck")))
        return None

    on_dec = _chain(watch, handler, _yes_no(answer_yes, seen_yes_no),
                    stop=_stop_at_charge(1))
    _drive(e, on_dec)
    assert played
    summoned = next((c for c in _zone(e, 0, "graveyard")
                     if _defn(e, c) == "T001"), None) if answer_yes else None
    return e, seen_yes_no, snap[0], summoned


def test_002_match_puts_top_into_bz(rules):
    e, seen, snap, summoned = _summon_with_002(rules, ["T827"] * 8)
    assert len(seen) == 1                    # 破壊の諮問が1度だけ
    top = snap[0]
    assert _zone_of(e, top) == "bz"          # 同じ文明（自然）の獣は場に出る
    assert e.s.cards[top].controller == 0
    assert summoned is not None              # 召喚した獣は破壊された


def test_002_other_civ_goes_to_hand(rules):
    e, seen, snap, summoned = _summon_with_002(rules, ["T034"] * 8)
    top = snap[0]
    assert _zone_of(e, top) == "hand"        # 火は自然と一致しない
    assert summoned is not None


def test_002_spell_goes_to_hand(rules):
    e, seen, snap, summoned = _summon_with_002(rules, ["T003"] * 8)
    top = snap[0]
    assert _zone_of(e, top) == "hand"        # クリーチャーでなければ手札へ
    assert summoned is not None


def test_002_decline_keeps_everything(rules):
    e, seen, snap, _ = _summon_with_002(rules, ["T827"] * 8, answer_yes=False)
    assert len(seen) == 1
    assert any(_defn(e, c) == "T001" for c in _zone(e, 0, "bz"))
    assert _zone(e, 0, "deck") == snap       # 山札は動かない
