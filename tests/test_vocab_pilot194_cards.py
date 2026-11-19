"""語彙パイロット第194弾のカード適用テスト（登録形）。

ラウンド230で must_attack_creature_if_able の6件のうち5件を新規登録、
1件を差し戻した。
- 登録5件: converted.yaml から読み、must_attack_creature 系の mod を
  含むことを確認。dmex14-017 は attack_untapped（allow attack_creature）も
  併せて解消。dmr23-022 は modal の第2モード。
- dmr10-016 は差し戻し: シールドゾーンに表向きで置かれている間だけ効く
  常在型は未対応（新ギャップ shield_zone_static）。

ラウンド297で残りの must_attack_creature_if_able 6件のうち4件を新規登録、
2件を差し戻した。
- 登録4件: dm22rp1-023（tap_entry＋相手クリーチャーへの must_attack_creature
  常在型）、dm24ex3-rp1010（ハイパー時の破壊時誘発＋cost_of: event.subject
  のコスト比較）、dm24ex3-rp3s09（相手プレイヤーへの攻撃誘発で
  パワード・ブレイカー付与）、dmex12-046（Dスイッチ＋ドリームメイトでの
  攻撃中止）。
- 差し戻し2件: dmrp16-s07 → must_attack_creature_first_attack_of_turn
  （ターンの最初の攻撃だけ、という制限は first_only では表せない）、
  dmr22-025 → mana_tap_placement（マナゾーンに置く時タップして置く）。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card
from dmsim.scenario import build

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dmrp18-087", "dmr14-054", "dmr23-022", "dmrp04s-093", "dmex14-017",
              "dm22rp1-023", "dm24ex3-rp1010", "dm24ex3-rp3s09", "dmex12-046")


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] == cid:
            return r
    raise KeyError(cid)


def _mods(card):
    out = []

    def walk(x):
        if isinstance(x, dict):
            if "mod" in x:
                out.append(x["mod"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(card.get("abilities") or [])
    walk(card.get("spell") or [])
    return out


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        mods = _mods(card)
        assert any("must_attack_creature" in m or "must_be_attacked" in m
                   for m in mods), cid


def test_specific_forms():
    m = _mods(_converted("dmrp18-087"))[0]
    assert m["grant"] == ["must_attack"] and m["must_attack_creature"] is True
    spell = _converted("dmr23-022")["spell"]
    assert spell[0]["op"] == "modal" and len(spell[0]["modes"]) == 2
    mods = _mods(_converted("dmex14-017"))
    assert any(mm.get("allow") == [{"action": "attack_creature",
                                     "other": {"tapped": False}}]
               for mm in mods)


def test_dmr10_016_bounced():
    r = _reject("dmr10-016")
    assert r["gaps"] == ["shield_zone_static"]
    assert (r["partial"].get("keywords") or []) != []


def test_round297_specific_forms():
    c = _converted("dm22rp1-023")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["tap_entry"] is True
    statics = [ab for ab in c["abilities"] if ab["kind"] == "static"]
    assert any(ab["mod"].get("must_attack_creature") is True
               and ab["affects"]["owner"] == "opp" for ab in statics)
    assert any(ab["mod"].get("power") == 5000 for ab in statics)

    c = _converted("dm24ex3-rp1010")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["hyper"] is True
    trig = [ab for ab in c["abilities"]
            if ab["kind"] == "trigger" and ab["when"].get("reason") == "destroy"]
    assert len(trig) == 1
    trig = trig[0]
    assert trig.get("first_time") is True and trig.get("if") == {"hyper": True}
    mv = trig["effect"][0]["body"][0]
    assert mv["op"] == "move" and mv["to"] == "bz" and mv["reason"] == "put"
    fle = mv["select"]["filter"]["cost_le"]
    assert fle == {"sum": [{"cost_of": "event.subject"}, -1]}

    c = _converted("dm24ex3-rp3s09")
    parse_card(copy.deepcopy(c), TABLES)
    trig = [ab for ab in c["abilities"]
            if ab["kind"] == "trigger" and ab["when"].get("event") == "attack"]
    assert len(trig) == 1
    trig = trig[0]
    assert trig["when"].get("target") == "player"
    assert trig["when"]["subject"].get("other") is True
    mod = trig["effect"][0]
    assert mod["op"] == "modify" and mod["select"] == {"ref": "subject", "count": 1}
    assert mod["mod"] == {"power": 6000, "grant": ["powered_breaker"]}
    assert mod["duration"] == "end_of_turn"

    c = _converted("dmex12-046")
    parse_card(copy.deepcopy(c), TABLES)
    ds = [ab for ab in c["abilities"] if ab.get("dswitch") is True]
    assert len(ds) == 1
    assert ds[0]["when"] == {"event": "turn_start", "player": "opp"}
    body = ds[0]["effect"][0]["body"]
    assert body[0] == {"op": "dswitch"}
    assert body[1]["mod"] == {"must_attack_creature": True}
    assert body[1]["duration"] == "end_of_turn"
    atk = [ab for ab in c["abilities"]
           if ab["kind"] == "trigger" and ab["when"].get("event") == "attack"]
    assert len(atk) == 1
    abody = atk[0]["effect"][0]["body"]
    assert abody[0]["op"] == "mana_put" and abody[0]["as"] == "placed"
    assert abody[1]["op"] == "if"
    assert abody[1]["cond"] == {"exists": {"ref": "placed",
                                           "filter": {"races": ["ドリームメイト"]}}}
    assert abody[1]["then"] == [{"op": "cancel_attack"}]


def test_round297_bounced():
    r = _reject("dmrp16-s07")
    assert r["gaps"] == ["must_attack_creature_first_attack_of_turn"]
    assert len(r["partial"]["abilities"]) == 2  # 出た時＋アバレチェーンを bank
    r = _reject("dmr22-025")
    assert r["gaps"] == ["mana_tap_placement"]
    assert len(r["partial"]["abilities"]) == 3  # パワー＋選ばれ防止＋Dスイッチを bank


def test_round297_attack_trigger_grants_powered_breaker():
    """dm24ex3-rp3s09: 自分の他のクリーチャーが相手プレイヤーを攻撃する時、
    そのクリーチャーのパワーを+6000し、「パワード・ブレイカー」を与える。"""
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["dm24ex3-rp3s09", "T001"], "deck": ["T001"] * 10},
                      "p1": {"bz": [], "deck": ["T001"] * 10},
                      "filler": "T001", "seed": 1, "deck_size": 14})
    t001 = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T001"][0]
    base = e.chars(t001)["power"]
    boosted = {"v": False}
    for _ in range(400):
        if (e.chars(t001)["power"] == base + 6000
                and "powered_breaker" in e.chars(t001)["keywords"]):
            boosted["v"] = True
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack":
            atk = next((i for i, k in enumerate(keys) if k == "attack:T001:player"), None)
            if atk is not None and e.s.active == 0:
                e.answer([atk])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert boosted["v"]
