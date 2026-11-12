"""語彙パイロット第183弾（2026-11-11）の検証: S級侵略。

- declare + invade（第24弾の侵略イディオム）に、発生源ゾーンとして墓地・マナ・
  バトルゾーンを追加。1枚のカードが複数ゾーンから宣言できる（ゾーンごとに declare を1つずつ。
  アタック・チャンスの手札＋墓地の前例と同じ型）
- bz 経路: _declarable が bz を走査（controller・top・攻撃者自身を除外）。
  攻撃者自身は自分の上には重ねられない（「自分以外のクリーチャーが攻撃する時」）
- bz→bz の重ねは「離れた時」ではない（_match_when のガード。公式Q&A・
  DARK MATERIAL COMPLEX の裁定）。「出た時」は「置くは出すと同義」で発火する
- 「このカード」型（アダムスキー）は進化元を置いていく剥がし重ねのため対象外。
  「このクリーチャー」型（[轟速][不死][原始]）はクリーチャーごと移動し、既存の
  _stack と同じ挙動（公式Q&A 2023年2月17日更新版・総合ルール 409.1f）
"""
from conftest import setup


def _drive(e, want_defn, done, max_steps=120):
    """攻撃を進め、want_defn を含む選択肢が出たらそれを選ぶ（yes_no は yes）。done(e) で終了。"""
    for _ in range(max_steps):
        if done(e):
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        hit = [i for i, k in enumerate(keys) if want_defn in k and not k.startswith("charge:")]
        if hit and d["kind"] not in ("pay_mana", "charge"):
            e.answer([hit[0]])
        elif d["kind"] == "yes_no" and "yes" in keys:
            e.answer([keys.index("yes")])
        elif d["kind"] == "attack":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return done(e)


def _drive_watch(e, watch_defn, done, max_steps=120):
    """攻撃を進める。watch_defn を含む選択肢が出たかを記録するが、選ばない。"""
    saw = False
    for _ in range(max_steps):
        if done(e):
            return True, saw
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if any(watch_defn in k for k in keys):
            saw = True
        if d["kind"] == "yes_no" and "no" in keys:
            e.answer([keys.index("no")])
        elif d["kind"] == "attack":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return done(e), saw


def _attacker(e, defn="T424"):
    e.s.cards[next(c for c in e.bz_tops(0) if e.s.cards[c].defn == defn)].entered_turn = -1


def _stacked(e, top_defn, under_defn):
    tops = [c for c in e.bz_tops(0) if e.s.cards[c].defn == top_defn]
    assert tops, f"{top_defn} がバトルゾーンにいない"
    top = tops[0]
    under = e.s.cards[top].under
    assert under and e.s.cards[under[0]].defn == under_defn, \
        f"下が {under_defn} ではない: {[e.s.cards[u].defn for u in under]}"


def test_s_class_invasion_from_graveyard(rules):
    e = setup(rules, {"bz": ["T424"], "graveyard": ["T425"]}, {"shield": ["T001", "T001"]})
    _attacker(e)
    base_hand = len(e.zlist("hand", 0))
    ok = _drive(e, "declare:T425", lambda e: any(e.s.cards[c].defn == "T425" for c in e.bz_tops(0))
                  and len(e.zlist("shield", 1)) == 1)
    assert ok, "墓地からのS級侵略で重ならなかった"
    _stacked(e, "T425", "T424")
    assert len(e.zlist("shield", 1)) == 1                                    # 攻撃が続いた
    assert len(e.zlist("hand", 0)) == base_hand + 1                          # CIP ドロー
    assert not e.zlist("graveyard", 0)


def test_s_class_invasion_from_hand(rules):
    e = setup(rules, {"bz": ["T424"], "hand": ["T426"]}, {"shield": ["T001", "T001"]})
    _attacker(e)
    base_hand = len(e.zlist("hand", 0))
    ok = _drive(e, "declare:T426", lambda e: any(e.s.cards[c].defn == "T426" for c in e.bz_tops(0))
                  and len(e.zlist("shield", 1)) == 1)
    assert ok, "手札からのS級侵略で重ならなかった"
    _stacked(e, "T426", "T424")
    assert len(e.zlist("shield", 1)) == 1
    assert len(e.zlist("hand", 0)) == base_hand                             # -1 + CIP ドロー


def test_s_class_invasion_from_graveyard_second_declare(rules):
    e = setup(rules, {"bz": ["T424"], "graveyard": ["T426"]}, {"shield": ["T001", "T001"]})
    _attacker(e)
    base_hand = len(e.zlist("hand", 0))
    ok = _drive(e, "declare:T426", lambda e: any(e.s.cards[c].defn == "T426" for c in e.bz_tops(0))
                  and len(e.zlist("shield", 1)) == 1)
    assert ok, "墓地からのS級侵略（2つ目の declare）で重ならなかった"
    _stacked(e, "T426", "T424")
    assert len(e.zlist("shield", 1)) == 1
    assert len(e.zlist("hand", 0)) == base_hand + 1                          # CIP ドロー
    assert not e.zlist("graveyard", 0)


def test_s_class_invasion_from_mana_cost3(rules):
    e = setup(rules, {"bz": ["T428"], "mana": ["T427", "T001"]}, {"shield": ["T001", "T001"]})
    _attacker(e, "T428")
    base_hand = len(e.zlist("hand", 0))
    ok = _drive(e, "declare:T427", lambda e: any(e.s.cards[c].defn == "T427" for c in e.bz_tops(0))
                  and len(e.zlist("shield", 1)) == 1)
    assert ok, "マナからのS級侵略（コスト3）で重ならなかった"
    _stacked(e, "T427", "T428")
    assert len(e.zlist("shield", 1)) == 1
    assert len(e.zlist("hand", 0)) == base_hand + 1                          # CIP ドロー


def test_s_class_invasion_mana_not_offered_for_wrong_attacker(rules):
    e = setup(rules, {"bz": ["T424"], "mana": ["T427", "T001"]}, {"shield": ["T001", "T001"]})
    _attacker(e)
    ok, saw = _drive_watch(e, "declare:T427", lambda e: len(e.zlist("shield", 1)) == 1)
    assert ok, "攻撃が終わらなかった"
    assert not saw, "条件外の攻撃者（闇・コスト4）でマナの T427 が宣言に出た"
    assert any(e.s.cards[c].defn == "T427" for c in e.zlist("mana", 0))      # マナに残る
    assert any(e.s.cards[c].defn == "T424" for c in e.bz_tops(0))


def test_s_class_invasion_from_bz(rules):
    e = setup(rules, {"bz": ["T424", "T429"]}, {"shield": ["T001", "T001"]})
    _attacker(e)
    base_hand = len(e.zlist("hand", 0))
    ok = _drive(e, "declare:T429", lambda e: any(e.s.cards[c].defn == "T429" for c in e.bz_tops(0))
                  and len(e.zlist("shield", 1)) == 1)
    assert ok, "バトルゾーンからのS級侵略で重ならなかった"
    _stacked(e, "T429", "T424")
    assert len(e.zlist("shield", 1)) == 1                                    # 攻撃が続いた
    # CIP ドローは1回だけ。bz→bz の重ねで「離れた時」ドローが出たら +2 になる
    assert len(e.zlist("hand", 0)) == base_hand + 1


def test_s_class_invasion_bz_self_attack_not_offered(rules):
    e = setup(rules, {"bz": ["T429"]}, {"shield": ["T001", "T001"]})
    _attacker(e, "T429")
    ok, saw = _drive_watch(e, "declare:T429", lambda e: len(e.zlist("shield", 1)) == 1)
    assert ok, "攻撃が終わらなかった"
    assert not saw, "攻撃者自身のS級侵略が宣言に出た（自己重ねは不可）"
    assert any(e.s.cards[c].defn == "T429" for c in e.bz_tops(0))
    assert not e.s.cards[next(c for c in e.bz_tops(0)
                              if e.s.cards[c].defn == "T429")].under


def test_s_class_invasion_bz_opp_not_offered(rules):
    e = setup(rules, {"bz": ["T424"]}, {"bz": ["T429"], "shield": ["T001", "T001"]})
    _attacker(e)
    ok, saw = _drive_watch(e, "declare:T429", lambda e: len(e.zlist("shield", 1)) == 1)
    assert ok, "攻撃が終わらなかった"
    assert not saw, "相手のバトルゾーンの T429 が自分に宣言に出た"
    assert any(e.s.cards[c].defn == "T429" for c in e.bz_tops(1))
