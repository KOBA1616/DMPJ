"""再変換ラウンド408（第373弾 deck_bottom_to_hand）の記録テスト。

- 新規登録1件: dmrp04s-011 ラジコンBOY
  （登録形は提出形と完全一致: partial の骨格
  〔ゼロ / コスト6 / パワー3000 / 種族 ジョーカーズ、
  keywords [super_s_trigger]、xB 誘発〔sst: true〕
  1件〕の abilities の**先頭**に第373弾の確立形
  CIP 誘発〔trigger {event: move, to: bz,
  subject: self} → move {select: {zone: deck,
  owner: you, from_bottom: 1}, to: hand,
  reason: draw}（第287弾形A・登録先例 dmr06-002 と
  同形）〕を足し、unsupported を外したもの。
  abilities は [CIP, xB] の2件ちょうど。text は
  partial の時点で公式全文と一致するため text の
  補完はなし）。
- alias 畳み込み0件（alias 自体が無い）。正本判定:
  対象 id dmrp04s-011 を real.yaml /
  real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml と
  照合し、いずれにも登録なし（proto.yaml のヒットは
  T1121 の notes 内参照のみ）。identity 実測で
  canon(dmrp04s-011) = dmrp04s-011（対象 id が正本）、
  aliases_for(ラジコンBOY, dmrp04s-011) = []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [deck_bottom_to_hand] のため
  reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,352→10,353 / rejects 1,960→1,959、
  canonical 重なり0・alias 重なり0・漏れ0。
  deck_bottom_to_hand はファミリーがこの1件
  だけだったため完全に解消。
- 付記: 初回の submit はスキーマ不一致で失敗した。
  原因は schema.py の selector 定義に from_bottom
  （第287弾で defs.py の SELECTOR_KEYS に追加済み）が
  欠けていたことで、selector に "from_bottom" を
  追加して data/schema/card.schema.json を再生成
  （差分は from_bottom の $ref 3行のみ）してから
  修正形を直接再提出して合格した。検証に失敗した
  submit は登録も rejects への差し戻しもしない
  （行は reopen で外れたまま）ため、再 reopen は
  していない。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第373弾本体の薄い包み（対象を登録カードに差し
替えたもの）で、tests.conftest は import しない
（第319弾以降の作法）。判別役は既存 proto を流用
（T827・T828・T003＝山札の中身、T423＝マナ役）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmrp04s-011"
GAP = "deck_bottom_to_hand"

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [{"op": "move",
                   "select": {"zone": "deck", "owner": "you", "from_bottom": 1},
                   "to": "hand", "reason": "draw"}]}
XB = {"kind": "trigger", "sst": True,
      "when": {"event": "move", "to": "bz", "subject": "self"},
      "effect": [
          {"op": "choose",
           "select": {"zone": "bz", "owner": "opp", "chooser": "opp",
                      "filter": {"types": ["creature"]}, "count": 3},
           "as": "trio"},
          {"op": "choose",
           "select": {"ref": "trio", "chooser": "opp", "count": 1},
           "as": "tohand"},
          {"op": "move", "select": {"ref": "tohand"},
           "to": "hand", "reason": "return"},
          {"op": "choose",
           "select": {"ref": "trio", "chooser": "opp", "count": 1},
           "as": "tomana"},
          {"op": "mana_put", "select": {"ref": "tomana"}},
          {"op": "move", "select": {"ref": "trio", "count": "all"},
           "to": "deck", "reason": "put", "position": "bottom"}]}
FORM = [CIP, XB]
FULL_TEXT = ("スーパー・S・トリガー（このクリーチャーを自分のシールドゾーンから"
             "手札に加える時、コストを支払わずにすぐ召喚してもよい。その時自分の"
             "シールドが１つもなければ、このクリーチャーにxB能力を与える）"
             "このクリーチャーがバトルゾーンに出た時、自分の山札の一番下の"
             "カードを手札に加える。xBこのクリーチャーがバトルゾーンに出た時、"
             "相手は自身のクリーチャーを３体選び、そのうちの１体を自身の手札に"
             "加え、１体をマナゾーンに置き、１体を山札の一番下に置く。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round408_disposition():
    rej = _reject_rows()
    assert len(rej) == 1959
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10353
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: abilities は [CIP, xB] の2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["keywords"] == ["super_s_trigger"]
    assert c["text"] == FULL_TEXT        # text の補完はなし
    assert c["name"] == "ラジコンBOY"
    assert c["types"] == ["creature"] and c["civs"] == ["zero"]
    assert c["cost"] == 6 and c["power"] == 3000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    d = parse_card(c, TABLES)
    trigs = [a for a in d.abilities if a["kind"] == "trigger"]
    assert trigs[0] == CIP
    assert trigs[1].get("sst") is True
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第373弾本体と同形、対象は登録カード） ----------

def _setup(rules, p0, p1=None):
    """山札の中身を spec の deck リストだけにする（deck_exact）。
    山札の並びは seed でシャッフルされるため、テストは実状態を読む。"""
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20,
                                  "deck_exact": [True, True]})


def _deck(e, player=0):
    return list(e.s.zones["deck"][player])


def _zone_of(e, cid):
    return e.s.cards[cid].zone


def _drive(e, on_decision, limit=600):
    for _ in range(limit):
        if e.s.result is not None:
            return "result"
        d = e.advance()
        if d is None:
            return "done"
        r = on_decision(e, d)
        if r == "stop":
            return "stopped"
        if r == "ok":
            continue
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("driver limit reached")


def _summon_registered(rules, p1=None):
    """登録カードを手札から召喚し、解決後の観測点（次の相手
    ターンのチャージ決定）まで進める。戻り値: (engine, 召喚
    時点の山札)。"""
    e = _setup(rules, {"hand": [TARGET], "mana": ["T423"] * 6,
                       "deck": ["T827", "T003", "T828", "T827"]},
               p1 if p1 is not None else {"deck": ["T827"] * 3})
    snap = []
    played = []

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and f"play:{TARGET}" in keys:
            played.append(True)
            snap.append(_deck(e, 0))       # 召喚時点（ドロー後）の山札
            e.answer([keys.index(f"play:{TARGET}")])
            return "ok"
        if played and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        if played and d["kind"] == "charge":
            return "stop"                  # 解決済みの観測点
        return None

    _drive(e, on_dec)
    assert played, "registered card was not played"
    return e, snap[0]


def test_registered_cip_bottom_card_to_hand(rules):
    """登録カード: 出た時、自分の山札の一番下のカードが
    手札に加わり、残りの並びは変わらない（第287弾形A）。"""
    e, deck0 = _summon_registered(rules)
    bottom, second = deck0[-1], deck0[-2]
    assert _zone_of(e, bottom) == "hand"          # 一番下が手札に来た
    assert _deck(e, 0) == deck0[:-1]              # 残りの並びは不変
    assert _deck(e, 0)[-1] == second


def test_registered_xb_does_not_fire_on_normal_summon(rules):
    """登録カード: 通常召喚では sst 印が無いため xB 誘発は
    発動しない: 相手のクリーチャー3体はすべてバトルゾーンに
    残る（xB が発動すれば手札・マナ・山札下へ1体ずつ移る
    はず）。CIP 自体は働く。"""
    e, deck0 = _summon_registered(rules, {"bz": ["T827", "T827", "T827"],
                                          "deck": ["T827"] * 3})
    opp_bz = list(e.bz_tops(1))     # bz は共有ゾーンのため所有者で照合
    assert len(opp_bz) == 3
    assert all(_zone_of(e, c) == "bz" for c in opp_bz)
    # CIP 自体は働いている（一番下が自分の手札に来ている）
    assert _zone_of(e, deck0[-1]) == "hand"
