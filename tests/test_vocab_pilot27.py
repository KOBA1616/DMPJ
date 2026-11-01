"""語彙パイロット第27弾（2026-11-01）の検証: フェーズ5（ロングテール）。

- ムゲンクライム: 自分のクリーチャーを指定数タップ+代替コストで手札/墓地から実行する選択肢
- S・トリガー・プラス: 相手のターンに自分のシールドが2つ以上ブレイクされて使った時だけ追加能力
- O・ドライブ: 召喚時に指定文明のマナを追加でタップしたら追加のETB能力を得る
- シールド・ゴー: 破壊された時、かわりに表向きにシールド化する（キーワードの置換効果）
"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=70):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive and drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def test_mugen_climb_from_hand(rules):
    e = setup(rules, {"bz": ["T001", "T004"], "hand": ["T079"], "mana": ["T003", "T003"]}, {})
    def drive(e, d, keys):
        if d["kind"] == "main":
            hit = [i for i, k in enumerate(keys) if k == "play:T079:climb"]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T079" for c in e.bz_tops(0)), drive)
    assert ok, "ムゲンクライムで出なかった"
    tapped = [c for c in e.bz_tops(0) if e.s.cards[c].defn in ("T001", "T004") and e.s.cards[c].tapped]
    assert len(tapped) == 2, "タップするクリーチャーが2体選ばれなかった"


def test_mugen_climb_from_graveyard(rules):
    e = setup(rules, {"bz": ["T001", "T004"], "graveyard": ["T079"], "mana": ["T003", "T003"]}, {})
    def drive(e, d, keys):
        if d["kind"] == "main":
            hit = [i for i, k in enumerate(keys) if k == "play:T079:climb"]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T079" for c in e.bz_tops(0)), drive)
    assert ok, "墓地からムゲンクライムで出なかった"


def test_s_trigger_plus(rules):
    # W・ブレイカーに2枚割られ、そのうちSTP呪文をS・トリガーで唱える → 追加能力（全タップ）が働く
    e = setup(rules, {"shield": ["T080", "T001"], "deck": ["T001"] * 5}, {"bz": ["T005", "T001"]})
    e.s.cards[next(iter(e.bz_tops(1)))].entered_turn = -1

    def drive(e, d, keys):
        if d["kind"] == "attack" and d["player"] == 1:
            hit = [i for i, k in enumerate(keys) if k.startswith("attack:T005")]
            e.answer([hit[0]] if hit else [0])
            return True
        if d["kind"] == "declare_strigger":
            hit = [i for i, k in enumerate(keys) if "T080" in k]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    opp_t001 = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "T001")
    ok = _settle(e, lambda: e.s.cards[opp_t001].tapped, drive, 90)
    assert ok, "S・トリガー・プラスの追加能力（全タップ）が働かなかった"


def test_o_drive(rules):
    e = setup(rules, {"hand": ["T081"], "mana": ["T004"] * 9}, {"bz": ["T001", "T005"]})
    def drive(e, d, keys):
        if d["kind"] == "main":
            hit = [i for i, k in enumerate(keys) if k == "play:T081"]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
            return True
        if d["kind"] == "choose_cards":      # バウンスは相手の T005 を選ぶ
            hit = [i for i, k in enumerate(keys) if "T005" in k]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    # 追加能力（バウンス）まで働けば、相手の場は1体減る（通常能力はタップのみ）
    ok = _settle(e, lambda: len(e.bz_tops(1)) == 1, drive, 80)
    assert ok, "O・ドライブの追加能力が働かなかった"


def test_shield_go(rules):
    e = setup(rules, {"bz": ["T082"]}, {"bz": ["T005"]})
    e.s.cards[next(iter(e.bz_tops(1)))].entered_turn = -1
    t005 = next(iter(e.bz_tops(1)))
    p0 = e.chars(t005)["power"]

    def drive(e, d, keys):
        if d["kind"] == "attack" and d["player"] == 1:
            e.answer([0])
            return True
        if d["kind"] == "block":
            hit = [i for i, k in enumerate(keys) if "T082" in k]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T082" and e.s.cards[c].face_up
                                for c in e.zlist("shield", 0)), drive, 90)
    assert ok, "破壊された時に表向きシールドにならなかった"
    assert e.chars(t005)["power"] == p0 - 1000, "表向きシールドの間の常在型が働いていない"
