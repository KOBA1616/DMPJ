"""語彙パイロット第287弾のカード適用テスト（登録形）。

ラウンド322で deck_bottom_card 純粋4件 + deck_bottom_reveal 純粋3件の
計7行を処理し、新規登録5件 + alias 畳み込み3行で両ファミリーを解消:
- dm26rp3-018 キング・ザ・ベスト: partial 完全。攻撃時誘発（形C）を追加。
- dm32-019 サイバーX・ザナドゥ: partial に abilities 無し。出た時
  （相手の進化ではないクリーチャー1体を山札の一番下に戻す）と形D
  （離れた時、相手が自身の一番下を公開し出してもよい）を構築。
  dm32-019hc は同一カードの別刷りで、canon は本刷りのため alias に畳んだ
  （reject 行は reopen で外し、登録時に alias として取り込んだ）。
- dmr06-002 合身巨兵エクスキュベーターMS: partial のガチンコ勝利分岐の
  then 末尾に形A（その後、一番下を手札に加えてもよい）を追加。
  partial の text の文字化けは reject 行の公式全文で戻した。
- dm26sd1-n006 カツラデランス / 「アフロ行きま～す!!」: canon 刷りはこちら
  （dmrp05-007 は alias。当初の対象指定だった rp05-007 は canon でないため
  submit できず、n006 を登録して rp05-007 の reject 行は reopen で外した）。
  partial の faces は仮置きのため公式 faces から再構築。クリーチャー面は
  形Bのジョーカーズ変種（ゲートなし・コスト6以下）だが、原文が
  「なら出す」の強制形のため may を付けない（第287弾の提出形メモの
  may 形から修正）。呪文面は手札を1枚捨て、カードを2枚引く。
- dm26rp3-tr007 一王二命三眼槍: canon 刷りはこちら（dm26sd1-c001 は
  alias。c001 の reject 行は reason が無く reopen 対象外だったため、
  登録後に stale な alias 行として直接除去した）。partial は null のため
  公式データから全構築（形Eの手札からの敗北置換 + 形Bの鬼エンド）。
- converted 10,172 / rejects 2,158、重なり0・漏れ0。
  deck_bottom_card / deck_bottom_reveal / deck_bottom_mill は残り0件。

プロトテスト（test_vocab_pilot287.py）とは別プロセスで実行すること
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
    ここでは直接 scenario.build を包む（第286弾 cards と同じ）。"""
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

CANON = ["dm26rp3-018", "dm32-019", "dmr06-002", "dm26sd1-n006",
         "dm26rp3-tr007"]
ALIASES = {"dm32-019": ["dm32-019hc"],
           "dm26sd1-n006": ["dmex12-008", "dmex19-011", "dmrp05-007"],
           "dm26rp3-tr007": ["dm22ex2-s09", "dm23bd2-005", "dm23rp2-sp05",
                             "dm26sd1-c001", "dm26sd1-c001star", "dmart01-002",
                             "dmex17-cho37", "dmrp16-s10", "dmrp21-tr7"]}

GATE = {"any": [{"cmp": [{"count": {"zone": "shield", "owner": "you"}}, "==", 0]},
                {"cmp": [{"count": {"zone": "shield", "owner": "opp"}}, "==", 0]}]}

BOTTOM_TO_GRAVE = {"op": "move",
                   "select": {"zone": "deck", "owner": "you", "from_bottom": 1},
                   "to": "graveyard", "reason": "put", "as": "bot"}

FORM_B = {"kind": "trigger",
          "when": {"event": "move", "to": "bz", "subject": "self"},
          "if": GATE,
          "effect": [BOTTOM_TO_GRAVE,
                     {"op": "if",
                      "cond": {"exists": {"ref": "bot",
                                          "filter": {"types": ["creature"],
                                                     "cost_le": 5}}},
                      "then": [{"op": "may",
                                "body": [{"op": "play_free",
                                          "select": {"ref": "bot"}}]}]}]}

FORM_B_JOKERS_MAND = {"kind": "trigger",
                      "when": {"event": "move", "to": "bz", "subject": "self"},
                      "effect": [BOTTOM_TO_GRAVE,
                                 {"op": "if",
                                  "cond": {"exists": {"ref": "bot",
                                                      "filter": {"types": ["creature"],
                                                                 "races": ["ジョーカーズ"],
                                                                 "cost_le": 6}}},
                                  "then": [{"op": "play_free",
                                            "select": {"ref": "bot"}}]}]}

FORM_C = {"kind": "trigger",
          "when": {"event": "attack", "subject": "self"},
          "effect": [{"op": "choose",
                      "select": {"zone": "deck", "owner": "you", "from_bottom": 3,
                                 "look": True, "count": "all"},
                      "as": "pile", "reveal": True},
                     {"op": "play_free",
                      "select": {"ref": "pile",
                                 "filter": {"types": ["creature"],
                                            "races": ["ジョーカーズ"],
                                            "cost_le": 8},
                                 "count": 1, "up_to": True}},
                     {"op": "move",
                      "select": {"ref": "pile", "count": "all"},
                      "to": "deck", "position": "top", "order": "choose",
                      "reason": "put"}]}

CIP_BOTTOM_RETURN = {"kind": "trigger",
                     "when": {"event": "move", "to": "bz", "subject": "self"},
                     "effect": [{"op": "move",
                                 "select": {"zone": "bz", "owner": "opp",
                                            "filter": {"types": ["creature"],
                                                       "evolution": False},
                                            "count": 1},
                                 "to": "deck", "position": "bottom",
                                 "reason": "return"}]}

FORM_D = {"kind": "trigger",
          "when": {"event": "move", "from": "bz", "subject": "self"},
          "effect": [{"op": "choose",
                      "select": {"zone": "deck", "owner": "opp", "from_bottom": 1,
                                 "look": True, "count": "all"},
                      "as": "pile", "reveal": True},
                     {"op": "play_free",
                      "select": {"ref": "pile",
                                 "filter": {"types": ["creature"],
                                            "evolution": False},
                                 "count": 1, "up_to": True, "chooser": "opp"},
                      "player": "opp"}]}

FORM_E_REPLACE = {"kind": "replace", "zone": "hand", "optional": True,
                  "when": {"event": "lose"},
                  "if": {"all": [{"is_turn": "opp"},
                                 {"exists": {"zone": "mana", "owner": "you",
                                             "filter": {"civs": ["darkness"]}}},
                                 {"exists": {"zone": "mana", "owner": "you",
                                             "filter": {"civs": ["fire"]}}}]},
                  "instead": [{"op": "move", "select": {"ref": "self"},
                               "to": "deck", "position": "bottom",
                               "face_up": True, "reason": "put"}]}

FORM_002 = {"kind": "trigger",
            "when": {"event": "attack", "subject": "self"},
            "effect": [{"op": "gachinko", "times": 1, "as": "wins"},
                       {"op": "if",
                        "cond": {"cmp": [{"var": "wins"}, ">=", 1]},
                        "then": [
                            {"op": "may", "body": [
                                {"op": "move",
                                 "select": {"zone": "bz", "owner": "any",
                                            "count": 1,
                                            "filter": {"types": ["creature"]}},
                                 "to": "hand", "reason": "return"}]},
                            {"op": "may", "body": [
                                {"op": "move",
                                 "select": {"zone": "deck", "owner": "you",
                                            "from_bottom": 1},
                                 "to": "hand", "reason": "draw"}]}]}]}

TEXT_018 = ("{GS} G・ストライク（このカードを自分のシールドゾーンから手札に"
            "加える時、表向きにし、相手のクリーチャーを１体選んでもよい。"
            "このターン、そのクリーチャーは攻撃できない）\n"
            "スピードアタッカー\nW・ブレイカー\n"
            "このクリーチャーが攻撃する時、自分の山札の下から３枚を表向きに"
            "する。その中からコスト８以下のジョーカーズ・クリーチャーを"
            "１体、出してもよい。残りを好きな順序で山札の上に置く。")

TEXT_019 = ("このクリーチャーをバトルゾーンに出した時、バトルゾーンにある"
            "相手の進化ではないクリーチャーを１体選び、持ち主の山札の"
            "一番下に戻す。\n"
            "W・ブレイカー(このクリーチャーはシールドを２枚ブレイクする)\n"
            "このクリーチャーがバトルゾーンを離れた時、相手は自分自身の"
            "山札の一番下のカードを表向きにする。それが進化ではない"
            "クリーチャーであれば、相手はそれをバトルゾーンに出してもよい。")

TEXT_002 = ("進化ー自分のグレートメカオー１体の上に置く。\n"
            "このクリーチャーが攻撃する時、相手とガチンコ・ジャッジする。"
            "自分が勝ったら、バトルゾーンにあるクリーチャーを１体選び、"
            "持ち主の手札に戻してもよい。その後、自分の山札の一番下の"
            "カードを、手札に加えてもよい。(ガチンコ・ジャッジ：各プレイヤーは"
            "自身の山札の上から１枚目を見せ、それを一番下に置く。そのカードの"
            "コストが相手以上であれば、自分の勝ちとする)\n"
            "W・ブレイカー(このクリーチャーはシールドを２枚ブレイクする)")

TEXT_N006 = ("W・ブレイカー（このクリーチャーはシールドを２つブレイクする）\n"
             "このクリーチャーが出た時、自分の山札の下から１枚を墓地に置く。"
             "それがコスト６以下のジョーカーズ・クリーチャーなら出す。")

TEXT_TR007 = ("相手のターン中に自分がゲームに負ける時、自分のマナゾーンに"
              "闇と火文明があれば、かわりに自分の手札にあるこのカードを"
              "表向きにし、山札の下に置いてもよい。\n"
              "スピードアタッカー\nW・ブレイカー\n"
              "鬼エンド：このクリーチャーが出た時、シールドが１つもない"
              "プレイヤーがいれば、自分の山札の下から１枚を墓地に置く。"
              "それがコスト５以下のクリーチャーなら、出してもよい。")


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
    for cid in CANON:
        assert cid not in rej, cid
        _converted(cid)
    # alias 刷りの reject 行も残らない（019hc / rp05-007 は reopen で除去、
    # c001 は登録後に stale alias 行として直接除去）
    for als in ALIASES.values():
        for a in als:
            assert a not in rej, a
            assert _conv_cache.find(CONVERTED, a) is None, a
    # ファミリー解消: 3つのギャップ名を含む行は rejects に残らない
    assert not [r["id"] for r in rej.values()
                if set(r.get("gaps") or []) & {"deck_bottom_card",
                                               "deck_bottom_reveal",
                                               "deck_bottom_mill"}]
    for cid, als in ALIASES.items():
        assert (_converted(cid).get("source") or {}).get("aliases") == als, cid

    c = _converted("dm26rp3-018")
    assert c["keywords"] == ["g_strike", "speed_attacker", "double_breaker"]
    assert c["abilities"] == [FORM_C]
    assert c["text"] == TEXT_018
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.abilities[-1] == FORM_C

    c = _converted("dm32-019")
    assert c["keywords"] == ["double_breaker"]
    assert c["abilities"] == [CIP_BOTTOM_RETURN, FORM_D]
    assert c["text"] == TEXT_019
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.abilities[0]["kind"] == "static" \
        and d.abilities[0].get("keyword") == "double_breaker"
    assert d.abilities[1:] == [CIP_BOTTOM_RETURN, FORM_D]

    c = _converted("dmr06-002")
    assert c["keywords"] == ["double_breaker"]
    assert c["abilities"] == [FORM_002]
    assert c["text"] == TEXT_002
    assert c["types"] == ["creature", "evolution"]
    assert c["evolve_from"] == {"races": ["グレートメカオー"]}
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    trig = next(a for a in d.abilities if a["kind"] == "trigger")
    assert trig["effect"][1]["then"][-1]["body"][0]["select"]["from_bottom"] == 1

    c = _converted("dm26sd1-n006")
    assert c["mana"] == 1
    assert c["text"] == TEXT_N006
    assert "unsupported" not in (c.get("source") or {})
    f0, f1 = c["faces"]
    assert f0["name"] == "カツラデランス"
    assert f0["keywords"] == ["double_breaker"]
    assert f0["abilities"] == [FORM_B_JOKERS_MAND]
    assert f1["name"] == "「アフロ行きま～す!!」"
    assert f1["spell"] == [{"op": "discard",
                            "select": {"zone": "hand", "owner": "you",
                                       "count": 1}},
                           {"op": "draw", "count": 2}]
    d = parse_card(c, TABLES)
    assert d.faces[0].abilities[0].get("keyword") == "double_breaker"
    assert d.faces[0].abilities[1:] == [FORM_B_JOKERS_MAND]

    c = _converted("dm26rp3-tr007")
    assert c["name"] == "一王二命三眼槍"
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    assert c["abilities"] == [FORM_E_REPLACE, FORM_B]
    assert c["text"] == TEXT_TR007
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert [a for a in d.abilities if a["kind"] == "replace"] == [FORM_E_REPLACE]
    assert [a for a in d.abilities if a["kind"] == "trigger"] == [FORM_B]


# ---------- 実挙動の共通部品（第287弾プロトと同じ型） ----------

def _deck(e, player=0):
    return list(e.s.zones["deck"][player])


def _defn(e, cid):
    return e.cdef(cid).id


def _zone_of(e, cid):
    return e.s.cards[cid].zone


def _drive(e, on_decision, limit=900):
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


def _stop_at(kind, player=None):
    def on_dec(e, d):
        if d["kind"] == kind and (player is None or d.get("player") == player):
            return "stop"
        return None
    return on_dec


def _play_and_pay(play_key, player=0, on_play=None):
    played = []

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == player \
                and play_key in keys:
            played.append(True)
            if on_play:
                on_play(e)
            e.answer([keys.index(play_key)])
            return "ok"
        if played and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        return None

    return handler, played


def _answer_yes(d, yes=True):
    keys = [o["key"] for o in d["options"]]
    if yes:
        return [keys.index("yes")] if "yes" in keys else [0]
    return [keys.index("no")] if "no" in keys else [1]


# ---------- dm26rp3-018: 形C ----------

def test_018_form_c_plays_jokers_and_rest_on_top(rules):
    e = setup_exact(rules, {"bz": ["dm26rp3-018"],
                            "deck": ["T828", "T003", "T827"]},
                    {"deck": ["T827"] * 3})
    seen = []
    attacked = []

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and not attacked:
            if "attack:dm26rp3-018:player" in keys:
                attacked.append(True)
                e.answer([keys.index("attack:dm26rp3-018:player")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            return "ok"
        if attacked and d["kind"] in ("choose_cards", "order_cards"):
            seen.append((d["kind"], d))
            return "stop"
        return None

    _drive(e, on_dec)
    assert seen, "trigger decision did not appear"
    kind, d = seen[0]
    assert kind == "choose_cards"
    # 出せるのは ジョーカーズ・コスト8以下だけ = T828 のみ
    assert [_defn(e, o["cid"]) for o in d["options"]] == ["T828"]
    e.answer([0])
    seen2 = []

    def on_dec2(e, d):
        if d["kind"] == "order_cards":
            seen2.append(d)
            return "stop"
        return None

    _drive(e, on_dec2)
    assert seen2, "order_cards decision expected"
    od = seen2[0]
    odefs = [_defn(e, o["cid"]) for o in od["options"]]
    assert sorted(odefs) == ["T003", "T827"]
    e.answer([1, 0])     # 提示順と逆に置く
    _drive(e, _stop_at("charge"))
    deck_defns = [_defn(e, c) for c in _deck(e, 0)]
    assert deck_defns == [odefs[1], odefs[0]]
    assert any(e.s.cards[c].defn == "T828" and e.s.cards[c].controller == 0
               for c in e.zlist("bz", 0))


# ---------- dm32-019: 出た時 + 形D ----------

def test_019_cip_returns_to_bottom(rules):
    e = setup(rules, {"hand": ["dm32-019"], "mana": ["T010"] * 7},
              {"bz": ["T001"]}, filler="T002")
    handler, played = _play_and_pay("play:dm32-019")

    def on_dec(e, d):
        r = handler(e, d)
        if r:
            return r
        if played and d["kind"] == "charge" and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, on_dec)
    assert played
    # 相手の T001 はバトルゾーンを離れ、相手の山札の一番下にいる
    assert not any(e.s.cards[c].defn == "T001" for c in e.zlist("bz", 1))
    bottom = _deck(e, 1)[-1]
    assert _defn(e, bottom) == "T001"


def test_019_form_d_opponent_plays_own_bottom(rules):
    e = setup_exact(rules, {"bz": ["dm32-019"], "deck": ["T827"] * 3},
                    {"hand": ["T056"], "mana": ["T082"] * 3,
                     "deck": ["T827"] * 3})
    cast = []
    hit = []
    snap = []
    handler, _ = _play_and_pay(
        "play:T056", player=1, on_play=lambda e: snap.append(_deck(e, 1)))

    def on_dec(e, d):
        r = handler(e, d)
        if r:
            cast.append(True)
            return r
        if cast and d["kind"] == "choose_cards":
            tgt = [o for o in d["options"] if o.get("cid") is not None
                   and e.cdef(o["cid"]).id == "dm32-019"]
            if tgt:
                e.answer([d["options"].index(tgt[0])])
                return "ok"
            if d.get("player") == 1:
                hit.append(d)
                e.answer([0])
                return "ok"
        if cast and d["kind"] == "charge" and d.get("player") == 0:
            return "stop"
        return None

    _drive(e, on_dec)
    assert hit, "opponent play decision expected"
    bottom = snap[0][-1]
    card = e.s.cards[bottom]
    assert card.zone == "bz" and card.controller == 1   # 相手の獣として出る
    assert _deck(e, 1) == snap[0][:-1]
    assert any(e.s.cards[c].defn == "dm32-019"
               for c in e.zlist("graveyard", 0))


# ---------- dm26sd1-n006: クリーチャー面（強制形）+ 呪文面 ----------

def test_n006_creature_face_plays_jokers_without_asking(rules):
    """原文は「なら出す」の強制形: yes_no の諮問は無く、底の
    ジョーカーズ（コスト6以下）はそのままバトルゾーンに出る。"""
    e = setup_exact(rules, {"hand": ["dm26sd1-n006"], "mana": ["T034"] * 7,
                            "deck": ["T828"] * 3},
                    {"deck": ["T827"] * 3})
    kinds = []
    snap = []
    handler, played = _play_and_pay(
        "play:dm26sd1-n006:0", on_play=lambda e: snap.append(_deck(e, 0)))

    def on_dec(e, d):
        r = handler(e, d)
        if r:
            return r
        kinds.append(d["kind"])
        if played and d["kind"] == "charge":
            return "stop"
        return None

    _drive(e, on_dec)
    assert played
    assert "yes_no" not in kinds          # 強制形なので諮問されない
    bottom = snap[0][-1]
    card = e.s.cards[bottom]
    assert card.zone == "bz" and card.controller == 0
    assert _defn(e, bottom) == "T828"
    assert _deck(e, 0) == snap[0][:-1]


def test_n006_creature_face_non_jokers_stays_in_graveyard(rules):
    """ジョーカーズでなければ墓地に置かれるだけ（対照）。"""
    e = setup_exact(rules, {"hand": ["dm26sd1-n006"], "mana": ["T034"] * 7,
                            "deck": ["T827"] * 3},
                    {"deck": ["T827"] * 3})
    snap = []
    handler, played = _play_and_pay(
        "play:dm26sd1-n006:0", on_play=lambda e: snap.append(_deck(e, 0)))

    def on_dec(e, d):
        r = handler(e, d)
        if r:
            return r
        if played and d["kind"] == "charge":
            return "stop"
        return None

    _drive(e, on_dec)
    assert played
    bottom = snap[0][-1]
    assert _zone_of(e, bottom) == "graveyard"
    assert _deck(e, 0) == snap[0][:-1]


def test_n006_spell_face_discard_and_draw(rules):
    e = setup(rules, {"hand": ["dm26sd1-n006", "T001"],
                      "mana": ["T034", "T034"]},
              {"bz": ["T001"]}, filler="T002")
    handler, played = _play_and_pay("play:dm26sd1-n006:1")
    hand_before = []

    def on_dec(e, d):
        if not played:
            hand_before.append(len(e.zlist("hand", 0)))
        r = handler(e, d)
        if r:
            return r
        if played and d["kind"] == "choose_cards":
            # 捨てる1枚は T001 を選ぶ
            for i, o in enumerate(d["options"]):
                if o.get("cid") is not None and e.cdef(o["cid"]).id == "T001":
                    e.answer([i])
                    return "ok"
        if played and d["kind"] == "charge":
            return "stop"
        return None

    _drive(e, on_dec)
    assert played
    gy = [e.cdef(c).id for c in e.zlist("graveyard", 0)]
    assert "dm26sd1-n006" in gy and "T001" in gy
    # 手札: 唱えた1枚と捨てた1枚が減り、2枚引く（枚数は不変）。
    # 残っているのは引いた2枚（フィラー T002）だけ。
    hand = [e.cdef(c).id for c in e.zlist("hand", 0)]
    assert len(hand) == hand_before[0] and set(hand) == {"T002"}


# ---------- dm26rp3-tr007: 形B（鬼エンド）+ 形E（敗北置換） ----------

def _summon_and_watch(e, play_key, watch_kinds=("yes_no",)):
    seen = []
    snap = []
    handler, played = _play_and_pay(
        play_key, on_play=lambda e: snap.append(_deck(e, 0)))

    def on_dec(e, d):
        r = handler(e, d)
        if r:
            return r
        if d["kind"] in watch_kinds:
            seen.append((d["kind"], d))
            return "stop"
        if played and d["kind"] == "charge":
            return "stop"
        return None

    _drive(e, on_dec)
    return (seen[0] if seen else None), snap[0]


def test_tr007_oni_end_plays_bottom_creature(rules):
    e = setup_exact(rules, {"hand": ["dm26rp3-tr007"],
                            "mana": ["T008", "T034", "T001", "T001", "T001"],
                            "shield": [], "deck": ["T827"] * 3},
                    {"deck": ["T827"] * 3})
    hit, snap = _summon_and_watch(e, "play:dm26rp3-tr007")
    bottom = snap[-1]
    assert hit is not None and hit[0] == "yes_no"   # 「出してもよい」の諮問
    e.answer(_answer_yes(hit[1], yes=True))
    _drive(e, _stop_at("charge", player=1))
    card = e.s.cards[bottom]
    assert card.zone == "bz" and card.controller == 0
    assert _deck(e, 0) == snap[:-1]


def test_tr007_form_e_hand_lose_replacement(rules):
    e = setup(rules, {"hand": ["dm26rp3-tr007"], "mana": ["T008", "T034"],
                      "shield": []},
              {"bz": ["T034"], "mana": ["T001"] * 3}, filler="T002")
    target = next(c for c in e.zlist("hand", 0)
                  if e.cdef(c).id == "dm26rp3-tr007")
    seen = []
    attacked = []

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "lose_replace":
            seen.append(d)
            assert any(k.startswith("lose_replace:dm26rp3-tr007")
                       for k in keys)
            e.answer([next(i for i, k in enumerate(keys)
                           if k.startswith("lose_replace:dm26rp3-tr007"))])
            return "stop"
        if d["kind"] == "attack" and d.get("player") == 1 and not attacked:
            if "attack:T034:player" in keys:
                attacked.append(True)
                e.answer([keys.index("attack:T034:player")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            return "ok"
        return None

    _drive(e, on_dec)
    assert seen, "lose_replace decision expected"
    _drive(e, _stop_at("charge"))
    assert e.s.result is None                       # 敗北は置換された
    card = e.s.cards[target]
    assert card.zone == "deck"
    assert _deck(e, 0)[-1] == target                # 山札の一番下


# ---------- dmr06-002: ガチンコ勝利分岐の末尾節（形A） ----------

def test_002_win_branch_bottom_to_hand(rules):
    """進化召喚して攻撃し、ガチンコに勝つ（自分の山札は全てコスト6、
    相手は全てコスト2）。バウンスは辞退し、一番下を手札に加える。"""
    e = setup_exact(rules, {"bz": ["T685"], "hand": ["dmr06-002"],
                            "mana": ["T010"] * 5, "deck": ["T828"] * 6},
                    {"deck": ["T827"] * 6})
    state = {"attacked": False, "yes_no": 0, "deck_at_attack": None,
             "done": False}

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:dmr06-002" in keys:
            e.answer([keys.index("play:dmr06-002")])
            return "ok"
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state["attacked"] \
                and "attack:dmr06-002:player" in keys:
            state["attacked"] = True
            state["deck_at_attack"] = len(_deck(e, 0))
            e.answer([keys.index("attack:dmr06-002:player")])
            return "ok"
        if state["attacked"] and d["kind"] == "yes_no":
            state["yes_no"] += 1
            # 1つ目はバウンス（辞退）、2つ目は一番下を手札に（受ける）
            e.answer(_answer_yes(d, yes=state["yes_no"] >= 2))
            return "ok"
        if state["yes_no"] >= 2 and d["kind"] == "charge":
            state["done"] = True
            return "stop"
        return None

    _drive(e, on_dec, limit=2000)
    assert state["attacked"], "attack decision did not appear"
    assert state["yes_no"] >= 2, "win branch may decisions expected"
    # ガチンコは枚数を変えず、末尾節で山札が1枚減って手札に T828 が来る
    assert len(_deck(e, 0)) == state["deck_at_attack"] - 1
    assert any(e.cdef(c).id == "T828" for c in e.zlist("hand", 0))
