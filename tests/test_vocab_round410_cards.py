"""再変換ラウンド410（第375弾 metamorph）の記録テスト。

- 新規登録1件: dm14-018 サルベージ・クラスター
  （登録形は提出形と完全一致: partial の組立て済み
  部分〔keywords [unblockable]＋破壊置換〕に第375弾の
  確立形の条件 if {cmp: [{count: {zone: mana, owner:
  you}}, ">=", 7]} を足し、unsupported を外したもの。
  abilities は条件つき置換1件ちょうどで、無条件形の
  混入なし。text は partial の時点で公式全文と一致
  するため補完なし）。
- 第375弾で見つかった登録ブロッカー（rule_convert.
  split が破壊置換を無条件形で所有し merge_split が
  完全一致でしか dedupe しない）は、変換ツール改修
  ステージ（コミット 964746b、(a) split にメタモーフ
  条件を伝える改修）で解消済み。submit 前に split/
  merge を実測し、merge 結果が条件つき置換1件
  ちょうどになることを目視で確認した。
- alias 畳み込み0件（alias 自体が無い）。正本判定:
  対象 id を real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / proto.yaml /
  converted.yaml と照合し、いずれにも登録なし
  （proto.yaml のヒットは T1123 の notes 内参照のみ）。
  identity 実測で canon(dm14-018) = dm14-018
  （対象 id が正本）、aliases_for = []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [metamorph] のため reopen で
  外してから submit（reopen の出力は対象1件ちょうど）。
- converted 10,354→10,355 / rejects 1,958→1,957、
  canonical 重なり0・漏れ0。metamorph はファミリーが
  この1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債
  （無条件形＋条件つき形の二重付き）は判断待ちのため
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第375弾本体の薄い包み（対象 T1123 を登録カードに
差し替えたもの）で、tests.conftest は import しない
（第319弾以降の作法）。判別役は既存 proto を流用
（T1105=パワー4000ブロッカー / T001=マナ役）。
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
TARGET = "dm14-018"
GAP = "metamorph"

UNCONDITIONAL = {"kind": "replace",
                 "when": {"event": "move", "from": "bz", "to": "graveyard",
                          "reason": "destroy", "subject": "self"},
                 "instead": [{"op": "move", "select": {"ref": "self"},
                              "to": "hand", "reason": "return"}]}
REPLACE = dict(UNCONDITIONAL,
               **{"if": {"cmp": [{"count": {"zone": "mana", "owner": "you"}},
                                 ">=", 7]}})
FORM = [REPLACE]
FULL_TEXT = ("このクリーチャーは、ブロックされない。\n"
             "メタモーフ(自分のマナゾーンに７枚以上カードがあれば、"
             "このクリーチャーは次の能力を得る)\n"
             "このクリーチャーが破壊される時、墓地に置くかわりに"
             "自分の手札に戻す。")


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


def test_round410_disposition():
    rej = _reject_rows()
    assert len(rej) == 1957
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10355
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0（aliases 欄）
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: 条件つき置換1件ちょうど、
    # 無条件形（改修前の split が所有していた形）の混入なし
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert UNCONDITIONAL not in c["abilities"]
    assert c["keywords"] == ["unblockable"]
    assert c["text"] == FULL_TEXT        # text の補完はなし
    assert c["name"] == "サルベージ・クラスター"
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 5 and c["power"] == 3000 and c["mana"] == 1
    assert c["races"] == ["サイバー・クラスター"]
    d = parse_card(c, TABLES)
    assert REPLACE in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行・既存データ負債には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]
    dm14_073 = _conv_cache.find(CONVERTED, "dm14-073")
    assert dm14_073 is not None and len(dm14_073["abilities"]) == 2


# ---------- 実挙動ドライバ（第375弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_attack(e, attacker, block_with=None):
    """p1 の attacker でプレイヤーを攻撃する。第375弾の作法。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if block_with and k.startswith(f"bz:{block_with}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def _drive_destroyed_in_battle(e, target=TARGET, hunter="T1105"):
    """target（p1）はブロックされないため、破壊経路は
    「プレイヤーを攻撃してタップした後、相手の hunter に
    クリーチャー攻撃される」形にする（第375弾の作法）。"""
    state = {"charged": False, "hunted": False, "hunt_turn": None,
             "replace_offered": False}
    for _ in range(1500):
        if state["hunted"] and e.s.turn >= state["hunt_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == 1:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{target}:player"]
            if hit and not state["charged"]:
                state["charged"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "attack" and d.get("player") == 0:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{hunter}:{target}"]
            if hit and state["charged"] and not state["hunted"]:
                state["hunted"] = True
                state["hunt_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_replacement":
            state["replace_offered"] = True
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"replace:{target}:")]
            assert hit, keys
            e.answer([hit[0]])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_registered_destroy_returns_to_hand_with_seven_mana(rules):
    """登録カード: 自分のマナが7枚あれば、バトルに負けて
    破壊される代わりに手札に戻る（墓地には行かない）。"""
    e = _build(rules, {"bz": ["T1105"]},
               {"bz": [TARGET], "mana": ["T001"] * 7})
    st = _drive_destroyed_in_battle(e)
    assert st["charged"] and st["hunted"]
    assert TARGET in _defns(e, "hand", 1)
    assert TARGET not in _defns(e, "graveyard", 1)
    assert TARGET not in _defns(e, "bz", 1)
    assert "T1105" in _defns(e, "bz", 0)


def test_registered_destroy_goes_to_graveyard_with_six_mana(rules):
    """登録カード: 対照として、自分のマナが6枚では
    メタモーフ条件が外れ、置換は適用されず、そのまま
    破壊され墓地に行く（無条件形が混入していれば
    ここで手札に戻ってしまう）。"""
    e = _build(rules, {"bz": ["T1105"]},
               {"bz": [TARGET], "mana": ["T001"] * 6})
    st = _drive_destroyed_in_battle(e)
    assert st["charged"] and st["hunted"] and not st["replace_offered"]
    assert TARGET in _defns(e, "graveyard", 1)
    assert TARGET not in _defns(e, "hand", 1)
    assert "T1105" in _defns(e, "bz", 0)


def test_registered_unblockable_cannot_be_blocked(rules):
    """登録カード: ブロックされないため、ブロッカーが
    いてもプレイヤー攻撃が通りシールドが1枚ブレイク
    される。"""
    e = _build(rules, {"bz": ["T1105"]}, {"bz": [TARGET]})
    before = len(e.zlist("shield", 0))
    st = _drive_attack(e, TARGET, block_with="T1105")
    assert st["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1
    assert TARGET in _defns(e, "bz", 1)
    assert "T1105" in _defns(e, "bz", 0)
