"""再変換ラウンド414（第379弾 deck_rule）の記録テスト。

- 新規登録1件: dmx22b-110 素晴らしい犬 ワンワンワン
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 自然 / コスト2 / パワー1111 /
  種族 アウトレイジ犬、mana 1、keywords・abilities
  ともに無し〕に第379弾の確立形 static〔power
  {amount: 1111, count: {zone: bz, owner: you,
  filter: {races: [アウトレイジ犬]}, other: true}}〕
  1能力を足し、unsupported を外したもの。abilities
  はこの1件ちょうど、keywords は無いまま。補完あり:
  partial の text はデッキ条項の断片のみのため、
  text には行の公式テキスト全文を入れた。デッキ条項
  「４枚より多くデッキに入れることができる」は
  デッキ構築ルールで、登録先例 dmex13-057 どおり
  text のみで保持し能力化しない）。
- alias 畳み込み0件（alias dmx22b-111 は rejects に
  独自行が無く、登録形の source.aliases に入って
  いる）。正本判定: 対象 id と alias を real.yaml /
  real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
  proto.yaml / converted.yaml と照合し、いずれにも
  登録なし（proto.yaml のヒットは T1131 の notes 内
  参照のみ）。identity 実測で canon_id(dmx22b-110) =
  dmx22b-110（対象 id が正本）、canon_id(dmx22b-111)
  = dmx22b-110、aliases_for(素晴らしい犬 ワンワンワン,
  dmx22b-110) = [dmx22b-111]（partial の
  source.aliases と一致）。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [deck_rule] のため reopen で
  外してから submit（reopen の出力は対象1件ちょうど）。
- converted 10,358→10,359 / rejects 1,954→1,953、
  canonical 重なり0・漏れ0。deck_rule はファミリーが
  この1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第379弾本体と同形（対象を proto T1131 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
proto T1132（他のアウトレイジ犬役）/ T1133
（水・パワー2000ブロッカー）を流用。
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
TARGET = "dmx22b-110"
GAP = "deck_rule"
ALIASES = ["dmx22b-111"]

STATIC = {"kind": "static", "affects": "self",
          "mod": {"power": {"amount": 1111,
                            "count": {"zone": "bz", "owner": "you",
                                      "filter": {"races": ["アウトレイジ犬"]},
                                      "other": True}}}}
FORM = [STATIC]
FULL_TEXT = ("{Dog Souls}《素晴らしい犬 ワンワンワン》は、"
             "４枚より多くデッキに入れることができる。"
             "バトルゾーンにある自分の他のアウトレイジ犬１匹につき、"
             "このクリーチャーのパワーを+1111する。")


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


def test_round414_disposition():
    rej = _reject_rows()
    assert len(rej) == 1953
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10359
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0（aliases 欄）
    assert TARGET not in rej             # 対象行は解消
    for a in ALIASES:
        assert a not in rej              # alias に rejects の独自行は無い
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")
    # alias は source.aliases に入っている
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")         # キーワードは無いまま
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    assert c["name"] == "素晴らしい犬 ワンワンワン"
    assert c["types"] == ["creature"]
    assert c["civs"] == ["nature"]
    assert c["cost"] == 2 and c["power"] == 1111 and c["mana"] == 1
    assert c["races"] == ["アウトレイジ犬"]
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第379弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _powers(e, tid, p):
    return [e.chars(c)["power"] for c in e.bz_tops(p)
            if e.cdef(c).id == tid]


def test_registered_power_alone_counts_no_self(rules):
    # 登録カード単独では自分を数えず 1111 のまま
    # （other: true が効いていなければ 2222 になる判別）
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    assert _powers(e, TARGET, 0) == [1111]


def test_registered_power_scales_with_other_dog(rules):
    # 他のアウトレイジ犬（T1132）1匹で 2222
    e = _build(rules, {"bz": [TARGET, "T1132"]}, {"bz": []})
    assert _powers(e, TARGET, 0) == [2222]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _battle(e, attacker_p, attacker, blocker):
    """attacker_p の attacker がプレイヤーを攻撃し、相手が
    blocker でブロックする。バトルが終わって attacker_p の
    次の charge が来たら戻る。"""
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == attacker_p \
                and state.get("blocked"):
            return state
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d["min"])))
        elif d["kind"] == "attack" and d.get("player") == attacker_p \
                and not state.get("attacked"):
            tgt = [k for k in keys if k == f"attack:{attacker}:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blocker}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("battle never finished")


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tops(e, p):
    return [e.s.cards[c].defn for c in e.bz_tops(p)]


def test_registered_battle_loses_without_other_dog(rules):
    # 登録カード: 素パワー1111ではパワー2000ブロッカー
    # （T1133）に負ける
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1133"]})
    state = _battle(e, 0, TARGET, "T1133")
    assert state.get("attacked") and state.get("blocked"), state
    assert TARGET in _defns(e, "graveyard", 0)
    assert "T1133" in _tops(e, 1)


def test_registered_battle_wins_with_other_dog(rules):
    # 登録カード: 他の犬1匹で 2222 になりパワー2000
    # ブロッカー（T1133）に勝つ
    e = _build(rules, {"bz": [TARGET, "T1132"]}, {"bz": ["T1133"]})
    state = _battle(e, 0, TARGET, "T1133")
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1133" in _defns(e, "graveyard", 1)
    assert TARGET in _tops(e, 0)
