"""語彙パイロット第311弾: reveal_and_cast_free（表向きにして好きなだけ唱える）。

対象は dm17-s04 ネオウェーブ・カタストロフィー 1件のみ
（gaps = [evolution_cross_gear, reveal_and_cast_free]。
evolution_cross_gear は第304弾で実装済みで、これが同ギャップの
最後の併記行）。第310弾で「第267弾の輪廻虹災形とほぼ同型の
ドリフト候補」と評価されていた。

結論: **ドリフト**（新規語彙・エンジン変更なし）。残余の条項
「これをクロスしたクリーチャーが攻撃する時、自分の山札の上から
３枚を表向きにする。その中から、「S・トリガー」付き呪文を
好きなだけ選び、コストを支払わずに唱えてもよい。その後、
唱えなかったカードを自分の山札の一番下に好きな順番で戻す」は
既存部品で完全構成できた:

- 誘発点 = {event: attack, subject: crossed}（cross_gear_effect
  イディオム。ギア側の攻撃誘発）
- 表向き = choose {from_top: 3, look: true, count: all,
  reveal: true, as: pile}（第267弾 輪廻虹災 T740 形）
- 「好きなだけ選び」 = choose {ref: pile, filter: {types: [spell],
  keyword: s_trigger}, count: all, up_to: true, as: casts}
  （count: all ＋ up_to: true は selectors の any_n 形＝0〜全部。
  keyword フィルタは定義の keywords を見るので S・トリガー呪文
  だけが候補になる）
- 「唱える」 = repeat {over: casts, as: it, body: [play_free
  {select: {ref: it}}]}（第233弾の repeat over）
- 残り = move {ref: pile, zone: deck, count: all, to: deck,
  position: bottom, order: choose, reason: put}（T740 形。
  唱えたカードは山札を離れているので残りだけが戻る）

ブロッカー付与は partial の常在型 {affects: crossed, mod:
{grant: [blocker]}}、進化は第304弾の civs 形
（types [cross_gear, evolution] ＋ evolve_from {civs:
[light, water]}）。

proto: T958（dm17-s04 型）/ T959（光ギア＝進化元）/
T960（S・トリガー光呪文: マナ全アンタップ）/ T961（S・トリガー
水呪文: 同効果）/ T962（S・トリガーを持たない対照呪文）。
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402
from tests.conftest import setup  # noqa: E402

TABLES = load_tables()
IDS = ("T958", "T959", "T960", "T961", "T962")
GEAR = "T958"
HOST = "T001"
MANA10 = ["T030"] * 5 + ["T010"] * 5
# 山札 spec は末尾が一番上: 上から T960 / T962 / T961
DECK_PILE = ["T002"] * 6 + ["T961", "T962", "T960"]
OPP = {}


def _rules():
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _cid(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn
                and (zone != "bz" or e.s.cards[c].controller == p))


def _fixture(deck=DECK_PILE, bz=("T959", "T001")):
    return setup(_rules(), {"bz": list(bz), "hand": [GEAR], "mana": MANA10,
                            "deck": deck}, OPP)


def _run(e, casts=None, order=None, cross=True, attacker=HOST, limit=600):
    """ギアを出し（任意でクロスし）attacker でプレイヤーを攻撃し、
    誘発を解決し切って相手の最初の決定まで進める。
    casts: 唱える呪文の defn 列（提示順）。order: 山札の下へ戻す順序。
    戻り値: 観測した決定 kind の列。"""
    st = {"played": False, "crossed": False, "attacked": False}
    kinds = []
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kinds.append(d["kind"])
        keys = [o["key"] for o in d["options"]]
        p = d["player"]
        if st["attacked"] and p == 1:
            return kinds
        if d["kind"] == "main" and p == 0:
            if not st["played"] and f"play:{GEAR}" in keys:
                e.answer([keys.index(f"play:{GEAR}")])
                st["played"] = True
                continue
            if cross and st["played"] and not st["crossed"]:
                ck = [k for k in keys if k.startswith(f"cross:{GEAR}:")]
                if ck:
                    e.answer([keys.index(ck[0])])
                    st["crossed"] = True
                    continue
        if d["kind"] == "choose_evo_source":
            idx = next(i for i, o in enumerate(d["options"])
                       if e.s.cards[o["cid"]].defn == "T959")
            e.answer([idx])
            continue
        if d["kind"] == "pay_mana":
            if not st.get("pay1"):
                # 1回目の支払いは水に寄せ、クロス（もう一度5マナ）の
                # ために光マナを残す
                st["pay1"] = True
                idx = max(range(len(d["options"])),
                          key=lambda i: d["options"][i]["key"].count("T010"))
                e.answer([idx])
            else:
                e.answer([0])
            continue
        if d["kind"] in ("attack", "declare_attack") and p == 0 \
                and (st["crossed"] or not cross) and not st["attacked"]:
            ak = f"attack:{attacker}:player"
            if ak in keys:
                e.answer([keys.index(ak)])
                st["attacked"] = True
                continue
        if d["kind"] == "choose_cards":
            want = list(casts or [])
            ans = []
            for dn in want:
                ans += [i for i, o in enumerate(d["options"])
                        if e.s.cards[o["cid"]].defn == dn]
            e.answer(ans)
            continue
        if d["kind"] == "order_cards":
            want = list(order or [])
            used = set()
            ans = []
            for dn in want:
                idx = next(i for i, o in enumerate(d["options"])
                           if i not in used
                           and e.s.cards[o["cid"]].defn == dn)
                used.add(idx)
                ans.append(idx)
            e.answer(ans)
            continue
        if d["kind"] == "choose_shields":
            e.answer([0])
            continue
        if d["kind"] in ("block", "declare_block") and "no_block" in keys:
            e.answer([keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
            continue
        e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


# ---- parse ----

def test_protos_parse():
    for cid in IDS:
        parse_card(proto_card(cid), TABLES)
    d = parse_card(proto_card(GEAR), TABLES)
    assert d.types == ["cross_gear", "evolution"]
    assert d.evolve_from == {"civs": ["light", "water"]}
    trig = [a for a in d.abilities if a["kind"] == "trigger"]
    assert len(trig) == 1
    assert trig[0]["when"] == {"event": "attack", "subject": "crossed"}


# ---- 進化元プール（civs 形、第304弾の再確認） ----

def test_pool_gate_civs_form():
    mana = ["T030", "T010", "T002", "T002", "T002"]
    # クリーチャーはギアの進化元にならない（文明が合っていても）
    e = setup(_rules(), {"bz": ["T030"], "hand": [GEAR], "mana": mana}, OPP)
    cid = _cid(e, "hand", 0, GEAR)
    assert e._evo_sources(cid, 0, None) == []
    # 文明の合わないギア（自然）は進化元にならない
    e = setup(_rules(), {"bz": ["T062"], "hand": [GEAR], "mana": mana}, OPP)
    cid = _cid(e, "hand", 0, GEAR)
    assert e._evo_sources(cid, 0, None) == []
    # 光ギアがあれば出せる
    e = setup(_rules(), {"bz": ["T959"], "hand": [GEAR], "mana": mana}, OPP)
    cid = _cid(e, "hand", 0, GEAR)
    assert e._evo_sources(cid, 0, None) == [_cid(e, "bz", 0, "T959")]


# ---- 攻撃誘発の実挙動 ----

def test_cast_both_strigger_spells():
    """上3枚 [ST光, 通常火, ST水] から ST 呪文2枚とも唱える。"""
    e = _fixture()
    _run(e, casts=["T960", "T961"])
    # 唱えた2枚は墓地へ、唱えなかった通常呪文は山札の一番下へ
    assert sorted(_defns(e, "graveyard", 0)) == ["T960", "T961"]
    deck = _defns(e, "deck", 0)
    assert deck[-1] == "T962"
    assert "T962" not in _defns(e, "hand", 0)
    # 表向きにした記録が3枚分ある
    reveals = [r for r in e.s.pub if r["kind"] == "reveal"]
    assert len(reveals) == 3
    # 呪文の効果（マナ全アンタップ）が解けている: 支払った10枚が戻っている
    assert not [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    # クロスした宿主はブロッカーを得ている
    host = _cid(e, "bz", 0, HOST)
    assert "blocker" in e.chars_ro(host)["keywords"]


def test_cast_one_with_order():
    """1枚だけ唱え、残り2枚は指定した順で山札の下へ。"""
    e = _fixture()
    _run(e, casts=["T961"], order=["T962", "T960"])
    assert _defns(e, "graveyard", 0) == ["T961"]
    deck = _defns(e, "deck", 0)
    assert deck[-2:] == ["T962", "T960"]   # 指定順の最後が一番下


def test_cast_none():
    """1枚も唱えなければ3枚とも指定順で山札の下へ。"""
    e = _fixture()
    _run(e, casts=[], order=["T961", "T962", "T960"])
    assert _defns(e, "graveyard", 0) == []
    deck = _defns(e, "deck", 0)
    assert deck[-3:] == ["T961", "T962", "T960"]


def test_no_strigger_in_pile():
    """束に S・トリガー呪文が無ければ唱える選択自体が出ない。"""
    deck = ["T002"] * 6 + ["T002", "T002", "T962"]   # 上から T962/T002/T002
    e = _fixture(deck=deck)
    kinds = _run(e, casts=[], order=["T962", "T002", "T002"])
    assert "choose_cards" not in kinds
    assert _defns(e, "graveyard", 0) == []
    deck_after = _defns(e, "deck", 0)
    assert deck_after[-3:] == ["T962", "T002", "T002"]


def test_no_trigger_when_not_crossed():
    """ギアをクロスしていなければ攻撃しても誘発しない。"""
    e = _fixture()
    _run(e, cross=False)
    assert _defns(e, "deck", 0)[:3] == ["T960", "T962", "T961"]
    assert _defns(e, "graveyard", 0) == []
    assert not [r for r in e.s.pub if r["kind"] == "reveal"]


def test_no_trigger_when_other_creature_attacks():
    """クロス先でないクリーチャーの攻撃では誘発しない。"""
    e = _fixture(bz=("T959", "T001", "T007"))
    _run(e, attacker="T007")
    assert _defns(e, "deck", 0)[:3] == ["T960", "T962", "T961"]
    assert _defns(e, "graveyard", 0) == []
    assert not [r for r in e.s.pub if r["kind"] == "reveal"]
