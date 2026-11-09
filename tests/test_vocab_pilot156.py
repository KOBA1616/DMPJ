"""leave_under_untap（離れた時、その下にあったクリーチャーをアンタップする）。

設計ノート: pilot155-leave-under-untap-design.md（ファイル名の「第155弾」は
リンク成立（link_establish_event）と重複しているため、ツリー内では第156弾として実装する）。

- 拡張は2点だけ: (1) move レコードへの `under` スナップショット（離れる直前の under のうち
  最初のクリーチャー1体の ref。再構築で下が場に残る分岐＝スター進化／card_only の時だけ載せる）、
  (2) セレクタ `ref: event.under` の受理（`event.top` と同じ単一 ref の経路）。
- 解決時に `under_of: self` では届かない（離脱で under が消える。§2.3 の回帰ガードを兼ねて
  X213 で対照する）。
- proto T213（T058 と同型のスター進化＋離脱時アンタップ誘発）。対照は誘発を持たない T058。
- 下のカードは T214（cannot_untap 持ちの火クリーチャー）を使う: 再構築で引き継いだ
  タップ状態が次のターン開始のアンタップで消えてしまうと、誘発でアンタップされたのか
  自然にアンタップしたのか判別できないため（設計ノートは T005 流用としていたが、
  観測可能性のために変更。untap イベント自体は untap_at_start の禁止では止まらない）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()

X_CARDS = """
cards:
  - id: X213
    name: 離脱アンタップ対照龍
    types: [creature, evolution]
    civs: [fire]
    cost: 6
    power: 7000
    races: [テスト]
    keywords: [double_breaker]
    star: true
    evolve_from: {civs: [fire]}
    text: スター進化。このクリーチャーが離れた時、under_of で下にあったクリーチャーをアンタップしようとする（届かない対照）。
    abilities:
      - kind: trigger
        when: {event: move, from: bz, subject: self}
        effect:
          - {op: untap, select: {under_of: self}}
"""


@pytest.fixture(scope="session")
def xr(tmp_path_factory):
    p = tmp_path_factory.mktemp("pilot156x") / "x_cards.yaml"
    p.write_text(X_CARDS, encoding="utf-8")
    return load_rules(card_yaml_files() + [p])


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _by_defn(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.cdef(c).id == defn)


def _play_star(e, top_id, base_id="T214"):
    """base_id を出し、その上に top_id をスター進化させて出す。top の cid を返す。"""
    for _ in range(40):
        tops = [c for c in e.bz_tops(0) if e.s.cards[c].defn == top_id]
        if tops:
            return tops[0]
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and f"play:{base_id}" in keys:
            e.answer([keys.index(f"play:{base_id}")])
        elif d["kind"] == "main" and f"play:{top_id}" in keys:
            e.answer([keys.index(f"play:{top_id}")])
        elif d["kind"] == "choose_evo_source":
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"bz:{base_id}"))])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("スター進化クリーチャーが出なかった")


def _finish_with_spell(e, spell_id, target_defn, done, max_steps=200):
    """相手（p1）が spell_id を唱えるまで進め、done() になるまで回す。

    対象選択は候補が対象1体だけになる局面で使うため、通常の回答（先頭から min 個）で足りる。"""
    cast = {"done": False}
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast["done"] and d["kind"] == "main" and d["player"] == 1 and f"play:{spell_id}" in keys:
            e.answer([keys.index(f"play:{spell_id}")])
            cast["done"] = True
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return done()


def _tap_then_remove(e, top_id, finisher):
    """top_id をスター進化で出し、相手の T024 でタップさせ、finisher（T056 破壊／T140 バウンス）で離す。

    戻り値: (top_cid, base_cid)。離脱の誘発が解決し終わった時点で返す。"""
    top = _play_star(e, top_id)
    base = _by_defn(e, "bz", 0, "T214")
    assert e.s.cards[top].under == [base]
    ok = _finish_with_spell(e, "T024", top_id, lambda: e.s.cards[top].tapped)
    assert ok and e.s.cards[top].tapped
    if finisher == "T056":
        ok = _finish_with_spell(e, "T056", top_id, lambda: e.s.cards[top].zone == "graveyard")
    else:
        ok = _finish_with_spell(e, "T140", top_id, lambda: e.s.cards[top].zone == "hand")
    assert ok
    # 誘発の解決まで進める（待機効果はチェックポイントで解決される）。
    # pending が空になった時点で止める: 次の自分のターンのはじめまで進めると、
    # 通常のアンタップステップで下のカードがアンタップされてしまい判別できない
    for _ in range(80):
        if not e.s.pending:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return top, base


P1 = {"hand": ["T024", "T056", "T140"], "mana": ["T009", "T008", "T008", "T008", "T008"]}


def test_proto_parse():
    c = parse_card(_proto_card("T213"), TABLES)
    trig = [a for a in c.abilities if a["kind"] == "trigger"]
    assert trig and trig[0]["when"] == {"event": "move", "from": "bz", "subject": "self"}
    assert trig[0]["effect"] == [{"op": "untap", "select": {"ref": "event.under"}}]


def test_leave_untap_on_destroy(rules):
    """(1) タップした T213 が破壊で離れると、下の T214 がアンタップされる。"""
    e = setup(rules, {"hand": ["T214", "T213"], "mana": ["T005"] * 9}, dict(P1))
    top, base = _tap_then_remove(e, "T213", "T056")
    assert e.s.cards[top].zone == "graveyard"
    assert e.s.cards[base].zone == "bz" and base in e.bz_tops(0)
    assert e.s.cards[base].tapped is False


def test_leave_untap_control_no_trigger(rules):
    """(2) 対照: 誘発の無い T058 では、下の T214 はタップしたまま残る（801.4d の引き継ぎ）。"""
    e = setup(rules, {"hand": ["T214", "T058"], "mana": ["T005"] * 9}, dict(P1))
    top, base = _tap_then_remove(e, "T058", "T056")
    assert e.s.cards[top].zone == "graveyard"
    assert e.s.cards[base].zone == "bz"
    assert e.s.cards[base].tapped is True


def test_leave_untap_on_return(rules):
    """(3) 手札に戻して離す場合でもアンタップされる（行き先を問わない）。"""
    e = setup(rules, {"hand": ["T214", "T213"], "mana": ["T005"] * 9}, dict(P1))
    top, base = _tap_then_remove(e, "T213", "T140")
    assert e.s.cards[top].zone == "hand"
    assert e.s.cards[base].zone == "bz"
    assert e.s.cards[base].tapped is False


def test_leave_untap_under_of_cannot_reach(xr):
    """(5) 対照: 解決時に under_of: self で指す形では届かない（スナップショットが要る理由）。"""
    e = setup(xr, {"hand": ["T214", "X213"], "mana": ["T005"] * 9}, dict(P1))
    top, base = _tap_then_remove(e, "X213", "T056")
    assert e.s.cards[top].zone == "graveyard"
    assert e.s.cards[base].zone == "bz"
    assert e.s.cards[base].tapped is True   # under_of は離脱後に空なので、アンタップされない
    assert e.s.cards[top].under == []


def test_leave_untap_no_under(rules):
    """(4) 下にクリーチャーが無いスター進化が離れても、エラーにならず効果は空振りする。"""
    e = setup(rules, {"bz": ["T213"]}, {"hand": ["T056"], "mana": ["T008"] * 3})
    top = _by_defn(e, "bz", 0, "T213")
    ok = _finish_with_spell(e, "T056", "T213", lambda: e.s.cards[top].zone == "graveyard")
    assert ok
    assert e.s.cards[top].under == []
    for _ in range(30):   # 誘発の空振り後もゲームが進む
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
