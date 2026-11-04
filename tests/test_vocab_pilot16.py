"""語彙パイロット第16弾（2026-10-31）の検証: ゴッドリンク（docs/g-link-plan.md）。

- Phase 0-1: グループ表現（Card.link）と特性統合（パワーは合計、キーワードは和集合、代表1体として扱う）
- Phase 2: 出た時のリンク手順（中央はリンク外し→リンク先、左/右はリンク先の選択）
- Phase 3: 離脱の置換（グループが離れる時は中から1枚だけが離れる）
- Phase 4: 式 link_count（「カード3枚でリンクしていれば」）
"""
from conftest import setup


def _drive_to_bz(e, defn, link_key=None):
    """手札の defn を召喚し、場に出てリンク手順が終わるまで進める。link_key があればリンク手順でその選択肢を選ぶ。"""
    entered = False
    for _ in range(30):
        d = e.advance()
        if d is None:
            return
        if any(e.s.cards[c].defn == defn for c in e.zlist("bz", 0)):
            entered = True
        if entered and d["kind"] not in ("choose_link_target", "choose_unlink"):
            return   # リンク手順は出た直後に割り込む。それ以外の判断に移ったら手順は終わっている
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and f"play:{defn}" in keys:
            e.answer([keys.index(f"play:{defn}")])
        elif d["kind"] == "choose_link_target" and link_key is not None:
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(link_key))])
        elif d["kind"] == "choose_unlink":
            e.answer([keys.index("done")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def test_g_link_full_cycle(rules):
    e = setup(rules, {"hand": ["T053", "T054", "T055"], "mana": ["T008"] * 12}, {})
    _drive_to_bz(e, "T053")          # 左ゴッド単独（リンク先なし）
    left = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T053")
    assert e.s.cards[left].link == 0
    _drive_to_bz(e, "T054", link_key="bz:T053")   # 中央が出て左にリンクする
    center = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T054")
    assert e.s.cards[center].link != 0 and e.s.cards[center].link == e.s.cards[left].link
    assert e.link_rep(center) == center
    ch = e.chars(center)
    assert ch["power"] == 2000 + 3000                  # パワーは合計
    assert "double_breaker" in ch["keywords"]          # キーワードは和集合
    assert len(e.bz_tops(0)) == 1                      # グループは1体として数える
    hand_before = len(e.zlist("hand", 0))
    _drive_to_bz(e, "T055", link_key="bz:T054")     # 右が出て3枚リンク。中央の出た時誘発（3枚で引く）が解決する
    right = next(c for c in e.s.zones["bz"][0] if e.s.cards[c].defn == "T055")
    for _ in range(10):   # 誘発の解決まで進める
        if len(e.zlist("hand", 0)) > hand_before:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert e.s.cards[right].link == e.s.cards[center].link
    assert e.chars(center)["power"] == 2000 + 3000 + 2500
    assert len(e.zlist("hand", 0)) == hand_before + 1   # 3枚リンクの出た時誘発で1枚引いた


def test_g_link_leave_replacement(rules):
    # 相手が破壊呪文でグループを狙う: 置換で「離れる1枚」を聞かれ、その1枚だけが墓地へ行く
    e = setup(rules, {"hand": ["T053", "T054"], "mana": ["T008"] * 8},
              {"hand": ["T056"], "mana": ["T008"] * 3})
    _drive_to_bz(e, "T053")
    _drive_to_bz(e, "T054", link_key="bz:T053")
    center = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T054")
    left = next(x for x in e.s.zones["bz"][0] if e.s.cards[x].defn == "T053")
    picked = False
    for _ in range(40):
        if e.s.cards[center].zone == "graveyard":
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_link_leave":
            picked = True
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("bz:T054"))])
        elif d["kind"] == "main" and d["player"] == 1 and "play:T056" in keys:
            e.answer([keys.index("play:T056")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert picked
    assert e.s.cards[center].zone == "graveyard"       # 選んだ1枚だけが離れた
    assert e.s.cards[left].zone == "bz"                # 残りはバトルゾーンに残る
    assert e.s.cards[left].link == 0                   # 1枚だけになったのでリンク解消
