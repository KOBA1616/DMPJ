"""Rust エンジン（段階1）が Python 版と決定・digest を 1 手ずつ一致させることの基準（lockstep）。
段階1の範囲: ターン進行・ドロー・マナチャージ・パス・デッキ切れ。プレイ（play）は未移植 → Unsupported が構造化されて返ること。"""
import pytest

from dmsim.engine import rustcore
from dmsim.cards.defs import load_rules
from dmsim.engine.api import Session, lockstep

pytestmark = pytest.mark.skipif(not rustcore.available(), reason="dmcore 未ビルド")


@pytest.fixture(scope="module")
def env():
    r = load_rules()
    plain = [i for i, d in r.cards.items() if rustcore._is_plain(d)]
    return r, rustcore.rules_bundle(r), [plain[i % len(plain)] for i in range(40)]


def _pair(env, seed, fp):
    r, b, deck = env
    spec = {"kind": "new_game", "decks": [deck, deck], "seed": seed, "first_player": fp}
    return Session.open(r, spec), rustcore.RustSession.open(r, spec, b)


@pytest.mark.parametrize("seed", [1, 2, 3, 99])
@pytest.mark.parametrize("fp", [0, 1])
def test_passive_game_matches_to_deckout(env, seed, fp):
    a, b = _pair(env, seed, fp)
    res = lockstep(a, b, "passive")
    assert res["ok"] is True and res["steps"] > 20


def test_non_plain_is_structured_unsupported(env):
    """未移植の語彙は Unsupported として構造化して返る（ここでは、出た時に封印を解放するコマンド種族）"""
    r, b, _ = env
    cmd = [i for i, d in r.cards.items() if d.types == ["creature"] and d.power > 0 and any("コマンド" in x for x in d.races)
           and not rustcore._is_plain(d)][:1]
    assert cmd
    with pytest.raises(rustcore.dmcore.Unsupported):
        rustcore.RustSession.open(r, {"decks": [cmd * 40, cmd * 40], "seed": 1}, b)


def test_non_plain_card_rejected_at_open(env):
    r, b, _ = env
    ids = [i for i, d in r.cards.items() if i.startswith("dm") and not rustcore._is_plain(d)][:1] * 40
    with pytest.raises(rustcore.dmcore.Unsupported):
        rustcore.RustSession.open(r, {"decks": [ids, ids], "seed": 1}, b)


@pytest.mark.parametrize("pol", ["first", "random:1", "random:2", "random:3"])
@pytest.mark.parametrize("seed", range(1, 21))
def test_full_game_matches(env, pol, seed):
    """召喚・攻撃・バトル・ブレイク・ダイレクトアタックを含む1局が、1手ごとに決定と digest まで一致して終局する。"""
    a, b = _pair(env, seed, seed % 2)
    res = lockstep(a, b, f"random:{seed}" if pol == "first" else pol)
    assert res["divergence"] is None and res["ok"] is True and res["steps"] >= 5


@pytest.fixture(scope="module")
def real_env():
    """確認前の変換結果（converted.yaml）も含めた全カード。テストの既定は除外しているが、エンジンの一致検査は広い札の集合で行う。"""
    import os
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        r = load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old
    return r, rustcore.rules_bundle(r)


def _portable(r, cost_max=6):
    return [i for i, d in r.cards.items() if i.startswith("dm") and rustcore._is_plain(d) and d.cost <= cost_max]


@pytest.mark.parametrize("seed", range(1, 41))
def test_real_cards_match(real_env, seed):
    """実カード（自分自身への許可・禁止・ブレイク数だけを持つクリーチャー: ブロッカー・スピードアタッカー・スレイヤー・
    W/T/Qブレイカー等）のランダムなデッキで、1局が決定と digest まで一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)
    assert len(pool) > 200
    rnd = random.Random(seed)
    spec = {"kind": "new_game", "decks": [[rnd.choice(pool) for _ in range(40)] for _ in range(2)], "seed": seed,
            "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 31))
def test_trigger_cards_match(real_env, seed):
    """誘発（出た時・攻撃する時の、引く／任意で引く／自身のタップ・アンタップ）を持つ札を多く入れたデッキで、
    待機・解決順・効果インタプリタ・yes/no の決定まで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)
    trig = [i for i in pool if any(a["kind"] == "trigger" for a in r.cards[i].abilities)]
    assert len(trig) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(trig) if rnd.random() < 0.5 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 31))
def test_select_move_cards_match(real_env, seed):
    """段階2-d: セレクタ（ゾーン・持ち主・枚数・選ぶ人・types）と 移動／タップ／アンタップ／シャッフル の op を持つ札を
    多く入れたデッキで、choose_cards の決定を含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)
    sel = [i for i in pool if any(o["op"] in ("move", "tap", "untap", "shuffle", "choose")
                                  for a in r.cards[i].abilities if a["kind"] == "trigger" for o in a["effect"])]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.5 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 21))
def test_s_trigger_creatures_match(real_env, seed):
    """段階2-d: S・トリガーを持つクリーチャー（ブレイク→宣言→手札→待機→コストなしの召喚）を多く入れたデッキで、
    declare_strigger の決定を含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)
    st = [i for i in pool if any(k in r.cards[i].keywords for k in ("s_trigger", "s_trigger_plus", "super_s_trigger"))]
    assert len(st) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(st) if rnd.random() < 0.75 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 21))
def test_filter_put_cards_match(real_env, seed):
    """段階2-d 第5弾: フィルタ（コスト・パワー・文明・種族・キーワード・タップ等）と up_to、バトルゾーン／シールドへの移動
    を含む札を多く入れたデッキで1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)

    def has(i):
        out = []

        def w(ops):
            for o in ops:
                out.append(o)
                for k in ("body", "then", "else"):
                    if isinstance(o.get(k), list):
                        w(o[k])
        for a in r.cards[i].abilities:
            if a["kind"] == "trigger":
                w(a["effect"])
        return any((o["op"] == "move" and o.get("to") in ("bz", "shield")) or
                   (isinstance(o.get("select"), dict) and (o["select"].get("filter") or o["select"].get("up_to"))) for o in out)
    sel = [i for i in pool if has(i)]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 21))
def test_static_cards_match(real_env, seed):
    """増分B: affects 辞書の常在型（フィルタ常在効果）と self の power / power_when・コスト修整・
    require を持つ札を多く入れたデッキで、特性の畳み込み（パワー・支払いコスト・許可／禁止・
    ブレイク数・強制攻撃／ブロック・バトル中修整）まで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)

    def has_b(d):
        for a in d.abilities:
            if a["kind"] != "static":
                continue
            m = a.get("mod", {})
            if isinstance(a.get("affects"), dict):
                return True
            if "power_when" in m or isinstance(m.get("power"), dict):
                return True
            if "cost" in m or "require" in m or "battle_power" in m or "win_all_battles" in m:
                return True
        return False
    sel = [i for i in pool if has_b(r.cards[i])]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 21))
def test_modify_cards_match(real_env, seed):
    """増分A: duration つき modify（一時修整。deny / allow / power / grant、対象固定と dynamic）を持つ札を
    多く入れたデッキで、継続的効果の生成・特性への畳み込み・期限切れまで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)

    def has_modify(i):
        out = []

        def w(ops):
            for o in ops:
                out.append(o)
                for k in ("body", "then", "else"):
                    if isinstance(o.get(k), list):
                        w(o[k])
                if isinstance(o.get("modes"), list):
                    for m in o["modes"]:
                        if isinstance(m, list):
                            w(m)
        d = r.cards[i]
        if d.spell:
            w(d.spell)
        for a in d.abilities:
            if a["kind"] in ("trigger", "replace"):
                w(a.get("effect") or a.get("instead") or [])
        return any(o["op"] == "modify" for o in out)
    sel = [i for i in pool if has_modify(i)]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 21))
def test_trigger_shapes_match(real_env, seed):
    """増分C: trigger の subject=dict（フィルタ指定）と追加キー first_time / once_per_turn / optional を
    持つ札を多く入れたデッキで、誘発の収集・回数制限まで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)

    def has_shape(i):
        for a in r.cards[i].abilities:
            if a["kind"] != "trigger":
                continue
            if isinstance((a.get("when") or {}).get("subject"), dict):
                return True
            if a.get("first_time") or a.get("once_per_turn") or a.get("optional"):
                return True
        return False
    sel = [i for i in pool if has_shape(i)]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 21))
def test_move_selector_shapes_match(real_env, seed):
    """増分D: move の selector 拡張（参照の特殊名・ゾーンのリスト・除外／極値・合計制限つき選択・
    フィルタの式の値・order の一般化・face_up/face_down・owner_of 等）を持つ札を多く入れたデッキで、
    選択の決定（合計制限の1枚ずつ積み上げと tc_answers の再生を含む）まで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)

    def has_shape(i):
        out = []

        def w(ops):
            for o in ops or []:
                if isinstance(o, dict):
                    out.append(o)
                    for k in ("body", "then", "else"):
                        if isinstance(o.get(k), list):
                            w(o[k])
                    if isinstance(o.get("modes"), list):
                        for m in o["modes"]:
                            if isinstance(m, list):
                                w(m)
        d = r.cards[i]
        for f in (d.faces or [d]):
            w(getattr(f, "spell", None))
            for a in f.abilities or []:
                if a["kind"] in ("trigger", "replace"):
                    w(a.get("effect") or a.get("instead") or [])
        for o in out:
            if o.get("op") == "move" and ("face_up" in o or "face_down" in o):
                return True
            if o.get("op") == "move" and o.get("order") in ("choose", "shuffle") \
                    and not (isinstance(o.get("select"), dict) and set(o["select"]) == {"ref"}):
                return True
            s = o.get("select")
            if not isinstance(s, dict):
                continue
            if any(k in s for k in ("owner_of", "exclude", "extremal", "distinct_from", "distinct_costs",
                                    "total_cost_le", "total_cost_ge", "total_power_le", "total_power_ge")):
                return True
            if s.get("ref") in ("subject", "self_moved", "self_entered") or str(s.get("ref", "")).startswith("event."):
                return True
            if s.get("ref") == "self" and set(s) != {"ref"}:
                return True
            if isinstance(s.get("zone"), list) or isinstance(s.get("from_top"), dict):
                return True
            if s.get("chooser") == "opponent":
                return True
            if "under_of" in s and (s.get("under_of") != "self" or "filter" in s):
                return True
            if any(isinstance(v, dict) for v in (s.get("filter") or {}).values()):
                return True
        return False
    sel = [i for i in pool if has_shape(i)]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 11))
def test_total_select_cards_match(real_env, seed):
    """増分D: 合計制限つき選択（total_cost_le 等と distinct_costs）を持つ札を多く入れたデッキで、
    1枚ずつ積み上げる選択と下限到達時の打ち切りまで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)

    def has_total(i):
        out = []

        def w(ops):
            for o in ops or []:
                if isinstance(o, dict):
                    out.append(o)
                    for k in ("body", "then", "else"):
                        if isinstance(o.get(k), list):
                            w(o[k])
        d = r.cards[i]
        if d.spell:
            w(d.spell)
        for a in d.abilities:
            if a["kind"] in ("trigger", "replace"):
                w(a.get("effect") or a.get("instead") or [])
        return any(isinstance(o.get("select"), dict) and any(
            k in o["select"] for k in ("total_cost_le", "total_cost_ge", "total_power_le", "total_power_ge",
                                       "distinct_costs", "distinct_from")) for o in out)
    sel = [i for i in pool if has_total(i)]
    assert len(sel) >= 10
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


def test_owner_of_spell_matches(real_env):
    """増分D: owner_of（束変数のカードの持ち主を対象にする）を含む呪文 dm23ex2-cho018 の照合。
    対象クリーチャーの持ち主の手札から、コスト式（{sum: [{cost_of}, -1]}）で絞った
    play_free まで通す構成。複数局のうち少なくとも1回はこの呪文が唱えられること。"""
    r, b = real_env
    spell = "dm23ex2-cho018"
    assert rustcore._is_plain(r.cards[spell])
    vanilla = [i for i, d in r.cards.items()
               if d.types == ["creature"] and not d.abilities and d.cost <= 3 and rustcore._is_plain(d)][:8]
    assert len(vanilla) >= 4
    deck = [spell] * 20 + [vanilla[i % len(vanilla)] for i in range(20)]
    played_any = False
    for seed in range(1, 7):
        spec = {"kind": "new_game", "decks": [deck, deck], "seed": seed, "first_player": seed % 2}
        a, bb = Session.open(r, spec), rustcore.RustSession.open(r, spec, b)
        res = lockstep(a, bb, f"random:{seed}")
        assert res["divergence"] is None and res["ok"] is True
        played_any = played_any or any(o.get("keys") and o["keys"][0] == f"play:{spell}" for o in a.eng.log)
    assert played_any


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_first_time_trigger_matches(real_env, seed):
    """増分C: first_time（各ターン、はじめて〜した時）の記録と抑制が踏まれる構成での照合。
    dmrp16-095 は自分のクリーチャーの召喚をはじめての時だけ見る監視役で、監視役20枚＋安いバニラの
    デッキでは同一ターン2体目以降の召喚で抑制が実際に起きる（計装で発火17回・抑制7回を確認済み）。"""
    r, b = real_env
    watcher = "dmrp16-095"
    assert rustcore._is_plain(r.cards[watcher])
    vanilla = [i for i, d in r.cards.items()
               if d.types == ["creature"] and not d.abilities and d.cost <= 2 and rustcore._is_plain(d)][:8]
    assert len(vanilla) >= 4
    deck = [watcher] * 20 + [vanilla[i % len(vanilla)] for i in range(20)]
    spec = {"kind": "new_game", "decks": [deck, deck], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_if_cards_match(real_env, seed):
    """段階2-d 第6弾: if（exists / cmp / not / all / any）を含む札を多く入れたデッキで1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)
    sel = [i for i in pool if any(o["op"] == "if" for a in r.cards[i].abilities if a["kind"] == "trigger" for o in a["effect"])]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 21))
def test_modify_until_next_turn_matches(real_env, seed):
    """増分F・カテゴリ2: duration=until_next_own_turn_start の modify（「次の自分のターンのはじめまで」）
    を持つ札を多く入れたデッキで、継続的効果の生成・相手ターンを跨いだ持続・自分のターン開始時の
    期限切れまで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)

    def has_until(i):
        out = []

        def w(ops):
            for o in ops:
                out.append(o)
                for k in ("body", "then", "else"):
                    if isinstance(o.get(k), list):
                        w(o[k])
                if isinstance(o.get("modes"), list):
                    for m in o["modes"]:
                        if isinstance(m, list):
                            w(m)
        d = r.cards[i]
        if d.spell:
            w(d.spell)
        for a in d.abilities:
            if a["kind"] in ("trigger", "replace"):
                w(a.get("effect") or a.get("instead") or [])
        return any(o["op"] == "modify" and o.get("duration") == "until_next_own_turn_start" for o in out)
    sel = [i for i in pool if has_until(i)]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 21))
def test_static_remainder_matches(real_env, seed):
    """増分F・カテゴリ3: 常在型の残り（add_races / add_civs / must_be_attacked / battle_indestructible）と
    sum/mul を含む条件を持つ札を多く入れたデッキで、特性の畳み込み（文明・種族の追加、誘引による
    攻撃先の制限、バトル中破壊されないこと、マナの文明の見え方）まで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)

    def has_sum(c):
        if isinstance(c, dict):
            for k, v in c.items():
                if k == "cmp" and isinstance(v, list) and len(v) == 3 and \
                        any(isinstance(e, dict) and ("sum" in e or "mul" in e) for e in (v[0], v[2])):
                    return True
                if has_sum(v):
                    return True
        elif isinstance(c, list):
            return any(has_sum(x) for x in c)
        return False

    def has_f3(d):
        for a in d.abilities:
            if a["kind"] == "static" and any(k in (a.get("mod") or {})
                                             for k in ("add_races", "add_civs", "must_be_attacked", "battle_indestructible")):
                return True
            if "if" in a and has_sum(a["if"]):
                return True
        return any(o.get("op") == "if" and has_sum(o.get("cond")) for o in (d.spell or []))
    sel = [i for i in pool if has_f3(r.cards[i])]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_mana_add_civs_matches(real_env, seed):
    """増分F・カテゴリ3: dm24-106《聖火妖精パルック》（自分のマナゾーンの自然カードに光・火文明を
    追加する常在型）。自然マナだけでは払えない光クリーチャーの支払い可否と支払いの組が、
    マナカードの文明を特性で見る両エンジンで一致すること。"""
    r, b = real_env
    card = "dm24-106"
    assert rustcore._is_plain(r.cards[card])
    light = [i for i, d in r.cards.items()
             if d.types == ["creature"] and not d.abilities and d.civs == ["light"] and d.cost <= 3
             and rustcore._is_plain(d)][:8]
    assert len(light) >= 4
    deck = [card] * 24 + [light[i % len(light)] for i in range(16)]
    spec = {"kind": "new_game", "decks": [deck, deck], "seed": seed, "first_player": seed % 2}
    a, bb = Session.open(r, spec), rustcore.RustSession.open(r, spec, b)
    res = lockstep(a, bb, f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True
    assert any(o.get("keys") and o["keys"][0] == f"play:{card}" for o in a.eng.log)


@pytest.mark.parametrize("seed", range(1, 21))
def test_g_strike_cards_match(real_env, seed):
    """増分F・カテゴリ6: G・ストライク（zone=hand の誘発: シールドから手札に加わった時、相手の
    クリーチャー1体はこのターン攻撃できない）を持つ札を多く入れたデッキで、手札からの誘発収集・
    待機・解決（may → choose → modify）まで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)
    sel = [i for i in pool if "g_strike" in r.cards[i].keywords]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_g_strike_fires_matches(real_env, seed):
    """増分F・カテゴリ6: dm25rp3-056（G・ストライク）をシールドに含むデッキで、ブレイクされて
    手札に加わるたびに誘発が立ち、may の yes_no 決定が実際に現れる局が一致すること。"""
    r, b = real_env
    card = "dm25rp3-056"
    assert rustcore._is_plain(r.cards[card]) and "g_strike" in r.cards[card].keywords
    vanilla = [i for i, d in r.cards.items()
               if d.types == ["creature"] and not d.abilities and d.cost <= 2 and rustcore._is_plain(d)][:8]
    assert len(vanilla) >= 4
    deck = [card] * 20 + [vanilla[i % len(vanilla)] for i in range(20)]
    spec = {"kind": "new_game", "decks": [deck, deck], "seed": seed, "first_player": seed % 2}
    a, bb = Session.open(r, spec), rustcore.RustSession.open(r, spec, b)
    res = lockstep(a, bb, f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True
    assert any(o.get("kind") == "yes_no" for o in a.eng.log)


@pytest.mark.parametrize("seed", range(1, 21))
def test_declare_cards_match(real_env, seed):
    """増分F・カテゴリ4: 使用宣言（declare: 革命チェンジの swap、侵略の play_free、遅延誘発の登録）を
    持つ札を多く入れたデッキで、宣言候補の走査・宣言の諮問・待機と解決、入れ替えの後半処理
    （swap_in / swap_fix）と遅延誘発の収集・期限切れまで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)
    sel = [i for i in pool if any(a["kind"] == "declare" for a in r.cards[i].abilities)]
    assert len(sel) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(sel) if rnd.random() < 0.6 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_revolution_change_fires_matches(real_env, seed):
    """増分F・カテゴリ4: dmex12-076（革命チェンジ: 自分の光/水クリーチャーが攻撃する時、手札の
    このカードと入れ替える）。安い光/水バニラが攻撃するたびに宣言の諮問（declare_attack）が
    現れ、選べば swap で攻撃クリーチャーが差し替わる局が digest まで一致すること。"""
    r, b = real_env
    card = "dmex12-076"
    assert rustcore._is_plain(r.cards[card])
    assert any(a["kind"] == "declare" for a in r.cards[card].abilities)
    vanilla = [i for i, d in r.cards.items()
               if d.types == ["creature"] and not d.abilities and d.cost <= 2
               and set(d.civs) <= {"light", "water"} and rustcore._is_plain(d)][:8]
    assert len(vanilla) >= 4
    deck = [card] * 20 + [vanilla[i % len(vanilla)] for i in range(20)]
    spec = {"kind": "new_game", "decks": [deck, deck], "seed": seed, "first_player": seed % 2}
    a, bb = Session.open(r, spec), rustcore.RustSession.open(r, spec, b)
    res = lockstep(a, bb, f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True
    assert any(o.get("kind") == "declare_attack" for o in a.eng.log)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_trigger_keyword_matches(real_env, seed):
    """増分F・カテゴリ1: keyword 印つき誘発（キーワード辞書から展開された能力）の照合。
    dm01-106《青銅の鎧》は mana_boost_cip の展開（出た時、山札の上1枚をマナへ）だけで、
    印は Python の誘発収集でも Rust の collect_triggers でも読まれない。
    20枚＋安いバニラのデッキで召喚のたびに誘発が解決され、マナゾーンの digest まで一致すること。"""
    r, b = real_env
    card = "dm01-106"
    assert rustcore._is_plain(r.cards[card])
    assert any(a.get("keyword") == "mana_boost_cip" for a in r.cards[card].abilities)
    vanilla = [i for i, d in r.cards.items()
               if d.types == ["creature"] and not d.abilities and d.cost <= 2 and rustcore._is_plain(d)][:8]
    assert len(vanilla) >= 4
    deck = [card] * 20 + [vanilla[i % len(vanilla)] for i in range(20)]
    spec = {"kind": "new_game", "decks": [deck, deck], "seed": seed, "first_player": seed % 2}
    a, bb = Session.open(r, spec), rustcore.RustSession.open(r, spec, b)
    res = lockstep(a, bb, f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True
    assert any(o.get("keys") and o["keys"][0] == f"play:{card}" for o in a.eng.log)


@pytest.mark.parametrize("seed", range(1, 61))
def test_spell_decks_match(real_env, seed):
    """段階3-a: 単純な呪文（引く・選ぶ・移動・タップ・if・may と S・トリガー）を半分入れた実カードのデッキで、
    1局が決定と digest まで一致する。呪文を1枚以上唱えた局であること。"""
    import random
    r, b = real_env
    spells = [i for i in _portable(r) if r.cards[i].types == ["spell"]]
    creatures = [i for i in _portable(r) if r.cards[i].types == ["creature"]]
    assert len(spells) > 100
    rnd = random.Random(seed * 7 + 1)
    decks = [[rnd.choice(spells) for _ in range(20)] + [rnd.choice(creatures) for _ in range(20)] for _ in range(2)]
    spec = {"kind": "new_game", "decks": decks, "seed": seed, "first_player": seed % 2}
    a, bb = Session.open(r, spec), rustcore.RustSession.open(r, spec, b)
    res = lockstep(a, bb, f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True, res.get("divergence")
    sp = set(spells)
    assert any(o.get("keys") and o["keys"][0].startswith("play:") and o["keys"][0].split(":")[1] in sp for o in a.eng.log) \
        or any(e["kind"] == "declare_strigger" and e["keys"] for e in a.eng.log)
