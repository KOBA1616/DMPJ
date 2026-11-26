"""語彙パイロット第372弾: set_power（ドリフト）。

センサス（rejects 1,961件を取り直し）: pure 1,813件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜371弾）は再提案しない。第371弾で
「power_set: 500 の一括形自体は第272弾の mod で届くが、
進化元の補完検証が要るため本弾の最小ではない。次弾
以降の候補として残す」とされた **set_power
（pure 1件、multi にも現れない）** を、取り直した
センサスで裏取りし、補完の検証を済ませて選定した
（pure 1件が最小単位）。本弾で個別に評価して見送った
候補は docs/vocab-pilot.md 第372弾に記録:
deck_bottom_to_hand は表現可能と評価し次弾以降の
候補として残した。

対象は pure 1件すべて: dm32-011 超神龍イエス・
ヤザリス（光 / コスト5 / パワー5500 /
アポロニア・ドラゴン、alias dm32-011hc）。partial は
骨格（types [creature]、keywords [blocker] のみ）で、
未解決は unsupported の set_power 1件だけ。条項は
すべて確立済みの部品で表せる（追加語彙なし）:

- 「進化-自分の『ブロッカー』を持つクリーチャー
  １体の上に置く」は evolve_from {types: [creature],
  keyword: blocker}。同セットの登録先例 dm32-002
  （真姫ヴィクトリア）・dm32-072（聖皇エール・
  マグナス）が同文・同形。partial に欠けた要素の
  補完は types への evolution 追加と evolve_from の
  追加（第371弾の申し送りどおり検証済み。なお
  defs の _fix_evolution_type も同形を補う）。
- 「このクリーチャーをバトルゾーンに出した時、
  そのターン、バトルゾーンにある相手の進化では
  ないクリーチャーすべてのパワーは500になる」は
  CIP 誘発 {event: move, to: bz, subject: self} →
  modify {select: {zone: bz, owner: opp, filter:
  {types: [creature], not_types: [evolution]},
  count: all}, mod: {power_set: 500},
  duration: end_of_turn}。power_set は第272弾の mod
  （第370・371弾で単体対象の確立形）。一括の
  one-shot modify（zone セレクタ＋count: all）は
  登録先例多数（dm23bd5-059 の power +2000 他）。
  非 dynamic の modify は解決時の範囲に固定される
  （110.2e）ため、そのターン後から出たクリーチャー
  には及ばない。「進化ではない」は第365弾の
  not_types: [evolution]（登録先例 dm22ex1-cho37）。

確立形: abilities = [CIP 誘発] の1件、
types = [creature, evolution]、
evolve_from = {types: [creature], keyword: blocker}。

proto T1116（dm32-011 型）/ T1117（ブロッカー進化元
役＋光マナ役）/ T1118（パワー7000・非進化役）/
T1119（パワー4000・進化役）/ T1120（パワー300・
非進化役）。判別役は既存 proto も流用: T1114
（自己パワー+3000役＝実効6000。power_set が加算
ごと上書きすることの判別役）/ T1107（能力なし
パワー2000＝ブロッカーを持たない進化元対照）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED
が復活するので scenario.build を直接包む
（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [
           {"op": "modify",
            "select": {"zone": "bz", "owner": "opp",
                       "filter": {"types": ["creature"],
                                  "not_types": ["evolution"]},
                       "count": "all"},
            "mod": {"power_set": 500},
            "duration": "end_of_turn"}]}
EVOLVE_FROM = {"types": ["creature"], "keyword": "blocker"}
FORM = [CIP]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1116")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature", "evolution"]
    assert c["evolve_from"] == EVOLVE_FROM
    assert c["civs"] == ["light"] and c["cost"] == 5
    assert c["power"] == 5500 and c["mana"] == 1
    assert c["races"] == ["アポロニア・ドラゴン"]
    assert c["keywords"] == ["blocker"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert CIP in d.abilities
    assert d.evolve_from == EVOLVE_FROM
    for tid in ("T1117", "T1118", "T1119", "T1120", "T1114", "T1107"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX372", "name": "x",
                    "types": ["creature", "evolution"],
                    "civs": ["light"], "cost": 5, "power": 5500,
                    "races": ["アポロニア・ドラゴン"], "mana": 1,
                    "keywords": ["blocker"],
                    "evolve_from": copy.deepcopy(EVOLVE_FROM),
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert CIP in d.abilities
    assert d.evolve_from == EVOLVE_FROM


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn):
    cards = e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)
    return next(c for c in cards if e.cdef(c).id == defn)


def _power(e, p, defn):
    return e.chars(_find(e, "bz", p, defn))["power"]


def _drive(e, plays=(), pick=None, stop=None, on_main=None,
           limit=600):
    """汎用ドライバ（第361弾と同形）。plays は p0 の main で
    使う play キー、pick は選択系で優先するキー断片、
    on_main は p0 の main 決定のキー一覧を受ける。"""
    plays = list(plays)
    for _ in range(limit):
        if stop is not None and stop():
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and d.get("player") == 0:
            if on_main is not None:
                on_main(keys)
            hit = next((k for k in plays if k in keys), None)
            if hit is not None:
                plays.remove(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def _summon_setup(rules, p1_bz):
    return _build(rules,
                  {"bz": ["T1117"], "hand": ["T1116"],
                   "mana": ["T1117"] * 5},
                  {"bz": p1_bz})


def test_cip_sets_all_opponent_non_evolution_powers(rules):
    """実挙動: T1116 をブロッカー（T1117）の上に進化
    させて出すと、そのターン、相手の進化ではない
    クリーチャーすべてのパワーが500になる。
    パワー7000（T1118）は500に下がり、パワー300
    （T1120）は500に上がり（『500になる』は設定で
    あって軽減ではない）、実効6000（T1114＝印刷3000
    ＋加算3000）も加算ごと上書きされて500になる。
    進化クリーチャー（T1119、パワー4000）は対象から
    外れて変わらない。"""
    e = _summon_setup(rules, ["T1118", "T1119", "T1120", "T1114"])
    assert _power(e, 1, "T1118") == 7000     # 前提
    assert _power(e, 1, "T1114") == 6000     # 前提: 加算が効いている
    assert _power(e, 1, "T1120") == 300      # 前提
    assert _power(e, 1, "T1119") == 4000     # 前提
    _drive(e, plays=["play:T1116"], pick="T1117",
           stop=lambda: _power(e, 1, "T1118") == 500)
    assert "T1116" in _defns(e, "bz", 0)
    assert _power(e, 0, "T1116") == 5500     # 自分は対象外
    assert _power(e, 1, "T1118") == 500
    assert _power(e, 1, "T1120") == 500      # 引き上げも起きる
    assert _power(e, 1, "T1114") == 500      # 加算ごと上書き
    assert _power(e, 1, "T1119") == 4000     # 進化は対象外


def test_power_set_expires_at_end_of_turn(rules):
    """持続は『そのターン』だけ: ターンが終われば
    パワーは元に戻る（duration: end_of_turn）。"""
    e = _summon_setup(rules, ["T1118"])
    _drive(e, plays=["play:T1116"], pick="T1117",
           stop=lambda: _power(e, 1, "T1118") == 500)
    assert _power(e, 1, "T1118") == 500
    _drive(e, stop=lambda: e.s.turn >= 2)
    assert "T1118" in _defns(e, "bz", 1)
    assert _power(e, 1, "T1118") == 7000


def test_no_evolution_onto_non_blocker_base(rules):
    """判別: ブロッカーを持たないクリーチャー
    （T1107）の上には進化できない。main の選択肢に
    play:T1116 が一度も現れず、手札に留まる
    （正例 test_cip_sets_all_... と対）。"""
    e = _build(rules,
               {"bz": ["T1107"], "hand": ["T1116"],
                "mana": ["T1117"] * 5},
               {})
    offered = {"play": False}

    def on_main(keys):
        if "play:T1116" in keys:
            offered["play"] = True

    _drive(e, plays=["play:T1116"], on_main=on_main,
           stop=lambda: e.s.turn >= 5, limit=300)
    assert not offered["play"]
    assert "T1116" in _defns(e, "hand", 0)
    assert "T1116" not in _defns(e, "bz", 0)


def test_cip_with_no_opponent_creatures(rules):
    """判別: 相手のクリーチャーがいなければ一括
    modify の対象は無く、効果は空振りで解決する。
    T1116 は通常どおり場に出る。"""
    e = _summon_setup(rules, [])
    _drive(e, plays=["play:T1116"], pick="T1117",
           stop=lambda: "T1116" in _defns(e, "bz", 0)
           and e.s.turn >= 2)
    assert "T1116" in _defns(e, "bz", 0)
    assert _power(e, 0, "T1116") == 5500
    assert _defns(e, "graveyard", 0) == []
    assert _defns(e, "graveyard", 1) == []
