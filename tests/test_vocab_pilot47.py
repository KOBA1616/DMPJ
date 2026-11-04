"""語彙パイロット第47弾の検証: 多文明O・ドライブ＋呪文側O・ドライブ。

- o_drive {civs: {文明: 枚数}}: 複数文明をまとめてタップする形（全部タップしたら能力を得る）
- o_drive {civs: {...}, each: true}: 文明ごとにタップするか選べ、能力は odrive: <文明> の印で文明別
- odrive_spell: 呪文が追加タップで得る追加の解決 ops（stp_spell と同型）
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


def _play_driver(card, yes_no_answers, keep_civs=()):
    state = {"yn": 0}
    def drive(e, d, keys):
        if d["kind"] == "main":
            hit = [i for i, k in enumerate(keys) if k == f"play:{card}"]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "pay_mana" and keep_civs:
            for i, o in enumerate(d["options"]):
                tapped = set(o.get("cids") or [])
                left = {}
                for c in e.zlist("mana", 0):
                    if c not in tapped:
                        for cv in e.chars(c)["civs"]:
                            left[cv] = left.get(cv, 0) + 1
                if all(left.get(cv, 0) >= 1 for cv in keep_civs):
                    e.answer([i])
                    return True
            return False
        if d["kind"] == "yes_no":
            ans = yes_no_answers[min(state["yn"], len(yes_no_answers) - 1)]
            state["yn"] += 1
            e.answer([keys.index("yes" if ans else "no")])
            return True
        return False
    return drive


def test_multi_civ_odrive_paid(rules):
    e = setup(rules, {"hand": ["T133"], "mana": ["T004"] * 4 + ["T003"] * 4}, {})
    start = len(e.zlist("hand", 0))
    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T133" for c in e.bz_tops(0))
                 and len(e.zlist("hand", 0)) == start + 1,
                 _play_driver("T133", [True], keep_civs=("light", "water")), 40)
    assert ok, "多文明O・ドライブ（光+水）を払っても追加能力（2ドロー）が働かなかった"


def test_multi_civ_odrive_not_paid(rules):
    e = setup(rules, {"hand": ["T133"], "mana": ["T004"] * 4 + ["T003"] * 4}, {})
    start = len(e.zlist("hand", 0))
    drive = _play_driver("T133", [False], keep_civs=("light", "water"))
    seen = False
    for _ in range(40):   # 出た直後の判断時点で CIP は解決済みのはず（次の判断が出る前に処理される）
        if any(e.s.cards[c].defn == "T133" for c in e.bz_tops(0)):
            seen = True
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert seen, "T133 が出なかった"
    assert len(e.zlist("hand", 0)) == start - 1, "払っていないのに追加能力が働いた"


def test_per_civ_odrive_only_fire(rules):
    e = setup(rules, {"hand": ["T134"],
                      "mana": ["T005"] * 3 + ["T001"] * 3 + ["T004"] * 2},
              {"bz": ["T005"]})
    opp = next(iter(e.bz_tops(1)))
    start = len(e.zlist("hand", 0))
    drive = _play_driver("T134", [True, False], keep_civs=("fire", "nature"))

    ok = _settle(e, lambda: any(e.s.cards[c].defn == "T134" for c in e.bz_tops(0))
                 and opp in e.zlist("graveyard", 1), drive, 50)
    assert ok, "火だけタップしたのに火の能力（破壊）が働かなかった"
    assert len(e.zlist("hand", 0)) == start - 1, "自然をタップしていないのに自然の能力（ドロー）が働いた"


def test_odrive_spell_paid_and_unpaid(rules):
    e = setup(rules, {"hand": ["T135"], "mana": ["T004"] * 5}, {})
    start = len(e.zlist("hand", 0))
    ok = _settle(e, lambda: len(e.zlist("hand", 0)) == start + 1
                 and any(e.s.cards[c].defn == "T135" for c in e.zlist("graveyard", 0)),
                 _play_driver("T135", [True]), 40)
    assert ok, "呪文のO・ドライブ追加解決（+1ドロー）が働かなかった"

    e = setup(rules, {"hand": ["T135"], "mana": ["T004"] * 5}, {})
    ok = _settle(e, lambda: len(e.zlist("hand", 0)) == start
                 and any(e.s.cards[c].defn == "T135" for c in e.zlist("graveyard", 0)),
                 _play_driver("T135", [False]), 40)
    assert ok, "払っていないのに呪文のO・ドライブ追加解決が働いた"
