"""再変換ラウンド344（第309弾 rinne_infinity）の記録テスト。

- 新規登録1件: dmrp21-tr2 天地命動 バラギアラ / 輪廻暴冥。
  stale クリーンアップ・差し戻しは0件（alias dmrp08-mh03 は
  source.aliases への記録のみで畳み込み扱い）。
- 正本判定は identity の実データ照合による: canon_id は
  dmrp21-tr2 自身＝独立正本。alias dmrp08-mh03 の canon_id も
  dmrp21-tr2 で、独立エントリ・reject 行は無い。
- converted 10,247→10,248 / rejects 2,074→2,073、
  canonical 重なり0・漏れ0。rinne_infinity は解消。
- reopen（rinne_infinity）は対象1件だけを外した。

登録形は第309弾の確立形 FORM と完全一致（submit の連結・
merge_split 由来の混入なし）:
- partial の faces はプレースホルダ（名前 x / y・火コスト1）
  だったため、faces と両面 text は公式データ
  （by_product/rp21）から構築。トップレベル text は
  dm26rp3-s011 の体裁（面ごとに text、「 ／ 」連結）。
- クリーチャー面: rinne: true ＋ CIP（reason: summon →
  マナ全アンタップ）＋ チャージ誘発（cast via: rinne →
  bz の同名カウント分だけ山札上→マナ）＋ triple_breaker。
- 呪文面（輪廻暴冥）: S・トリガー、choose 相手獣 →
  modify -4000（end_of_turn）＋ move 墓地 {types: [creature],
  cost_le: 5} → bz, reason: put。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。相手側・墓地役は第267・309弾プロト（T004 / T001 /
T741）を使う。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGET = "dmrp21-tr2"
ALIAS = "dmrp08-mh03"

FACE0_TEXT = ("このクリーチャーが召喚によって出た時、自分のマナゾーンにあるカードをすべてアンタップする。\n"
              "輪廻∞：このカードの呪文側を、バトルゾーンに置いたまま唱えてもよい。"
              "そうした時、自分の《天地命動 バラギアラ》１体につき、自分の山札の上から１枚をマナゾーンに置く。"
              "（その呪文のコストは支払う）\n"
              "T・ブレイカー")
FACE1_TEXT = ("S・トリガー\n"
              "相手のクリーチャーを１体選ぶ。このターン、そのクリーチャーのパワーを－4000する。\n"
              "コスト５以下のクリーチャーを１体、自分の墓地から出す。")

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self",
                "reason": "summon"},
       "effect": [{"op": "untap",
                   "select": {"zone": "mana", "owner": "you",
                              "count": "all"}}]}

CHARGE = {"kind": "trigger",
          "when": {"event": "cast", "via": "rinne", "subject": "self"},
          "effect": [{"op": "repeat",
                      "times": {"count": {"zone": "bz", "owner": "you",
                                          "filter": {"name_has": "天地命動 バラギアラ"}}},
                      "body": [{"op": "move",
                                "select": {"zone": "deck", "owner": "you",
                                           "from_top": 1},
                                "to": "mana", "reason": "put"}]}]}

BOUMEI = [{"op": "choose",
           "select": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"]}, "count": 1},
           "as": "x"},
          {"op": "modify", "select": {"ref": "x"},
           "mod": {"power": -4000}, "duration": "end_of_turn"},
          {"op": "move",
           "select": {"zone": "graveyard", "owner": "you",
                      "filter": {"types": ["creature"], "cost_le": 5},
                      "count": 1},
           "to": "bz", "reason": "put"}]

FORM = {"id": TARGET,
        "name": "天地命動 バラギアラ / 輪廻暴冥",
        "mana": 1,
        "faces": [
            {"name": "天地命動 バラギアラ",
             "types": ["creature"], "civs": ["nature"],
             "cost": 9, "power": 17000,
             "races": ["マスター・ハザード", "グランセクト"],
             "keywords": ["triple_breaker"],
             "rinne": True,
             "abilities": [CIP, CHARGE],
             "text": FACE0_TEXT},
            {"name": "輪廻暴冥",
             "types": ["spell"], "civs": ["darkness"],
             "cost": 6,
             "keywords": ["s_trigger"],
             "spell": BOUMEI,
             "text": FACE1_TEXT}],
        "text": (FACE0_TEXT.replace("\n", " ") + " ／ "
                 + FACE1_TEXT.replace("\n", " "))}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round344_disposition():
    rej = _reject_rows()
    assert len(rej) == 2073
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10248
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv(TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert TARGET not in rej             # 漏れ0
    assert (c.get("source") or {}).get("aliases") == [ALIAS]
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "mana", "faces", "text"):
        assert c.get(k) == FORM[k], k
    f0, f1 = c["faces"]
    assert f0["abilities"] == [CIP, CHARGE]      # 2件ちょうど
    assert f1["spell"] == BOUMEI                 # [choose, modify, move]
    assert f0["rinne"] is True
    # alias は独立エントリにも reject 行にも無い
    assert ALIAS not in ids and ALIAS not in rej
    d = parse_card(c, TABLES)
    assert d.faces[0].rinne is True
    # rinne_infinity は解消
    holders = {rid for rid, r in rej.items()
               if "rinne_infinity" in (r.get("gaps") or [])}
    assert holders == set(), holders


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(
        rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]


def _cid(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn
                and (zone != "bz" or e.s.cards[c].controller == p))


def _run(e, handler, limit=900, done=None):
    for _ in range(limit):
        if e.s.result is not None or (done and done()):
            return
        d = e.advance()
        if d is None:
            return
        r = handler(e, d)
        if r is not None:
            e.answer(r)
            continue
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))


def _handler(play_suffix=None, picks=()):
    st = {"played": False}
    picks = list(picks)

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 0 \
                and play_suffix and not st["played"]:
            want = f"play:{TARGET}:{play_suffix}"
            if want in keys:
                st["played"] = True
                return [keys.index(want)]
        if d["kind"] == "choose_cards" and picks:
            for dn in picks:
                idx = [i for i, o in enumerate(d["options"])
                       if o.get("cid") is not None
                       and e.s.cards[o["cid"]].defn == dn]
                if idx:
                    picks.remove(dn)
                    return idx[:1]
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [0]
        if d["kind"] in ("block", "declare_block") \
                and "no_block" in keys:
            return [keys.index("no_block")]
        return None

    handler.state = st
    return handler


# ---------- 実挙動（登録形） ----------

def test_registered_rinne_cast_boumei(rules):
    """dmrp21-tr2: 輪廻∞で暴冥を唱えると -4000 で相手獣が落ち、
    墓地のコスト5以下が出て、カードは場に残り1枚チャージされる。"""
    e = _build(rules, {"bz": [TARGET], "mana": ["T008"] * 6,
                       "graveyard": ["T001", "T741"],
                       "deck": ["T002"] * 6},
               {"bz": ["T004"], "deck": ["T002"] * 6})
    host = _cid(e, "bz", 0, TARGET)
    handler = _handler(play_suffix="1:rinne", picks=("T004", "T001"))
    _run(e, handler,
         done=lambda: "T001" in _defns(e, "bz", 0)
         and len(e.zlist("mana", 0)) == 7)
    assert handler.state["played"]
    # 唱えたカードは場に面0のまま残り、墓地へ行かない
    assert e.s.cards[host].zone == "bz" and e.s.cards[host].face == 0
    assert TARGET not in _defns(e, "graveyard", 0)
    # -4000: パワー3000 → 破壊され相手の墓地へ
    assert "T004" not in _defns(e, "bz", 1)
    assert "T004" in _defns(e, "graveyard", 1)
    # 墓地からはコスト5以下の T001 だけ（コスト9の T741 は残る）
    assert "T001" in _defns(e, "bz", 0)
    assert "T741" in _defns(e, "graveyard", 0)
    # 支払い6枚タップ＋チャージ1枚（合計7枚・アンタップ）
    tapped = [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert len(e.zlist("mana", 0)) == 7 and len(tapped) == 6


def test_registered_cip_untaps_mana(rules):
    """dmrp21-tr2: 召喚によって出た時、マナをすべてアンタップする。"""
    e = _build(rules, {"hand": [TARGET], "mana": ["T001"] * 9,
                       "deck": ["T002"] * 6},
               {"deck": ["T002"] * 6})
    handler = _handler(play_suffix="0")
    _run(e, handler,
         done=lambda: TARGET in _defns(e, "bz", 0)
         and not any(e.s.cards[c].tapped for c in e.zlist("mana", 0)))
    assert handler.state["played"]
    assert TARGET in _defns(e, "bz", 0)
    # 支払いで9枚タップ → CIP で全アンタップ
    assert not any(e.s.cards[c].tapped for c in e.zlist("mana", 0))
