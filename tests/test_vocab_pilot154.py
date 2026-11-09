"""語彙パイロット第154弾: crystal_soul（水晶ソウル）。

- 面の宣言 `crystal_soul: N`: 「このカードを召喚／唱える時、自分のマナゾーンにある
  裏向きのカードのマナの数字はNになる」。キーワードではなく面の特性として書く。
- 読み口は chars の `crystal_soul`（面の宣言を種に、mod {crystal_soul: N} と max で集約）。
  付与は affects {zone: hand} の常在型＋mod（dm24bd6-001 の型。proto T200 で代表）。
- _mana_choices が裏向きグループの数値だけを水晶ソウル値に差し替える（早期判定の合計も同じ実効値）。
  裏向きマナは無色のまま（文明は得ない）。上書きは置換であって最大値ではない。
- 代替コスト・バズレンダの支払いにも _mana_choices 経由で一律に及ぶ（親判断。併せ持ち実カードなし）。
- proto T198（ソウル2・水・コスト7）／T199（ソウル3呪文・コスト6）／T200（付与）／
  T201（ゼニス・コスト9・宣言なし）／T202（マナ数3のバニラ。置換 vs 最大値の判別用）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import DefError, card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()

X_CARDS = """
cards:
  - id: X198
    name: 対照試験獣
    types: [creature]
    civs: [water]
    cost: 7
    power: 7000
    races: [テスト]
    text: ""
  - id: X199
    name: 小ソウル試験獣
    types: [creature]
    civs: []
    cost: 4
    power: 4000
    races: [テスト]
    crystal_soul: 2
    text: 水晶ソウル2
  - id: X200
    name: 小無ソウル試験獣
    types: [creature]
    civs: []
    cost: 4
    power: 4000
    races: [テスト]
    text: ""
  - id: X201
    name: 中ソウル試験獣
    types: [creature]
    civs: [water]
    cost: 6
    power: 6000
    races: [テスト]
    crystal_soul: 3
    text: 水晶ソウル3
"""


@pytest.fixture(scope="session")
def xr(tmp_path_factory):
    p = tmp_path_factory.mktemp("pilot154x") / "x_cards.yaml"
    p.write_text(X_CARDS, encoding="utf-8")
    return load_rules(card_yaml_files() + [p])


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _cid(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.cdef(c).id == defn)


def _flip(e, defn, n=None):
    """マナゾーンの defn を n 枚（省略時は全部）裏向きにする。"""
    hit = [c for c in e.zlist("mana", 0) if e.cdef(c).id == defn]
    for c in hit[:n]:
        e.s.cards[c].face_down = True
    return hit[:n]


def test_proto_parse(rules):
    for cid, want in (("T198", 2), ("T199", 3), ("T200", 0), ("T201", 0), ("T202", 0)):
        cd = parse_card(_proto_card(cid), TABLES)
        assert cd.crystal_soul == want, cid
    assert rules.cards["T202"].mana == 3


def test_declaration_validation(rules):
    base = {"id": "X900", "name": "検証用", "types": ["creature"], "civs": ["water"], "cost": 3, "power": 3000}
    for bad in (0, -1, "2", 2.5, True):
        with pytest.raises(DefError):
            parse_card({**base, "crystal_soul": bad}, TABLES)
    ok = parse_card({**base, "crystal_soul": 2}, TABLES)
    assert ok.crystal_soul == 2
    grant = {**base, "id": "X901", "abilities": [
        {"kind": "static", "affects": {"zone": "hand", "owner": "you", "filter": {"race_has": "ゼニス", "types": ["creature"]}},
         "mod": {"crystal_soul": 3}}]}
    parse_card(grant, TABLES)   # 付与の型（dm24bd6-001）は通る
    bad_mod = {**base, "id": "X902", "abilities": [
        {"kind": "static", "affects": {"zone": "hand", "owner": "you", "filter": {"types": ["creature"]}},
         "mod": {"crystal_soul": 0}}]}
    with pytest.raises(DefError):
        parse_card(bad_mod, TABLES)


def test_soul2_pays_with_face_down(rules, xr):
    """(1) T198（水・コスト7・ソウル2）は「表向きの水1枚＋裏向き3枚」で支払える（1＋2＋2＋2＝7）。

    表向きの数値まで上書きされる実装だと合計は偶数だけになり 7 に届かない（判別）。
    早期判定の合計も実効値で見る必要がある（印刷値の合計は 4 で足りない）。
    """
    e = setup(rules, {"hand": ["T198"], "mana": ["T003", "T001", "T001", "T001"]}, {})
    _flip(e, "T001")
    me = _cid(e, "hand", 0, "T198")
    assert e.chars(me)["crystal_soul"] == 2
    choices = e._mana_choices(me, 0)
    assert len(choices) == 1
    assert sorted(choices[0]) == sorted(e.zlist("mana", 0))   # 4枚すべてを使う組合せだけ
    # 対照: 宣言の無い同コスト・同文明のカードは同じマナ構成では支払えない
    e2 = setup(xr, {"hand": ["X198"], "mana": ["T003", "T001", "T001", "T001"]}, {})
    _flip(e2, "T001")
    assert e2._mana_choices(_cid(e2, "hand", 0, "X198"), 0) == []


def test_face_down_only_cannot_pay_t198(rules):
    """(2) 裏向きだけでは T198 を支払えない（裏向きマナは文明を得ない）。"""
    e = setup(rules, {"hand": ["T198"], "mana": ["T001", "T001", "T001", "T001"]}, {})
    _flip(e, "T001")
    assert e._mana_choices(_cid(e, "hand", 0, "T198"), 0) == []


def test_face_down_grants_no_civ(xr):
    """裏向きは文明を得ないことの判別: X201（水・コスト6・ソウル3）は裏向き2枚で
    数値上は 3＋3＝6 に届くが、水文明が無いので支払えない。
    表向きの水を1枚足した構成（3＋1＋1＋1＝6）なら支払える。"""
    e = setup(xr, {"hand": ["X201"], "mana": ["T001", "T001"]}, {})
    _flip(e, "T001")
    assert e._mana_choices(_cid(e, "hand", 0, "X201"), 0) == []
    e2 = setup(xr, {"hand": ["X201"], "mana": ["T003", "T001", "T001", "T001"]}, {})
    _flip(e2, "T001", 1)
    assert e2._mana_choices(_cid(e2, "hand", 0, "X201"), 0) != []


def test_replacement_not_max(xr):
    """(4) 上書きは置換（最大値ではない）: マナ数3の T202 を裏向きにすると、ソウル2では
    2として数える。コスト4は裏向き T202 ×2（2＋2）で支払える。最大値の実装だと
    3＋3＝6 になり 4 では支払えない（判別）。宣言なしでは印刷値 3 のまま（3, 6 しか作れない）。"""
    e = setup(xr, {"hand": ["X199"], "mana": ["T202", "T202"]}, {})
    _flip(e, "T202")
    choices = e._mana_choices(_cid(e, "hand", 0, "X199"), 0)
    assert len(choices) == 1 and len(choices[0]) == 2
    e2 = setup(xr, {"hand": ["X200"], "mana": ["T202", "T202"]}, {})
    _flip(e2, "T202")
    assert e2._mana_choices(_cid(e2, "hand", 0, "X200"), 0) == []
    # 表向きの T202 は上書きされない（3のまま。コスト4は作れない）
    e3 = setup(xr, {"hand": ["X199"], "mana": ["T202", "T202"]}, {})
    assert e3._mana_choices(_cid(e3, "hand", 0, "X199"), 0) == []


def test_spell_soul3(rules):
    """(5) 呪文 T199（コスト6・ソウル3）は裏向き2枚（各3）で唱える支払いができる。"""
    e = setup(rules, {"hand": ["T199"], "mana": ["T001", "T001"]}, {})
    _flip(e, "T001")
    assert e._mana_choices(_cid(e, "hand", 0, "T199"), 0) != []
    e2 = setup(rules, {"hand": ["T199"], "mana": ["T001"]}, {})
    _flip(e2, "T001")
    assert e2._mana_choices(_cid(e2, "hand", 0, "T199"), 0) == []


def test_grant_from_bz(rules):
    """(6) 付与: T200 が場にあれば手札の T201（コスト9・宣言なし）は chars で
    crystal_soul 3 を得て、裏向き3枚（各3）で召喚の支払いができる。
    T200 がいなければ同じマナ構成では支払えない。付与は手札にある間だけ（場の T201 には及ばない）。"""
    e = setup(rules, {"bz": ["T200"], "hand": ["T201"], "mana": ["T001", "T001", "T001"]}, {})
    _flip(e, "T001")
    me = _cid(e, "hand", 0, "T201")
    assert e.chars(me)["crystal_soul"] == 3
    assert e._mana_choices(me, 0) != []
    e2 = setup(rules, {"hand": ["T201"], "mana": ["T001", "T001", "T001"]}, {})
    _flip(e2, "T001")
    me2 = _cid(e2, "hand", 0, "T201")
    assert e2.chars(me2)["crystal_soul"] == 0
    assert e2._mana_choices(me2, 0) == []
    e3 = setup(rules, {"bz": ["T200", "T201"]}, {})
    on_bz = _cid(e3, "bz", 0, "T201")
    assert e3.chars(on_bz)["crystal_soul"] == 0   # affects は zone: hand のみ


def test_plain_payment_unchanged(xr):
    """(8) 宣言のないカードの支払いは従来どおり（実効値＝印刷値）。"""
    e = setup(xr, {"hand": ["X200"], "mana": ["T001", "T001", "T001", "T001"]}, {})
    me = _cid(e, "hand", 0, "X200")
    assert e.chars(me)["crystal_soul"] == 0
    assert e._mana_choices(me, 0) != []           # 1×4＝4
    _flip(e, "T001", 2)
    assert e._mana_choices(me, 0) != []           # 裏向きでも印刷値 1 のまま数える


def test_summon_e2e(rules):
    """実支払いの経路: メインステップで T198 を選び、裏向きマナを含む組合せで召喚できる。"""
    e = setup(rules, {"hand": ["T198"], "mana": ["T003", "T001", "T001", "T001"]}, {})
    _flip(e, "T001")
    played = False
    for _ in range(200):
        if any(e.cdef(c).id == "T198" for c in e.bz_tops(0)):
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and not played and "play:T198" in keys:
            played = True
            e.answer([keys.index("play:T198")])
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert played
    assert any(e.cdef(c).id == "T198" for c in e.bz_tops(0))
    assert all(e.s.cards[c].tapped for c in e.zlist("mana", 0))   # 4枚すべてタップして払った
