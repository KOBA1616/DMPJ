"""語彙パイロット第428弾（cards 側）:
unblockable_only_when_attacking_creatures。

対象は同一文面の2件 dm09-030 ジョー・リザード /
dm09-050 鳥神兵クウザ（pure 2件、multi にも
現れない）。両件とも partial は骨格完備で text は
公式全文（補完なし）。未解決は unsupported の
unblockable_only_when_attacking_creatures 1件
だけで、提出形は abilities 2件（文面の条項順）:
第1条項 static {affects: self, mod:
{unblockable_vs_creatures: true}}（新規語彙・
最小。第426弾 must_be_blocked と同型）＋
第2条項 static {affects: self, mod: {power_when:
{amount: 3000, when: attacking}}}（確立形。
split の定型所有形そのもの）。alias は両件とも
無し（canon は対象自身）。形の根拠は本体テストの
docstring 参照。

ラウンド463で登録済み。登録形は abilities 以外の
全フィールドが提出形と完全一致し、abilities は
定型所有の power_when static が merge_split の
再付着で先頭に来るため登録順は [power_when,
unblockable_vs_creatures]（ラウンド410の先例と
同型。両方とも self の静的効果で順序に意味は
無い）。power_when は dedupe で1件だけ。
本ファイルは登録形に書き換え済み。ファミリーは
完全解消。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from tests._conv_cache import all_cards, find, proto_card  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
GAP = "unblockable_only_when_attacking_creatures"

STATIC_UB = {"kind": "static", "affects": "self",
             "mod": {"unblockable_vs_creatures": True}}
STATIC_PW = {"kind": "static", "affects": "self",
             "mod": {"power_when": {"amount": 3000,
                                    "when": "attacking"}}}
FORM = [STATIC_UB, STATIC_PW]            # 提出形（文面の条項順）
REG_ABILITIES = [STATIC_PW, STATIC_UB]   # 登録形（定型所有が先頭）
FULL_TEXT = ("このクリーチャーは、クリーチャーを攻撃するとき"
             "ブロックされない。\n"
             "パワーアタッカー+3000(攻撃中、このクリーチャーの"
             "パワーは+3000される)")
TARGETS = {
    "dm09-030": {"name": "ジョー・リザード", "cost": 6,
                 "power": 3000, "races": ["デューンゲッコー"],
                 "proto": "T1206"},
    "dm09-050": {"name": "鳥神兵クウザ", "cost": 3,
                 "power": 1000, "races": ["アーマロイド"],
                 "proto": "T1207"},
}


def submit_form(tid):
    t = TARGETS[tid]
    return {"id": tid, "name": t["name"], "types": ["creature"],
            "civs": ["fire"], "cost": t["cost"],
            "power": t["power"], "races": t["races"], "mana": 1,
            "text": FULL_TEXT, "abilities": copy.deepcopy(FORM)}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_targets_registered_and_family_cleared():
    rows = _reject_rows()
    assert len(rows) == 1902
    mine = {r["id"]: r for r in rows}
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) == 10409
    for tid, t in TARGETS.items():
        assert tid not in mine           # 対象行は登録で解消
        assert canon_id(tid) == tid
        assert aliases_for(t["name"], tid) == []
        c = find(CONVERTED, tid)
        assert c is not None
        reg = {k: v for k, v in c.items() if k != "source"}
        sub = submit_form(tid)
        reg_ab = reg.pop("abilities")
        sub.pop("abilities")
        assert reg == sub                # abilities 以外は完全一致
        # 登録後は abilities が static 2件ちょうど。
        # power_when は dedupe で1件だけ（二重付着なし）
        assert reg_ab == REG_ABILITIES
        assert len(reg_ab) == 2
        assert all(a["kind"] == "static" for a in reg_ab)
        pw = [a for a in reg_ab
              if (a.get("mod") or {}).get("power_when")]
        assert len(pw) == 1
        assert c["text"] == FULL_TEXT    # 公式全文
        assert not c.get("aliases") and not c.get("keywords")
        src = c.get("source") or {}
        assert not src.get("unsupported")
        assert not src.get("aliases")
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == [
        "destroy_self_after_attacking_player"]


def test_submit_forms_parse_and_match_proto():
    for tid, t in TARGETS.items():
        sub = submit_form(tid)
        d = parse_card(copy.deepcopy(sub), TABLES)
        for a in FORM:
            assert a in d.abilities
        assert len(d.abilities) == 2
        assert d.types == ["creature"] and d.civs == ["fire"]
        assert d.cost == t["cost"] and d.power == t["power"]
        assert d.races == t["races"]
        proto = proto_card(t["proto"])
        for k in ("name", "types", "civs", "cost", "power",
                  "races", "mana", "text", "abilities"):
            assert proto[k] == sub[k]


def test_official_rows_match_skeleton_and_text():
    offs = {}
    for line in (ROOT / "data/cards/raw/by_product/9.jsonl") \
            .read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("id") in TARGETS:
            offs[r["id"]] = r
    assert sorted(offs) == sorted(TARGETS)
    for tid, t in TARGETS.items():
        off = offs[tid]
        assert off["name"] == t["name"]
        assert off["text"] == FULL_TEXT
        assert int(off["cost"]) == t["cost"]
        assert int(off["power"]) == t["power"]
        assert off["race"] == "/".join(t["races"])
        assert off["civilization"] == "火"
