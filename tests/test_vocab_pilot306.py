"""語彙パイロット第306弾: same_name_sweep（同名一掃）。

対象は dm17-004 エクスプロード・カタストロフィー 1件のみ
（第2ギャップ evolution_cross_gear は第304弾で実装済み）。
残る条項は「これをクロスしたクリーチャーがバトルに勝った時、
相手の手札を見る。相手は自分自身の手札、マナゾーン、墓地、
バトルゾーンから、このバトルで負けたクリーチャーと同じ名前の
自分自身のカードをすべて山札の一番下に置く」。

結論: **新規語彙なしのドリフト**。部品はすべて既存で足りる:
- 誘発点: battle_win 記録は {subject: 勝者, opponent: 敗者} を
  持ち（combat.py _battle）、subject: crossed の照合は
  cross_gear_effect のイディオム（第223弾〜）でギア側誘発に使える。
- 敗者の名前: フィルタ {name: {name_of: event.opponent}}。
  name_of の event.<キー> 解決は基盤 expr-event-ref で
  event.opponent が明示対応（selectors._expr_refs）。名前フィルタ
  自体は第140弾・第282弾の確立形。
- 手札を見る: choose {zone: hand, owner: opp, count: all} で
  束縛だけする look 形（converted dm36-083 ミルルンの先例）。
- 一掃: move {select: {zone: [hand, mana, graveyard, bz],
  owner: opp, filter: {name: ...}, count: all}, to: deck,
  position: bottom}。複数ゾーン選択と count: all は確立形
  （全戻し bounce 等）。敗者自身も墓地から一緒に下へ行く
  （本文は墓地も対象に含む）。

proto: T939（dm17-004 型）/ T940（闇ギア＝進化元）/
T941（火獣＝宿主）/ T942（同名獣＝敗者役とそのコピー）/
T943（別名獣＝対照）/ T944（強獣＝負けケース用）。
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402
from tests.conftest import setup  # noqa: E402

TABLES = load_tables()
IDS = ("T939", "T940", "T941", "T942", "T943", "T944")
MANA = ["T008", "T034", "T001"]          # T939（コスト3・闇/火）の支払い
OPP_DECK = {"deck": ["T002"] * 6}


def _rules():
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _cid(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == p)


def _sources(e, defn, p=0):
    cid = _cid(e, "hand", p, defn)
    return e._evo_sources(cid, p, None)


def _answer_default(e, d):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] in ("pay_mana", "choose_evo_source", "choose_cards"):
        e.answer(list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _run(e, attack_key=None, done=None, max_steps=600):
    """T939 を進化で出し T941 にクロスし、attack_key で攻撃する駆動。

    done(e) が真になったら止める。attack_key が None の時は攻撃しない。
    """
    state = {"attacked": False}
    for _ in range(max_steps):
        if done and done(e):
            return state
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "main" and any(k.startswith("play:T939") for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if k.startswith("play:T939"))])
            continue
        if kind == "main" and "cross:T939:T941" in keys:
            e.answer([keys.index("cross:T939:T941")])
            continue
        if kind == "attack" and attack_key and not state["attacked"]:
            if attack_key in keys:
                state["attacked"] = True
                e.answer([keys.index(attack_key)])
                continue
        if kind in ("block", "declare_block") and "no_block" in keys:
            e.answer([keys.index("no_block")])
            continue
        _answer_default(e, d)
    raise AssertionError("driver did not reach the done condition")


def _opp_full():
    return {"bz": ["T942", "T943"], "hand": ["T942", "T943"],
            "mana": ["T942", "T943"], "graveyard": ["T942"],
            "deck": ["T002"] * 6}


# ---- parse / 進化元プール ----

def test_proto_parse():
    for cid in IDS:
        parse_card(proto_card(cid), TABLES)
    d = parse_card(proto_card("T939"), TABLES)
    assert d.types == ["cross_gear", "evolution"]
    assert d.evolve_from == {"civs": ["darkness", "fire"]}


def test_pool_requires_matching_cross_gear():
    # クリーチャーはギアの進化元にならない（文明が合っていても）
    e = setup(_rules(), {"bz": ["T941"], "hand": ["T939"], "mana": MANA},
              OPP_DECK)
    assert _sources(e, "T939") == []
    # 文明の合わないギアは進化元にならない
    e = setup(_rules(), {"bz": ["T928"], "hand": ["T939"], "mana": MANA},
              OPP_DECK)
    assert _sources(e, "T939") == []
    # 相手のギアは進化元にならない
    e = setup(_rules(), {"hand": ["T939"], "mana": MANA},
              {"bz": ["T940"], "deck": ["T002"] * 4})
    assert _sources(e, "T939") == []
    # 闇ギアがあれば出せる
    e = setup(_rules(), {"bz": ["T940"], "hand": ["T939"], "mana": MANA},
              OPP_DECK)
    assert _sources(e, "T939") == [_cid(e, "bz", 0, "T940")]


# ---- 実挙動: バトルに勝つと同名をすべて山札の下へ ----

def test_sweep_on_battle_win():
    e = setup(_rules(), {"bz": ["T940", "T941"], "hand": ["T939"],
                         "mana": MANA, "deck": ["T002"] * 6},
              _opp_full())
    host = _cid(e, "bz", 0, "T941")
    gear = _cid(e, "hand", 0, "T939")
    st = _run(e, attack_key="attack:T941:T942",
              done=lambda e: _defns(e, "deck", 1).count("T942") == 4)
    # タップされていないクリーチャーを攻撃できた（ギアの常在型）
    assert st["attacked"]
    assert e.s.cards[gear].crossed[0] == host
    # 相手の同名カードは4ゾーンからすべて消えた
    for zone in ("hand", "mana", "graveyard", "bz"):
        assert "T942" not in _defns(e, zone, 1), zone
    # 別名カードは残る
    assert "T943" in _defns(e, "bz", 1)
    assert "T943" in _defns(e, "hand", 1)
    assert "T943" in _defns(e, "mana", 1)
    # 行き先は相手の山札の一番下（山札リストは上が先頭なので末尾4枚）。
    # 内訳: 手札1・マナ1・墓地1（元から）＋敗者自身（墓地経由）= 4枚
    deck = _defns(e, "deck", 1)
    assert deck.count("T942") == 4
    assert deck[-4:] == ["T942"] * 4
    # 勝った宿主は場に残る
    assert "T941" in _defns(e, "bz", 0)


def test_no_sweep_on_battle_lose():
    opp = _opp_full()
    opp["bz"] = ["T944", "T943"]
    e = setup(_rules(), {"bz": ["T940", "T941"], "hand": ["T939"],
                         "mana": MANA, "deck": ["T002"] * 6}, opp)
    st = _run(e, attack_key="attack:T941:T944",
              done=lambda e: "T941" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    # 宿主が負けたので一掃は起きない（相手の同名は各ゾーンに残る）
    assert "T942" in _defns(e, "hand", 1)
    assert "T942" in _defns(e, "mana", 1)
    assert "T942" in _defns(e, "graveyard", 1)
    assert "T942" not in _defns(e, "deck", 1)


def test_no_sweep_on_player_attack():
    opp = {"bz": ["T943"], "hand": ["T942"], "mana": ["T942"],
           "graveyard": ["T942"], "deck": ["T002"] * 6}
    e = setup(_rules(), {"bz": ["T940", "T941"], "hand": ["T939"],
                         "mana": MANA, "deck": ["T002"] * 6}, opp)
    before = len(e.zlist("shield", 1))
    st = _run(e, attack_key="attack:T941:player",
              done=lambda e: len(e.zlist("shield", 1)) == before - 1)
    assert st["attacked"]
    # プレイヤー攻撃はバトルではないので一掃は起きない
    assert "T942" in _defns(e, "hand", 1)
    assert "T942" in _defns(e, "mana", 1)
    assert "T942" in _defns(e, "graveyard", 1)
    assert "T942" not in _defns(e, "deck", 1)
