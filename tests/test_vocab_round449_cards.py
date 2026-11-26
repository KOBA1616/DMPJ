"""再変換ラウンド449（第414弾 chosen_creature_can_be_
attacked_while_untapped）の記録テスト。

- 新規登録1件: dm01-034 カオス・ストライク
  （登録形は提出形と完全一致: partial の骨格
  〔呪文 / 火 / コスト2、mana 1〕に第414弾の
  確立形 spell 2 op〔choose {select: {zone: bz,
  owner: opp, filter: {types: [creature]},
  count: 1}, as: tgt} / modify {select:
  {zone: bz, owner: you, filter: {types:
  [creature]}, count: all}, mod: {allow:
  [{action: attack_creature, other: {tapped:
  false}, only: {var: tgt}}]}, duration:
  end_of_turn}〕を足し、unsupported を外した
  もの。spell はこの2 op ちょうど、allow 項目の
  only {var: tgt} は保持。登録済み dmr09-102
  戦場のロックンロール〔第275弾〕と同型で、差は
  選択フィルタに tapped: false が無いことだけ）。
- 補完なし（提出形の text は reject 行の公式
  テキスト＝改行ありの全文。partial の text は
  内容一致だが文間の改行が欠けるためそのまま
  使っていない。登録後の text の全文一致
  〔改行を含む〕も照合済み）。
- split は None で定型所有なし＝ツール側
  ブロッカーなし。
- alias 畳み込み0件（alias は無し。対象 id を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1182 の notes 内参照のみ〕、identity
  実測で canon_id は対象自身、aliases_for = []
  のため登録エントリに source.aliases は付かない。
  正本判定は提出前に再確認済み）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔chosen_creature_can_be_attacked_
  while_untapped〕の出力は対象1件ちょうどで
  巻き込みなし）。
- converted 10,393→10,394 / rejects
  1,918→1,917、canonical 重なり0・漏れ0。
  chosen_creature_can_be_attacked_while_untapped
  は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第414弾本体と同形（対象を proto T1182 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1090（印刷スピードアタッカー
役＝攻撃側・火マナ役）/ T008（パワー1000バニラ
役＝選ぶ対象）/ T1091（パワー2000バニラ役＝
選ばない対照）。
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
from tests.test_vocab_pilot414 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm01-034"
GAP = "chosen_creature_can_be_attacked_while_untapped"
NAME = "カオス・ストライク"


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


def test_round449_disposition():
    rej = _reject_rows()
    assert len(rej) == 1917
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10394
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["spell"] and c["civs"] == ["fire"]
    assert c["cost"] == 2 and c["mana"] == 1
    assert c["text"] == FULL_TEXT        # 公式全文（改行あり、補完なし）
    # 登録形は提出形と完全一致: spell は 2 op ちょうど
    assert c["spell"] == FORM
    assert len(c["spell"]) == 2
    assert [op["op"] for op in c["spell"]] == ["choose", "modify"]
    assert c["spell"][1]["mod"]["allow"][0]["only"] == {"var": "tgt"}
    assert "tapped" not in c["spell"][0]["select"]["filter"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無しのため付かない
    d = parse_card(c, TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "modify"]
    assert d.spell[0]["as"] == "tgt"
    assert d.spell[1]["mod"]["allow"][0]["only"] == {"var": "tgt"}
    assert d.spell[1]["duration"] == "end_of_turn"
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第414弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _setup(rules):
    return _build(rules,
                  {"bz": ["T1090"], "hand": [TARGET],
                   "mana": ["T1090", "T1090"]},
                  {"bz": ["T008", "T1091"]})


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _drive(e, choose_defn=None, attack_key=None, stop=None, limit=1200,
           log=None):
    """汎用ドライバ: player 0 が登録カードを唱えて
    choose_defn を選び、attack_key があれば一度だけ
    攻撃する。stop(e) が真になったら止める。
    観測した player 0 の攻撃決定を (turn, keys) の
    リストで返す（log を渡せばそこへ追記する）。"""
    st = {"played": False, "chose": False, "attacked": False}
    if log is None:
        log = []
    for _ in range(limit):
        if stop and stop(e):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and d.get("player") == 0 \
                and not st["played"] and f"play:{TARGET}" in keys:
            st["played"] = True
            e.answer([keys.index(f"play:{TARGET}")])
            continue
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if kind == "choose_cards" and choose_defn is not None \
                and not st["chose"]:
            hit = [i for i, o in enumerate(d["options"])
                   if e.cdef(o["cid"]).id == choose_defn]
            if hit:
                st["chose"] = True
                e.answer([hit[0]])
                continue
        if kind == "attack" and d.get("player") == 0:
            log.append((e.s.turn, list(keys)))
            if attack_key is not None and not st["attacked"] \
                    and attack_key in keys:
                st["attacked"] = True
                e.answer([keys.index(attack_key)])
                continue
        if kind == "declare_strigger":
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return st, log


def test_control_untapped_cannot_be_attacked(rules):
    """対照: 唱えなければ、アンタップしている相手
    クリーチャーはどちらも攻撃できない（プレイヤー
    への攻撃だけが選択肢に出る）。"""
    e = _setup(rules)
    keys = [o["key"] for o in e._attack_options(0)]
    assert keys == ["attack:T1090:player"]


def test_cast_choose_untapped_attack_only_chosen(rules):
    """登録カードの実挙動: 唱えてアンタップの T008 を
    選ぶと、このターン T008 だけが（タップされて
    いなくても）攻撃でき、選ばなかった T1091 は
    攻撃できない。実際に攻撃すると T008（パワー
    1000）はバトルで破壊され、T1090 は残る。"""
    e = _setup(rules)
    st, log = _drive(
        e, choose_defn="T008", attack_key="attack:T1090:T008",
        stop=lambda e: _in_zone(e, 1, "graveyard", "T008"))
    assert st["played"] and st["chose"] and st["attacked"]
    first = log[0][1]
    assert "attack:T1090:T008" in first       # 選んだ対象は攻撃可
    assert "attack:T1090:T1091" not in first  # 選んでいない対象は不可
    assert "attack:T1090:player" in first
    assert _in_zone(e, 1, "graveyard", "T008")
    assert _in_zone(e, 0, "bz", "T1090")          # 勝者は残る
    assert _in_zone(e, 1, "bz", "T1091")          # 対照は無事
    assert _in_zone(e, 0, "graveyard", TARGET)    # 呪文は墓地へ


def test_cast_choose_tapped_target(rules):
    """選択フィルタに tapped: false が無いことの判別:
    タップしている T008 も選べる（第275弾形なら
    選べない）。選ばなかった T1091 は攻撃できない。"""
    e = _setup(rules)
    cid = next(c for c in e.zlist("bz", 1)
               if e.s.cards[c].defn == "T008")
    e.s.cards[cid].tapped = True
    st, log = _drive(
        e, choose_defn="T008", attack_key="attack:T1090:T008",
        stop=lambda e: _in_zone(e, 1, "graveyard", "T008"))
    assert st["played"] and st["chose"] and st["attacked"]
    first = log[0][1]
    assert "attack:T1090:T008" in first
    assert "attack:T1090:T1091" not in first
    assert _in_zone(e, 1, "graveyard", "T008")


def test_effect_expires_next_turn(rules):
    """duration: end_of_turn の判別: 唱えて T008 を
    選んでも攻撃しなければ、自分の次のターンには
    T008（アンタップのまま）を攻撃できない。"""
    e = _setup(rules)
    log = []
    st, log = _drive(e, choose_defn="T008", attack_key=None, log=log,
                     stop=lambda e: len({t for t, _ in log}) >= 2)
    assert st["played"] and st["chose"]
    turns = {}
    for t, keys in log:
        turns.setdefault(t, keys)
    ts = sorted(turns)
    assert len(ts) >= 2
    assert "attack:T1090:T008" in turns[ts[0]]       # 当ターンは攻撃可
    assert "attack:T1090:T008" not in turns[ts[1]]   # 次ターンは不可
    assert "attack:T1090:player" in turns[ts[1]]
    assert _in_zone(e, 1, "bz", "T008")              # 攻撃されず残る
