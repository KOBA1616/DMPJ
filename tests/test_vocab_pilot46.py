"""語彙パイロット第46弾（フェーズ17-7）: 封印（seal_mechanic 単独18件）。

実装したもの:
- 状態: Card.seals（上に重なった封印）/ Card.seal_of。封印カードは top_of を持ち、バトルゾーンの
  「一番上」には数えない
- 無視: 封印されているクリーチャーは特性（種族・タイプ・キーワード）を持たず、能力も機能しない。
  通常のフィルタでは選べず、filter の sealed: true でだけ指せる。パワーは印刷どおり
- op: attach_seal（持ち主の山札の上から重ねる）/ op: remove_seal（墓地に置く。移動イベントになる）
- コマンドが出た時、その持ち主は同じ文明を持つ自身のカードから封印を1つ外す（seal_release タスク）
- 封印されたカードが離れる時、封印は持ち主の墓地に置かれる。封印の移動記録には sealed_from が付き、
  「このカードの封印がすべてなくなった時」は when の sealed_from: self ＋ if の seals_on で表す
"""
from conftest import answer, setup


def _answer_default(e, d):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "pay_mana":
        e.answer(list(range(d["min"])))
    elif d["kind"] in ("yes_no", "may"):
        e.answer([keys.index("yes") if "yes" in keys else 0])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def drive(e, stop_at_play=None, max_steps=400):
    """判断を既定の答えで処理し続ける。stop_at_play がメインの選択肢に出たらそれを出して止める。"""
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return "done"
        keys = [o["key"] for o in d["options"]]
        if stop_at_play and d["kind"] == "main" and stop_at_play in keys:
            e.answer([keys.index(stop_at_play)])
            return "played"
        _answer_default(e, d)
    raise AssertionError("drive did not settle")


def settle(e, max_steps=14):
    """効果の解決を済ませる。次のメインの判断が出たら止める（答えない）。
    メインが自動で流れる場合に備え、判断の回数にも上限を付ける。"""
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return "done"
        if d["kind"] == "main":
            return "main"
        _answer_default(e, d)
    return "capped"


def _find(e, defn, zone="bz", p=0):
    return [c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn]


def test_attach_seal_and_ignored(rules):
    """出た時に自分へ封印を2つ付ける。封印中は特性を持たず、パワー0扱いで破壊もされない。"""
    e = setup(rules, {"hand": ["T129"], "mana": ["T127"] * 4}, {})
    assert drive(e, "play:T129") == "played"
    settle(e)
    g = _find(e, "T129")
    assert len(g) == 1
    c = e.s.cards[g[0]]
    assert len(c.seals) == 2
    ch = e.chars(g[0])
    assert ch["types"] == [] and ch["races"] == [] and ch["keywords"] == set()
    assert len(_find(e, "T129")) == 1   # 状況起因処理で破壊されていない


def test_command_release_and_all_removed_trigger(rules):
    """コマンドが出るたび封印が1つ外れ、すべて外れた時に1ドローが誘発する。"""
    e = setup(rules, {"hand": ["T129", "T131", "T131"], "mana": ["T127"] * 6}, {})
    assert drive(e, "play:T129") == "played"
    settle(e)
    assert drive(e, "play:T131") == "played"
    settle(e)
    g = _find(e, "T129")[0]
    assert len(e.s.cards[g].seals) == 1   # 1つ外れた（まだ封印中）
    assert drive(e, "play:T131") == "played"
    # 封印が0になった直後（ターンをまたぐ前）に「すべて外れた時」のドローが解決することを見る
    unsealed_at = None
    drew = False
    for _ in range(30):
        if unsealed_at is not None and len(e.zlist("hand", 0)) == unsealed_at + 1:
            drew = True
            break
        d = e.advance()
        if d is None:
            break
        if unsealed_at is None and len(e.s.cards[g].seals) == 0:
            unsealed_at = len(e.zlist("hand", 0))
        _answer_default(e, d)
    assert len(e.s.cards[g].seals) == 0   # すべて外れた
    assert e.chars(g)["types"] == ["creature"]   # 特性が戻る
    assert drew   # 「すべて外れた時」に1枚引いた
    assert len(e.zlist("graveyard", 0)) == 2        # 外れた封印2枚は墓地へ


def test_remove_seal_op(rules):
    """remove_seal で相手の封印を1つ墓地に置ける（sealed: true のフィルタでだけ選べる）。"""
    e = setup(rules, {"hand": ["T129"], "mana": ["T127"] * 4},
              {"hand": ["T132"], "mana": ["T003"] * 3})
    assert drive(e, "play:T129") == "played"
    settle(e)
    assert drive(e, "play:T132") == "played"
    settle(e)
    g = _find(e, "T129")[0]
    assert len(e.s.cards[g].seals) == 1
    assert len(e.zlist("graveyard", 0)) == 1


def test_attach_seal_to_opponent(rules):
    """相手のクリーチャーに封印を付けると、そのクリーチャーは無視される。"""
    e = setup(rules, {"bz": ["T127"]}, {"hand": ["T130"], "mana": ["T005"] * 3})
    assert drive(e, "play:T130") == "played"
    settle(e)
    g = _find(e, "T127")[0]
    assert len(e.s.cards[g].seals) == 1
    assert e.chars(g)["types"] == []


def test_seals_follow_to_graveyard_when_host_leaves(rules):
    """封印されたカードが離れる時、封印は持ち主の墓地に置かれる。"""
    e = setup(rules, {"hand": ["T129"], "mana": ["T127"] * 4}, {})
    assert drive(e, "play:T129") == "played"
    settle(e)
    g = _find(e, "T129")[0]
    assert len(e.s.cards[g].seals) == 2
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(g), "to": "graveyard", "reason": "destroy"}))
    for _ in range(40):   # 滞っていたメインの判断をパスしながら、積んだ移動タスクを処理させる
        if len(e.zlist("graveyard", 0)) == 3:
            break
        d = e.advance()
        if d is None:
            break
        _answer_default(e, d)
    assert len(e.zlist("graveyard", 0)) == 3   # 本体＋封印2枚


def test_seal_on_enter_suppresses_cip(rules):
    """封印を付けた状態で出たクリーチャーは無視され、出た時能力が誘発しない（move の seal 指定。第46弾v2）。
    T129 は出た時に自分へ封印を2つ付ける能力を持つ: 封印1つ付きで出れば、その能力は解決されず封印は1つのまま。"""
    e = setup(rules, {"hand": ["T129"], "mana": ["T127"] * 4}, {})
    g = e.zlist("hand", 0)[0]
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(g), "to": "bz", "reason": "put", "seal": 1}))
    for _ in range(40):
        d = e.advance()
        if d is None:
            break
        if e.bz_tops(0):
            gid = e.bz_tops(0)[0]
            if len(e.s.cards[gid].seals) >= 1 and d["kind"] == "main":
                break
        _answer_default(e, d)
    tops = e.bz_tops(0)
    assert len(tops) == 1
    assert len(e.s.cards[tops[0]].seals) == 1      # 出た時能力（+2つ）は無視されて解決されていない
    assert e.chars(tops[0])["races"] == []            # 特性も無視されている
