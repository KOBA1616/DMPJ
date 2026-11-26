"""語彙パイロット第373弾: deck_bottom_to_hand（ドリフト）。

対象は pure 1件: dmrp04s-011 ラジコンBOY の残る条項
「このクリーチャーがバトルゾーンに出た時、自分の山札の一番下の
カードを手札に加える」。山札の一番下を選ぶ手段は第287弾の
セレクタキー from_bottom で確立済みで、本条項はその形A
（登録先例 dmr06-002 の末尾節、proto T822）そのもの:
CIP 誘発 {event: move, to: bz, subject: self} →
move {select: {zone: deck, owner: you, from_bottom: 1},
to: hand, reason: draw}。「手札に加える」は必須形で
（「てもよい」ではない）、from_bottom は count を書かなければ
候補をそのまま返し決定を出さない（第287弾）ため、move は
諮問なしに一番下の1枚を手札へ移す。

partial の残りは組立て済み: スーパー・S・トリガーは
keywords [super_s_trigger]、xB 誘発は sst: true の印つきで
abilities に入っている。xB 誘発はカードの sst 印がある時
だけ発動する（core の照合）ため、通常召喚では CIP だけが
働くことを実挙動で判別する。

新規語彙・エンジン変更なし（ドリフト）。from_bottom は
Rust 側セレクタの許可キーに無いため、この選択を含む効果は
Python フォールバックになる（第287弾の記録どおり）。
"""
import pytest

from dmsim.cards.defs import load_rules, load_tables, parse_card
from dmsim.engine.scenario import build

TABLES = load_tables()

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [{"op": "move",
                   "select": {"zone": "deck", "owner": "you", "from_bottom": 1},
                   "to": "hand", "reason": "draw"}]}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    d = parse_card(_proto_card("T1121"), TABLES)
    trigs = [a for a in d.abilities if a["kind"] == "trigger"]
    assert trigs[0] == CIP                       # 条項順: CIP が先
    assert trigs[1].get("sst") is True           # xB 誘発は partial 既存
    assert "super_s_trigger" in d.keywords


def setup_exact(rules, p0, p1=None, filler="T002"):
    """山札の中身を spec の deck リストだけにする（deck_exact）。
    山札の並びは seed でシャッフルされるため、テストは実状態を読む。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": 1, "deck_size": 20,
                         "deck_exact": [True, True]})


def _deck(e, player=0):
    return list(e.s.zones["deck"][player])


def _zone_of(e, cid):
    return e.s.cards[cid].zone


def _drive(e, on_decision, limit=600):
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


def _summon_t1121(rules, p1=None):
    """T1121 を手札から召喚し、解決後の観測点（次の相手ターンの
    チャージ決定）まで進める。戻り値: (engine, 召喚時点の山札)。"""
    e = setup_exact(rules, {"hand": ["T1121"], "mana": ["T423"] * 6,
                            "deck": ["T827", "T003", "T828", "T827"]},
                    p1 if p1 is not None else {"deck": ["T827"] * 3})
    snap = []
    played = []

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and "play:T1121" in keys:
            played.append(True)
            snap.append(_deck(e, 0))       # 召喚時点（ドロー後）の山札
            e.answer([keys.index("play:T1121")])
            return "ok"
        if played and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        if played and d["kind"] == "charge":
            return "stop"                  # 解決済みの観測点
        return None

    _drive(e, on_dec)
    assert played, "T1121 was not played"
    return e, snap[0]


def test_cip_bottom_card_to_hand(rules):
    """出た時、自分の山札の一番下のカードが手札に加わり、
    残りの並びは変わらない（第287弾形Aと同形）。"""
    e, deck0 = _summon_t1121(rules)
    bottom, second = deck0[-1], deck0[-2]
    assert _zone_of(e, bottom) == "hand"          # 一番下が手札に来た
    assert _deck(e, 0) == deck0[:-1]              # 残りの並びは不変
    assert _deck(e, 0)[-1] == second


def test_xb_does_not_fire_on_normal_summon(rules):
    """通常召喚では sst 印が無いため xB 誘発は発動しない:
    相手のクリーチャー3体はすべてバトルゾーンに残る
    （xB が発動すれば手札・マナ・山札下へ1体ずつ移るはず）。"""
    e, deck0 = _summon_t1121(rules, {"bz": ["T827", "T827", "T827"],
                                     "deck": ["T827"] * 3})
    opp_bz = list(e.bz_tops(1))     # bz は共有ゾーンのため所有者で照合
    assert len(opp_bz) == 3
    assert all(_zone_of(e, c) == "bz" for c in opp_bz)
    # CIP 自体は働いている（一番下が自分の手札に来ている）
    assert _zone_of(e, deck0[-1]) == "hand"
