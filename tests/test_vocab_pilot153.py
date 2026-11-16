"""語彙パイロット第153弾: kizuna_plus（キズナプラス）。

- キーワード `kizuna_plus`（keywords.yaml）: 攻撃時誘発（when: attack、subject: self、
  「下のカード1枚以上」の if つき）。may の body で下のカード1枚を墓地に置き（支払い）、
  自分の[P]と他のクリーチャー1体の[P]を使う。
- op `use_partner` に引数 of: self／exclude_self: true（候補の絞り込み）と pending: true を追加。
  pending の時は選んだ[P]をその場で解決せず待機中の効果として登録する。
- 2つの[P]は支払いの時点でそれぞれ確定した独立の待機効果になり、解決順は使う側が
  好きな順番で選べる（総合ルール 603.3a／605.1。公式裏取り faq-check-kizuna-20261109）。
  発生源が解決前に離れても不発にならない（110.5a）。
- 他の[P]持ちがいなくても、支払いだけ行って自分の[P]だけ使える（101.3／605.2b）。
  誘発の if は「下のカード1枚以上」のみで、他の[P]の存在条件は付けない。
- 引数なしの use_partner（素のキズナ、第44弾）の挙動は変えない。
- proto T196（キズナプラス＋[P]）／T197（[P]のみ）。進化元は既存の T001 を流用。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


X_CARDS = """
cards:
  - id: X196
    name: 絆破壊試獣
    civs: [darkness]
    cost: 4
    power: 4000
    types: [creature]
    races: [テスト]
    text: "[P]クリーチャーを1体破壊する。"
    abilities:
      - kind: partner
        effect:
          - {op: move, select: {zone: bz, owner: any, filter: {types: [creature]}, count: 1}, to: graveyard, reason: destroy}
"""


@pytest.fixture(scope="session")
def xr(tmp_path_factory):
    p = tmp_path_factory.mktemp("pilot153x") / "x_cards.yaml"
    p.write_text(X_CARDS, encoding="utf-8")
    return load_rules(card_yaml_files() + [p])


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _cid(e, defn, player=0):
    return next(c for c in e.bz_tops(player) if e.cdef(c).id == defn)


def _answer(e, d, st):
    keys = [o["key"] for o in d["options"]]
    k = d["kind"]
    if k == "main" and st.get("play_key") in keys and not st.get("played"):
        st["played"] = True
        e.answer([keys.index(st["play_key"])])
    elif k == "choose_evo_source":
        hit = [i for i, o in enumerate(d["options"]) if o["key"].startswith(st.get("evo_pick", ""))]
        e.answer([hit[0] if hit else 0])
    elif k == "pay_mana":
        e.answer(list(range(d["min"])))
    elif k == "attack" and st.get("attack_key") in keys and not st.get("attacked"):
        st["attacked"] = True
        e.answer([keys.index(st["attack_key"])])
    elif k == "yes_no":
        e.answer([keys.index("yes" if st.get("pay", True) else "no")])
    elif k == "use_partner" and st.get("partner_pick"):
        hit = [i for i, o in enumerate(d["options"]) if o["key"].startswith("partner:" + st["partner_pick"])]
        e.answer([hit[0] if hit else 0])
    elif k == "order_pending" and st.get("order_pick"):
        hit = [i for i, o in enumerate(d["options"]) if st["order_pick"] in o["key"]]
        e.answer([hit[0] if hit else 0])
    elif k == "choose_cards" and st.get("destroy_defn"):
        tgt = _cid(e, st["destroy_defn"])
        hit = [i for i, o in enumerate(d["options"]) if o.get("cid") == tgt]
        e.answer([hit[0] if hit else 0])
    elif k in ("declare_strigger", "declare_sback"):
        e.answer([])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _drive(e, st, stop=None, record=None, maxn=400):
    for _ in range(maxn):
        if stop and stop(e):
            return
        d = e.advance()
        if d is None:
            return
        if record is not None:
            record.append(d)
        _answer(e, d, st)


def _attack_done(e):
    """相手のターンに入ったら攻撃の一連の処理は終わっている。"""
    return e.s.turn >= 2


# ---------- parse / 検証 ----------

def test_proto_parse():
    t196 = parse_card(_proto_card("T196"), TABLES)
    trig = next(a for a in t196.abilities if a.get("keyword") == "kizuna_plus")
    assert trig["kind"] == "trigger"
    assert trig["when"] == {"event": "attack", "subject": "self"}
    assert trig["if"] == {"cmp": [{"count": {"under_of": "self"}}, ">=", 1]}
    body = trig["effect"][0]["body"]
    assert body[0] == {"op": "move", "select": {"under_of": "self", "count": 1},
                       "to": "graveyard", "reason": "put"}
    assert body[1] == {"op": "use_partner", "of": "self", "pending": True}
    assert body[2] == {"op": "use_partner", "exclude_self": True, "pending": True}
    partner = next(a for a in t196.abilities if a["kind"] == "partner")
    assert partner["effect"] == [{"op": "draw", "count": 1}]
    t197 = parse_card(_proto_card("T197"), TABLES)
    assert [a["kind"] for a in t197.abilities] == ["partner"]


def test_keyword_kizuna_unchanged(rr):
    """素のキズナの展開（第44弾）は従来どおり（引数なし use_partner のまま）。"""
    t123 = next(c for c in rr.cards.values() if c.id == "T123")
    trig = next(a for a in t123.abilities if a["kind"] == "trigger")
    assert trig["effect"] == [{"op": "use_partner"}]


# ---------- 実挙動 ----------

def test_both_partners_used_and_attack_continues(rr):
    """重ねた T196 が攻撃し、支払うと自分の[P]（1ドロー）と T197 の[P]（2ドロー）が
    どちらも使われ、下のカードは墓地へ、攻撃クリーチャーは場に残って攻撃が解決する。"""
    e = setup(rr, {"bz": ["T001", "T197"], "hand": ["T196"], "mana": ["T001"] * 5},
              {"shield": ["T001"] * 5})
    rec = []
    st = {"play_key": "play:T196:neo", "evo_pick": "bz:T001", "attack_key": "attack:T196:player"}
    _drive(e, st, stop=_attack_done, record=rec)
    assert [e.cdef(c).id for c in e.zlist("graveyard", 0)] == ["T001"]   # 支払いで下のカードが墓地へ
    assert len(e.zlist("hand", 0)) == 3                                  # 1ドロー＋2ドロー
    assert e.cdef(_cid(e, "T196")).id == "T196"                          # 攻撃クリーチャーは場に残る
    assert len(e.zlist("shield", 1)) == 4                                # 攻撃は通常どおりブレイクした
    # どちらのスロットも候補が1つだけなので、use_partner の選択は出ない
    assert not any(d["kind"] == "use_partner" for d in rec)


def test_decline_payment(rr):
    """may を断ると下のカードは残り、[P]はどちらも使われない。"""
    e = setup(rr, {"bz": ["T001", "T197"], "hand": ["T196"], "mana": ["T001"] * 5},
              {"shield": ["T001"] * 5})
    st = {"play_key": "play:T196:neo", "evo_pick": "bz:T001", "attack_key": "attack:T196:player",
          "pay": False}
    _drive(e, st, stop=_attack_done)
    assert len(e.zlist("hand", 0)) == 0
    assert e.zlist("graveyard", 0) == []
    assert len(e.s.cards[_cid(e, "T196")].under) == 1   # 下のカードは残っている
    assert len(e.zlist("shield", 1)) == 4                # 攻撃自体は解決する


def test_no_under_no_prompt(rr):
    """重ねずに通常召喚した T196 は下のカードが無いので、攻撃しても提示されない。"""
    e = setup(rr, {"hand": ["T196"], "mana": ["T001"] * 5}, {"shield": ["T001"] * 5})
    rec = []
    st = {"play_key": "play:T196", "attack_key": "attack:T196:player"}
    _drive(e, st, stop=lambda e: st.get("attacked") and len(e.zlist("shield", 1)) == 4, record=rec)
    assert st.get("attacked") is True
    assert not any(d["kind"] == "yes_no" for d in rec)   # 支払いの提示自体が出ない
    assert e.zlist("graveyard", 0) == []


def test_only_own_partner_without_other(rr):
    """他の[P]持ちがいなくても、支払いだけ行って自分の[P]だけ使うことができる（101.3）。"""
    e = setup(rr, {"bz": ["T001"], "hand": ["T196"], "mana": ["T001"] * 5},
              {"shield": ["T001"] * 5})
    st = {"play_key": "play:T196:neo", "evo_pick": "bz:T001", "attack_key": "attack:T196:player"}
    _drive(e, st, stop=_attack_done)
    assert len(e.zlist("hand", 0)) == 1   # 自分の[P]の1ドローだけ
    assert [e.cdef(c).id for c in e.zlist("graveyard", 0)] == ["T001"]


def test_choose_among_multiple_others(rr):
    """他の[P]持ちが複数いれば選択が出て、選んだ方の[P]だけが使われる。
    自分自身は「他の」候補に出ない（exclude_self）。"""
    e = setup(rr, {"bz": ["T001", "T124", "T197"], "hand": ["T196"], "mana": ["T001"] * 5},
              {"shield": ["T001"] * 5})
    rec = []
    st = {"play_key": "play:T196:neo", "evo_pick": "bz:T001", "attack_key": "attack:T196:player",
          "partner_pick": "T197"}
    _drive(e, st, stop=_attack_done, record=rec)
    ups = [d for d in rec if d["kind"] == "use_partner"]
    assert len(ups) == 1
    keys = [o["key"] for o in ups[0]["options"]]
    assert len(keys) == 2
    assert {k.split(":")[1] for k in keys} == {"T124", "T197"}
    assert not any("T196" in k for k in keys)
    assert len(e.zlist("hand", 0)) == 3   # 自分の1ドロー＋選んだ T197 の2ドロー（T124 の分は無い）


def _destroy_setup(xr):
    return setup(xr, {"bz": ["T001", "X196"], "hand": ["T196"], "mana": ["T001"] * 5},
                 {"shield": ["T001"] * 5})


def test_order_other_first_and_source_leaves(xr):
    """順序選択の判別テスト（603.3a）: 相手の[P]（破壊）を先に解決して発生源の
    T196 を破壊しても、待機中の自分の[P]は不発にならず解決する。"""
    e = _destroy_setup(xr)
    snap = {}

    def hook_stop(e):
        return "T196" in [e.cdef(c).id for c in e.zlist("graveyard", 0)] and len(e.zlist("hand", 0)) == 1

    rec = []
    st = {"play_key": "play:T196:neo", "evo_pick": "bz:T001", "attack_key": "attack:T196:player",
          "order_pick": "X196", "destroy_defn": "T196"}
    for _ in range(400):
        if hook_stop(e):
            break
        d = e.advance()
        if d is None:
            break
        rec.append(d)
        if d["kind"] == "choose_cards" and st.get("destroy_defn"):
            snap["hand_at_destroy"] = len(e.zlist("hand", 0))   # 破壊の選択時点ではまだ引いていない
        _answer(e, d, st)
    orders = [d for d in rec if d["kind"] == "order_pending"]
    assert len(orders) == 1
    assert len(orders[0]["options"]) == 2                        # 2つの[P]が待機効果として並ぶ
    assert snap["hand_at_destroy"] == 0                          # X196 の[P]が先に解決した
    assert "T196" in [e.cdef(c).id for c in e.zlist("graveyard", 0)]
    assert len(e.zlist("hand", 0)) == 1                          # 発生源が離れた後も自分の[P]が解決した


def test_order_own_first(xr):
    """逆順では自分の[P]（ドロー）が先に解決し、その後に破壊が解決する。"""
    e = _destroy_setup(xr)
    snap = {}
    st = {"play_key": "play:T196:neo", "evo_pick": "bz:T001", "attack_key": "attack:T196:player",
          "order_pick": "T196", "destroy_defn": "T196"}
    for _ in range(400):
        if "T196" in [e.cdef(c).id for c in e.zlist("graveyard", 0)]:
            break
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "choose_cards" and st.get("destroy_defn"):
            snap["hand_at_destroy"] = len(e.zlist("hand", 0))
        _answer(e, d, st)
    assert snap["hand_at_destroy"] == 1   # 破壊の選択が出た時点でドロー済み＝自分の[P]が先
    assert "T196" in [e.cdef(c).id for c in e.zlist("graveyard", 0)]
