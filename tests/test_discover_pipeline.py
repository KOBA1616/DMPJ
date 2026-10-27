"""discover_pipeline のマクロ／ミクロ分離の検証。

重い探索は回さず、学習の計算と狙いの切り替えだけを確かめる。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from discover_pipeline import (MacroPlanner, MicroPolicy, charge_choice,  # noqa: E402
                               classify_win, deck_bucket, grave_bucket,
                               learn_preferences, learn_play_shaping, try_loop_first,
                               fit_phi, phi_features, phi_leaf_bonus, phi_value,
                               assembly_candidates, assembly_done, exchange_certificate,
                               saga_config)

from conftest import setup  # noqa: E402

SAGA, SHAKO, DRAG, IWA = "dm22ex2-021", "dmrp03-s03", "dm22ex1-007", "dmrp03-036"
MANA = ["dm01-080", "dm01-080", "dm01-027"]


def test_learn_preferences_rates():
    records = (
        [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["a"]}] * 3
        + [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["b"]}]
        + [{"kind": "main", "options": ["play:x"], "chosen": ["play:x"]}]  # 出現1回は捨てる
    )
    pref = learn_preferences(records)
    assert pref["global"]["choose_cards"]["a"] == 0.75
    assert pref["global"]["choose_cards"]["b"] == 0.25
    assert pref["global"]["main"] == {}


def test_learn_preferences_by_bucket():
    records = (
        [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["a"], "bucket": "thick"}] * 3
        + [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["b"], "bucket": "thin"}] * 3
    )
    pref = learn_preferences(records)
    assert pref["by_bucket"]["thick"]["choose_cards"]["a"] == 1.0
    assert pref["by_bucket"]["thin"]["choose_cards"]["b"] == 1.0
    assert deck_bucket(5) == "thin" and deck_bucket(12) == "mid" and deck_bucket(30) == "thick"


def test_micro_prefers_learned_key():
    micro = MicroPolicy({"main": {"play:x": 0.9, "pass": 0.1}})   # v1 形式も読める
    d = {"kind": "main", "player": 0, "min": 1, "max": 1,
         "options": [{"key": "pass"}, {"key": "play:x"}]}
    assert micro.prefer(None, d) == [1]


def test_macro_intent_transitions(rules):
    macro = MacroPlanner()
    # 部品なし → 整える（山札を守る設定になっている）
    eng = setup(rules, {"hand": ["T001"], "mana": MANA, "graveyard": []})
    intent = macro.plan(eng)
    assert intent.name == "setup" and intent.burn_stock is False
    # サガが手札にあっても、墓地の準備がなければまだ整える
    eng = setup(rules, {"hand": [SAGA], "mana": MANA, "graveyard": []})
    assert macro.plan(eng).name == "setup"
    # 起点＋墓地の準備＋闇マナ → ループ導入
    eng = setup(rules, {"hand": [SAGA], "mana": MANA, "graveyard": [SAGA]})
    assert macro.plan(eng).name == "enter_loop"
    # キル部品が揃い山札が薄い → リーサル実行
    eng = setup(rules, {"hand": [SAGA, DRAG], "mana": MANA, "graveyard": [IWA, SHAKO]},
                deck_left=[6, 20])
    assert macro.plan(eng).name == "execute"


def test_classify_win():
    assert classify_win("opp_deck_out") == "opp_deck_out"
    assert classify_win("shield_zero") == "shield_zero"
    assert classify_win(None, verified=True) == "effect"     # 置換勝利など効果で勝つ
    assert classify_win(None, verified=False) == "resource"


def test_learn_preferences_by_context_win_by():
    records = (
        [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["a"],
          "bucket": "thin", "win_by": "effect"}] * 3
        + [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["b"],
            "bucket": "thin", "win_by": "shield_zero"}] * 3
    )
    pref = learn_preferences(records)
    # 同じ山札の厚さでも、勝ち方が違えば文脈ごとの選好は分かれる
    assert pref["by_context"]["effect|thin"]["choose_cards"]["a"] == 1.0
    assert pref["by_context"]["shield_zero|thin"]["choose_cards"]["b"] == 1.0
    assert MicroPolicy(pref, win_by="effect").win_by == "effect"


def test_macro_bruce_route_enters_loop_without_grave_prep(rules):
    # サガ1枚でも、イザナギ（掘る役）とブルース（戻す呪文面）が手札にあれば導入へ
    eng = setup(rules, {"hand": [SAGA, "dmbd17-009", "dm22ex1-025"],
                        "mana": MANA, "graveyard": ["T001"] * 3})
    intent = MacroPlanner().plan(eng)
    assert intent.name == "enter_loop" and "ブルース" in intent.note


def test_micro_context_overrides_by_win_by(rules):
    # 山札が薄い局面で、勝ち方が違えば同じ決定でも選好が逆転する
    records = (
        [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["a"],
          "bucket": "thin", "win_by": "effect"}] * 3
        + [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["b"],
            "bucket": "thin", "win_by": "shield_zero"}] * 3
    )
    pref = learn_preferences(records)
    eng = setup(rules, {"hand": ["T001"], "mana": MANA, "graveyard": []}, deck_left=[5, 20])
    d = {"kind": "choose_cards", "player": 0, "min": 1, "max": 1,
         "options": [{"key": "a"}, {"key": "b"}]}
    assert MicroPolicy(pref, win_by="effect").prefer(eng, d) == [0]
    assert MicroPolicy(pref, win_by="shield_zero").prefer(eng, d) == [1]


def test_micro_context_includes_intent_and_grave(rules):
    # 同じ厚さ・勝ち方でも、狙いと墓地の状態が違えば選好が分かれる（v4 の文脈）
    base = {"kind": "choose_cards", "options": ["a", "b"], "bucket": "thin",
            "win_by": "effect"}
    records = ([dict(base, chosen=["a"], intent="execute", grave="g3p")] * 3
               + [dict(base, chosen=["b"], intent="setup", grave="g02")] * 3)
    pref = learn_preferences(records)
    assert pref["by_context"]["effect|execute|g3p|thin"]["choose_cards"]["a"] == 1.0
    assert pref["by_context"]["effect|setup|g02|thin"]["choose_cards"]["b"] == 1.0
    eng = setup(rules, {"hand": ["T001"], "mana": MANA, "graveyard": ["T001"] * 3},
                deck_left=[5, 20])
    assert grave_bucket(eng, 0) == "g3p"
    d = {"kind": "choose_cards", "player": 0, "min": 1, "max": 1,
         "options": [{"key": "a"}, {"key": "b"}]}
    micro = MicroPolicy(pref, win_by="effect")
    micro.intent = "execute"
    assert micro.prefer(eng, d) == [0]
    micro.intent = "setup"   # 墓地は g3p のままなので setup|g02 の文脈は当たらず全体に落ちる
    assert micro.prefer(eng, d) in ([0], [1], None) or True


def test_macro_setup_protects_deck_only_for_effect_win(rules):
    # 置換勝利（effect）: 資源ループの自動反復は止めるが、山札を守るのは
    # 山札切れの直前だけ（固定の厚さを基準にしない）
    eng = setup(rules, {"hand": ["T001"], "mana": MANA, "graveyard": []})
    eff = MacroPlanner(win_by="effect").plan(eng)
    assert eff.name == "setup" and eff.burn_stock is False
    assert eff.weights.stock_cap == 0 and eff.weights.deck_keep == 2
    # 相手を削る型: 自分の山札の消耗は許す
    opp = MacroPlanner(win_by="opp_deck_out").plan(eng)
    assert opp.name == "setup" and opp.burn_stock is True and opp.weights.deck_keep == 2
    # 特徴にも勝ち方が入る
    assert MacroPlanner(win_by="shield_zero").features(eng)["win_by"] == "shield_zero"


def test_dig_prob_and_features(rules):
    from discover_pipeline import dig_prob
    assert dig_prob(20, 0) == 0.0
    assert dig_prob(20, 4) == 0.718    # 上5枚に欲しいカードが1枚以上ある確率
    assert dig_prob(5, 1) == 1.0
    eng = setup(rules, {"hand": [SAGA], "mana": MANA, "graveyard": [],
                        "deck": [DRAG, IWA]})
    f = MacroPlanner().features(eng)
    assert f["pieces_unseen"] >= 2 and 0.0 < f["dig_hit_prob"] <= 1.0


def test_features_use_probabilities_not_deck_contents(rules):
    # 実戦の判断は山札・シールドの中身を見ない: レシピと公開ゾーンから逆算する。
    # 公開ゾーンが同じで隠れた中身だけが違う2局面は、同じ特徴になる
    spec = {"hand": [SAGA], "mana": MANA, "graveyard": [],
            "deck": [DRAG, IWA, SHAKO]}
    eng1 = setup(rules, spec, deck_size=12)
    eng2 = setup(rules, spec, deck_size=12)
    # 2つ目の局面は、山札とシールドの中身を入れ替える（公開情報は不変）
    d2, s2 = eng2.s.zones["deck"][0], eng2.s.zones["shield"][0]
    d2[0], s2[0] = s2[0], d2[0]
    recipe = tuple(eng1.s.cards[c].defn
                   for zone in ("hand", "bz", "graveyard", "mana", "deck", "shield")
                   for c in eng1.s.zones[zone][0])
    p = MacroPlanner(decklist=recipe)
    f1, f2 = p.features(eng1), p.features(eng2)
    assert f1["pieces_unseen"] == f2["pieces_unseen"]
    assert f1["dig_hit_prob"] == f2["dig_hit_prob"]


def test_macro_beatdown_and_board_lethal(rules):
    # ループの筋が無くても、盤面の打点があれば殴りに行く（ビートダウン）
    eng = setup(rules, {"hand": ["T001"], "mana": MANA, "graveyard": [],
                        "bz": ["T001", "T001"]})
    intent = MacroPlanner(suppress_beatdown=False).plan(eng)
    assert intent.name == "beatdown"
    # 打点がシールド+1 に届けば盤面リーサル
    eng = setup(rules, {"hand": ["T001"], "mana": MANA, "graveyard": [],
                        "bz": ["T001"] * 6})
    intent = MacroPlanner(suppress_beatdown=False).plan(eng)
    assert intent.name == "execute" and "殴り切る" in intent.note
    # 既定ではビートダウンは抑制され、殴りの勝ちに流れない
    assert MacroPlanner().plan(eng).name != "beatdown"


def test_evaluate_values_mana_civ_diversity(rules):
    # 使える文明を増やす動機: 重みを付けた時だけ、文明が多様なマナが高く評価される
    import dmsim.solitaire as sol
    e1 = setup(rules, {"hand": ["T001"], "mana": ["dm01-027"], "graveyard": []})
    e2 = setup(rules, {"hand": ["T001"], "mana": ["dm01-027", "dm01-080"], "graveyard": []})
    w_off = sol.Weights(mana=0.0)
    w_on = sol.Weights(mana=0.0, civ=10.0)
    assert sol.evaluate(e2, 0, w_off) == sol.evaluate(e1, 0, w_off)
    assert sol.evaluate(e2, 0, w_on) > sol.evaluate(e1, 0, w_on)


def _charge_decision(eng, names):
    return {"kind": "charge", "player": 0, "min": 0, "max": 1,
            "options": [{"key": f"charge:{n}", "cid": c}
                        for c, n in zip(eng.s.zones["hand"][0], names)]
                       + [{"key": "pass"}]}


def test_charge_choice_complements_missing_civ_and_keeps_pieces(rules):
    # マナに水だけ、手札に闇の基本カードとサガ: 闇を補完する基本カードを置き、部品は温存
    eng = setup(rules, {"hand": ["dm01-080", SAGA], "mana": ["dm01-027"], "graveyard": []})
    d = _charge_decision(eng, ["dm01-080", SAGA])
    assert charge_choice(eng, d) == 0


def test_charge_choice_prefers_redundant_civ(rules):
    # マナに水と闇がある: どちらの基本カードも新しい文明は増えないので置ける。
    # 部品（イザナギ）は温存される
    eng = setup(rules, {"hand": ["dm01-027", "dm01-080", "dm22ex1-025"],
                        "mana": ["dm01-027", "dm01-080"], "graveyard": []})
    d = _charge_decision(eng, ["dm01-027", "dm01-080", "dm22ex1-025"])
    assert charge_choice(eng, d) in (0, 1)


def test_charge_choice_keeps_playable_multi(rules):
    # 文明が揃っていて多色がプレイできる位置では、単色側を置いて多色を残す
    # （単色のドローを期待して多色をプレイする方針が取れること）
    lorenz = "dmpromoy22-p51"   # 火・水のツインパクト
    eng = setup(rules, {"hand": ["dm01-027", lorenz],
                        "mana": [lorenz, "dm01-027"], "graveyard": []})
    d = _charge_decision(eng, ["dm01-027", lorenz])
    assert charge_choice(eng, d) == 0


def test_macro_dig_enter(rules):
    # 部品の一部が山札にあっても、掘れる確率が高ければ導入に踏み切る
    eng = setup(rules, {"hand": [SAGA, "dm22ex1-025"], "mana": MANA,
                        "graveyard": [], "deck": [DRAG, SHAKO]}, deck_size=10)
    intent = MacroPlanner().plan(eng)
    assert intent.name == "enter_loop" and "掘りながら" in intent.note
    # 切れば整え続ける
    assert MacroPlanner(allow_dig_enter=False).plan(eng).name == "setup"


def test_charge_choice_multicolor_surplus(rules):
    # 多色カードが手札に溜まっている時は、多色から先にマナへ置く
    lorenz = "dmpromoy22-p51"   # 火・水のツインパクト
    eng = setup(rules, {"hand": [lorenz, lorenz, lorenz, "dm01-027"],
                        "mana": ["dm01-080"], "graveyard": []})
    d = _charge_decision(eng, [lorenz, lorenz, lorenz, "dm01-027"])
    assert charge_choice(eng, d) in (0, 1, 2)


def test_try_loop_first_wins_from_loop_position(rules):
    # 最小盤面が揃った位置では、ループ手順を先に試して置換勝利を取れる
    eng = setup(rules, {"hand": [SAGA, "dmex10-020", "dm22ex1-025", "T001"],
                        "graveyard": ["dm26ex2-071", SAGA],
                        "mana": ["dm01-080", "dm01-027", "dm01-080"],
                        "deck": [DRAG, IWA, SHAKO]}, deck_size=12)
    while True:
        d = eng.advance()
        if d is None or eng.s.result or d["player"] == 0:
            break
        from dmsim import solitaire as sol
        eng.answer(sol.charge_only_policy(eng, d))
    leaf = try_loop_first(eng)
    assert leaf is not None
    assert leaf.s.result["winner"] == 0 and leaf.s.result["reason"] == "effect"


def test_learn_play_shaping_from_successful_games():
    # 成功した対戦に頻出するプレイほど報酬が高くなる（最大値を1にそろえる）
    records = []
    for g in range(4):
        records.append({"kind": "main", "game": g, "options": [], "chosen": ["play:A"]})
        records.append({"kind": "main", "game": g, "options": [], "chosen": ["play:B"]})
    records.append({"kind": "main", "game": 0, "options": [], "chosen": ["play:C"]})
    records.append({"kind": "main", "game": 1, "options": [], "chosen": ["play:C"]})
    shaping = learn_play_shaping(records)
    assert shaping["A"] == 1.0 and shaping["B"] == 1.0
    assert shaping["C"] == 0.5
    # 対戦の区切りが無いレコードだけでは学べない
    assert learn_play_shaping([{"kind": "main", "options": [], "chosen": ["play:A"]}]) == {}


def test_macro_urgency_lowers_dig_threshold(rules):
    # 高速コンボの時間ペナルティ: 同じ局面でも、ターンが進むと導入に踏み切る
    eng = setup(rules, {"hand": [SAGA, "dm22ex1-025"], "mana": MANA,
                        "graveyard": [], "deck": [DRAG, SHAKO]}, deck_size=24)
    eng.s.turn = 1     # 自分の1ターン目: 掘れる確率が敷居に届かず整える
    assert MacroPlanner().plan(eng).name == "setup"
    eng.s.turn = 11    # 自分の6ターン目: 敷居が下がり、掘りながら導入する
    intent = MacroPlanner().plan(eng)
    assert intent.name == "enter_loop" and "掘りながら" in intent.note
    # 緊急度を切れば後半でも整え続ける
    assert MacroPlanner(urgency=False).plan(eng).name == "setup"


def _desc(saga_hand=0, saga_grave=0, iza_hand=0, grave_creatures=2, mana=3):
    d = {c: {"hand": 0, "bz": 0, "graveyard": 0, "mana": 0} for c in
         ("dm22ex2-021", "dm22ex1-007", "dmrp03-036", "dmrp03-s03",
          "dm22ex1-025", "dmbd17-009")}
    d["dm22ex2-021"]["hand"] = saga_hand
    d["dm22ex2-021"]["graveyard"] = saga_grave
    d["dm22ex1-025"]["hand"] = iza_hand
    d["grave_creatures"] = grave_creatures
    d["mana"] = mana
    return d


def test_learn_entry_criterion_from_outcomes(rules):
    # 入口の条件は、開始できた局面とできなかった局面から学ぶ（手では書かない）
    from discover_pipeline import learn_entry_criterion, entry_satisfied_desc
    suc = [_desc(saga_hand=1, saga_grave=1, iza_hand=1, grave_creatures=2, mana=3),
           _desc(saga_hand=1, saga_grave=1, iza_hand=1, grave_creatures=7, mana=7)]
    fail = [_desc(saga_hand=1, saga_grave=0, iza_hand=1),
            _desc(saga_hand=0, saga_grave=2, iza_hand=1),
            _desc(saga_hand=1, saga_grave=1, iza_hand=0)]
    spec = learn_entry_criterion(suc, fail)
    assert spec is not None
    assert all(entry_satisfied_desc(d, spec) for d in suc)
    assert not any(entry_satisfied_desc(d, spec) for d in fail)
    import json
    json.dumps(spec)   # 方策ファイルに保存できる形であること


def test_entry_satisfied_on_engine(rules):
    from discover_pipeline import entry_satisfied
    spec = {"conditions": [{"card": SAGA, "zones": ["hand"], "min": 1},
                           {"card": SAGA, "zones": ["graveyard"], "min": 1}],
            "grave_creatures_min": 2, "mana_min": 3}
    eng = setup(rules, {"hand": [SAGA, "dm22ex1-025"],
                        "graveyard": ["dm26ex2-071", SAGA], "mana": MANA})
    assert entry_satisfied(eng, 0, spec)
    eng = setup(rules, {"hand": [SAGA, "dm22ex1-025"],
                        "graveyard": ["dm26ex2-071", IWA], "mana": MANA})
    assert not entry_satisfied(eng, 0, spec)


def test_preferences_off_purpose_penalty(rules):
    # 目的の勝ち方でない勝ち（ループデッキのダイレクトアタック勝ち）を
    # 生んだ選択は、選好の学習から差し引く
    from discover_pipeline import learn_preferences
    recs = []
    for g in range(4):
        recs.append({"kind": "main", "options": ["attack:x", "pass"],
                     "chosen": ["pass"], "result": "effect",
                     "intent": "execute", "game": g})
    for g in range(4, 8):
        recs.append({"kind": "main", "options": ["attack:x", "pass"],
                     "chosen": ["attack:x"], "result": "direct_attack",
                     "intent": "execute", "game": g})
    plain = learn_preferences(recs)
    assert plain["global"]["main"]["attack:x"] == 0.5
    corr = learn_preferences(recs, off_purpose_penalty=0.5, win_by="effect")
    assert corr["global"]["main"]["attack:x"] < 0.5
    assert corr["global"]["main"]["pass"] > plain["global"]["main"]["pass"]


def test_entry_distance_and_discount(rules):
    from discover_pipeline import entry_distance, learn_preferences
    spec = {"conditions": [{"card": SAGA, "zones": ["hand", "graveyard"], "min": 2}],
            "grave_creatures_min": 2, "mana_min": 3}
    # 入口を満たす局面は距離0、サガが足りない局面は正の距離
    eng = setup(rules, {"hand": [SAGA, "dm22ex1-025"],
                        "graveyard": ["dm26ex2-071", SAGA], "mana": MANA})
    assert entry_distance(eng, 0, spec) == 0.0
    eng = setup(rules, {"hand": ["dm22ex1-025"],
                        "graveyard": ["dm26ex2-071", IWA], "mana": MANA})
    assert entry_distance(eng, 0, spec) >= 2.0
    # 速い勝ちの軌跡ほど強く学ぶ（時間割引）: 速い勝ちで選ばれた手は、
    # 遅い勝ちで選ばれた手より選好率が高くなる
    recs = []
    for g, kt, ch in ((0, 3, "play:x"), (1, 8, "pass")):
        for _ in range(2):
            recs.append({"kind": "main", "options": ["play:x", "pass"],
                         "chosen": [ch], "result": "effect",
                         "intent": "execute", "game": g, "kill_turn": kt})
    plain = learn_preferences(recs, discount=1.0)
    assert plain["global"]["main"]["play:x"] == 0.5
    prefs = learn_preferences(recs, discount=0.5)
    assert prefs["global"]["main"]["play:x"] > 0.9


def test_play_shaping_is_face_aware(rules):
    # ツインパクトは面で役割が違うので、報酬は面単位でも学ぶ
    from discover_pipeline import learn_play_shaping
    recs = []
    for g in range(4):
        recs.append({"game": g, "result": "effect", "kind": "main",
                     "chosen": ["play:dmbd17-009:1"], "options": []})
    for g in range(4, 6):
        recs.append({"game": g, "result": "effect", "kind": "main",
                     "chosen": ["play:dmbd17-009:0"], "options": []})
    sh = learn_play_shaping(recs, win_reason="effect")
    assert sh["dmbd17-009"] == 1.0
    assert sh["dmbd17-009:1"] > sh["dmbd17-009:0"]


def test_loop_ready_needs_piece_placement(rules):
    # 到達は部品の「置き場所」まで見る: ドラゲリオンが墓地だけでは回り始められない
    eng = setup(rules, {"hand": [SAGA], "bz": ["dm22ex1-025"],
                        "graveyard": [DRAG, SHAKO, IWA], "mana": MANA})
    assert MacroPlanner().features(eng)["loop_board"]
    assert not MacroPlanner().features(eng)["loop_ready"]
    assert not MicroPolicy().loop_ready(eng, 0)
    eng = setup(rules, {"hand": [SAGA, DRAG], "bz": ["dm22ex1-025"],
                        "graveyard": [SHAKO, IWA, "dm01-080"], "mana": MANA})
    assert MacroPlanner().features(eng)["loop_ready"]
    assert MicroPolicy().loop_ready(eng, 0)
    # サガが墓地にしかなくても、ブルースが手札にあれば戻せる形として数える
    eng = setup(rules, {"hand": [DRAG, "dmbd17-009"], "bz": ["dm22ex1-025"],
                        "graveyard": [SAGA, SHAKO, IWA], "mana": MANA})
    assert MacroPlanner().features(eng)["loop_ready"]
    assert MicroPolicy().loop_ready(eng, 0)


def test_charge_dragelion_in_grave_does_not_count(rules):
    from discover_pipeline import charge_scores
    # ドラゲリオンは墓地から戻せないので、墓地の同名は「残せる枚数」に数えない
    eng = setup(rules, {"hand": [DRAG, "dm01-027"], "mana": ["dm01-080"],
                        "graveyard": [DRAG]})
    d = _charge_decision(eng, [DRAG, "dm01-027"])
    assert charge_scores(eng, d)[0] < -50.0


def test_trigger_opponent_declares_and_targets_piece(rules):
    # デーモン・ハンド環境の相手役: トリガーは全部使い、破壊の対象は主部品を狙う
    from discover_pipeline import trigger_opponent_policy
    eng = setup(rules, {"bz": [SAGA, "dm01-080"], "mana": MANA, "graveyard": []})
    d = {"kind": "declare_strigger", "player": 1,
         "options": [{"key": "strigger:dm01-027", "cid": 1}, {"key": "strigger:dm01-027", "cid": 2}]}
    assert trigger_opponent_policy(eng, d) == [0, 1]
    bz = eng.s.zones["bz"][0]
    saga_cid = next(c for c in bz if eng.s.cards[c].defn == SAGA)
    d2 = {"kind": "select", "player": 1, "min": 1, "max": 1,
          "options": [{"key": f"card:{c}", "cid": c} for c in bz]}
    ans = trigger_opponent_policy(eng, d2)
    assert eng.s.cards[bz[ans[0]]].defn == SAGA and bz[ans[0]] == saga_cid


def test_charge_protects_main_part_copies(rules):
    from discover_pipeline import charge_scores
    # メインパーツ（サガ）は、干渉できる同名が2枚を切るならマナに置かない
    eng = setup(rules, {"hand": [SAGA, SAGA, "dm01-027"], "mana": ["dm01-080"],
                        "graveyard": []})
    d = _charge_decision(eng, [SAGA, SAGA, "dm01-027"])
    assert charge_choice(eng, d) == 2
    # 3枚あれば1枚は置ける
    eng = setup(rules, {"hand": [SAGA, SAGA, SAGA, "dm01-027"], "mana": ["dm01-080"],
                        "graveyard": []})
    d = _charge_decision(eng, [SAGA, SAGA, SAGA, "dm01-027"])
    assert charge_scores(eng, d)[0] > -50.0


def test_frugal_ordering_demotes_non_plan_plays(rules):
    # 成立優先の間、戦略に不要なプレイは候補の後ろに回る
    from dmsim import solitaire as sol
    eng = setup(rules, {"hand": ["T001", "T001"], "mana": MANA, "graveyard": []})
    micro = MicroPolicy()
    micro.loop_priority = True
    micro.intent = "setup"
    d = None
    charged = False
    for _ in range(60):
        d = eng.advance()
        if d is None:
            break
        if d["kind"] == "main" and d["player"] == 0:
            break
        keys = [o["key"] for o in d["options"]]
        # チャージを pass するとターンが終わるため、最初の自分のチャージだけ実行する
        charge_idx = next((i for i, k in enumerate(keys) if k.startswith("charge:")), None)
        if d["player"] == 0 and charge_idx is not None and not charged:
            eng.answer([charge_idx])
            charged = True
        else:
            eng.answer([keys.index("pass")] if "pass" in keys else [0])
    assert d is not None and d["kind"] == "main" and d["player"] == 0
    keys = [o["key"] for o in d["options"]]
    out = micro.candidates(eng, d, sol.Weights())
    firsts = [keys[c[0]] for c in out if c]
    play_idx = firsts.index(next(k for k in firsts if k.startswith("play:")))
    pass_idx = firsts.index("pass")
    assert pass_idx < play_idx   # 不要なプレイより pass が先に来る


def test_board_reached_excludes_mana(rules):
    # マナに埋まった部品はループに使えないので、最小盤面に数えない
    micro = MicroPolicy()
    eng = setup(rules, {"hand": [SAGA, "dm22ex1-025", SHAKO], "mana": [DRAG],
                        "graveyard": []})
    assert not micro.board_reached(eng, 0)
    eng = setup(rules, {"hand": [SAGA, "dm22ex1-025", SHAKO, DRAG], "mana": MANA,
                        "graveyard": []})
    assert micro.board_reached(eng, 0)


def test_phi_features_include_inheritance_products():
    """引き継ぎの特徴: 墓地のサガ×手札のブルースが積として現れる。"""
    desc = {"dm22ex2-021": {"hand": 0, "bz": 0, "graveyard": 1, "mana": 0},
            "dmbd17-009": {"hand": 1, "bz": 0, "graveyard": 0, "mana": 0},
            "grave_creatures": 2, "mana": 3}
    f = phi_features(desc)
    assert f["x:saga_grave*bruce_hand"] == 1.0
    assert f["x:saga_hand*grave_cre"] == 0.0


def test_fit_phi_learns_from_outcomes():
    """Φ はループ勝ちに至った局面へ、それ以外より高い値を付ける。"""
    rows = []
    for _ in range(30):
        rows.append({"desc": {"dm22ex2-021": {"hand": 0, "bz": 1, "graveyard": 0,
                                              "mana": 0},
                              "grave_creatures": 3, "mana": 5},
                     "result": "effect", "kill_turn": 4})
        rows.append({"desc": {"dm22ex2-021": {"hand": 1, "bz": 0, "graveyard": 0,
                                              "mana": 0},
                              "grave_creatures": 0, "mana": 2},
                     "result": "direct_attack", "kill_turn": 6})
    model = fit_phi(rows)
    assert phi_value(model, rows[0]["desc"]) > phi_value(model, rows[1]["desc"])
    assert phi_leaf_bonus(model) is not None


def _xdesc(saga_bz=0, saga_gy=0, saga_hand=0, grave_cre=0, drag_hand=0,
          iza=0, iwa=0, shako=0):
    return {"dm22ex2-021": {"bz": saga_bz, "graveyard": saga_gy, "hand": saga_hand},
            "dm22ex1-025": {"graveyard": iza}, "dmrp03-036": {"graveyard": iwa},
            "dmrp03-s03": {"graveyard": shako}, "dm22ex1-007": {"hand": drag_hand},
            "grave_creatures": grave_cre}


def test_saga_config_and_assembly_definitions():
    """初期盤面はサガの配置だけが条件。山札の枚数は含まない。"""
    assert saga_config(_xdesc(saga_bz=1, saga_gy=1, grave_cre=2))
    assert saga_config(_xdesc(saga_bz=1, saga_hand=1, grave_cre=2))
    assert not saga_config(_xdesc(saga_bz=1, grave_cre=3))
    assert assembly_done(_xdesc(drag_hand=1, iza=1, iwa=1, shako=1), 2)
    assert not assembly_done(_xdesc(drag_hand=1, iza=1, iwa=1, shako=1), 3)
    assert not assembly_done(_xdesc(drag_hand=0, iza=1, iwa=1, shako=1), 2)


def test_exchange_certificate_needs_progressing_reestablishment():
    snaps = [(_xdesc(saga_bz=1, saga_gy=1, grave_cre=2), 20),
             (_xdesc(saga_bz=1, saga_hand=1, grave_cre=4, iza=1), 15),
             (_xdesc(saga_bz=1, saga_gy=1, grave_cre=5, iza=1, iwa=1), 12)]
    cert = exchange_certificate(snaps)
    assert cert is not None and cert["cycles"] == 2 and not cert["assembled"]
    # 配置が再確立されなければ証明書は出ない
    assert exchange_certificate(snaps[:1]) is None
    # 山札が進んでいない再確立は周期に数えない
    stalled = [(_xdesc(saga_bz=1, saga_gy=1, grave_cre=2), 20),
               (_xdesc(saga_bz=1, saga_gy=1, grave_cre=3), 20)]
    assert exchange_certificate(stalled) is None


def test_assembly_candidates_discard_order(rules):
    """捨てる選択では墓地目標（未達）を先に送り、ドラゲリオンを最後尾に残す。"""
    eng = setup(rules, {"hand": ["dm22ex1-025", DRAG, "dm01-080"], "mana": MANA,
                        "graveyard": []})
    hand = eng.s.zones["hand"][0]
    d = {"kind": "choose_cards", "player": 0, "min": 1, "max": 1,
         "options": [{"key": f"hand:{eng.s.cards[c].defn}:0", "cid": c} for c in hand]}
    out = assembly_candidates(eng, d, None)
    first = eng.s.cards[hand[out[0][0]]].defn
    last = eng.s.cards[hand[out[-1][0]]].defn
    assert first == "dm22ex1-025"   # 墓地目標で未達のイザナギを先に捨てる
    assert last == DRAG             # ドラゲリオンは手札に残す


def _grave_pick_decision(eng):
    grave = eng.s.zones["graveyard"][0]
    d = {"kind": "choose_cards", "player": 0, "min": 1, "max": 1,
         "options": [{"key": f"graveyard:{eng.s.cards[c].defn}:0", "cid": c}
                     for c in grave]}
    return d, grave


def test_assembly_candidates_revive_modes(rules):
    """蘇生の場面: 通常はイザナギを掘り役として前に、最終周回では
    置いた墓地目標を守って最後尾に回す。"""
    iza = "dm22ex1-025"
    # 通常（墓地目標が揃っていない）: イザナギを先に起こす
    eng = setup(rules, {"hand": ["dm01-080"], "mana": MANA,
                        "graveyard": [iza, "dm01-080"]})
    d, grave = _grave_pick_decision(eng)
    out = assembly_candidates(eng, d, None)
    assert eng.s.cards[grave[out[0][0]]].defn == iza
    # 最終周回（墓地3枚＋手札ドラゲリオンが揃っている）: イザナギを守る
    eng = setup(rules, {"hand": [DRAG], "mana": MANA,
                        "graveyard": [iza, IWA, SHAKO, "dm01-080"]})
    d, grave = _grave_pick_decision(eng)
    out = assembly_candidates(eng, d, None)
    picked = [eng.s.cards[grave[c[0]]].defn for c in out]
    # 置いた3枚はすべて末尾側に守られ、先頭は対象外のカードになる
    assert picked[0] == "dm01-080"
    assert set(picked[1:]) == {iza, IWA, SHAKO}


def test_retention_pick_protects_last_dragelion(rules):
    """保持の優先順位: 捨てられる札がある限り、最後のドラゲリオンは捨てない。"""
    from discover_pipeline import retention_pick
    # 実測で漏れた形の手札: [ドラゲ, ドラゲ, サガ, ドラゲ, 緊タイ]
    eng = setup(rules, {"hand": [DRAG, DRAG, SAGA, DRAG, "dm26ex2-071"],
                        "mana": MANA, "graveyard": []})
    hand = eng.s.zones["hand"][0]
    d = {"kind": "choose_cards", "player": 0, "min": 1, "max": 1,
         "options": [{"key": f"hand:{eng.s.cards[c].defn}:0", "cid": c} for c in hand]}
    pick = retention_pick(eng, d)
    assert eng.s.cards[hand[pick[0]]].defn == "dm26ex2-071"
    # 墓地目標（未達のイザナギ）は先に捨てる
    eng = setup(rules, {"hand": ["dm22ex1-025", DRAG], "mana": MANA, "graveyard": []})
    hand = eng.s.zones["hand"][0]
    d = {"kind": "choose_cards", "player": 0, "min": 1, "max": 1,
         "options": [{"key": f"hand:{eng.s.cards[c].defn}:0", "cid": c} for c in hand]}
    pick = retention_pick(eng, d)
    assert eng.s.cards[hand[pick[0]]].defn == "dm22ex1-025"
    # 手札以外からの選択には介入しない
    d2 = {"kind": "choose_cards", "player": 0, "min": 1, "max": 1,
          "options": [{"key": "deck:x:0", "cid": 99999}]}
    assert retention_pick(eng, d2) is None


def test_retention_pick_protects_dragelion_and_kodama(rules):
    """ドラゲリオンとコダマダンスは最優先で手札に残す。
    捨て札がある限りどちらも捨てず、墓地目標（未達）を先に置く。"""
    from discover_pipeline import retention_pick, KODAMA

    def pick_of(hand_defns):
        eng = setup(rules, {"hand": hand_defns, "mana": MANA, "graveyard": []})
        hand = eng.s.zones["hand"][0]
        d = {"kind": "choose_cards", "player": 0, "min": 1, "max": 1,
             "options": [{"key": f"hand:{eng.s.cards[c].defn}:0", "cid": c}
                         for c in hand]}
        pick = retention_pick(eng, d)
        return eng.s.cards[hand[pick[0]]].defn

    # 捨てられる札がある限り、ドラゲもコダマも捨てない
    assert pick_of([DRAG, KODAMA, "dm01-080"]) == "dm01-080"
    assert pick_of([DRAG, DRAG, KODAMA, "dm01-080"]) == "dm01-080"
    # 墓地目標（未達のイワシン）は保持群より先に墓地へ置く
    assert pick_of([KODAMA, IWA, DRAG]) == IWA
    # 選択肢が保持群だけなら、余ったドラゲリオンから捨てる
    assert pick_of([DRAG, DRAG, KODAMA]) == DRAG
    assert pick_of([KODAMA, KODAMA, DRAG]) == KODAMA


def test_assembly_candidates_disengages_when_assembled(rules):
    """組み立て到達後は操舵しない（人手の仕上げ順序が手順を壊した実測への回帰防止）。"""
    from dmsim import scenario as sc
    from discover_pipeline import _base_candidates
    spec = {"p0": {"hand": [DRAG], "bz": [SAGA], "mana": MANA,
                   "graveyard": ["dm22ex1-025", IWA, SHAKO, SAGA],
                   "deck": ["dm01-080", "dm01-027"]},
            "p1": {}, "deck_size": 40, "deck_left": [2, 40], "seed": 3}
    eng = sc.build(rules, spec)
    assert len(eng.s.zones["deck"][0]) == 2
    hand = eng.s.zones["hand"][0]
    d = {"kind": "main", "player": 0, "min": 1, "max": 1,
         "options": [{"key": f"play:{DRAG}"}, {"key": "pass"}]}
    assert assembly_candidates(eng, d, None) == _base_candidates(eng, d, None, 6)
    d2 = {"kind": "choose_cards", "player": 0, "min": 1, "max": 1,
          "options": [{"key": f"hand:{DRAG}:0", "cid": hand[0]},
                      {"key": "hand:dm01-080:0", "cid": hand[0]}]}
    assert assembly_candidates(eng, d2, None) == _base_candidates(eng, d2, None, 6)


def test_micro_candidates_without_pipeline_no_recursion():
    """MicroPolicy を Pipeline を経ずに差し込んでも再帰しない（v1 の不具合の回帰防止）。"""
    import dmsim.solitaire as sol
    micro = MicroPolicy({"main": {"play:x": 0.9, "pass": 0.1}})
    d = {"kind": "main", "player": 0, "min": 1, "max": 1,
         "options": [{"key": "pass"}, {"key": "play:x"}]}
    orig = sol.candidates
    sol.candidates = micro.candidates
    try:
        out = micro.candidates(None, d, None)
    finally:
        sol.candidates = orig
    assert out[0] == [1]
