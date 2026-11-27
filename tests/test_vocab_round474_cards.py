"""再変換ラウンド474（第440弾 bottom_deck_mill）の記録テスト。

- 新規登録1件: dmx13-010 真実の名 ハデスギル・スキル
  （提出形は partial〔骨格: クリーチャー / ゼロ /
  コスト8 / パワー8000 / 種族 ドラゴン・ゾンビ/
  アンノウン、mana 1、keywords [double_breaker]、
  text 公式全文〕に第440弾の確立形 abilities 2件
  〔(1) trigger {when: {event: move, to: bz,
  subject: self}, effect: [may [move {select:
  {zone: deck, owner: you, from_bottom: 5},
  to: graveyard, reason: put}]]}、(2) trigger
  {when: {event: move, from: bz, to: graveyard,
  reason: destroy, subject: self}, effect:
  [may [play_free {select: {zone: graveyard,
  owner: you, filter: {types: [creature],
  colorless: true, evolution: false, not_name:
  真実の名 ハデスギル・スキル}, count: 1}}]]}〕を
  足し、unsupported を外したもの。登録形は提出形と
  完全一致〔source 以外の全フィールドを照合〕、
  abilities は trigger 2件ちょうど、keywords は
  [double_breaker] のまま、text は公式全文）。
- 補完あり: abilities（trigger 2件とも。text・
  keywords の補完は無い）。
- alias 畳み込み0件（alias 無し。正本判定は通常型で
  対象 id を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1230 の notes 内参照のみ〕、
  identity 実測で canon_id は対象自身、
  aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔bottom_deck_mill〕の出力は対象1件
  ちょうど＝巻き込みなし。bottom_deck_mill は
  完全解消）。
- converted 10,419→10,420 / rejects 1,892→1,891、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ
  （第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。
- submit 時に play_free への注意行（reason: summon
  の言い回し）が出たが警告表示のみで登録は合格。
  「墓地からバトルゾーンに出してもよい」の
  play_free 受けは登録済み dmd19-006 の先例どおり。

実挙動は登録カード自身で固定する。ドライバは
第440弾本体と同形（対象を proto T1230 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T423（ゼロ・非進化＝復活先の
正例）/ T001（有色）/ T1229（進化）/ T056（相手の
破壊呪文）/ T140（相手のバウンス呪文）。
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
from tests.test_vocab_pilot440_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot440 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmx13-010"
GAP = "bottom_deck_mill"


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


def test_round474_disposition():
    rej = _reject_rows()
    assert len(rej) == 1891
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10420
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 2      # abilities は trigger 2件ちょうど
    assert [a["kind"] for a in c["abilities"]] == ["trigger", "trigger"]
    assert c["abilities"] == FORM
    assert c["text"] == FULL_TEXT        # 公式全文
    assert c["keywords"] == ["double_breaker"]
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    assert d.types == ["creature"]
    for a in FORM:
        assert a in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第440弾本体と同形、対象は登録カード） ----------

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


def _cid(e, defn, player, zone):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == player)


def _deck(e, player=0):
    return list(e.s.zones["deck"][player])


def _summon_target(rules, deck_ids, answer_yes):
    """登録カードを手札から召喚し、CIP の may に answer_yes で
    答える。戻り値: (engine, 召喚時点の山札スナップ, may が
    提示されたか)。観測点は次の相手ターンのチャージ。"""
    e = scenario.build(rules, {
        "p0": {"hand": [TARGET], "mana": ["T423"] * 8,
               "deck": deck_ids},
        "p1": {},
        "filler": "T002", "seed": 1, "deck_size": 20,
        "deck_exact": [True, False]})
    snap = []
    state = {"played": False, "may_seen": False}

    def on_dec(e, d):
        keys = _keys(d)
        if not state["played"] and d["kind"] == "main" \
                and d.get("player") == 0 \
                and f"play:{TARGET}" in keys:
            state["played"] = True
            snap.append(_deck(e, 0))
            e.answer([keys.index(f"play:{TARGET}")])
            return "ok"
        if state["played"] and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        if state["played"] and d["kind"] == "yes_no" \
                and d.get("player") == 0:
            state["may_seen"] = True
            e.answer([keys.index("yes" if answer_yes else "no")])
            return "ok"
        if state["played"] and d["kind"] == "charge" \
                and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, on_dec)
    assert state["played"], "登録カードを召喚できなかった"
    return e, snap[0], state["may_seen"]


def test_mill_bottom_five(rules):
    """yes: 山札の下5枚が墓地に落ち、残りの並びは不変。"""
    e, snap, may_seen = _summon_target(
        rules, ["T827", "T003", "T828", "T827", "T003",
                "T828", "T827"], answer_yes=True)
    assert may_seen
    bottom5, rest = snap[-5:], snap[:-5]
    gy = list(e.s.zones["graveyard"][0])
    assert sorted(gy) == sorted(bottom5)
    assert _deck(e, 0) == rest


def test_mill_decline(rules):
    """no: 山札はそのまま、墓地は空のまま。"""
    e, snap, may_seen = _summon_target(
        rules, ["T827", "T003", "T828", "T827", "T003",
                "T828", "T827"], answer_yes=False)
    assert may_seen
    assert _deck(e, 0) == snap
    assert list(e.s.zones["graveyard"][0]) == []


def _destroy_target(rules, spell, mana, answer_yes):
    """相手が spell（T056 破壊 / T140 バウンス）で場の
    登録カードを対象にする。戻り値: (engine, may が提示
    されたか, 復活選択の options の defn リスト or None)。
    観測点は解決後の自分ターンのチャージ。"""
    e = scenario.build(rules, {
        "p0": {"bz": [TARGET],
               "graveyard": ["T423", "T001", "T1229", TARGET]},
        "p1": {"hand": [spell], "mana": mana},
        "filler": "T002", "seed": 1, "deck_size": 20})
    state = {"cast": False, "may_seen": False, "pick": None}

    def on_dec(e, d):
        keys = _keys(d)
        if not state["cast"] and d["kind"] == "main" \
                and d.get("player") == 1 \
                and f"play:{spell}" in keys:
            state["cast"] = True
            e.answer([keys.index(f"play:{spell}")])
            return "ok"
        if state["cast"] and d["kind"] == "pay_mana" \
                and d.get("player") == 1:
            e.answer([0])
            return "ok"
        if state["cast"] and d["kind"] == "choose_cards" \
                and d.get("player") == 1:
            tgt = [o for o in d["options"]
                   if o.get("cid") is not None
                   and e.cdef(o["cid"]).id == TARGET
                   and e.s.cards[o["cid"]].zone == "bz"]
            if tgt:
                e.answer([d["options"].index(tgt[0])])
                return "ok"
        if state["cast"] and d["kind"] == "yes_no" \
                and d.get("player") == 0:
            state["may_seen"] = True
            e.answer([keys.index("yes" if answer_yes else "no")])
            return "ok"
        if state["cast"] and d["kind"] == "choose_cards" \
                and d.get("player") == 0:
            state["pick"] = [e.cdef(o["cid"]).id
                             for o in d["options"]
                             if o.get("cid") is not None]
            e.answer([0])
            return "ok"
        if state["cast"] and d["kind"] == "charge" \
                and d.get("player") == 0:
            return "stop"
        return None

    _drive(e, on_dec)
    assert state["cast"], f"{spell} を唱えられなかった"
    return e, state["may_seen"], state["pick"]


def test_destroy_revives_colorless(rules):
    """破壊された時、墓地のゼロ・非進化・同名以外
    （T423 だけが候補）をバトルゾーンに出せる。"""
    e, may_seen, pick = _destroy_target(
        rules, "T056", ["T082"] * 3, answer_yes=True)
    assert may_seen
    # 候補は T423 のみ。候補が1体だけだと選択決定は
    # 自動化されて提示されない（第437弾の実測）ため、
    # 提示された場合だけ一致を見る
    assert pick in (None, ["T423"])
    t423 = _cid(e, "T423", 0, "bz")
    assert e.s.cards[t423].controller == 0
    # 破壊された本体は墓地にいる
    assert any(e.cdef(c).id == TARGET
               for c in e.zlist("graveyard", 0))
    # 落ちた候補は墓地に残る
    gy_defns = sorted(e.cdef(c).id
                      for c in e.zlist("graveyard", 0))
    assert gy_defns == ["T001", "T1229", TARGET, TARGET]


def test_destroy_decline(rules):
    """may を断れば何も出ない。"""
    e, may_seen, pick = _destroy_target(
        rules, "T056", ["T082"] * 3, answer_yes=False)
    assert may_seen
    assert pick is None
    assert not any(e.cdef(c).id == "T423"
                   for c in e.zlist("bz", 0))
    assert any(e.cdef(c).id == "T423"
               for c in e.zlist("graveyard", 0))


def test_bounce_does_not_trigger(rules):
    """バウンス（reason: destroy でない）では誘発しない。"""
    e, may_seen, pick = _destroy_target(
        rules, "T140", ["T009"] * 3, answer_yes=True)
    assert not may_seen
    assert pick is None
    # 本体は手札に戻り、墓地の候補は動かない
    assert any(e.cdef(c).id == TARGET
               for c in e.zlist("hand", 0))
    assert any(e.cdef(c).id == "T423"
               for c in e.zlist("graveyard", 0))
