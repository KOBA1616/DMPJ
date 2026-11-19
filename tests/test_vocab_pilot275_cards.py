"""語彙パイロット第275弾のカード適用テスト（登録形）。

ラウンド310で attack_specific_target の3件を新規登録、1件を差し戻し。
- 新規3件: dmr09-102 戦場のロックンロール（火・呪文・コスト2、呪文面）、
  dmr14-050 爆旗持ち ラガブーリン（火・コスト2・パワー1000・ヒューマノイド爆、
  CIP形）、dmrp06-080 ポリスワン（火・コスト4・パワー3000・ジョーカーズ、
  CIP形・付与先は自分の他のクリーチャー＝modify の select に exclude {ref: self}）。
  いずれも choose で対象を束縛し、modify で allow 項目の only {var: tgt} を
  duration: end_of_turn で与える形（第275弾）。
- 差し戻し1件: dmrp08-058 ホンヤクツーヤク は攻撃強制のフィルタ形で本弾の
  対象外。ギャップ名を must_attack_filtered_target（must_attack_creature に
  other フィルタ＝パワー2222以下を持たせる形）に精緻化し、partial に残した。
- converted 10,131 / rejects 2,202、重複0・漏れ0。attack_specific_target
  ギャップは残り0件でファミリー解消。

プロトテスト（test_vocab_pilot275.py）とは別プロセスで実行すること
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
IDS = ["dmr09-102", "dmr14-050", "dmrp06-080"]


def _setup(rules, p0, p1=None):
    # tests.conftest の setup と同形。conftest を import すると
    # DMSIM_SKIP_CONVERTED=1 が復活するため、ここで直接 build を呼ぶ。
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001",
                         "seed": 1, "deck_size": 20})


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


def _cid(e, zone, p, defn):
    cids = e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)
    return next(c for c in cids if e.cdef(c).id == defn)


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第275弾プロトテストのものを流用）。

    choose_defn: choose_cards ではその defn のカードを選ぶ。
    attack_key: 自分（player 0）の攻撃決定でそのキーを一度だけ選ぶ。
    attack_log: (turn, player, keys) を全攻撃決定について記録する。
    """

    def __init__(self, play=None, choose_defn=None, attack_key=None):
        self.play = play
        self.choose_defn = choose_defn
        self.attack_key = attack_key
        self.attack_used = False
        self.attack_log = []

    def run(self, e, stop, limit=800):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            if kind == "choose_cards" and self.choose_defn is not None:
                hit = [i for i, o in enumerate(d["options"])
                       if e.cdef(o["cid"]).id == self.choose_defn]
                if hit:
                    e.answer(hit[:1])
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
            if kind == "attack":
                self.attack_log.append((e.s.turn, d["player"], list(keys)))
                if (d["player"] == 0 and self.attack_key is not None
                        and not self.attack_used and self.attack_key in keys):
                    self.attack_used = True
                    e.answer([keys.index(self.attack_key)])
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


def _allow_mod(ops):
    mod = next(o for o in ops if o.get("op") == "modify")
    allow = mod["mod"]["allow"]
    assert allow == [{"action": "attack_creature", "other": {"tapped": False},
                      "only": {"var": "tgt"}}]
    choose = next(o for o in ops if o.get("op") == "choose")
    assert choose["select"]["owner"] == "opp"
    assert choose["select"]["filter"] == {"types": ["creature"], "tapped": False}
    assert choose["as"] == "tgt"
    assert mod["duration"] == "end_of_turn"
    return mod


# ---------- 登録形 ----------

def test_registered_forms():
    c = _converted("dmr09-102")
    parse_card(copy.deepcopy(c), TABLES)
    assert "unsupported" not in (c.get("source") or {})
    assert c["name"] == "戦場のロックンロール"
    assert c["types"] == ["spell"] and c["civs"] == ["fire"]
    assert c["cost"] == 2 and c["mana"] == 1
    assert c["text"] == ("バトルゾーンにある相手のタップされていないクリーチャーを"
                         "１体選ぶ。このターン、バトルゾーンにある自分の"
                         "クリーチャーはすべて、そのクリーチャーを攻撃できる。")
    mod = _allow_mod(c["spell"])
    assert "exclude" not in mod["select"]

    c = _converted("dmr14-050")
    parse_card(copy.deepcopy(c), TABLES)
    assert "unsupported" not in (c.get("source") or {})
    assert c["name"] == "爆旗持ち ラガブーリン"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 2 and c["power"] == 1000
    assert c["races"] == ["ヒューマノイド爆"]
    (ab,) = c["abilities"]
    assert ab["kind"] == "trigger"
    assert ab["when"] == {"event": "move", "to": "bz", "subject": "self"}
    mod = _allow_mod(ab["effect"])
    assert "exclude" not in mod["select"]

    c = _converted("dmrp06-080")
    parse_card(copy.deepcopy(c), TABLES)
    assert "unsupported" not in (c.get("source") or {})
    assert c["name"] == "ポリスワン"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 4 and c["power"] == 3000
    assert c["races"] == ["ジョーカーズ"]
    (ab,) = c["abilities"]
    assert ab["kind"] == "trigger"
    assert ab["when"] == {"event": "move", "to": "bz", "subject": "self"}
    mod = _allow_mod(ab["effect"])
    assert mod["select"]["exclude"] == {"ref": "self"}   # 「自分の他のクリーチャー」


def test_bounced_dmrp08_058():
    r = _reject("dmrp08-058")
    assert r["gaps"] == ["must_attack_filtered_target"]
    uns = (r["partial"].get("source") or {}).get("unsupported")
    assert uns == [{"need": "must_attack_filtered_target",
                    "text": "このクリーチャーが攻撃する時、可能なら"
                            "パワー2222以下のクリーチャーを攻撃する"}]
    try:
        _converted("dmrp08-058")
        raise AssertionError("dmrp08-058 が converted に入ってしまった")
    except KeyError:
        pass


# ---------- 実挙動 ----------

def test_registered_spell_grants_attack_on_chosen_untapped():
    """dmr09-102（呪文形）: 選んだ T001 だけが攻撃でき、他のアンタップ T004 は不可。
    実際に攻撃するとバトルが起きる（5000 vs 2000 で T001 が破壊される）。"""
    e = _setup(load_rules(),
               {"hand": ["dmr09-102"], "mana": ["T034", "T001"], "bz": ["T779"]},
               {"bz": ["T001", "T004"]})
    drv = _Driver(play=_play_once("play:dmr09-102"), choose_defn="T001",
                  attack_key="attack:T779:T001")
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    keys = next(k for t, p, k in drv.attack_log if t == 1 and p == 0)
    assert "attack:T779:T001" in keys        # 選んだクリーチャーは攻撃できる
    assert "attack:T779:T004" not in keys    # 他のアンタップは攻撃できないまま
    assert "T001" in _defns(e, "graveyard", 1)
    assert "T779" in _defns(e, "bz", 0)


def test_registered_cip_grants_attack_on_chosen_untapped():
    """dmr14-050（CIP形）: 出た時に同じ付与（自分のクリーチャーすべて）。"""
    e = _setup(load_rules(),
               {"hand": ["dmr14-050"], "mana": ["T034", "T001"], "bz": ["T779"]},
               {"bz": ["T001", "T004"]})
    drv = _Driver(play=_play_once("play:dmr14-050"), choose_defn="T001",
                  attack_key="attack:T779:T001")
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    keys = next(k for t, p, k in drv.attack_log if t == 1 and p == 0)
    assert "attack:T779:T001" in keys
    assert "attack:T779:T004" not in keys
    assert "T001" in _defns(e, "graveyard", 1)
    assert "T779" in _defns(e, "bz", 0)


def test_registered_cip_grant_excludes_self():
    """dmrp06-080（CIP形）: 付与は「自分の他のクリーチャー」だけ。
    継続的効果の affected と特性の allow の両方で、発生源自身が外れていることを見る。"""
    e = _setup(load_rules(),
               {"hand": ["dmrp06-080"],
                "mana": ["T034", "T034", "T001", "T001"], "bz": ["T779"]},
               {"bz": ["T001", "T004"]})
    drv = _Driver(play=_play_once("play:dmrp06-080"), choose_defn="T001",
                  attack_key="attack:T779:T001")

    def granted(ev):
        return any(isinstance(x, dict) and "only" in x
                   for ce in ev.s.continuous for x in ce["mod"].get("allow", []))

    drv.run(e, granted)
    t001 = _cid(e, "bz", 1, "T001")
    police = _cid(e, "bz", 0, "dmrp06-080")
    t779 = _cid(e, "bz", 0, "T779")
    ce = next(ce for ce in e.s.continuous
              if any(isinstance(x, dict) and "only" in x for x in ce["mod"].get("allow", [])))
    assert [t779, e.s.cards[t779].gen] in ce["affected"]       # 他のクリーチャーは対象
    assert [police, e.s.cards[police].gen] not in ce["affected"]   # 発生源自身は対象外
    baked = next(x["only"] for x in ce["mod"]["allow"] if isinstance(x, dict) and "only" in x)
    assert baked == [[t001, e.s.cards[t001].gen]]              # 選んだ T001 にベイク済み
    allow779 = [x for x in e.chars_ro(t779)["allow"] if isinstance(x, dict) and "only" in x]
    allow_police = [x for x in e.chars_ro(police)["allow"] if isinstance(x, dict) and "only" in x]
    assert allow779 and not allow_police
    # 実挙動: T779 は T001 を攻撃でき、バトルで破壊する
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 1)
    assert "T779" in _defns(e, "bz", 0)
