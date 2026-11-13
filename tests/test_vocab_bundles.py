"""第2段・小パイロットその1: 束（バンドル）数えの式 {bundles: ...}。

- 数え方の単位は公式ルール 113.2 で分かれる: 「シールドの数」は束単位、
  「シールドゾーンにあるカードの枚数」は束の中身を含むカード単位。
  表向きカードの「カード数」は既存の bundle_of セレクタ＋filter: face_up で数えられるが、
  「表向きのカードを含むシールドが10以上」（ℵHEAVEN dm24ex2-025）と
  「表向きのシールド1つにつき」（ミケランジェロ dm26rp2-022）は束の数であり、
  数える式が無かった（faq-check-judgments-20261109.md 論点4。ラウンド175で bundle_of 形に
  統一した2枚は、束に表向きカードが2枚以上ある局面では文面と一致しない既知の不完全さ）。
- 追加する式アトム: {bundles: {owner: you/opp, face_up?: bool}}。
  face_up: true は「表向きのカードを1枚以上含む束」だけを数える（覆われている表向き
  カードも含む。文面の「含む」に対応）。false は含まない束だけ。省略時は全束。
  評価は selectors.py の eval_expr（count_of からも引ける）、検証は defs.py の
  expr / count_spec、schema にも追加した。
- カード側の是正（上記2枚の書き換え）は次ラウンド。本ファイルは式とテストのみ。
- proto: T211（条件式の形。ℵHEAVEN 型）／T212（ドロー枚数の形。ミケランジェロ型）。
"""
import copy
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _settle(e, done, drive=None, max_steps=300):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive and drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def _flush(e, steps=60):
    for _ in range(steps):
        if not e.s.pending:
            return
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))


def _play_drive(want_key):
    def drive(e, d, keys):
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == want_key]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    return drive


def _arrange(e):
    """P0 のシールド5枚を3つの束に組み替える（エンジンの束表現そのものを使う）:
    束A: 表向きトップ＋表向き（覆われている）／束B: 裏向きトップ＋表向き（覆われている）／
    束C: 裏向き単独。
    → 束の総数 3、表向きを含む束 2、表向きカードの枚数 3（bundle_of の数えと区別できる配置）。"""
    s = e.s
    a, b, c, d, f = list(e.zlist("shield", 0))
    lst = e.zlist("shield", 0)
    for u in (b, d):
        lst.remove(u)
    s.cards[a].under = [b]
    s.cards[b].top_of = a
    s.cards[c].under = [d]
    s.cards[d].top_of = c
    for cid in (a, b, d):
        s.cards[cid].face_up = True
    return e


def test_bundles_expr_counts(rr):
    """式の数え: 束数と、表向きを含む束の数は、表向きカードの枚数（既存 bundle_of）と一致しない。"""
    e = _arrange(setup(rr, {"shield": ["T001"] * 5}, {}))
    env = {"you": 0}
    assert e.eval_expr({"bundles": {"owner": "you"}}, env) == 3
    assert e.eval_expr({"bundles": {"owner": "you", "face_up": True}}, env) == 2
    assert e.eval_expr({"bundles": {"owner": "you", "face_up": False}}, env) == 1
    assert e.eval_expr({"bundles": {"owner": "opp"}}, env) == 5
    assert e.eval_expr({"bundles": {"owner": "opp", "face_up": True}}, env) == 0
    # カード単位の数え（既存の bundle_of＋filter）は別の数になる（113.2 の数え分け）
    assert e.eval_expr({"count": {"bundle_of": {"zone": "shield", "owner": "you"},
                                   "filter": {"face_up": True}}}, env) == 3
    # count_of（mod の count 等）からも引ける
    assert e.count_of({"bundles": {"owner": "you", "face_up": True}}, env) == 2


def test_bundles_validation(rr):
    """T211／T212 が parse できる。bundles の形が悪いものは DefError。"""
    for cid in ("T211", "T212"):
        parse_card(_proto_card(cid), TABLES)
    card = next(c for c in rr.cards.values() if c.id == "T211")
    assert card.face(None).abilities[0]["if"]["cmp"][0] == {"bundles": {"owner": "you", "face_up": True}}
    bad = copy.deepcopy(_proto_card("T211"))
    bad["abilities"][0]["if"]["cmp"][0] = {"bundles": {"owner": "any"}}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad2 = copy.deepcopy(_proto_card("T211"))
    bad2["abilities"][0]["if"]["cmp"][0] = {"bundles": {"owner": "you", "face_up": "yes"}}
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)


def test_bundles_threshold_trigger(rr):
    """条件式の形（ℵHEAVEN 型）: 表向きを含む束が2つ以上あれば出た時に引く。"""
    e = setup(rr, {"hand": ["T211"], "mana": ["T004", "T004"], "shield": ["T001"] * 5}, {})
    _arrange(e)
    done = lambda: any(e.s.cards[c].defn == "T211" for c in e.zlist("bz", 0))
    assert _settle(e, done, _play_drive("play:T211"))
    _flush(e)
    assert len(e.zlist("hand", 0)) == 1


def test_bundles_threshold_not_met(rr):
    """表向きを含む束が1つだけでは引かない（束の中の表向きカードの枚数ではなく束で数える）。"""
    e = setup(rr, {"hand": ["T211"], "mana": ["T004", "T004"], "shield": ["T001"] * 5}, {})
    top = e.zlist("shield", 0)[0]
    e.s.cards[top].face_up = True   # 表向きは1束だけ
    done = lambda: any(e.s.cards[c].defn == "T211" for c in e.zlist("bz", 0))
    assert _settle(e, done, _play_drive("play:T211"))
    _flush(e)
    assert len(e.zlist("hand", 0)) == 0


def test_bundles_draw_count_spell(rr):
    """ドロー枚数の形（ミケランジェロ型）: 表向きを含む束1つにつき1枚引く（この配置では2枚）。"""
    e = setup(rr, {"hand": ["T212"], "mana": ["T003"], "shield": ["T001"] * 5}, {})
    _arrange(e)
    done = lambda: len(e.zlist("hand", 0)) == 2
    assert _settle(e, done, _play_drive("play:T212"))
    _flush(e)
    assert len(e.zlist("hand", 0)) == 2
