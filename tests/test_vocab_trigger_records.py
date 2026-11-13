"""第3段その2b: 合成レコードの誘発時機（バンドB U7）。

- chosen_trigger（相手に選ばれた時）は既存の choose レコードで発火することを確認（精査で既存可）
- use_s_trigger レコード（S・トリガーとして宣言・使用された時。S・バック経由は対象外）を新設
- battle_end レコード（バトルの後。攻撃フローと force_battle の両方）を新設。
  battle_lose レコードの生成形は統一メモ §4-1 で未確定のため、本弾では実装しない
- 式の {ref: "event.<key>"}（event.opponent 等）で誘発イベントの相手を参照できる

proto: T267 選ばれ誘発試験獣 / T268 ST使用観測試験獣 / T269 バトル後自壊試験獣 /
T270 強制バトル試験呪文。既存 proto: T207 / T256 除去試験呪文。
なお choose レコードは「選んだプレイヤーが対象のコントローラの相手」の時だけ作られる
（selectors.select の picked_opp 条件）。「相手は自身のクリーチャーを選ぶ」形（chooser: opp で
被害側が選ぶ）では作られない — 実在の「相手がこのクリーチャーを選んだ時」の文面と一致する。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _cid(e, p, defn, zone):
    return next(c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn)


def _names(e, p, zone):
    return sorted(e.s.cards[c].defn for c in e.zlist(zone, p))


def _boring(d):
    if d["kind"] in ("charge", "main", "attack"):
        keys = [o["key"] for o in d["options"]]
        for want in ("pass", "end_turn", "end_attack", "end_phase"):
            if want in keys:
                return [keys.index(want)]
        return [0]
    return [0]


def _drive(e, handler=None, until=None, kinds=None, limit=900):
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


def _play(e, d, key_prefix):
    e.answer([next(i for i, o in enumerate(d["options"]) if o["key"].startswith(key_prefix))])


def _shield_idx(e, d, cid):
    for i, o in enumerate(d["options"]):
        if o.get("cid") == cid:
            return i
    return e.zlist("shield", e.s.cards[cid].owner).index(cid)


def test_proto_parse(rules):
    for cid in ("T267", "T268", "T269", "T270"):
        parse_card(_proto_card(cid), TABLES)


def test_chosen_trigger_fires(rules):
    """U7: 相手の効果で選ばれた時、その時点で choose レコードから誘発が拾える（既存可の確認）。
    手札の内訳: _drive は次の自ターン開始ドローの後に止まるため、誘発ドロー1+開始ドロー1=2、
    誘発が無ければ開始ドローだけの1になる。"""
    e = setup(rules, {"bz": ["T267", "T004"]}, {"hand": ["T256"], "mana": ["T266"] * 3})
    d = _to_main(e, 1)
    _play(e, d, "play:T256")

    def h(dd):
        if dd["kind"] == "choose_cards":
            return [next(i for i, o in enumerate(dd["options"]) if ":T267:" in o["key"])]
        return None
    _drive(e, h, until=lambda: "T267" in _names(e, 0, "graveyard"))
    assert len(e.zlist("hand", 0)) == 2             # 選ばれた誘発で1枚引いた

    # 対照: 別のクリーチャーを選んだら発火しない
    e = setup(rules, {"bz": ["T267", "T004"]}, {"hand": ["T256"], "mana": ["T266"] * 3})
    d = _to_main(e, 1)
    _play(e, d, "play:T256")

    def h2(dd):
        if dd["kind"] == "choose_cards":
            return [next(i for i, o in enumerate(dd["options"]) if ":T004:" in o["key"])]
        return None
    _drive(e, h2, until=lambda: "T004" in _names(e, 0, "graveyard"))
    assert len(e.zlist("hand", 0)) == 1             # 開始ドローだけ（判別）
    assert "T267" in _names(e, 0, "bz")


def test_use_s_trigger_record(rules):
    """U7: 相手が S・トリガーを使った時、use_s_trigger レコードで誘発が拾える。"""
    e = setup(rules, {"shield": ["T207", "T001", "T001", "T001", "T001"]},
              {"bz": ["T001", "T268"]})
    t207 = _cid(e, 0, "T207", "shield")

    def h(d):
        if d["kind"] == "attack" and d["player"] == 1:
            ks = [o["key"] for o in d["options"]]
            return [ks.index("attack:T001:player")] if "attack:T001:player" in ks else None
        if d["kind"] == "choose_shields":
            return [_shield_idx(e, d, t207)]
        if d["kind"] == "declare_strigger":
            return [i for i, o in enumerate(d["options"]) if o["key"] == "strigger:T207"]
        return None
    _drive(e, h, until=lambda: any(e.s.cards[c].defn == "T207" for c in e.zlist("bz", 0)))
    # P1 の手札: ターン開始ドロー1 + 観測の誘発ドロー1 = 2
    assert len(e.zlist("hand", 1)) == 2

    # 対照: S・トリガーを宣言しなければレコードは出ず、誘発もしない
    e = setup(rules, {"shield": ["T207", "T001", "T001", "T001", "T001"]},
              {"bz": ["T001", "T268"]})
    t207 = _cid(e, 0, "T207", "shield")

    def h2(d):
        if d["kind"] == "declare_strigger":
            return []
        return h(d)
    _drive(e, h2, until=lambda: e.s.cards[t207].zone == "hand")
    assert len(e.zlist("hand", 1)) == 1             # ターン開始ドローのみ


def test_battle_end_after_battle(rules):
    """U7: バトルの後に battle_end レコードが双方へ出て、勝った側の自壊誘発も拾える。"""
    e = setup(rules, {"bz": ["T269"]}, {"bz": ["T277"]})
    # P0 の T269 がプレイヤー攻撃（バトルではない）→ battle_end は出ず生き残る
    for _ in range(600):
        d = e.advance()
        assert d is not None
        if d["kind"] == "attack" and d["player"] == 0:
            e.answer([next(i for i, o in enumerate(d["options"]) if o["key"] == "attack:T269:player")])
            break
        e.answer(_boring(d))
    _drive(e, until=lambda: e.s.turn == 2)
    assert "T269" in _names(e, 0, "bz")

    # P1 の T277（パワー1000）がタップ中の T269（4000）に攻撃 → バトルで T277 が負け、
    # battle_end で T269 の自壊誘発が発火する
    def h(d):
        if d["kind"] == "attack" and d["player"] == 1:
            ks = [o["key"] for o in d["options"]]
            atk = [i for i, o in enumerate(d["options"]) if o["key"].startswith("attack:") and "T269" in o["key"]]
            return atk[:1] or None
        return None
    _drive(e, h, until=lambda: "T269" in _names(e, 0, "graveyard"))
    assert "T277" in _names(e, 1, "graveyard")      # バトルで負けた側
    assert "T269" in _names(e, 0, "graveyard")      # バトル後の自壊誘発で落ちた


def test_battle_end_via_force_battle(rules):
    """U7: force_battle でも battle_end レコードが出る。"""
    e = setup(rules, {"bz": ["T269"], "hand": ["T270"], "mana": ["T277", "T277"]},
              {"bz": ["T277"]})
    d = _to_main(e, 0)
    _play(e, d, "play:T270")
    _drive(e, until=lambda: "T269" in _names(e, 0, "graveyard"))
    assert "T277" in _names(e, 1, "graveyard")
    assert "T269" in _names(e, 0, "graveyard")


def test_event_ref_in_expr(rules):
    """U7: 式の {ref: "event.<key>"} で誘発イベントの相手などを参照できる。"""
    e = setup(rules, {"bz": ["T004"]}, {})
    cid = _cid(e, 0, "T004", "bz")
    env = {"you": 0, "event": {"opponent": e.s.ref(cid)}, "vars": {}}
    assert e.eval_expr({"power_of": {"ref": "event.opponent"}}, env) == 3000
    assert e.eval_expr({"power_of": {"ref": "event.missing"}}, env) == 0
