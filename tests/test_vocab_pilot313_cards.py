"""語彙パイロット第313弾の対象カード検証（ラウンド348で登録済み）。

cost_le_count は dm26rp3-std010 BARUGA-雷座87 の3刷
（std010 / stdchosec010 / stdsec010）のみ。いずれも gaps は
空で、partial の source.unsupported にだけ cost_le_count が
残る監査行（第312弾の監査の継続で精査）だった。

第313弾の結論はドリフト: 「自分のマナゾーンにあるカードの
枚数よりコストが小さい」は第117弾 cost_lt_count の確立形
cost_le: {sum: [{count: {zone: mana, owner: you}}, -1]} で
書ける（マナ枚数形の登録済み先例 dm26ex3-082）。攻撃時
メテオバーンは dm19-007 の may + move(as: paid) + if
{exists: {ref: paid}} イディオム、マナから出すは move →
bz, reason: put（dm26ex3-082 と同形）。

ラウンド348で登録した。登録形は partial（NEO進化・
W・ブレイカー・CIP 誘発まで完成済み）＋ メテオバーン誘発、
unsupported を外したもので、abilities は [CIP誘発,
メテオバーン誘発] の2件ちょうど（連結・merge_split 由来の
混入なし）。正本判定は identity の実データ照合による:
canon_id は3刷とも dm26rp3-std010 で、stdchosec010 /
stdsec010 は独立登録せず alias として畳み込んだ
（aliases_for には旧刷 dm25ex3-023 / dm25rp2-021 も含まれる）。
対象行は gaps が空のため reopen では外れず直接 submit
（第323・343・347弾の先例）。submit では std010 の行だけが
外れたため、alias としてカバーされた stdchosec010 /
stdsec010 の reject 行は stale 行として行だけを除去した
（第347弾と同型）。ギャップ名 cost_le_count は多重ギャップ行
dm25ex3-rp1s02（neo_summon_cost_reduction 併せ持ち、別用法）
にのみ残る。登録名は公式データの表記
「BARUGA-雷座87(DM26RP3 STD10/)」（partial の表記と一致）。
実挙動は test_vocab_round348_cards.py が登録カード自身で固定。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活
するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
TABLES = load_tables()

TARGET = "dm26rp3-std010"
PRINTINGS = ["dm26rp3-std010", "dm26rp3-stdchosec010", "dm26rp3-stdsec010"]
ALIASES = ["dm25ex3-023", "dm25rp2-021",
           "dm26rp3-stdchosec010", "dm26rp3-stdsec010"]
GAP = "cost_le_count"

TEXT = ("NEO進化：光、火、または自然のクリーチャー１体の上に置いてもよい。\n"
        "W・ブレイカー\n"
        "このクリーチャーが出た時、自分の山札の上から２枚をタップしてマナゾーンに置く。\n"
        "メテオバーン：このクリーチャーが攻撃する時、このクリーチャーの下にあるカードを１枚墓地に置いてもよい。"
        "そうしたら、自分のマナゾーンにあるカードの枚数よりコストが小さいクリーチャーを１体、自分のマナゾーンから出す。")

CIP_TRIGGER = {"kind": "trigger",
               "when": {"event": "move", "to": "bz", "subject": "self"},
               "effect": [
                   {"op": "move",
                    "select": {"zone": "deck", "owner": "you",
                               "from_top": 2},
                    "to": "mana", "reason": "put", "tapped": True}]}

METEOR_TRIGGER = {"kind": "trigger",
                  "when": {"event": "attack", "subject": "self"},
                  "effect": [
                      {"op": "may",
                       "body": [
                           {"op": "move",
                            "select": {"under_of": "self", "count": 1},
                            "to": "graveyard", "reason": "put",
                            "as": "paid"},
                           {"op": "if",
                            "cond": {"exists": {"ref": "paid"}},
                            "then": [
                                {"op": "move",
                                 "select": {"zone": "mana", "owner": "you",
                                            "filter": {
                                                "types": ["creature"],
                                                "cost_le": {"sum": [
                                                    {"count": {
                                                        "zone": "mana",
                                                        "owner": "you"}},
                                                    -1]}},
                                            "count": 1},
                                 "to": "bz", "reason": "put"}]}]}]}

FORM = {"id": TARGET,
        "name": "BARUGA-雷座87(DM26RP3 STD10/)",
        "types": ["creature"],
        "civs": ["nature"],
        "cost": 5, "power": 6000,
        "races": ["アーマード・ドラゴン", "テクノ・サムライ"],
        "mana": 1,
        "neo": True,
        "evolve_from": {"civs": ["light", "fire", "nature"],
                        "types": ["creature"]},
        "text": TEXT,
        "abilities": [CIP_TRIGGER, METEOR_TRIGGER],
        "keywords": ["double_breaker"]}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 2066
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10252
    assert not (ids & set(rows))          # canonical 重なり0
    aliases = set()
    for c in conv:
        aliases.update((c.get("source") or {}).get("aliases") or [])
    for t in PRINTINGS:
        assert t not in rows              # 3刷とも reject 行は外れた
    assert TARGET in ids
    for a in ALIASES:
        assert a not in ids and a in aliases   # alias 畳み込み
    c = next(c for c in conv if c["id"] == TARGET)
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == ALIASES
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "neo", "evolve_from", "text", "abilities",
              "keywords"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2       # [CIP誘発, メテオバーン誘発]
    # cost_le_count は対象3行から解消。ギャップ名は多重ギャップ行
    # dm25ex3-rp1s02（neo_summon_cost_reduction を併せ持ち、手札枚数
    # 以下のコストで実行する別用法）にのみ残る
    def _unsup(r):
        return [u.get("need") if isinstance(u, dict) else u
                for u in (((r.get("partial") or {}).get("source") or {})
                          .get("unsupported") or [])]
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == {"dm25ex3-rp1s02"}, left


def test_established_form_parses():
    d = parse_card(FORM, TABLES)
    assert d.neo
    assert d.evolve_from == {"civs": ["light", "fire", "nature"],
                             "types": ["creature"]}
    trigs = [a for a in d.abilities if a["kind"] == "trigger"]
    assert len(trigs) == 2                        # CIP + メテオバーン
    atk = [a for a in trigs
           if (a.get("when") or {}).get("event") == "attack"]
    assert len(atk) == 1
    # 第117弾 cost_lt_count の確立形そのもの
    put = atk[0]["effect"][0]["body"][1]["then"][0]
    assert put["op"] == "move" and put["to"] == "bz"
    assert put["select"]["filter"]["cost_le"] == {
        "sum": [{"count": {"zone": "mana", "owner": "you"}}, -1]}
    # 登録カード自身も parse できる
    c = _conv_cache.find(CONVERTED, TARGET)
    d2 = parse_card(c, TABLES)
    assert len([a for a in d2.abilities if a["kind"] == "trigger"]) == 2
