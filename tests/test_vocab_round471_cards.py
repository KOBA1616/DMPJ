"""再変換ラウンド471（第437弾 shield_faceup_trigger）の記録テスト。

- 新規登録1件: dmd11-006 大焔団 フォルクス
  （提出形は partial〔骨格: クリーチャー / 火 / コスト7 /
  パワー7000 / 種族 アウトレイジMAX、mana 1、keywords
  [speed_attacker, double_breaker]、text は公式全文〕に
  第437弾の確立形 ability 1件〔trigger {when:
  {event: move, from: shield, reason: break, subject:
  {owner: you}, face_up: true}, effect: [destroy
  {select: {zone: bz, owner: opp, filter: {types:
  [creature], power_le: 6000}, count: 1}}]}〕を足し、
  unsupported を外したもの。登録形は提出形と完全一致
  〔source 以外の全フィールドを照合〕、abilities は
  trigger 1件ちょうど、text は公式全文）。
- 補完あり: abilities のみ（partial に ability が
  未構築。text は partial の時点で公式全文）。
- alias 畳み込み0件（alias 無し。正本判定は通常型で
  対象 id を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1227 の notes 内参照のみ〕、
  identity 実測で canon_id は対象自身、
  aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔shield_faceup_trigger〕の出力は対象1件
  ちょうど）。
- converted 10,416→10,417 / rejects 1,895→1,894、
  canonical 重なり0・漏れ0。shield_faceup_trigger は
  完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ（第387弾で
  観察）・distinct_type_count の count_spec 未同期
  （第405弾で観察）は本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは第437弾
本体と同形（対象を proto T1227 から登録カードに
差し替えたもの）で、tests.conftest は import しない
（第319弾以降の作法）。判別役は既存 proto を流用:
T001（パワー2000＝破壊対象になる攻撃役）/ T004
（選ばなかった側）/ T1225（パワー9000＝power_le:
6000 の対象外）/ T061（シールド回収呪文＝reason:
return の非ブレイク離脱）。
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
from tests.test_vocab_pilot437_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot437 import FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmd11-006"
GAP = "shield_faceup_trigger"


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


def test_round471_disposition():
    rej = _reject_rows()
    assert len(rej) == 1894
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10417
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # shield_faceup_trigger 完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 1      # abilities は trigger 1件ちょうど
    assert c["abilities"][0]["kind"] == "trigger"
    assert c["abilities"][0]["when"] == {
        "event": "move", "from": "shield", "reason": "break",
        "subject": {"owner": "you"}, "face_up": True}
    assert c["text"] == FULL_TEXT        # 公式全文
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    assert d.types == ["creature"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第437弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _cid(e, defn, player, zone):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn)


def _make_face_up(e, defn, player=0):
    cid = _cid(e, defn, player, "shield")
    e.s.cards[cid].face_up = True
    return cid


def _attack_break(e, attacker_defn, break_cid):
    """p1 の attacker_defn でプレイヤーを攻撃し、break_cid の
    シールドをブレイクする。破壊対象の選択肢が出たら
    攻撃役自身（p1 の T001）を選ぶ。"""
    state = {"destroy_offered": False}

    def want(kind, keys, d):
        if kind == "attack" and d.get("player") == 1 \
                and f"attack:{attacker_defn}:player" in keys:
            return f"attack:{attacker_defn}:player"
        if kind == "choose_breaker":
            return max(keys, key=lambda k: int(k.split(":")[1]))
        if kind == "choose_cards":
            hit = [o.get("key") for o in d["options"]
                   if o.get("cid") is not None
                   and e.s.cards[o["cid"]].controller == 1
                   and e.s.cards[o["cid"]].defn == "T001"]
            if hit:
                state["destroy_offered"] = True
                return hit[0]
        return None

    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "choose_shields":
            hit = [i for i, o in enumerate(d["options"])
                   if o.get("cid") == break_cid]
            rest = [i for i in range(len(keys)) if i not in hit]
            e.answer((hit + rest)[:d["min"]])
            continue
        k = want(d["kind"], keys, d)
        if k:
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
    return state


def test_faceup_shield_break_destroys_attacker(rules):
    """登録カード: 表向きシールドがブレイクされた時、攻撃役
    （パワー2000）を破壊する。選ばなかった T004 は残る。"""
    e = scenario.build(rules, {
        "p0": {"bz": [TARGET], "shield": ["T002", "T001", "T001"]},
        "p1": {"bz": ["T001", "T004"]},
        "filler": "T002"})
    up = _make_face_up(e, "T002", 0)
    atk = _cid(e, "T001", 1, "bz")
    other = _cid(e, "T004", 1, "bz")
    state = _attack_break(e, "T001", up)
    assert state["destroy_offered"], "破壊対象の選択が提示されなかった"
    assert e.s.cards[atk].zone == "graveyard"
    assert e.s.cards[other].zone == "bz"
    assert e.s.cards[up].zone == "hand"
    assert e.s.cards[_cid(e, TARGET, 0, "bz")].zone == "bz"


def test_facedown_shield_break_no_trigger(rules):
    """裏向きシールドのブレイクでは誘発しない（攻撃役は残る）。"""
    e = scenario.build(rules, {
        "p0": {"bz": [TARGET], "shield": ["T002", "T001", "T001"]},
        "p1": {"bz": ["T001"]},
        "filler": "T002"})
    down = _cid(e, "T002", 0, "shield")
    assert e.s.cards[down].face_up is False
    atk = _cid(e, "T001", 1, "bz")
    state = _attack_break(e, "T001", down)
    assert not state["destroy_offered"]
    assert e.s.cards[atk].zone == "bz"
    assert e.s.cards[down].zone == "hand"


def test_faceup_shield_returned_no_trigger(rules):
    """表向きシールドが効果で手札に戻る（reason: return）では誘発しない。"""
    e = scenario.build(rules, {
        "p0": {"bz": [TARGET], "hand": ["T061"], "mana": ["T001"],
               "shield": ["T002", "T001", "T001"]},
        "p1": {"bz": ["T001"]},
        "filler": "T002"})
    up = _make_face_up(e, "T002", 0)
    atk = _cid(e, "T001", 1, "bz")
    # シールド選択肢の key はすべて 'shield' で重複するため index で答える
    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "main" and "play:T061" in keys:
            e.answer([keys.index("play:T061")])
            continue
        if d["kind"] == "choose_cards":
            hit = [i for i, o in enumerate(d["options"])
                   if o.get("cid") == up]
            e.answer(hit[:1] if hit else list(range(d["min"])))
            continue
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.cards[up].zone == "hand"  # 回収された
    assert e.s.cards[atk].zone == "bz"   # 破壊されていない


def test_opponent_faceup_shield_break_no_trigger(rules):
    """相手の表向きシールドをブレイクしても誘発しない（subject owner: you）。"""
    e = scenario.build(rules, {
        "p0": {"bz": [TARGET, "T001"]},
        "p1": {"bz": ["T001"], "shield": ["T002", "T001", "T001"]},
        "filler": "T002"})
    up = _make_face_up(e, "T002", 1)
    theirs = _cid(e, "T001", 1, "bz")

    def want(kind, keys, d):
        if kind == "attack" and d.get("player") == 0 \
                and "attack:T001:player" in keys:
            return "attack:T001:player"
        return None

    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "choose_shields":
            hit = [i for i, o in enumerate(d["options"])
                   if o.get("cid") == up]
            rest = [i for i in range(len(keys)) if i not in hit]
            e.answer((hit + rest)[:d["min"]])
            continue
        k = want(d["kind"], keys, d)
        if k:
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
    assert e.s.cards[up].zone == "hand"      # ブレイク自体は成立
    assert e.s.cards[theirs].zone == "bz"    # 誘発せず相手クリーチャーは残る


def test_power_over_6000_not_destroyed(rules):
    """パワー9000の攻撃役は power_le: 6000 の対象外（誘発しても破壊できない）。"""
    e = scenario.build(rules, {
        "p0": {"bz": [TARGET], "shield": ["T002", "T001", "T001"]},
        "p1": {"bz": ["T1225"]},
        "filler": "T002"})
    up = _make_face_up(e, "T002", 0)
    big = _cid(e, "T1225", 1, "bz")
    _attack_break(e, "T1225", up)
    assert e.s.cards[up].zone == "hand"   # ブレイクは成立
    assert e.s.cards[big].zone == "bz"    # 対象外なので残る


def test_no_source_no_trigger(rules):
    """発生源が場に無ければ、表向きシールドがブレイクされても何も起きない。"""
    e = scenario.build(rules, {
        "p0": {"shield": ["T002", "T001", "T001"]},
        "p1": {"bz": ["T001"]},
        "filler": "T002"})
    up = _make_face_up(e, "T002", 0)
    atk = _cid(e, "T001", 1, "bz")
    state = _attack_break(e, "T001", up)
    assert not state["destroy_offered"]
    assert e.s.cards[atk].zone == "bz"
    assert e.s.cards[up].zone == "hand"
