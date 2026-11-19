"""語彙パイロット第278弾: filter_race_and（種族の AND フィルタ races_all）。

rejects の filter_race_and 純粋3件はいずれも「アンノウンとゼニス両方を
種族に持つ」という種族の AND 条件だけが不足:
- dm23ex3-t13 黒神龍オンバシ・ラオーン（両種族クリーチャーが出た時に
  自分を破壊する誘発の subject フィルタ）
- dm23ex3-t01 極頂秘伝ゼニス・シンフォニー（呪文面の召喚対象フィルタ）
- dm24bd6-023 「武」の頂 マキシマム・ザ・マックス（ツインパクト呪文面が
  dm23ex3-t01 と同文）

既存の filter の races は OR（どれか1つを持てばよい）、race_has は部分一致の
OR で、2種族の両方を要求する形が無かった。文明には同じ非対称があり、
civs（OR）に対して civs_all（第24弾）が用意されている。本弾はその種族版
として新フィルタキー races_all を追加する:

- defs.FILTER_KEYS に "races_all" を追加（値の式化は civs_all と同じく不可）
- selectors.filter_match: set(races_all) <= set(ch["races"])（civs_all と
  同形。文字列が来た場合は civs の _civ_list と同じく単一種族として正規化）
- スキーマは filter キー enum の差分のみで再生成。新規 GameState
  フィールドなし（state.rs 変更なし）。Rust の単純形に races_all を含む
  フィルタは現れない（未知キーとして Python 側で評価される）。

プロト:
- T787 両種族獣（アンノウン＋ゼニス）/ T788 アンノウンのみ / T789 ゼニスのみ
- T790 監視獣: 両種族クリーチャーが出た時に山札の上から1枚をマナゾーンに
  置く誘発（t13 の subject フィルタの形。観測はマナ枚数で行う。ドローだと
  相手ターン内の発火と自分の次のターンのドローが数え分けられないため）
- T791 召喚呪文: 手札から両種族クリーチャーを無償召喚し、ターン終了時に
  手札へ戻す（t01 呪文面の形。play_free の as: 束縛＋delayed_trigger の
  turn_end 戻しはニンジャ・ストライクの登録先例と同形）
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()
BOTH = ["アンノウン", "ゼニス"]


def _defns(e, zone, p):
    # zlist("bz", p) は共有ゾーンで両軍分を含むため、バトルゾーンは bz_tops で絞る
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第277弾のものから play / choose フックだけを残した形）。

    play: main 決定で (e, d) -> 答えのリストか None を返すフック。
    choose: choose_cards へのフック (e, d) -> 答えのリストか None。
    seen に全決定種別を記録する。
    """

    def __init__(self, play=None, choose=None):
        self.play = play
        self.choose = choose
        self.seen = []

    def run(self, e, stop, limit=800):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen.append(kind)
            if kind == "choose_cards" and self.choose is not None:
                ans = self.choose(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "main" and self.play is not None:
                ans = self.play(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "declare_strigger":
                e.answer([])
            elif kind == "declare_sback":
                e.answer([])
            elif kind == "choose_breaker":
                e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
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
            if stop(e):
                return
        raise AssertionError("limit reached")


def _play_once(key, capture=None):
    seen = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            if capture is not None:
                capture(e)
            return [keys.index(key)]
        return None

    return play


# ---------- parse / validation ----------

def test_pilot278_protos_parse():
    rules = load_rules()
    assert rules.cards["T787"].races == BOTH
    assert rules.cards["T788"].races == ["アンノウン"]
    assert rules.cards["T789"].races == ["ゼニス"]
    trig = rules.cards["T790"].abilities[0]
    assert trig["kind"] == "trigger"
    assert trig["when"]["subject"]["filter"]["races_all"] == BOTH
    sp = rules.cards["T791"].faces[0].spell if rules.cards["T791"].faces else None
    ops = sp if sp is not None else rules.cards["T791"].spell
    assert ops[0]["select"]["filter"]["races_all"] == BOTH


def test_races_all_validation():
    base = {"id": "X278", "name": "検証用", "types": ["creature"],
            "civs": ["nature"], "cost": 1, "power": 1000,
            "abilities": [{"kind": "trigger",
                           "when": {"event": "move", "to": "bz",
                                    "subject": {"owner": "you",
                                                "filter": {"types": ["creature"],
                                                           "races_all": BOTH}}},
                           "effect": [{"op": "draw", "count": 1}]}]}
    parse_card(base, TABLES)   # races_all は通る
    # 未知キーは検証される位置（affects / select のフィルタ）では弾かれる。
    # when の subject フィルタは parse_card のキー検証対象外（既存の性質）で、
    # submit 時はスキーマ（再生成済みで races_all を含む）が受ける。
    bad = {"id": "X278", "name": "検証用", "types": ["creature"],
           "civs": ["nature"], "cost": 1, "power": 1000,
           "abilities": [{"kind": "static",
                          "affects": {"owner": "you", "zone": "hand",
                                      "filter": {"races_and": BOTH}},
                          "mod": {"cost": -1}}]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)   # 未知キー races_and は弾く


# ---------- filter_match の意味論 ----------

def test_races_all_filter_match():
    e = setup(load_rules(), {"bz": ["T787", "T788", "T789"]}, {"bz": ["T001"]})
    cid = {}
    for c in e.zlist("bz", 0):
        cid[e.cdef(c).id] = c
    both = {"races_all": BOTH}
    assert e.filter_match(cid["T787"], both)
    assert not e.filter_match(cid["T788"], both)
    assert not e.filter_match(cid["T789"], both)
    # 片方だけの指定は「少なくともその種族を持つ」と等しい
    assert e.filter_match(cid["T787"], {"races_all": ["アンノウン"]})
    assert e.filter_match(cid["T788"], {"races_all": ["アンノウン"]})
    assert not e.filter_match(cid["T789"], {"races_all": ["アンノウン"]})
    # 文字列1値は単一種族として正規化される（civs の _civ_list と同じ作法）
    assert e.filter_match(cid["T789"], {"races_all": "ゼニス"})
    # 持っていない種族を含むと落ちる
    assert not e.filter_match(cid["T787"], {"races_all": BOTH + ["ドラゴン"]})
    # 対照: 既存の races は OR（どれか1つで通る）
    either = {"races": BOTH}
    assert e.filter_match(cid["T787"], either)
    assert e.filter_match(cid["T788"], either)
    assert e.filter_match(cid["T789"], either)
    # 他キーとの積み重ね（AND）も通常どおり
    assert e.filter_match(cid["T787"], {"types": ["creature"], "races_all": BOTH})
    assert not e.filter_match(cid["T787"], {"types": ["spell"], "races_all": BOTH})


# ---------- 実挙動: 誘発の subject フィルタ（dm23ex3-t13 の形） ----------

def test_watcher_boosts_for_both_races():
    """T790: 自分の両種族クリーチャーが出た時、山札の上から1枚をマナへ。"""
    cap = {}
    e = setup(load_rules(),
              {"bz": ["T790"], "hand": ["T787"], "mana": ["T788"] * 3},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once(
        "play:T787", capture=lambda ev: cap.update(mana=len(ev.zlist("mana", 0)))))
    drv.run(e, lambda ev: "T787" in _defns(ev, "bz", 0) and _quiet(ev))
    assert len(e.zlist("mana", 0)) == cap["mana"] + 1   # 誘発で1枚増えた


def test_watcher_ignores_single_race():
    """T790: 片方の種族だけでは誘発しない。"""
    cap = {}
    e = setup(load_rules(),
              {"bz": ["T790"], "hand": ["T788"], "mana": ["T789"] * 3},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once(
        "play:T788", capture=lambda ev: cap.update(mana=len(ev.zlist("mana", 0)))))
    drv.run(e, lambda ev: "T788" in _defns(ev, "bz", 0) and _quiet(ev))
    assert len(e.zlist("mana", 0)) == cap["mana"]       # 増えていない


def test_watcher_ignores_opponents_both_races():
    """T790: 相手の両種族クリーチャーでは誘発しない（subject の owner: you）。"""
    cap = {}
    e = setup(load_rules(),
              {"bz": ["T790"]},
              {"hand": ["T787"], "mana": ["T788"] * 3})
    drv = _Driver(play=_play_once(
        "play:T787", capture=lambda ev: cap.update(mana=len(ev.zlist("mana", 0)))))
    drv.run(e, lambda ev: "T787" in _defns(ev, "bz", 1) and _quiet(ev))
    # 自分のマナは自分のターンでも増えない（チャージは pass、手札からの
    # プレイなし）ため、停止時点によらず誘発の有無が判定できる
    assert len(e.zlist("mana", 0)) == cap["mana"]       # 増えていない


# ---------- 実挙動: 呪文面の選択フィルタ＋終了時戻し（dm23ex3-t01 の形） ----------

def _run_spell_scenario(hand):
    """T791 を唱える専用ループ。

    召喚の選択は候補が1体だけなら自動で決まり、唱えた後の残りステップには
    自分の決定が現れないため、advance のたび（答える前）に場を見て記録する。
    戻り（ターン終了時）まで進めた時点の (saw_bz, engine) を返す。
    """
    e = setup(load_rules(), {"hand": hand, "mana": ["T789"] * 3, "bz": ["T001"]},
              {"bz": ["T001"]})
    cast = False
    saw_bz = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if "T787" in _defns(e, "bz", 0):
            saw_bz = True
        if cast and saw_bz and "T787" in _defns(e, "hand", 0) and _quiet(e):
            return saw_bz, e   # 召喚→終了時戻しまで観測できた
        if cast and not saw_bz and "T791" in _defns(e, "graveyard", 0) and _quiet(e):
            return saw_bz, e   # 解決が終わったが何も出なかった
        if kind == "main" and not cast and "play:T791" in keys:
            cast = True
            e.answer([keys.index("play:T791")])
        elif kind == "choose_cards":
            defns = [e.cdef(o["cid"]).id for o in d["options"]]
            e.answer([defns.index("T787")] if "T787" in defns
                     else list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif kind == "declare_sback":
            e.answer([])
        elif kind == "choose_breaker":
            e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
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


def test_spell_summons_only_both_races_and_returns():
    """T791: 両種族だけが召喚され、ターン終了時に手札へ戻る。"""
    saw_bz, e = _run_spell_scenario(["T791", "T787", "T788"])
    assert saw_bz                                # T787 が場に出た
    assert "T787" in _defns(e, "hand", 0)        # 終了時に手札へ戻った
    assert "T788" in _defns(e, "hand", 0)        # T788 は最後まで手札
    assert "T788" not in _defns(e, "bz", 0)


def test_spell_summons_nothing_without_both_races():
    """T791: 手札に両種族がいなければ何も出ない（T788 は対象外）。"""
    saw_bz, e = _run_spell_scenario(["T791", "T788"])
    assert not saw_bz
    assert "T788" in _defns(e, "hand", 0)
    assert _defns(e, "bz", 0) == ["T001"]   # 初期配置の T001 だけ
