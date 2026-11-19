"""語彙パイロット第278弾のカード適用テスト（登録形）。

ラウンド313で filter_race_and の純粋3件をすべて新規登録、差し戻しなし。
- dm23ex3-t13 黒神龍オンバシ・ラオーン（闇・コスト4・パワー4000）:
  partial の常在型は壊れていた（race_has に文章が入った軽減 -2 が1件だけ）
  ため、コスト軽減2件（アンノウン -1 / ゼニス -2、フィルタは races の
  OR 形で足り、両種族持ちは両方の軽減を受ける）と、両種族クリーチャーが
  出た時に自分を破壊する誘発（subject に races_all）を公式全文から
  組み直した。コストの下限0はエンジン既定（cost_min 既定0）。
  alias: dmr05-055 / dmr05-055m / dmx13-023。
  注意: submit は partial の abilities と回答の abilities を連結する
  （同一 dict は重複排除）ため、登録直後は壊れた常在型が残っていた。
  ラウンド307（dm26ex3-079）の先例どおり converted.yaml から直接除去済み。
- dm23ex3-t01 極頂秘伝ゼニス・シンフォニー（ゼロ・コスト9の呪文）:
  partial の declare（アタック・チャンス）は完全。呪文面に play_free
  {filter: races_all, as: summoned} ＋ delayed_trigger {turn_end} で
  手札へ戻す形を載せた。「てもよい」の辞退は select の min で確認し、
  count: 1 のままでは mn=mx=1 で強制になるため up_to: true を付けた
  （dmrp18-034 の先例形）。alias: dmbd06-012。
- dm24bd6-023 「武」の頂 マキシマム・ザ・マックス: ツインパクト。
  クリーチャー面は partial のまま、呪文面に dm23ex3-t01 と同じ形。
  alias: dm22ex1-043。
- converted 10,141 / rejects 2,192、重複0・漏れ0。filter_race_and
  ギャップは残り0件でファミリー解消。

プロトテスト（test_vocab_pilot278.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
IDS = ["dm23ex3-t13", "dm23ex3-t01", "dm24bd6-023"]
BOTH = ["アンノウン", "ゼニス"]

SUMMON_SPELL = [
    {"op": "play_free",
     "select": {"zone": "hand", "owner": "you",
                "filter": {"types": ["creature"], "races_all": BOTH},
                "count": 1, "up_to": True},
     "as": "summoned"},
    {"op": "delayed_trigger",
     "when": {"event": "turn_end"},
     "effect": [{"op": "move", "select": {"ref": "summoned"},
                 "to": "hand", "reason": "return"}]},
]

DECLARE_AC = {
    "kind": "declare", "zone": "hand",
    "when": {"event": "attack",
             "subject": {"owner": "you", "filter": {"races": ["アンノウン"]}}},
    "effect": [{"op": "may",
                "body": [{"op": "play_free", "select": {"ref": "self"}}]}],
}


def _setup(rules, p0, p1=None, **kw):
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001",
                         "seed": 1, "deck_size": 20, **kw})


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if r["id"] == cid:
                return r
    raise KeyError(cid)


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第277弾 cards と同形）。

    play: main 決定で (e, d) -> 答えのリストか None を返すフック。
    choose: choose_cards へのフック (e, d) -> 答えのリストか None。
    seen に全決定種別を記録する。
    """

    def __init__(self, play=None, choose=None):
        self.play = play
        self.choose = choose
        self.seen = []

    def run(self, e, stop, limit=1200):
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


def _play_once(key):
    seen = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None

    return play


def _play_face_once(defn, face):
    seen = {}

    def play(e, d):
        for i, o in enumerate(d["options"]):
            if (o["key"].startswith(f"play:{defn}") and o.get("face") == face
                    and not seen.get("opt")):
                seen["opt"] = True
                return [i]
        return None

    return play


def _choose_defn(defn):
    def choose(e, d):
        defns = [e.cdef(o["cid"]).id for o in d["options"]]
        if defn in defns:
            return [defns.index(defn)]
        return None

    return choose


# ---------- 登録形 ----------

def test_registered_forms():
    for cid in IDS:
        c = _converted(cid)
        parse_card(copy.deepcopy(c), TABLES)
        assert "unsupported" not in (c.get("source") or {}), cid
        try:
            _reject(cid)
            raise AssertionError(f"{cid} が rejects に残っている")
        except KeyError:
            pass

    c = _converted("dm23ex3-t13")
    assert c["name"] == "黒神龍オンバシ・ラオーン"
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 4 and c["power"] == 4000
    assert c["races"] == ["ドラゴン・ゾンビ", "アンノイズ"]
    assert c["source"]["aliases"] == ["dmr05-055", "dmr05-055m", "dmx13-023"]
    assert c["text"] == (
        "自分のアンノウン・クリーチャーの召喚コストを１、ゼニス・クリーチャーの"
        "召喚コストを２少なくする。ただし、コストは０以下にはならない。\n"
        "自分の、アンノウンとゼニス両方を種族に持つクリーチャーが出た時、"
        "このクリーチャーを破壊する。")
    # 壊れた partial の常在型（race_has に文章）は残っていないこと
    assert c["abilities"] == [
        {"kind": "static",
         "affects": {"owner": "you", "zone": "hand",
                     "filter": {"types": ["creature"], "races": ["アンノウン"]}},
         "mod": {"cost": -1}},
        {"kind": "static",
         "affects": {"owner": "you", "zone": "hand",
                     "filter": {"types": ["creature"], "races": ["ゼニス"]}},
         "mod": {"cost": -2}},
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz",
                  "subject": {"owner": "you",
                              "filter": {"types": ["creature"],
                                         "races_all": BOTH}}},
         "effect": [{"op": "destroy", "select": {"ref": "self"}}]},
    ]

    c = _converted("dm23ex3-t01")
    assert c["name"] == "極頂秘伝ゼニス・シンフォニー"
    assert c["types"] == ["spell"] and c["civs"] == ["zero"]
    assert c["cost"] == 9
    assert c["source"]["aliases"] == ["dmbd06-012"]
    assert c["abilities"] == [DECLARE_AC]
    assert c["spell"] == SUMMON_SPELL

    c = _converted("dm24bd6-023")
    assert c["source"]["aliases"] == ["dm22ex1-043"]
    f0, f1 = c["faces"]
    assert f0["name"] == "「武」の頂 マキシマム・ザ・マックス"
    assert f0["types"] == ["creature"] and f0["civs"] == ["zero"]
    assert f0["cost"] == 10 and f0["power"] == 12000
    assert f0["races"] == BOTH
    assert f0["keywords"] == ["world_breaker", "eternal_omega"]
    assert f0["abilities"] == [
        {"kind": "static", "affects": "self",
         "mod": {"power_when": {"amount": 12000, "when": "attacking"}}}]
    assert f1["name"] == "極頂秘伝ゼニス・シンフォニー"
    assert f1["types"] == ["spell"] and f1["civs"] == ["zero"]
    assert f1["cost"] == 9
    assert f1["abilities"] == [DECLARE_AC]
    assert f1["spell"] == SUMMON_SPELL


# ---------- 実挙動: dm23ex3-t13 ----------

def test_registered_t13_cost_reductions():
    """dm23ex3-t13: アンノウン -1 / ゼニス -2、両種族持ちは両方を受ける。"""
    e = _setup(load_rules(),
               {"bz": ["dm23ex3-t13"], "hand": ["T787", "T788", "T789"]},
               {"bz": ["T001"]})
    pay = {}
    for cid in e.zlist("hand", 0):
        pay[e.cdef(cid).id] = e.chars_ro(cid)["pay_cost"]
    assert pay == {"T787": 0, "T788": 2, "T789": 1}   # 素コストはすべて3


def test_registered_t13_trigger_destroys_self():
    """dm23ex3-t13: 自分の両種族クリーチャーが出た時、このクリーチャーを破壊する。"""
    e = _setup(load_rules(),
               {"bz": ["dm23ex3-t13"], "hand": ["T787"], "mana": ["T788"] * 3},
               {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T787"))
    drv.run(e, lambda ev: "dm23ex3-t13" in _defns(ev, "graveyard", 0)
            and "T787" in _defns(ev, "bz", 0) and _quiet(ev))
    assert "dm23ex3-t13" not in _defns(e, "bz", 0)


def test_registered_t13_trigger_ignores_single_race():
    """dm23ex3-t13: 片方の種族だけのクリーチャーでは誘発しない。"""
    e = _setup(load_rules(),
               {"bz": ["dm23ex3-t13"], "hand": ["T788"], "mana": ["T789"] * 3},
               {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T788"))
    drv.run(e, lambda ev: "T788" in _defns(ev, "bz", 0) and _quiet(ev))
    assert "dm23ex3-t13" in _defns(e, "bz", 0)
    assert "dm23ex3-t13" not in _defns(e, "graveyard", 0)


# ---------- 実挙動: 召喚呪文（dm23ex3-t01 / dm24bd6-023 呪文面） ----------

def _run_summon_spell(play_hook, hand, mode):
    """召喚呪文を唱える専用ループ（第278弾プロトの T791 用を登録形に転用）。

    mode="accept": 選択で T787 を選ぶ。mode="decline": 選択を辞退する
    （up_to: true で mn=0 のため空答えが合法）。戻り（ターン終了時）まで
    進めた時点の (saw_bz, engine) を返す。
    """
    e = _setup(load_rules(),
               {"hand": hand, "mana": ["T789"] * 9, "bz": ["T001"]},
               {"bz": ["T001"]})
    cast = False
    saw_bz = False
    passed = False   # 相手の main 決定を見た = 自分のターンが終わった
    for _ in range(1200):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if "T787" in _defns(e, "bz", 0):
            saw_bz = True
        if d.get("player") == 1:
            passed = True   # 相手の決定が出た時点で自分のターンは終わっている
        if cast and passed and _quiet(e):
            if mode == "decline":
                return saw_bz, e
            if saw_bz and "T787" in _defns(e, "hand", 0):
                return saw_bz, e   # 召喚→終了時戻しまで観測できた
            if not saw_bz:
                return saw_bz, e   # 解決が終わったが何も出なかった
        if kind == "main":
            ans = play_hook(e, d)
            if ans is not None:
                cast = True
                e.answer(ans)
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_cards":
            if mode == "decline":
                e.answer([])
            else:
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


def test_registered_t01_summons_and_returns():
    """dm23ex3-t01: 両種族だけが召喚され、ターン終了時に手札へ戻る。"""
    saw_bz, e = _run_summon_spell(_play_once("play:dm23ex3-t01"),
                                  ["dm23ex3-t01", "T787", "T788"], "accept")
    assert saw_bz                                # T787 が場に出た
    assert "T787" in _defns(e, "hand", 0)        # 終了時に手札へ戻った
    assert "T788" in _defns(e, "hand", 0)        # T788 は最後まで手札
    assert "T788" not in _defns(e, "bz", 0)


def test_registered_t01_decline():
    """dm23ex3-t01: 「てもよい」を辞退できる（up_to: true）。何も出ず、
    ターン終了時の戻しも空振りして相手のターンへ進む。"""
    saw_bz, e = _run_summon_spell(_play_once("play:dm23ex3-t01"),
                                  ["dm23ex3-t01", "T787"], "decline")
    assert not saw_bz
    assert "T787" in _defns(e, "hand", 0)
    assert "T787" not in _defns(e, "bz", 0)
    assert "dm23ex3-t01" in _defns(e, "graveyard", 0)   # 呪文は解決され墓地へ


def test_registered_bd6_spell_face_summons_and_returns():
    """dm24bd6-023: ツインパクトの呪文面も dm23ex3-t01 と同じ働きをする。"""
    saw_bz, e = _run_summon_spell(_play_face_once("dm24bd6-023", 1),
                                  ["dm24bd6-023", "T787", "T788"], "accept")
    assert saw_bz
    assert "T787" in _defns(e, "hand", 0)
    assert "T788" in _defns(e, "hand", 0)
    assert "T788" not in _defns(e, "bz", 0)
