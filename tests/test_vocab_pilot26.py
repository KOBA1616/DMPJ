"""語彙パイロット第26弾（2026-11-01）の検証: フェーズ4（判定/特殊系）。

- ガチンコ・ジャッジ: op gachinko（回数指定 / 負けるか中止するまで）。勝敗は山札の上のコスト比較、見せたカードは一番下へ
- スーパー・S・トリガー: シールド0枚で使った時だけ sst 印つき能力（と sst_spell）が有効になる
- 超魂X: 下に重なっているカードの choukon 印つき能力を一番上のクリーチャーが得る
- バズレンダ: 支払い時に追加コストを好きな回数払い、[OL]能力を1+追加回数使う
"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=60, play=None):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive and drive(e, d, keys):
            continue
        if play and d["kind"] == "main":
            hit = [i for i, k in enumerate(keys) if k.startswith(f"play:{play}")]
            if hit:
                e.answer([hit[0]])
                continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def _rig(e, p, defns):
    """山札の上を指定した並びにする（シナリオはシャッフル済みなので直接並べ替える）。"""
    lst = e.s.zones["deck"][p]
    chosen = []
    for d in defns:
        chosen.append(next(c for c in lst if e.s.cards[c].defn == d and c not in chosen))
    lst[:] = chosen + [c for c in lst if c not in chosen]


def test_gachinko_times(rules):
    # 自分の山札の上: T073(4), T001(2)。相手の上: T001(2), T073(4) → 1勝1敗で wins=1
    e = setup(rules, {"hand": ["T073"], "mana": ["T004"] * 4,
                      "deck": ["T073", "T001", "T001", "T001"]},
              {"deck": ["T001", "T073", "T001", "T001"]})
    _rig(e, 0, ["T073", "T001"])
    _rig(e, 1, ["T001", "T073"])
    mana0 = len(e.zlist("mana", 0))
    ok = _settle(e, lambda: len(e.zlist("mana", 0)) == mana0 + 1, play="T073")
    assert ok, "ガチンコの勝ち数（1）だけマナに置かれなかった"
    # 見せたカードはそれぞれ一番下へ（自分の山札の並びが回転している）
    assert [e.s.cards[c].defn for c in e.zlist("deck", 0)][:2] == ["T001", "T001"]


def test_gachinko_until_lose_stoppable(rules):
    # 自分は全勝できる並び（4,4）だが、1回で中止する → 引くのは1枚
    e = setup(rules, {"hand": ["T074"], "mana": ["T005"] * 3,
                      "deck": ["T073", "T073", "T001", "T001", "T001"]},
              {"deck": ["T001", "T001", "T001", "T001"]})
    hand0 = len(e.zlist("hand", 0))
    state = {"asked": 0}

    def drive(e, d, keys):
        if d["kind"] == "yes_no":
            state["asked"] += 1
            e.answer([keys.index("yes") if state["asked"] == 1 else keys.index("no")])
            return True
        return False

    ok = _settle(e, lambda: len(e.zlist("hand", 0)) == hand0 + 1, drive, 80, play="T074")
    assert ok, "中止するまでのガチンコ→勝ち数ドローができなかった"
    assert state["asked"] == 2        # 続ける→中止、の2回聞かれた


def test_super_s_trigger_bonus(rules):
    # 最後のシールドとして割られ、S・トリガーで召喚 → 通常分1枚+追加分2枚引く
    e = setup(rules, {"shield": ["T075"], "deck": ["T001"] * 6}, {"bz": ["T005"]})
    e.s.cards[next(iter(e.bz_tops(1)))].entered_turn = -1
    hand0 = len(e.zlist("hand", 0))

    def drive(e, d, keys):
        if d["kind"] == "attack" and d["player"] == 1:
            e.answer([0])
            return True
        if d["kind"] == "declare_strigger":
            e.answer([0])
            return True
        return False

    # ETB で 1+2 枚引き、続く自分のターンのドローでさらに1枚（合計+4）
    ok = _settle(e, lambda: len(e.zlist("hand", 0)) == hand0 + 4, drive, 90)
    assert ok, "スーパー・S・トリガーの追加能力が働かなかった"
    assert any(e.s.cards[c].defn == "T075" for c in e.bz_tops(0))


def test_super_s_trigger_not_from_hand(rules):
    # 手札から普通に召喚したら追加能力は働かない（1枚だけ引く）
    e = setup(rules, {"hand": ["T075"], "mana": ["T008"] * 9, "deck": ["T001"] * 6}, {})
    hand0 = len(e.zlist("hand", 0))
    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T075" for c in e.bz_tops(0))
                 and len(e.zlist("hand", 0)) == hand0, None, 60, play="T075")
    assert ok, "通常召喚で追加能力まで働いてしまった（または出なかった）"


def test_choukon_x(rules):
    e = setup(rules, {"bz": ["T076"], "hand": ["T077"], "mana": ["T003"] * 3,
                      "deck": ["T001"] * 4}, {"shield": ["T001", "T001"]})
    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T077" for c in e.bz_tops(0)), play="T077")
    assert ok, "進化できなかった"
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T077")
    assert e.chars(top)["power"] == 4500     # 3000 + 超魂Xのパワー+1500
    # 進化したクリーチャーで攻撃すると超魂Xの誘発で1枚引く
    e.s.cards[top].entered_turn = -1
    hand0 = len(e.zlist("hand", 0))

    def drive(e, d, keys):
        if d["kind"] == "attack":
            e.answer([0])
            return True
        return False

    ok = _settle(e, lambda: len(e.zlist("hand", 0)) == hand0 + 1, drive, 90)
    assert ok, "超魂Xの攻撃時誘発が働かなかった"


def test_bazurenda(rules):
    e = setup(rules, {"hand": ["T078"], "mana": ["T001"] * 11, "deck": ["T001"] * 6}, {})
    mana0 = len(e.zlist("mana", 0))
    state = {"extra": 0}

    def drive(e, d, keys):
        if d["kind"] == "main":
            hit = [i for i, k in enumerate(keys) if k == "play:T078"]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "yes_no":            # バズレンダの追加支払い: 2回払って止める
            state["extra"] += 1
            e.answer([keys.index("yes") if state["extra"] <= 2 else keys.index("no")])
            return True
        return False

    ok = _settle(e, lambda: len(e.zlist("mana", 0)) == mana0 + 3, drive, 80)
    assert ok, "バズレンダの能力が1+2回使われなかった"
    assert state["extra"] == 3
