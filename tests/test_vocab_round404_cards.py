"""再変換ラウンド404（第369弾 no_shield_break）の記録テスト。

- 新規登録1件: dmex03-061 夜のポンの助
  （登録形は提出形と完全一致: partial の骨格
  〔ゼロ / コスト1 / パワー820 / 種族
  ジョーカーズ、keywords・abilities 無し〕に
  第369弾の確立形2能力〔static {affects: self,
  mod: {breaks: 0}}（dmex17-106 の登録先例と
  同形）＋ static {affects: {zone: shield,
  owner: you}, mod: {deny: [s_trigger]}}
  （dm04-022 の登録先例の変種）〕を足し
  unsupported を外したもの。補完あり: partial の
  text は第1条項だけのため、text には行の公式
  テキスト全文（3条項）を入れた。第3条項は
  デッキ構築ルールで dmex13-057 の先例どおり
  テキストのみ）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id dmex03-061 を real.yaml /
  real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml
  と照合し、いずれにも登録なし（proto.yaml の
  ヒットは T1112 の notes 内参照のみ）。
  identity 実測で canon = dmex03-061。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [no_shield_break] のため
  reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,348→10,349 / rejects
  1,964→1,963、canonical 重なり0・漏れ0。
  no_shield_break はファミリーがこの1件
  だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第369弾本体の薄い包み（対象を登録カードに
差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
proto T1107（能力なしパワー2000アタッカー＝
対照）/ T006（S・トリガー呪文）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex03-061"
GAP = "no_shield_break"

BREAKS0 = {"kind": "static", "affects": "self", "mod": {"breaks": 0}}
STRIGGER_DENY = {"kind": "static",
                 "affects": {"zone": "shield", "owner": "you"},
                 "mod": {"deny": ["s_trigger"]}}
FORM = [BREAKS0, STRIGGER_DENY]
FULL_TEXT = ("このクリーチャーはシールドをブレイクできない。\n"
             "自分は「S・トリガー」能力を使えない。\n"
             "このカードは、４枚より多くデッキに入れることができる。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round404_disposition():
    rej = _reject_rows()
    assert len(rej) == 1963
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10349
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: static 2件ちょうど、
    # keywords は無いまま、text は公式テキスト全文
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    assert c["name"] == "夜のポンの助"
    assert c["types"] == ["creature"] and c["civs"] == ["zero"]
    assert c["cost"] == 1 and c["power"] == 820
    assert c["races"] == ["ジョーカーズ"] and c["mana"] == 1
    d = parse_card(c, TABLES)
    assert BREAKS0 in d.abilities and STRIGGER_DENY in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第369弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.cdef(c).id == defn)


def _drive(e, attacker, player, break_defn=None, use_strigger=False):
    """player の attacker でプレイヤーを攻撃する（第369弾本体と同形）。"""
    log = []
    attacked = False
    for _ in range(1500):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == player and not attacked:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit:
                attacked = True
                e.answer([hit[0]])
                continue
        if kind == "choose_shields" and break_defn:
            shields = e.zlist("shield", 1 - player)
            idx = next(i for i, c in enumerate(shields)
                       if e.cdef(c).id == break_defn)
            e.answer([idx])
            continue
        if kind == "declare_strigger":
            log.append((kind, d.get("player"), keys))
            e.answer(list(range(len(keys))) if use_strigger else [])
            continue
        if kind == "choose_cards":
            hit = [i for i, k in enumerate(keys) if attacker in k]
            if hit:
                e.answer(hit[:1])
                continue
        if kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
            continue
        e.answer(list(range(d.get("min", 0))))
        if attacked and kind == "main" and d.get("player") == player:
            break
    return log


def test_registered_chars_break_opts_and_shield_deny(rules):
    """登録カード: 特性レベルで break_opts は [0] ちょうど。
    自分のシールドは登録カードがいる間だけ deny
    [s_trigger] を持ち、相手のシールドには付かない。"""
    e = _build(rules, {"bz": [TARGET]}, {})
    ch = e.chars(_find(e, "bz", 0, TARGET))
    assert ch["break_opts"] == [0]
    e = _build(rules, {"bz": [TARGET], "shield": ["T006"]},
               {"shield": ["T006"]})
    assert "s_trigger" in e.chars(_find(e, "shield", 0, "T006"))["deny"]
    assert "s_trigger" not in e.chars(_find(e, "shield", 1, "T006"))["deny"]


def test_registered_attack_breaks_no_shield(rules):
    """登録カード: ブロックされずにプレイヤーを攻撃しても
    シールドは1枚もブレイクされない（攻撃自体は成立し、
    登録カードは場に残る）。"""
    e = _build(rules, {}, {"bz": [TARGET]})
    before = len(e.zlist("shield", 0))
    _drive(e, TARGET, 1)
    assert len(e.zlist("shield", 0)) == before
    assert TARGET in _defns(e, "bz", 1)


def test_registered_own_strigger_denied(rules):
    """登録カード: 自分の場にいる間、自分のシールド
    （T006）がブレイクされても S・トリガーの宣言判断
    自体が出ず、カードはそのまま手札に加わる
    （攻撃側は破壊されない）。"""
    e = _build(rules,
               {"bz": [TARGET],
                "shield": ["T006", "T001", "T001", "T001", "T001"]},
               {"bz": ["T1107"]})
    log = _drive(e, "T1107", 1, break_defn="T006", use_strigger=True)
    assert not [x for x in log if x[0] == "declare_strigger"]
    assert "T006" in _defns(e, "hand", 0)
    assert "T1107" in _defns(e, "bz", 1)      # 破壊されていない
    assert len(e.zlist("shield", 0)) == 4


def test_registered_opponent_strigger_unaffected(rules):
    """登録カード: deny は owner: you のため、相手の
    S・トリガー使用は妨げない。自分の T1107 が相手の
    T006 をブレイクすると、相手は宣言して使え、
    T1107 は破壊される。"""
    e = _build(rules,
               {"bz": [TARGET, "T1107"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T1107", 0, break_defn="T006", use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 1 and "strigger:T006" in st[0][2]
    assert "T1107" in _defns(e, "graveyard", 0)
    assert "T006" in _defns(e, "graveyard", 1)
    assert TARGET in _defns(e, "bz", 0)
