"""語彙パイロット第176弾: g_castle（G城）。

「G城は実行したら、表向きでシールド化される。このカードが表向きで自分の
シールドゾーンを離れる時、かわりに墓地に置く」— G城はカードの「種類」。

- 型印 `g_castle`（defs CARD_TYPES。第174弾の dream_creature と同型）。
  「自分のシールドゾーンにある城」は filter {types: [g_castle]} で指す。
- 実行: 面が g_castle なら通常の実行がシールド化になる。turn.h_play の
  to_shield 分岐（ギャラクシールドと同型）へ `d.is_castle()` で振り分ける
  ので、play_task を作る全経路（メイン・S・トリガー・無償実行）で同じ。
  実行アクションは "generate"（タマシード等と同じ「実行」）。
- 型ルール「表向きで離れる時、かわりに墓地に置く」は、シールド・ゴー
  （keywords.yaml）の2つ目の置換と同型の replace 能力として、types に
  g_castle を含む面すべてに _load_face で自動で付く（データ側に書かない）。
  `zone: shield` + `when: {event: move, from: shield, subject: self}` +
  `if: {face_up: true}` + instead で墓地へ。置換の諮問は既存の _replacement
  がシールドゾーンのカードも走査するため、そのまま働く。
- 離れる時のレコード: events._apply_one が、シールドを表向きで離れた時も
  レコードに face_up: true を載せる（従来は表向きで置く時だけ）。これで
  「表向きで置かれた時または離れた時」誘発を when の face_up で書ける。
  既存の when face_up はすべて to: shield の置く時誘発なので挙動は変わらない。
- シールドゾーンの能力の書き方（シールド・ゴーの流儀）: 静的・非移動誘発は
  `zone: shield` + `if: {face_up: true}`、置く時／離れる時誘発は
  `zone: shield` + when の face_up: true。裏向きでシールド化された G城に
  能力は働かない。
- proto T388（静的コスト軽減・dm26ex4-085型）/ T389（置かれた時ドロー・
  dm26rp1-023型）/ T390（置かれた時または離れた時バウンス・dm26rp1-002型。
  原文は「好きな数」だが proto は１体に簡略化）/ T391（置かれた時シールド
  下置き・dm26rp1-001型）/ T392（攻撃時自己墓地＋手札出し・dm26ex1-n022型。
  ブロッカー／スレイヤー付与とメカ指定は省略）/ T393（初回破壊時ドロー・
  dm26rp1-067型）。
"""
import pytest
import yaml
from pathlib import Path

from conftest import setup

from dmsim.defs import DefError, load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent
IDS = ("T388", "T389", "T390", "T391", "T392", "T393")


def _proto_card(cid):
    with open(ROOT / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in IDS:
        d = parse_card(_proto_card(cid), TABLES)
        assert d.types == ["g_castle"]
        leave = [a for a in d.abilities if a.get("keyword") == "g_castle"]
        assert len(leave) == 1 and leave[0]["kind"] == "replace"
        assert leave[0]["when"] == {"event": "move", "from": "shield", "subject": "self"}
        assert leave[0]["if"] == {"face_up": True}
        assert leave[0]["instead"] == [
            {"op": "move", "select": {"ref": "self"}, "to": "graveyard", "reason": "put"}]
    # 型印のないカードに型ルールは付かない
    assert not [a for a in parse_card(_proto_card("T005"), TABLES).abilities
                if a.get("keyword") == "g_castle"]
    assert _proto_card("T388")["abilities"][0]["mod"] == {"cost": -1}
    assert _proto_card("T389")["abilities"][0]["when"] == {
        "event": "move", "to": "shield", "subject": "self", "face_up": True}
    assert _proto_card("T390")["abilities"][1]["when"] == {
        "event": "move", "from": "shield", "subject": "self", "face_up": True}
    assert _proto_card("T391")["abilities"][0]["effect"][0]["op"] == "put_under"
    assert _proto_card("T392")["abilities"][0]["when"] == {
        "event": "attack", "subject": {"owner": "opp", "filter": {"types": ["creature"]}}}
    assert _proto_card("T393")["abilities"][0].get("first_time") is True


def test_bad_forms_rejected():
    bad = dict(_proto_card("T388"))
    bad["types"] = ["g_castle2"]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _settle(e, done, drive=None, max_steps=300):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        if done():
            # 状態が満たされた直後の決定は答えずに止める（次の _settle が同じ
            # 決定から再開できる）。答えてしまうとメイン等を pass してターンが
            # 進み、手札枚数などの前提が崩れる
            return True
        keys = _keys(d)
        if drive and drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def _drive_play(e, d, keys, defn, pick_defn=None):
    """手札の defn をメインで実行する（コスト支払いまで）。それ以外は pass / 先頭選択。"""
    if d["kind"] == "main" and f"play:{defn}" in keys:
        e.answer([keys.index(f"play:{defn}")])
        return True
    if d["kind"] == "pay_mana":
        e.answer([0])
        return True
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")])
        return True
    if d["kind"] == "choose_replacement":
        hit = [i for i, k in enumerate(keys) if k.startswith("replace:")]
        if hit:
            e.answer([hit[0]])
            return True
        if "decline" in keys:
            e.answer([keys.index("decline")])
            return True
    if d["kind"] == "choose_cards" and pick_defn:
        hit = [i for i, k in enumerate(keys) if pick_defn in k]
        if hit:
            e.answer([hit[0]])
            return True
    if d["kind"] in ("declare_strigger", "declare_sback"):
        e.answer([])
        return True
    return False


def _castle(e, defn):
    return next(i for i, c in enumerate(e.s.cards) if c.defn == defn)


def test_castle_play_to_shield(rules):
    e = setup(rules, {"hand": ["T388"], "mana": ["T004"] * 3}, {})
    cid = _castle(e, "T388")
    sh0 = len(e.zlist("shield", 0))
    ok = _settle(e, lambda: e.s.cards[cid].zone == "shield",
                 lambda e, d, k: _drive_play(e, d, k, "T388"))
    assert ok, "G城がシールドゾーンに置かれなかった"
    assert e.s.cards[cid].face_up is True
    assert len(e.zlist("shield", 0)) == sh0 + 1
    assert len(e.zlist("hand", 0)) == 0
    assert e.s.cards[cid].controller == 0


def test_castle_static_cost_reduction(rules):
    # 表向き: T003（水コスト2）が1マナで唱えられる
    e = setup(rules, {"hand": ["T388", "T003"], "mana": ["T004"] * 3 + ["T009"]}, {})
    cid = _castle(e, "T388")
    t003 = next(i for i, c in enumerate(e.s.cards) if c.defn == "T003")
    ok = _settle(e, lambda: e.s.cards[cid].zone == "shield",
                 lambda e, d, k: _drive_play(e, d, k, "T388"))
    assert ok
    assert e.chars_ro(t003)["pay_cost"] == 1, "表向きの軽減が pay_cost に反映されていない"
    hand0 = len(e.zlist("hand", 0))
    ok = _settle(e, lambda: len(e.zlist("hand", 0)) >= hand0 + 1,
                 lambda e, d, k: _drive_play(e, d, k, "T003"))
    assert ok, "軽減が働かず T003 が唱えられなかった"
    # 裏向き: シールド化された G城に常在型は働かない（pay_cost は元の2のまま）
    e = setup(rules, {"shield": ["T388"], "hand": ["T003"], "mana": ["T009"]}, {})
    cid = _castle(e, "T388")
    t003 = next(i for i, c in enumerate(e.s.cards) if c.defn == "T003")
    assert e.s.cards[cid].face_up is False
    assert e.chars_ro(t003)["pay_cost"] == 2


def test_castle_put_trigger_draw(rules):
    e = setup(rules, {"hand": ["T389"], "mana": ["T003"] * 4}, {})
    cid = _castle(e, "T389")
    ok = _settle(e, lambda: e.s.cards[cid].zone == "shield" and len(e.zlist("hand", 0)) == 1,
                 lambda e, d, k: _drive_play(e, d, k, "T389"))
    assert ok, "置かれた時ドローが働かなかった"


def _attack_and_break(e, attacker_defn, shield_defn, drive_extra=None):
    """attacker でプレイヤーへ攻撃し、shield_defn のシールドをブレイクする。
    choose_shields は min 枚ちょうど選ぶ（ダブル・ブレイカーは2枚）。選択肢の
    キーはすべて 'shield' なので、cid から defn で選ぶ。"""
    def drive(e, d, keys):
        if d["kind"] == "attack" and f"attack:{attacker_defn}:player" in keys:
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
            return True
        if d["kind"] == "choose_breaker":
            e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
            return True
        if d["kind"] == "choose_shields":
            hit = [i for i, o in enumerate(d["options"])
                   if o.get("cid") is not None and e.s.cards[o["cid"]].defn == shield_defn]
            rest = [i for i in range(len(keys)) if i not in hit]
            e.answer((hit + rest)[:d["min"]])
            return True
        if drive_extra and drive_extra(e, d, keys):
            return True
        return _drive_play(e, d, keys, "")
    return drive


def test_castle_break_goes_to_graveyard(rules):
    e = setup(rules, {"hand": ["T389"], "mana": ["T003"] * 4},
              {"bz": ["T005"]})
    cid = _castle(e, "T389")
    assert _settle(e, lambda: e.s.cards[cid].zone == "shield",
                   lambda e, d, k: _drive_play(e, d, k, "T389"))
    ok = _settle(e, lambda: e.s.cards[cid].zone == "graveyard",
                 _attack_and_break(e, "T005", "T389"))
    assert ok, "ブレイクされた G城が墓地に行かなかった"
    # T005 はダブル・ブレイカー: G城1枚＋裏向きシールド1枚をブレイクする。
    # G城は墓地へ、裏向きシールドは手札へ（ターン開始ドローが入るため手札枚数は数えない）
    assert e.s.cards[cid].zone == "graveyard"
    assert all(e.s.cards[c].defn != "T389" for c in e.zlist("hand", 0))
    assert len(e.zlist("shield", 0)) == 4


def test_castle_break_face_down_goes_to_hand(rules):
    # 対照実験: 裏向きの G城は型ルールの置換が働かず、手札に加わる
    e = setup(rules, {"shield": ["T389"]}, {"bz": ["T005"]})
    cid = _castle(e, "T389")
    assert e.s.cards[cid].face_up is False
    ok = _settle(e, lambda: e.s.cards[cid].zone == "hand",
                 _attack_and_break(e, "T005", "T389"))
    assert ok, "裏向きの G城が手札に加わらなかった"


def test_castle_enter_leave_triggers(rules):
    e = setup(rules, {"hand": ["T390"], "mana": ["T008"] * 4},
              {"bz": ["T005", "T001", "T004"]})
    cid = _castle(e, "T390")
    t005 = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "T005")
    t001 = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "T001")
    e.s.cards[t005].tapped = True
    e.s.cards[t001].tapped = True
    assert _settle(e, lambda: e.s.cards[cid].zone == "shield"
                   and e.s.cards[t005].zone == "hand",
                   lambda e, d, k: _drive_play(e, d, k, "T390", "T005"))
    assert e.s.cards[t005].zone == "hand", "置かれた時バウンスが働かなかった"
    # ターン開始のアンタップで T001 は起きているので、離れた時誘発の対象として改めてタップする
    e.s.cards[t001].tapped = True
    assert _settle(e, lambda: e.s.cards[cid].zone == "graveyard"
                   and e.s.cards[t001].zone == "hand",
                   _attack_and_break(e, "T004", "T390",
                                     lambda e, d, k: _drive_play(e, d, k, "", "T001")))
    assert e.s.cards[t001].zone == "hand", "離れた時バウンスが働かなかった"


def test_castle_put_under(rules):
    e = setup(rules, {"hand": ["T391"], "mana": ["T004"] * 4}, {})
    cid = _castle(e, "T391")
    deck0 = len(e.zlist("deck", 0))
    sh0 = len(e.zlist("shield", 0))
    assert _settle(e, lambda: e.s.cards[cid].zone == "shield"
                   and len(e.s.cards[cid].under) == 2,
                   lambda e, d, k: _drive_play(e, d, k, "T391"))
    assert len(e.s.cards[cid].under) == 2, "山札の上2枚がシールドの下に置かれなかった"
    assert len(e.zlist("deck", 0)) == deck0 - 2
    assert len(e.zlist("shield", 0)) == sh0 + 1, "束の下のカードがシールドの数に数えられた"
    assert all(e.s.cards[u].face_up is False for u in e.s.cards[cid].under)


def test_castle_attack_trigger_sacrifice(rules):
    e = setup(rules, {"hand": ["T392", "T005"], "mana": ["T004"] * 2 + ["T008"] * 2},
              {"bz": ["T004"]})
    cid = _castle(e, "T392")
    assert _settle(e, lambda: e.s.cards[cid].zone == "shield",
                   lambda e, d, k: _drive_play(e, d, k, "T392"))
    t005 = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "T005")
    ok = _settle(e, lambda: e.s.cards[cid].zone == "graveyard"
                 and e.s.cards[t005].zone == "bz",
                 _attack_and_break(e, "T004", "T001",
                                   lambda e, d, k: _drive_play(e, d, k, "", "T005")))
    assert ok, "攻撃時誘発の自己墓地＋手札出しが働かなかった"


def test_castle_first_destroy_draw(rules):
    e = setup(rules, {"hand": ["T393", "T056", "T056"],
                      "mana": ["T001"] * 3 + ["T008"] * 6},
              {"bz": ["T005", "T004"]})
    cid = _castle(e, "T393")
    assert _settle(e, lambda: e.s.cards[cid].zone == "shield",
                   lambda e, d, k: _drive_play(e, d, k, "T393"))
    hand0 = len(e.zlist("hand", 0))

    def drive(e, d, keys):
        if d["kind"] == "main" and "play:T056" in keys:
            e.answer([keys.index("play:T056")])
            return True
        if d["kind"] == "pay_mana":
            e.answer([0])
            return True
        if d["kind"] == "choose_cards":
            hit = [i for i, k in enumerate(keys) if "T005" in k or "T004" in k]
            if hit:
                e.answer([hit[0]])
                return True
        return _drive_play(e, d, keys, "")
    # 2体破壊する。初回だけドローするので、手札は -2（呪文2枚）+1（ドロー）= hand0 - 1
    ok = _settle(e, lambda: len(e.zlist("graveyard", 1)) >= 2
                 and len(e.zlist("hand", 0)) == hand0 - 1, drive, 400)
    assert ok, "初回破壊時ドローが1回だけ働かなかった"
