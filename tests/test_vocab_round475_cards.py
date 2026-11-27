"""再変換ラウンド475（第441弾 count_face_up_shields）の記録テスト。

- 新規登録1件: dm23bd7-019 煌メク聖晶 弩楼 /
  ビスティック・マース（ツインパクト。提出形は
  partial〔クリーチャー面の骨格のみ: 光 / コスト9 /
  パワー11500 / 種族 メタリカ/サバキスト、mana 1、
  text は条項だけの断片、keywords 未記載、
  abilities 未構築〕に第441弾の確立形で faces 2面を
  構築したもの。登録形は提出形と完全一致〔source
  以外の全フィールドを照合〕、faces は2面ちょうど、
  面0の abilities は trigger 1件ちょうど、面0の
  keywords は [blocker, double_breaker]、面1の
  keywords は [s_trigger]、text は両面の公式全文を
  登録先例の結合形式にしたもの）。
- 補完あり: text（両面の公式全文）＋keywords＋
  abilities＋呪文面まるごと。
- alias 畳み込み0件（alias dmbd07-b-002 は独自行が
  無く、登録エントリの source.aliases に validate が
  自動付与したのみ。正本判定: 対象 id と alias を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1231 の notes 内参照のみ〕、identity
  実測で canon_id は対象自身、aliases_for =
  [dmbd07-b-002]）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔count_face_up_shields〕の出力は対象
  1件ちょうど＝巻き込みなし。count_face_up_shields
  は完全解消）。
- converted 10,420→10,421 / rejects 1,891→1,890、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ
  （第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第441弾本体と同形（対象を proto T1231 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（通常シールド）/ T339
（マナ）/ T002（フィラー）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402
from tests.test_vocab_pilot441_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot441 import FACES, FULL_TEXT, NAME  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm23bd7-019"
GAP = "count_face_up_shields"
ALIAS = "dmbd07-b-002"


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


def test_round475_disposition():
    rej = _reject_rows()
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["faces"]) == 2          # faces は2面ちょうど
    f0, f1 = c["faces"]
    assert len(f0["abilities"]) == 1     # 面0の abilities は1件ちょうど
    assert f0["abilities"][0]["kind"] == "trigger"
    assert f0["keywords"] == ["blocker", "double_breaker"]
    assert f1["keywords"] == ["s_trigger"]
    assert c["text"] == FULL_TEXT        # 両面の公式全文（提出形一致）
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]  # alias は source.aliases のみ
    assert canon_id(TARGET) == TARGET
    assert canon_id(ALIAS) == TARGET
    assert aliases_for(NAME, TARGET) == [ALIAS]
    d = parse_card(c, TABLES)
    df0, df1 = d.faces
    assert df0.name == "煌メク聖晶 弩楼" and df0.power == 11500
    assert FACES[0]["abilities"][0] in df0.abilities
    assert df1.name == "ビスティック・マース" and df1.cost == 4
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第441弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _drive(e, on_decision, limit=800):
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
        keys = _keys(d)
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("driver limit reached")


def _arrange_face_up(e):
    """自分のシールド5枚を: 束a（トップ表向き＋下に表向き）
    / 束c（トップ裏向き＋下に表向き）/ 束f（裏向きのみ）に
    組み替える。表向きカードは3枚、表向きを含む束は2つ。"""
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


def _summon_target(rules, answers, arrange=True):
    """登録カードを召喚し、CIP の may（1枚ごと）に answers の
    列で答える。戻り値: (engine, may の提示回数)。観測点は
    相手ターンのチャージ。"""
    e = scenario.build(rules, {
        "p0": {"hand": [TARGET], "mana": ["T339"] * 9,
               "shield": ["T001"] * 5},
        "p1": {},
        "filler": "T002", "seed": 1, "deck_size": 20})
    if arrange:
        _arrange_face_up(e)
    state = {"played": False, "mays": 0}
    queue = list(answers)

    def on_dec(e, d):
        keys = _keys(d)
        if not state["played"] and d["kind"] == "main" \
                and d.get("player") == 0 \
                and f"play:{TARGET}:0" in keys:
            state["played"] = True
            e.answer([keys.index(f"play:{TARGET}:0")])
            return "ok"
        if state["played"] and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        if state["played"] and d["kind"] == "yes_no" \
                and d.get("player") == 0:
            state["mays"] += 1
            ans = queue.pop(0) if queue else "no"
            e.answer([keys.index(ans)])
            return "ok"
        if state["played"] and d["kind"] == "charge" \
                and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, on_dec)
    assert state["played"], "登録カードを召喚できなかった"
    return e, state["mays"]


def test_cip_draws_for_each_face_up_card(rules):
    """表向き3枚 → may が3回提示され、全部 yes で
    3枚引く（覆われた下の表向きも数える）。"""
    e, mays = _summon_target(rules, ["yes", "yes", "yes"])
    assert mays == 3
    assert len(e.zlist("hand", 0)) == 3
    assert len(e.zlist("bz", 0)) == 1


def test_cip_draw_is_optional_per_card(rules):
    """1枚ごとに任意: yes / no / yes で2枚だけ引く。"""
    e, mays = _summon_target(rules, ["yes", "no", "yes"])
    assert mays == 3
    assert len(e.zlist("hand", 0)) == 2


def test_cip_no_face_up_no_draw(rules):
    """表向きが無ければ may は提示されず引かない。"""
    e, mays = _summon_target(rules, [], arrange=False)
    assert mays == 0
    assert len(e.zlist("hand", 0)) == 0
    assert len(e.zlist("bz", 0)) == 1


def _cast_spell_face(rules, own_mana, opp_mana):
    """登録カードの呪文面を唱える。戻り値: engine。観測点は
    相手ターンのチャージ。"""
    e = scenario.build(rules, {
        "p0": {"hand": [TARGET], "mana": ["T339"] * own_mana},
        "p1": {"mana": ["T001"] * opp_mana},
        "filler": "T002", "seed": 1, "deck_size": 20})
    state = {"played": False}

    def on_dec(e, d):
        keys = _keys(d)
        if not state["played"] and d["kind"] == "main" \
                and d.get("player") == 0 \
                and f"play:{TARGET}:1" in keys:
            state["played"] = True
            e.answer([keys.index(f"play:{TARGET}:1")])
            return "ok"
        if state["played"] and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        if state["played"] and d["kind"] == "charge" \
                and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, on_dec)
    assert state["played"], "登録カードの呪文面を唱えられなかった"
    return e


def test_spell_face_puts_two_mana_when_opponent_has_more(rules):
    """相手マナ5 > 自分4 → 山札の上から2枚が
    アンタップでマナゾーンに置かれ、呪文は墓地へ。"""
    e = _cast_spell_face(rules, own_mana=4, opp_mana=5)
    mana = e.zlist("mana", 0)
    assert len(mana) == 6
    untapped = [c for c in mana if not e.s.cards[c].tapped]
    assert len(untapped) == 2
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == [TARGET]


def test_spell_face_does_nothing_when_not_behind(rules):
    """相手マナ5 = 自分5 → 何も置かれない。"""
    e = _cast_spell_face(rules, own_mana=5, opp_mana=5)
    assert len(e.zlist("mana", 0)) == 5
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == [TARGET]
