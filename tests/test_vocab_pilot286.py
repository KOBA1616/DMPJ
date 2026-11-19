"""語彙パイロット第286弾: choose_restriction（相手は可能ならこのクリーチャーを選ぶ）。

ギャップ名のドリフト: 中核の mod `must_be_chosen` は第199弾で実装済み
（セレクタの候補計算で、選ぶ側と別のコントローラーの候補の中に
must_be_chosen を持つクリーチャーがいれば、そのコントローラーの他の
クリーチャーを候補から外す。このクリーチャー自身が候補にいない効果では
制限しない）。4件の partial はいずれも「選択を強制する語彙が無い」と
書いているが、それは第199弾より前の評価の名残。本弾は新語彙・エンジン
変更なしのイディオム弾として、残る3形を実挙動で固定する:

- 形A（T820、dmr18-054 の形）: マナ武装条件つき常在型
  {kind: static, affects: self, if: {cmp: [水マナ数, ">=", 3]},
   mod: {must_be_chosen: true}}。条件が満たない時は制限しない。
  括弧書き「自分の他のクリーチャーを攻撃またはブロックしてもよい」は、
  攻撃対象・ブロックの決定がセレクタの候補計算を通らないため
  自動的に満たされることも確認する。
- 形B（T821、dmrp06-029 の形）: 出た時の誘発で modify により
  そのターンだけ must_be_chosen を付与する
  {op: modify, select: {ref: self}, mod: {must_be_chosen: true},
   duration: end_of_turn}。modify の継続的効果は chars に集約され、
  セレクタの制限が効く。ターンが回ると切れる。実挙動は、出たターンに
  自分の攻撃で割った相手の S・トリガー（T006）が、相手の対象選択を
  T821 に強制する形で確認する（制限は candidates() ではなく
  select の決定経路で効くため、候補関数の直接呼び出しでは観測できない）。
- 形C（dm26rp2-033 / dm26ex3-088）: T498（第199弾）の無条件常在型
  そのまま。実カードの提出形 parse は cards テストで確認する。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T820", "T821")

FORM_A = {"kind": "static", "affects": "self",
          "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                                    "filter": {"civs": ["water"]}}}, ">=", 3]},
          "mod": {"must_be_chosen": True}}

FORM_B = {"kind": "trigger",
          "when": {"event": "move", "to": "bz", "subject": "self"},
          "effect": [{"op": "modify", "select": {"ref": "self"},
                      "mod": {"must_be_chosen": True},
                      "duration": "end_of_turn"}]}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)
    assert parse_card(_proto_card("T820"), TABLES).abilities == [FORM_A]
    assert parse_card(_proto_card("T821"), TABLES).abilities == [FORM_B]


def _in_gy(e, defn, player=0):
    return any(e.s.cards[c].defn == defn for c in e.zlist("graveyard", player))


def _in_bz(e, defn, player=0):
    return any(e.s.cards[c].defn == defn and e.s.cards[c].controller == player
               for c in e.zlist("bz", player))


def _cast(e, caster, spell, target=None, limit=200):
    """caster が spell を唱える。target は (defn, controller) で選ぶ対象。
    戻り値: 対象選択で提示されたキー一覧 or None（候補が1体に絞られ
    自動解決された場合）。"""
    offered = None
    started = False
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not started and d["kind"] == "main" and d.get("player") == caster \
                and f"play:{spell}" in keys:
            started = True
            e.answer([keys.index(f"play:{spell}")])
            continue
        if started:
            if d["kind"] == "choose_cards" and offered is None:
                offered = list(keys)
                ans = None
                if target is not None:
                    for i, o in enumerate(d["options"]):
                        c = e.s.cards[o["cid"]]
                        if e.cdef(o["cid"]).id == target[0] \
                                and c.controller == target[1]:
                            ans = [i]
                            break
                e.answer(ans if ans is not None else list(range(d["min"])))
                continue
            if d["kind"] in ("attack", "charge"):
                break
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return offered


# ---------- 形A: 条件つき常在型 ----------

def test_form_a_restricts_when_armed(rules):
    """水マナ3枚以上で武装: 相手の単体破壊は T820 に自動で決まる。"""
    e = setup(rules, {"bz": ["T820", "T001"], "mana": ["T010"] * 3},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    offered = _cast(e, 1, "T056")
    assert offered is None                    # 候補が1体に絞られ自動解決
    assert _in_gy(e, "T820")
    assert _in_bz(e, "T001")


def test_form_a_inactive_below_three_water(rules):
    """水マナ2枚では武装せず、相手は自由に選べる（対照）。"""
    e = setup(rules, {"bz": ["T820", "T001"],
                      "mana": ["T010", "T010", "T001"]},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    offered = _cast(e, 1, "T056", target=("T001", 0))
    assert offered is not None
    assert any("T820" in k for k in offered) and any("T001" in k for k in offered)
    assert _in_gy(e, "T001")
    assert _in_bz(e, "T820")


def _p1_attack_options(e, p0_attackers):
    """P0 が指定した獣でプレイヤーを攻撃し（全てタップさせる）、
    P1 の最初の攻撃決定の選択肢キーを返す（第285弾 cards と同じ型）。"""
    queue = list(p0_attackers)
    for _ in range(600):
        if e.s.result is not None:
            raise AssertionError("game ended before P1 attack decision")
        d = e.advance()
        if d is None:
            raise AssertionError("no decision before P1 attack decision")
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "attack":
            if e.s.turn >= 2:
                return keys
            pick = None
            for i, k in enumerate(keys):
                if queue and k.startswith(f"attack:{queue[0]}:"):
                    pick = i
                    queue.pop(0)
                    break
            if pick is not None:
                e.answer([pick])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if kind in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif kind == "choose_breaker":
            e.answer([max(range(len(keys)),
                          key=lambda i: int(keys[i].split(":")[1]))])
        elif kind == "choose_shields":
            e.answer(list(range(d.get("min", 0))))
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif kind == "order_pending":
            e.answer([0])
        elif kind == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


def test_form_a_attack_targets_exempt(rules):
    """括弧書き: 武装中でも自分の他のクリーチャーを攻撃できる
    （攻撃対象の決定はセレクタの候補計算を通らない）。"""
    e = setup(rules, {"bz": ["T820", "T001"], "mana": ["T010"] * 3},
              {"bz": ["T034"], "mana": ["T001"] * 3}, filler="T002")
    keys = _p1_attack_options(e, ["T820", "T001"])
    assert "attack:T034:T001" in keys         # タップした味方は対象になる
    assert "attack:T034:T820" in keys         # 本人も通常どおり対象になる


def _block_options(e, limit=600):
    """P1 の T001 がプレイヤーを攻撃するまで進め、P0 のブロック決定の
    選択肢キーを返す。"""
    for _ in range(limit):
        if e.s.result is not None:
            raise AssertionError("game ended before block decision")
        d = e.advance()
        if d is None:
            raise AssertionError("no decision before block decision")
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "block":
            return keys
        if d["kind"] == "attack" and d.get("player") == 1 \
                and "attack:T001:player" in keys:
            e.answer([keys.index("attack:T001:player")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("limit reached")


def test_form_a_block_exempt(rules):
    """括弧書き: 武装中でも自分の他のクリーチャーでブロックできる。"""
    e = setup(rules, {"bz": ["T820", "T004"], "mana": ["T010"] * 3},
              {"bz": ["T001"], "mana": ["T001"] * 3}, filler="T002")
    keys = _block_options(e)
    assert any("T004" in k for k in keys)


# ---------- 形B: 出た時にそのターンだけ付与 ----------

def _cid_of(e, defn, controller=0):
    for c in e.zlist("bz", controller):
        card = e.s.cards[c]
        if card.controller == controller and e.cdef(c).id == defn:
            return c
    raise AssertionError(defn)


def _summon_821(e, limit=300):
    """P0 が手札から T821 を召喚し、解決直後の決定（攻撃ステップ）で止める。
    メインステップは単発で、召喚後に次のメイン決定は来ない（次の自分の
    ターンまで来ない）ため、支払い以外の最初の決定で止めるのが
    「出たターン」の観測点になる。"""
    played = False
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T821" in keys:
            played = True
            e.answer([keys.index("play:T821")])
            continue
        if played and d["kind"] != "pay_mana":
            return
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("summon did not resolve")


def test_form_b_grants_on_entry_turn_only(rules):
    """出たターンだけ chars に must_be_chosen が立つ。ターンが回ると
    付与は切れる。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T821"], "mana": ["T001"] * 4},
              {"bz": ["T001"]}, filler="T002")
    _summon_821(e)
    cid = _cid_of(e, "T821")
    assert e.chars(cid)["must_be_chosen"] is True
    for _ in range(300):
        if e.s.turn >= 2:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.turn >= 2
    assert e.chars(cid)["must_be_chosen"] is False


def test_form_b_no_grant_when_placed(rules):
    """対照: setup で直接置いた場合は出た時誘発が無いので制限しない。"""
    e = setup(rules, {"bz": ["T821", "T001"]}, {"bz": ["T001"]}, filler="T002")
    assert e.chars(_cid_of(e, "T821"))["must_be_chosen"] is False


def _strigger_scenario(e, summon, limit=600):
    """P0 が（summon なら T821 を召喚してから）T001 でプレイヤーを攻撃し、
    P1 のシールド（全て T006）を割る。P1 が S・トリガーを宣言して唱え、
    対象選択が提示されたらそのキー一覧を返す（自動解決なら None）。
    対照側の選択では T001 を選ぶ。"""
    played = not summon
    attacked = False
    declared = False
    offered = None
    for _ in range(limit):
        if declared and _in_gy(e, "T006", 1):
            return offered
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and d.get("player") == 0 and not played:
            played = True
            if "play:T821" in keys:
                e.answer([keys.index("play:T821")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if kind == "pay_mana":
            e.answer([0])
            continue
        if kind == "attack" and d.get("player") == 0 and not attacked:
            attacked = True
            if "attack:T001:player" in keys:
                e.answer([keys.index("attack:T001:player")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if kind == "choose_shields":
            e.answer(list(range(d.get("min", 0))))
            continue
        if kind == "declare_strigger":
            hit = None
            for i, o in enumerate(d["options"]):
                if (o.get("cid") is not None and e.cdef(o["cid"]).id == "T006") \
                        or "T006" in o["key"]:
                    hit = i
                    break
            if hit is not None:
                declared = True
                e.answer([hit])
            else:
                e.answer([])
            continue
        if kind == "choose_cards" and declared and offered is None:
            offered = list(keys)
            ans = None
            for i, o in enumerate(d["options"]):
                if o.get("cid") is not None \
                        and e.cdef(o["cid"]).id == "T001" \
                        and e.s.cards[o["cid"]].controller == 0:
                    ans = [i]
                    break
            e.answer(ans if ans is not None else list(range(d["min"])))
            continue
        if kind == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("S-trigger scenario did not finish")


def test_form_b_restricts_opponent_strigger_choice(rules):
    """出たターン: 自分の攻撃で割った相手の S・トリガー（T006）の
    対象選択は T821 に自動で決まり、攻撃した T001 は無事。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T821"], "mana": ["T001"] * 4},
              {"shield": ["T006"] * 5}, filler="T002")
    offered = _strigger_scenario(e, summon=True)
    assert offered is None                    # 候補が1体に絞られ自動解決
    assert _in_gy(e, "T821")
    assert _in_bz(e, "T001")


def test_form_b_strigger_choice_free_without_entry(rules):
    """対照: T821 がいなければ S・トリガーの対象は自由に選べる。"""
    e = setup(rules, {"bz": ["T001", "T010"]},
              {"shield": ["T006"] * 5}, filler="T002")
    offered = _strigger_scenario(e, summon=False)
    assert offered is not None
    assert any("T001" in k for k in offered) and any("T010" in k for k in offered)
    assert _in_gy(e, "T001")                  # ドライバが選んだ対象
    assert _in_bz(e, "T010")
