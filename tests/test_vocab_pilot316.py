"""語彙パイロット第316弾: filter_not_keyword（「『ブロッカー』以外のクリーチャー」）。

センサス先行（rejects 2,064件）: 第312〜315弾の空 gaps 監査ラインは
使い切ったため pure ファミリーを取り直し、範囲内・未評価で最小の
filter_not_keyword（純粋2件: dm06-016 / dm18-022、ともに
ジャスティス・バインドの同名2刷）を選定した。両行の partial の
notes 自身が「フィルタにキーワードの否定が無いため絞れない」と
明記する、フィルタキーの欠落そのものがギャップ。

追加語彙はフィルタキー not_keyword 1つだけ:
- defs FILTER_KEYS に not_keyword を追加（schema は FILTER_KEYS から
  生成されるため再生成で3箇所に反映。差分は not_keyword のみ）。
- selectors.filter_match に keyword の鏡像を追加:
  not_keyword が特性値の keywords に含まれれば不一致。
  特性値の keywords は付与分を含む（core の grant 反映）ため、
  静的で「ブロッカー」を得たクリーチャーも「ブロッカー以外の」
  対象から外れる。これは既存 keyword フィルタと同じ見方で、
  ルール上も付与されたブロッカーはブロッカーとして扱う。

確立形（呪文面）: {op: tap, select: {zone: bz, owner: any,
filter: {types: [creature], not_keyword: blocker}, count: all}}
— dm18-022 の partial に完成済みの tap 形があり、filter に
not_keyword: blocker を足すだけで正確に一致する。

プロト:
- T970: dm06-016 / dm18-022 型（光4コスト呪文、S・トリガー）
- T971: 役カード（自分の他のクリーチャーにブロッカーを付与する
  静的持ち。本体は other: true で自身を含まない）
既存の T001（バニラ）/ T004（ブロッカー）を対照に使う。
"""
import copy

import pytest
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()

SPELL = [{"op": "tap",
          "select": {"zone": "bz", "owner": "any",
                     "filter": {"types": ["creature"],
                                "not_keyword": "blocker"},
                     "count": "all"}}]


def _by_defn(e, zone, defn, player=0):
    return [c for c in e.zlist(zone, player)
            if e.s.cards[c].defn == defn
            and (zone != "bz" or e.s.cards[c].controller == player)]


def _run(e, handler, limit=900, done=None):
    for _ in range(limit):
        if e.s.result is not None or (done and done()):
            return
        d = e.advance()
        if d is None:
            return
        r = handler(e, d)
        if r is not None:
            e.answer(r)
            continue
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))


def _cast_handler(e, d):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "main" and d["player"] == 0 and "play:T970" in keys:
        return [keys.index("play:T970")]
    if d["kind"] == "pay_mana":
        return [0]
    return None


def _tapped(e, zone, defn, player):
    cs = _by_defn(e, zone, defn, player)
    assert len(cs) == 1, (zone, defn, player, cs)
    return e.s.cards[cs[0]].tapped


# ---------------------------------------------------------------- parse

def test_parse_form(rules):
    d = parse_card(proto_card("T970"), TABLES)
    assert d.types == ["spell"] and d.civs == ["light"] and d.cost == 4
    assert d.keywords == ["s_trigger"]
    assert d.spell == SPELL
    d2 = parse_card(proto_card("T971"), TABLES)
    assert d2.abilities[0]["mod"] == {"grant": ["blocker"]}


def test_unknown_filter_key_still_rejected(rules):
    # not_keyword の追加で検証が緩んでいないこと（未知キーは DefError）
    bad = proto_card("T970")
    bad["spell"] = [{"op": "tap",
                     "select": {"zone": "bz", "owner": "any",
                                "filter": {"types": ["creature"],
                                           "not_keyword2": "blocker"},
                                "count": "all"}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


# ---------------------------------------------------------------- 実挙動

def test_taps_all_non_blockers_both_sides(rules):
    # 自分・相手どちらのバニラもタップし、印刷ブロッカーは
    # どちらの側もタップしない（owner: any の全タップ）
    e = setup(rules,
              {"hand": ["T970"], "mana": ["T004"] * 4,
               "bz": ["T001", "T004"]},
              {"bz": ["T001", "T004"]})
    _run(e, _cast_handler,
         done=lambda: len(_by_defn(e, "graveyard", "T970", 0)) == 1)
    assert _tapped(e, "bz", "T001", 0) is True
    assert _tapped(e, "bz", "T004", 0) is False
    assert _tapped(e, "bz", "T001", 1) is True
    assert _tapped(e, "bz", "T004", 1) is False


def test_granted_blocker_is_not_tapped(rules):
    # T971 の静的でブロッカーを得た T001 は「ブロッカー以外」に
    # 入らない（付与分を含む特性値で判定）。T971 本体は
    # other: true で付与対象外かつ印刷ブロッカーも無いので
    # タップする。相手のバニラは通常どおりタップする
    e = setup(rules,
              {"hand": ["T970"], "mana": ["T004"] * 4,
               "bz": ["T971", "T001"]},
              {"bz": ["T001"]})
    _run(e, _cast_handler,
         done=lambda: len(_by_defn(e, "graveyard", "T970", 0)) == 1)
    assert _tapped(e, "bz", "T001", 0) is False   # 付与ブロッカー
    assert _tapped(e, "bz", "T971", 0) is True    # 本体は対象
    assert _tapped(e, "bz", "T001", 1) is True
