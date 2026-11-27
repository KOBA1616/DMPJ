"""再変換ラウンド472（第438弾 revolution_2）の記録テスト。

- 新規登録1件: dmex06-033 革命目 ギョギョウ
  （提出形は partial〔骨格: 進化クリーチャー / 自然 /
  コスト6 / パワー8000 / 種族 ジュラシック・コマンド・
  ドラゴン/革命軍、mana 1、evolve_from {types:
  [creature], civs: [nature]}、keywords
  [double_breaker]、text は公式全文＋partial
  構築済みの第2条項 trigger〕に第438弾の確立形
  革命２の static {affects: self, zone: hand,
  if: {cmp: [{count: {zone: shield, owner: you}},
  "<=", 2]}, mod: {cost: -5}} を足し、unsupported を
  外したもの。登録形は提出形と完全一致〔source 以外の
  全フィールドを照合〕、abilities は2件ちょうど、
  keywords は [double_breaker] のまま、evolve_from
  も保持）。
- 補完あり: abilities のみ（革命２の static 1件。
  text は partial の時点で公式全文で補完なし）。
- alias 畳み込み0件（alias dmr19-009 は独自行が
  無く、登録エントリの source.aliases にのみ入る。
  正本判定は通常型で対象 id と alias を real /
  real_akashic / real_vocab / real_zone / proto /
  converted と照合し登録なし〔proto のヒットは
  T1228 の notes 内参照のみ〕、identity 実測で
  canon は両方向とも dmex06-033）。
- stale クリーンアップ0件・差し戻し1件
  （reopen〔revolution_2〕の出力は2件: 対象＋
  dm26sd1-o004 理想と平和の決断。dm26sd1-o004 は
  呪文で革命２が S・トリガー付与形＋モード選択の
  複合＝形が異なるため登録しない。差し戻しの
  実測上の注意: submit の原文照合は load_rows の
  canonical_rows で同名カードの正本行だけを通す
  ため、非正本行の dm26sd1-o004 は submit に
  「取得済みの原文に無いID」と弾かれて戻せない。
  元の rejects 行をそのまま復元し、行全体が
  HEAD と完全一致〔バイト単位〕することを照合
  済み。revolution_2 は完全解消しない〔残り1件〕）。
- converted 10,417→10,418 / rejects 1,894→1,893、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ（第387弾で
  観察）・distinct_type_count の count_spec 未同期
  （第405弾で観察）は本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは第438弾
本体と同形（対象を proto T1228 から登録カードに
差し替えたもの）で、tests.conftest は import しない
（第319弾以降の作法）。判別役は既存 proto を流用:
T001（自然バニラ＝進化元・マナからの出場先）/
T428（自然コスト3＝cost_le 判別役）/ T828（自然
コスト6・能力なし＝進化フィルタ判別役）。
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
from tests.test_vocab_pilot438_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot438 import FULL_TEXT, STATIC, TRIG  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex06-033"
ALIAS = "dmr19-009"
OTHER = "dm26sd1-o004"
GAP = "revolution_2"


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


def test_round472_disposition():
    rej = _reject_rows()
    assert len(rej) == 1893
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10418
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == [OTHER]                # 残り1件（完全解消しない）
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    # 差し戻された行は gaps / partial を保ったまま残る
    other = rej[OTHER]
    assert other["gaps"] == [GAP] and other["reason"] == "vocab"
    needs = [u["need"] for u in
             (other["partial"].get("source") or {}).get("unsupported")
             or []]
    assert needs == [GAP]
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 2      # abilities は2件ちょうど
    assert c["abilities"][0] == TRIG
    assert c["abilities"][1] == STATIC
    assert c["text"] == FULL_TEXT        # 公式全文
    assert c["keywords"] == ["double_breaker"]
    assert c["evolve_from"] == {"types": ["creature"],
                                "civs": ["nature"]}
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]  # alias は source.aliases のみ
    d = parse_card(c, TABLES)
    assert d.types == ["creature", "evolution"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第438弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _cid(e, defn, player, zone):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == player)


def _drive(e, want=None, limit=400, seen=None):
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if seen is not None:
            seen.append((d["kind"], d.get("player"), list(keys),
                         [o.get("cid") for o in d["options"]]))
        if want is not None:
            k = want(d["kind"], keys, d)
            if k is not None:
                e.answer([keys.index(k)])
                continue
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return e


def _pay_cost(rules, p0_shields, p1_shields):
    e = scenario.build(rules, {
        "p0": {"hand": [TARGET], "shield": p0_shields},
        "p1": {"shield": p1_shields},
        "filler": "T002", "seed": 1, "deck_size": 20})
    cid = _cid(e, TARGET, 0, "hand")
    return e.chars_ro(cid)["pay_cost"]


def test_revolution_cost_by_shield_count(rules):
    """登録カード: 自分のシールド2つ以下で召喚コスト -5
    （6→1）、3つ以上では軽減なし。相手のシールド数は無関係。"""
    two = ["T002", "T001"]
    three = ["T002", "T001", "T001"]
    five = ["T002", "T001", "T001", "T001", "T001"]
    assert _pay_cost(rules, two, five) == 1      # 境界: ちょうど2つ
    assert _pay_cost(rules, ["T002"], five) == 1  # 1つでも成立
    assert _pay_cost(rules, three, []) == 6       # 3つでは不成立
    assert _pay_cost(rules, five, []) == 6        # 相手0でも不成立


def test_revolution_summon_with_one_mana(rules):
    """登録カード: シールド2つなら1マナで進化召喚できる。
    シールド3つではマナ5枚でも play が提示されない。"""
    def want(kind, keys, d):
        if kind == "main" and d.get("player") == 0 \
                and f"play:{TARGET}" in keys:
            return f"play:{TARGET}"
        if kind == "choose_cards" and d.get("player") == 0:
            base = [o.get("key") for o in d["options"]
                    if o.get("cid") is not None
                    and e.s.cards[o["cid"]].defn == "T001"
                    and e.s.cards[o["cid"]].zone == "bz"]
            if base:
                return base[0]
        return None

    e = scenario.build(rules, {
        "p0": {"bz": ["T001"], "hand": [TARGET], "mana": ["T001"],
               "shield": ["T002", "T001"]},
        "p1": {"shield": ["T002", "T001"]},
        "filler": "T002", "seed": 1, "deck_size": 20})
    hand = _cid(e, TARGET, 0, "hand")
    for _ in range(400):
        if e.s.cards[hand].zone == "bz":
            break
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        k = want(d["kind"], keys, d)
        if k is not None:
            e.answer([keys.index(k)])
        elif d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.cards[hand].zone == "bz"
    mana = _cid(e, "T001", 0, "mana")
    assert e.s.cards[mana].tapped  # 支払った1マナはタップ状態

    seen2 = []
    e = scenario.build(rules, {
        "p0": {"bz": ["T001"], "hand": [TARGET],
               "mana": ["T001", "T001", "T001", "T001", "T001"],
               "shield": ["T002", "T001", "T001"]},
        "p1": {"shield": ["T002", "T001"]},
        "filler": "T002", "seed": 1, "deck_size": 20})
    _drive(e, want, limit=120, seen=seen2)
    mains = [ks for kind, pl, ks, _c in seen2
             if kind == "main" and pl == 0]
    assert mains, "自分のメインが一度も来なかった"
    assert all(f"play:{TARGET}" not in ks for ks in mains)
    assert e.s.cards[_cid(e, TARGET, 0, "hand")].zone == "hand"


def _watcher_build(rules, p0_mana, p1_hand, p1_mana):
    return scenario.build(rules, {
        "p0": {"bz": [TARGET], "mana": p0_mana,
               "shield": ["T002", "T001"]},
        "p1": {"hand": p1_hand, "mana": p1_mana,
               "shield": ["T002", "T001"]},
        "filler": "T002", "seed": 1, "deck_size": 20})


def _play_and_watch(e, play_key, may_answer="yes", pick_defn=None):
    state = {"played": False, "yes_no": False, "offers": []}

    def want(kind, keys, d):
        if kind == "main" and d.get("player") == 1 \
                and play_key in keys and not state["played"]:
            state["played"] = True
            return play_key
        if kind == "yes_no" and d.get("player") == 0:
            state["yes_no"] = True
            return may_answer if may_answer in keys else None
        if kind == "choose_cards" and d.get("player") == 0:
            cids = [o.get("cid") for o in d["options"]
                    if o.get("cid") is not None]
            state["offers"].append(cids)
            if pick_defn is not None:
                hit = [o.get("key") for o in d["options"]
                       if o.get("cid") is not None
                       and e.s.cards[o["cid"]].defn == pick_defn
                       and e.s.cards[o["cid"]].zone == "mana"]
                if hit:
                    return hit[0]
        return None

    _drive(e, want, limit=300)
    return state


def test_watcher_puts_creature_from_mana(rules):
    """登録カード: 相手のクリーチャー（コスト3）が出た時、
    コスト以下の自然クリーチャーをマナから出せる
    （境界: コスト3ちょうどの T428 を選ぶ）。"""
    e = _watcher_build(rules, ["T001", "T428"], ["T004"],
                       ["T004", "T001", "T001"])
    st = _play_and_watch(e, "play:T004", pick_defn="T428")
    assert st["played"] and st["yes_no"]
    assert e.s.cards[_cid(e, "T428", 0, "bz")].zone == "bz"
    assert e.s.cards[_cid(e, "T001", 0, "mana")].zone == "mana"


def test_watcher_cost_le_discrimination(rules):
    """出たクリーチャーのコストが2なら、コスト3の T428 は
    選択肢に出ない（cost_le: {cost_of: entered} の判別）。"""
    e = _watcher_build(rules, ["T001", "T428"], ["T001"],
                       ["T001", "T001"])
    st = _play_and_watch(e, "play:T001", pick_defn="T001")
    assert st["played"] and st["yes_no"]
    offered = [e.s.cards[c].defn for offer in st["offers"] for c in offer]
    assert "T428" not in offered
    assert e.s.cards[_cid(e, "T001", 0, "bz")].zone == "bz"
    assert e.s.cards[_cid(e, "T428", 0, "mana")].zone == "mana"


def test_watcher_evolution_filter_discrimination(rules):
    """コスト6のクリーチャーが出ても、進化クリーチャー
    （登録カード自身）は evolution: false で選択肢に出ない。"""
    e = _watcher_build(rules, [TARGET, "T001"], ["T828"],
                       ["T001"] * 6)
    st = _play_and_watch(e, "play:T828", pick_defn="T001")
    assert st["played"] and st["yes_no"]
    offered = [e.s.cards[c].defn for offer in st["offers"] for c in offer]
    assert TARGET not in offered
    assert e.s.cards[_cid(e, "T001", 0, "bz")].zone == "bz"
    assert e.s.cards[_cid(e, TARGET, 0, "mana")].zone == "mana"


def test_watcher_may_decline(rules):
    """may を辞退すればマナのクリーチャーは出ない。"""
    e = _watcher_build(rules, ["T001", "T428"], ["T004"],
                       ["T004", "T001", "T001"])
    st = _play_and_watch(e, "play:T004", may_answer="no")
    assert st["played"] and st["yes_no"]
    assert e.s.cards[_cid(e, "T001", 0, "mana")].zone == "mana"
    assert e.s.cards[_cid(e, "T428", 0, "mana")].zone == "mana"


def test_watcher_own_entry_no_trigger(rules):
    """自分のクリーチャーが出ても誘発しない
    （subject owner: opp の判別）。"""
    e = scenario.build(rules, {
        "p0": {"bz": [TARGET], "hand": ["T001"],
               "mana": ["T428", "T001", "T001"],
               "shield": ["T002", "T001"]},
        "p1": {"shield": ["T002", "T001"]},
        "filler": "T002", "seed": 1, "deck_size": 20})
    seen = []

    def want(kind, keys, d):
        if kind == "main" and d.get("player") == 0 \
                and "play:T001" in keys:
            return "play:T001"
        return None

    _drive(e, want, limit=200, seen=seen)
    assert e.s.cards[_cid(e, "T001", 0, "bz")].zone == "bz"
    t428 = _cid(e, "T428", 0, "mana")
    offered = [c for kind, pl, _ks, cids in seen
               if kind == "choose_cards" and pl == 0
               for c in cids if c is not None]
    assert t428 not in offered
    assert e.s.cards[t428].zone == "mana"
