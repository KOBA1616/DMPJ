"""語彙パイロット第276弾: grant_duration（ターン境界を越える付与期間）。

rejects の grant_duration 純粋4件はいずれも「期間つき付与」の形で、不足していたのは
duration の語彙だけだった:
- dmex18-s11 地龍神バラフィオル: 破壊された時、次の自分のターンの終わりまで、
  自分のクリーチャーすべてに「ワールド・ブレイカー」を与える。
- dmr05-078 ビックリ・ガード: 次の自分のターンのはじめまで、自分のクリーチャー
  すべては「ブロッカー」を得る（既存の until_next_own_turn_start で足りる。本弾で検証）。
- dmr22-006 ジャッジメント・タイム: 次の相手のターンの終わりまで、相手の
  クリーチャーは攻撃もブロックもできず、アンタップしない。
- dmrp19-032 †正義†と「正義」: 次の相手のターン中、自分のクリーチャーは離れない
  （自分のターン中は効かない。開始時点の指定が要るため、下記のイディオムで表す）。

新語彙（duration 2値）:
- until_next_own_turn_end（次の自分のターンの終わりまで）
- until_next_opp_turn_end（次の相手のターンの終わりまで）
いずれも生成時に core._duration が until_turn_end:{player}:{生成ターン} へ解決し、
turn.st_end（とターンの残りをとばす経路）が、そのプレイヤーの生成より後のターンの
終了時に _expire_turn_end で落とす。生成がそのプレイヤーのターン中なら次のその
プレイヤーのターン、相手のターン中なら直後のそのプレイヤーのターンが期限になる
（追加ターンもそのプレイヤーのターンとして数える）。

イディオム（dmrp19-032 形）: 「次の相手のターン中のみ」は、呪文の解決時に
delayed_trigger {when: {event: turn_start, player: opp}, duration: permanent} を
登録し、相手のターン開始時に modify {mod: {no_leave: true}, duration: end_of_turn}
を発火させる。自分のターン中は継続的効果が存在しないので、S・トリガー等で
除去されうるという原文の挙動と一致する。

dmr22-006 の「アンタップしない」は deny の untap_at_start（既存。常在型での
使用例が converted にある）。「攻撃もブロックもできない」は deny
[attack_player, attack_creature, block] の既存形。

Rust: modify の duration が end_of_turn でない形は _simple_effect の単純形に
含まれないため Python フォールバック。新しい GameState フィールドは無い
（state.rs の変更なし）。スキーマは duration enum の追加で再生成した。
"""
from tests.conftest import setup
from tests._conv_cache import proto_card

from dmsim.cards.defs import DefError, load_tables, parse_card
from dmsim.engine.rustcore import _simple_effect

TABLES = load_tables()


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


class _Driver:
    """汎用ドライバ（第275弾のものに攻撃フックとブロック指定を追加）。

    play: main 決定で (e, d) -> 答えのリストか None を返すフック。
    choose_defn: choose_cards ではその defn のカードを選ぶ。
    attacks: {(turn, player): 攻撃キー}。その攻撃決定で一度だけそのキーを選ぶ。
    attack_log: (turn, player, keys) を全攻撃決定について記録する。
    block_defn: block 決定でその defn のブロッカーを選ぶ。
    """

    def __init__(self, play=None, choose_defn=None, attacks=None, block_defn=None):
        self.play = play
        self.choose_defn = choose_defn
        self.attacks = dict(attacks or {})
        self.block_defn = block_defn
        self.attack_log = []

    def run(self, e, stop, limit=1200):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
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
                key = self.attacks.get((e.s.turn, d["player"]))
                if key is not None and key in keys:
                    del self.attacks[(e.s.turn, d["player"])]
                    e.answer([keys.index(key)])
                    if stop(e):
                        return
                    continue
            if kind == "block" and self.block_defn is not None:
                hit = [i for i, o in enumerate(d["options"])
                       if o["key"].startswith(f"bz:{self.block_defn}")]
                if hit:
                    e.answer(hit[:1])
                    if stop(e):
                        return
                    continue
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


def _keywords(e, cid):
    return e.chars_ro(cid)["keywords"]


def test_pilot276_protos_parse():
    for tid in ("T780", "T781", "T782", "T783", "T784"):
        parse_card(proto_card(tid), TABLES)


def test_pilot276_duration_validation():
    base = {"id": "X276", "name": "検証用", "types": ["spell"], "civs": ["light"],
            "cost": 1,
            "spell": [{"op": "modify",
                       "select": {"zone": "bz", "owner": "you",
                                  "filter": {"types": ["creature"]}, "count": "all"},
                       "mod": {"grant": ["blocker"]},
                       "duration": "until_next_own_turn_end"}]}
    parse_card(base, TABLES)
    base2 = dict(base)
    base2["spell"] = [dict(base["spell"][0], duration="until_next_opp_turn_end")]
    parse_card(base2, TABLES)
    bad = dict(base)
    bad["spell"] = [dict(base["spell"][0], duration="next_turn")]
    try:
        parse_card(bad, TABLES)
        raise AssertionError("未知の duration が通ってしまった")
    except DefError:
        pass


def test_pilot276_not_rust_simple():
    assert not _simple_effect(proto_card("T780")["spell"])
    assert not _simple_effect(proto_card("T781")["spell"])


def test_next_own_turn_end_window(rules):
    """T780: 次の自分のターンの終わりまでブロッカー付与。
    自分のターン（1）→相手ターン（2）→次の自分のターン（3）まで有効で、
    ターン3の終了で切れる（ターン4では消えている）。"""
    e = setup(rules, {"hand": ["T780"], "mana": ["T030"], "bz": ["T001"]},
              {"bz": ["T001"]})
    t001 = _cid(e, "bz", 0, "T001")
    drv = _Driver(play=_play_once("play:T780"))
    drv.run(e, lambda ev: any(c["duration"].startswith("until_turn_end:")
                              for c in ev.s.continuous) and _quiet(ev))
    ce = next(c for c in e.s.continuous if c["duration"].startswith("until_turn_end:"))
    assert ce["duration"] == "until_turn_end:0:1"      # 自分・生成ターン1に解決
    assert "blocker" in _keywords(e, t001)             # ターン1（自分のターン）
    drv.run(e, lambda ev: ev.s.turn == 2 and _quiet(ev))
    assert "blocker" in _keywords(e, t001)             # ターン2（相手のターン）
    drv.run(e, lambda ev: ev.s.turn == 3 and _quiet(ev))
    assert "blocker" in _keywords(e, t001)             # ターン3（次の自分のターン）
    drv.run(e, lambda ev: ev.s.turn == 4 and _quiet(ev))
    assert "blocker" not in _keywords(e, t001)         # ターン3終了で失効
    assert not any(c["duration"].startswith("until_turn_end:") for c in e.s.continuous)


def test_next_own_turn_end_destroy_trigger(rules):
    """T784（dmex18-s11 形）: 相手のターンに破壊されても、付与は次の自分の
    ターン（3）の終わりまで続く。生成ターンが相手のターンでも期限がずれない。"""
    e = setup(rules, {"bz": ["T784", "T001"]},
              {"hand": ["T006"], "mana": ["T034", "T034", "T034"]})
    t001 = _cid(e, "bz", 0, "T001")
    drv = _Driver(play=_play_once("play:T006"), choose_defn="T784")
    drv.run(e, lambda ev: "T784" in _defns(ev, "graveyard", 0) and _quiet(ev))
    # 破壊は相手のターン（2）。観測は後始末が進んだ後になるため、生成ターンは
    # 解決済み duration の生成ターン欄で証明する（第271弾の教訓）
    ce = next(c for c in e.s.continuous if c["duration"].startswith("until_turn_end:"))
    assert ce["duration"] == "until_turn_end:0:2"      # 自分・生成ターン2に解決
    assert "double_breaker" in _keywords(e, t001)
    drv.run(e, lambda ev: ev.s.turn >= 3 and _quiet(ev))
    assert "double_breaker" in _keywords(e, t001)      # 次の自分のターンいっぱい
    drv.run(e, lambda ev: ev.s.turn >= 4 and _quiet(ev))
    assert "double_breaker" not in _keywords(e, t001)  # ターン3終了で失効


def test_next_opp_turn_end_lock(rules):
    """T781（dmr22-006 形）: 次の相手のターンの終わりまでロック。
    ターン3に唱えると、ターン4（相手）の開始時にアンタップせず、攻撃もできず、
    ターン4の終了で切れてターン6の開始時にはアンタップする。"""
    e = setup(rules, {"hand": ["T781"], "mana": ["T030", "T030", "T030"],
                      "bz": ["T001"]},
              {"bz": ["T004", "T001"]})
    t004 = _cid(e, "bz", 1, "T004")

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if e.s.turn == 3 and "play:T781" in keys:
            return [keys.index("play:T781")]
        return None

    drv = _Driver(play=play, block_defn="T004",
                  attacks={(1, 0): "attack:T001:player",
                           (2, 1): "attack:T004:player"})
    # ターン1: T001 が攻撃し T004 がブロック（T004 はタップして残る）
    # ターン2: T004 はアンタップして攻撃（タップ）。ターン3: T781 を唱える
    drv.run(e, lambda ev: any(c["duration"].startswith("until_turn_end:")
                              for c in ev.s.continuous) and _quiet(ev))
    ce = next(c for c in e.s.continuous if c["duration"].startswith("until_turn_end:"))
    assert ce["duration"] == "until_turn_end:1:3"      # 相手・生成ターン3に解決
    assert e.s.cards[t004].tapped                      # ターン2の攻撃でタップしたまま
    # ターン4（相手）: アンタップせず、攻撃決定にも T001 の攻撃が出ない。
    # ターン4の決定はチャージだけで、消費すると次の決定はターン5になるため
    # 観測はターン5のはじめで行う（タップ状態は相手ターン開始まで変わらない）
    drv.run(e, lambda ev: ev.s.turn >= 5 and _quiet(ev))
    assert e.s.cards[t004].tapped                      # ターン4開始時にアンタップしなかった
    assert not any(t == 4 and p == 1 and any(k.startswith("attack:T001")
                                             for k in keys)
                   for t, p, keys in drv.attack_log)
    # ターン6（相手）: ターン4終了で失効したので、今度はアンタップして攻撃もできる
    drv.run(e, lambda ev: ev.s.turn >= 6 and _quiet(ev))
    assert not e.s.cards[t004].tapped
    drv.run(e, lambda ev: any(t == 6 and p == 1 for t, p, _ in drv.attack_log))
    keys6 = next(k for t, p, k in drv.attack_log if t == 6 and p == 1)
    assert "attack:T001:player" in keys6               # 攻撃も再び可能


def test_until_next_own_turn_start_expires(rules):
    """T782（dmr05-078 形）: 既存の until_next_own_turn_start は modify の付与でも
    「次の自分のターンのはじめまで」を表す。ターン2までは有効で、ターン3の
    開始時に切れる。"""
    e = setup(rules, {"hand": ["T782"], "mana": ["T030"], "bz": ["T001"]}, {})
    t001 = _cid(e, "bz", 0, "T001")
    drv = _Driver(play=_play_once("play:T782"))
    drv.run(e, lambda ev: any(c["duration"] == "until_turn_start:0"
                              for c in ev.s.continuous) and _quiet(ev))
    assert "blocker" in _keywords(e, t001)
    drv.run(e, lambda ev: ev.s.turn == 2 and _quiet(ev))
    assert "blocker" in _keywords(e, t001)             # 相手のターンいっぱい
    drv.run(e, lambda ev: ev.s.turn == 3 and _quiet(ev))
    assert "blocker" not in _keywords(e, t001)         # 自分のターンのはじめに失効


def test_opp_next_turn_only_window(rules):
    """T783（dmrp19-032 形イディオム）: 次の相手のターン中のみ離れない。
    自分のターン（1）では効かず、相手のターン（2）ではバトル破壊も防ぎ、
    効果の切れたターン4のバトルでは破壊される。"""
    e = setup(rules, {"hand": ["T783"], "mana": ["T030", "T030"], "bz": ["T001"]},
              {"bz": ["T779"]})
    t001 = _cid(e, "bz", 0, "T001")
    drv = _Driver(play=_play_once("play:T783"),
                  attacks={(1, 0): "attack:T001:player",
                           (2, 1): "attack:T779:T001",
                           (3, 0): "attack:T001:player",
                           (4, 1): "attack:T779:T001"})
    drv.run(e, lambda ev: any(d["when"].get("event") == "turn_start"
                              for d in ev.s.delayed) and _quiet(ev))
    assert e.s.turn == 1
    assert e.chars_ro(t001)["no_leave"] == []          # 自分のターン中は効かない
    # ターン2の攻撃決定に答えた時点（バトル解決前）で、窓が開いていることを見る
    drv.run(e, lambda ev: ev.s.turn == 2 and _quiet(ev)
            and ev.chars_ro(t001)["no_leave"] != [])
    assert e.chars_ro(t001)["no_leave"] != []          # 相手のターン中は有効
    # バトル後始末は決定を挟まずターン3へ進むため、生存の観測はターン3のはじめで
    drv.run(e, lambda ev: ev.s.turn >= 3 and _quiet(ev))
    assert "T001" in _defns(e, "bz", 0)                # バトルでは離れなかった
    assert "T001" not in _defns(e, "graveyard", 0)
    assert e.s.cards[_cid(e, "bz", 1, "T779")].tapped  # T779 は確かに攻撃した
    assert e.chars_ro(t001)["no_leave"] == []          # ターン2終了で窓は閉じた
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert any(t == 4 and p == 1 and "attack:T779:T001" in keys
               for t, p, keys in drv.attack_log)       # 失効後のターン4のバトルで破壊
