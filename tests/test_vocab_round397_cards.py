"""再変換ラウンド397（第362弾 entry_turn_attack_restriction）の記録テスト。

- 新規登録1件: dm23bd6-003 アカシック・B /
  「バブルの泡に溺れるのヨ！」（ツインパクト。登録形は
  提出形と完全一致: クリーチャー面は第362弾の確立形
  1能力のみで keywords なし、呪文面は keywords
  [s_trigger]＋spell 2 op〔bounce＋may draw〕）。
- alias 畳み込み0件（converted の登録エントリに aliases
  なし。対象 id は real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / converted.yaml の
  いずれにも無く、proto.yaml のヒットは T1089 の notes 内
  参照のみ。identity の canon_id 実測で自ID、
  aliases_for は空）。stale クリーンアップ0件・
  差し戻し0件。
- 対象1行は gaps = [entry_turn_attack_restriction] のため
  reopen で外してから submit（reopen の出力は対象1件
  ちょうど）。
- converted 10,341→10,342 / rejects 1,971→1,970、
  canonical 重なり0・alias 重なり0・漏れ0。
  entry_turn_attack_restriction はファミリーがこの
  1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_attacking_
  player）は判断待ちのため本ラウンドでも触っていない。

呪文面の検証（ラウンド397で実施）:
「バブルの泡に溺れるのヨ！」（コスト7・水）は partial に
含まれておらず未検証だったが、既存語彙で正確に表せる
ことを確認した。根拠: (1) S・トリガーはツインパクト
呪文面の面キーワード s_trigger（登録先例 dm23rp3-048）。
(2) 「その相手のクリーチャーを1体選んで手札に戻す」は
op: bounce {select: {zone: bz, owner: opp, filter:
{types: [creature]}, count: 1}}（dm23rp4x-058 の CIP
効果・スパイラル・ゲートの呪文形と同形）。(3) 「カードを
1枚引いてもよい」の「〜てもよい」はドローにのみ係る
ため may {body: [draw {count: 1}]} とし、戻しの選択は
may の外の必須選択（choose の min=1 を実挙動で確認）。
(4) 「相手1人につき」は、本エンジンが2人戦であり、
登録済みカードにも2人戦前提で相手1人＝1回分として
登録した先例がある（dm23bd5-007 の notes「2人戦前提
（各相手＝相手）」、dm23bd7-005 の notes「『相手1人
につき』は2人戦前提で1体として登録した」）ため、その
慣行どおり1回分で正確に表せる。多人数戦そのものを
要する他の「相手1人につき」行（手札・マナ枚数の
相手ごと比較など）とは異なり、本件は相手ごとの
比較や集計を含まない。

実挙動は登録カード自身で固定する。ドライバは
scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。フィクスチャは
proto T1090（スピードアタッカー役）/ T1091（標的役）。
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
TARGET = "dm23bd6-003"
GAP = "entry_turn_attack_restriction"

CREATURE_FORM = [{"kind": "static",
                  "affects": {"zone": "bz", "owner": "opp",
                              "filter": {"types": ["creature"],
                                         "entered_this_turn": True}},
                  "mod": {"deny": ["attack_player", "attack_creature"]}}]
SPELL_FORM = [{"op": "bounce",
               "select": {"zone": "bz", "owner": "opp",
                          "filter": {"types": ["creature"]},
                          "count": 1}},
              {"op": "may", "body": [{"op": "draw", "count": 1}]}]


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


def test_round397_disposition():
    rej = _reject_rows()
    assert len(rej) == 1970
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10342
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias 畳み込み0件
    assert not (c.get("source") or {}).get("unsupported")
    f0, f1 = c["faces"]
    assert f0["name"] == "アカシック・B"
    assert f0["abilities"] == CREATURE_FORM
    assert len(f0["abilities"]) == 1     # 能力は1件ちょうど
    assert not f0.get("keywords")
    assert f0["cost"] == 3 and f0["power"] == 3000
    assert f0["races"] == ["マジック・コマンド", "マーメイド"]
    assert f1["name"] == "「バブルの泡に溺れるのヨ！」"
    assert f1["types"] == ["spell"] and f1["cost"] == 7
    assert f1["keywords"] == ["s_trigger"]
    assert f1["spell"] == SPELL_FORM
    d = parse_card(c, TABLES)
    assert [f.name for f in d.faces] == ["アカシック・B",
                                         "「バブルの泡に溺れるのヨ！」"]
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


# ---------- クリーチャー面の実挙動 ----------

def test_registered_creature_face_blocks_entry_turn_attacks(rules):
    """登録カードが場にいる時、出たターンの相手スピード
    アタッカーはプレイヤーへもクリーチャーへも攻撃
    できない（第362弾の確立形の登録形での再演）。"""
    e = _build(rules,
               {"bz": [TARGET, "T1091"]},
               {"hand": ["T1090"], "mana": ["T1090", "T1090"]})
    shields = len(e.zlist("shield", 0))
    played = False
    attack_keys = []
    target_turn = None
    for _ in range(600):
        if target_turn is not None and e.s.turn > target_turn + 1:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] in ("charge", "main", "attack") \
                and d.get("player") == 1 and target_turn is None:
            target_turn = e.s.turn
        if d["kind"] == "main" and d.get("player") == 1 and not played:
            hit = [i for i, k in enumerate(keys) if k == "play:T1090"]
            if hit:
                played = True
                target_turn = e.s.turn
                e.answer([hit[0]])
                continue
        if d["kind"] == "attack" and d.get("player") == 1 \
                and e.s.turn == target_turn:
            attack_keys.extend(keys)
        if d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert played
    assert not [k for k in attack_keys if k.startswith("attack:T1090:")]
    assert "T1090" in _defns(e, "bz", 1)
    cid = next(c for c in e.bz_tops(1) if e.cdef(c).id == "T1090")
    assert not e.s.cards[cid].tapped     # 攻撃していない
    assert len(e.zlist("shield", 0)) == shields   # ブレイクなし


# ---------- 呪文面の実挙動 ----------

def _cast_spell_face(rules, may_yes):
    """登録カードの呪文面を唱えて解決まで進める。
    （唱えたか, 解決後の局面）を返す。"""
    e = _build(rules, {"hand": [TARGET], "mana": [TARGET] * 7},
               {"bz": ["T1091", "T1091"]})
    cast = False
    chose_min = None
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 0 and not cast:
            if f"play:{TARGET}:1" in keys:
                cast = True
                e.answer([keys.index(f"play:{TARGET}:1")])
                continue
        if cast and d["kind"] == "choose_cards":
            chose_min = d["min"]
            idx = [i for i, o in enumerate(d["options"])
                   if "T1091" in o["key"]]
            assert idx
            e.answer(idx[:1])
            continue
        if cast and d["kind"] == "yes_no":
            e.answer([keys.index("yes" if may_yes else "no")])
            for _ in range(50):
                d2 = e.advance()
                if d2 is None or d2["kind"] in ("main", "charge", "attack"):
                    break
                e.answer(_boring(d2))
            break
        e.answer(_boring(d))
    return e, cast, chose_min


def test_registered_spell_face_bounces_and_may_draw(rules):
    """呪文面を唱えると相手のクリーチャー1体が持ち主の
    手札に戻り（選択は必須）、カードを1枚引いてもよい
    （引くことを選んだ場合）。"""
    e, cast, chose_min = _cast_spell_face(rules, may_yes=True)
    assert cast
    assert chose_min == 1                # 戻しの選択は必須
    assert _defns(e, "bz", 1) == ["T1091"]   # 2体のうち1体が戻った
    assert "T1091" in _defns(e, "hand", 1)
    assert len(e.zlist("hand", 0)) == 1  # ドロー1枚（手札は唱えた1枚のみだった）
    assert TARGET in _defns(e, "graveyard", 0)   # 唱えた後は墓地へ


def test_registered_spell_face_may_draw_declined(rules):
    """引かないことを選べばドローは無く、戻しだけが
    行われる（may はドローにのみ係る）。"""
    e, cast, chose_min = _cast_spell_face(rules, may_yes=False)
    assert cast
    assert chose_min == 1
    assert _defns(e, "bz", 1) == ["T1091"]
    assert len(e.zlist("hand", 0)) == 0  # ドローなし
    assert TARGET in _defns(e, "graveyard", 0)


def test_registered_spell_face_strigger_casts_for_free(rules):
    """シールドから手札に加わる時、S・トリガーで呪文面を
    コストなしで唱えられる: 攻撃してきた相手クリーチャー
    を手札に戻せる。"""
    e = _build(rules, {"shield": [TARGET, "T002", "T002", "T002", "T002"]},
               {"bz": ["T1090"]})
    shield_cid = next(c for c in e.zlist("shield", 0)
                      if e.cdef(c).id == TARGET)
    seen = []
    resolving = False
    for _ in range(1200):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 1 \
                and "attack:T1090:player" in keys:
            e.answer([keys.index("attack:T1090:player")])
            continue
        if d["kind"] == "choose_shields":
            e.answer([e.zlist("shield", 0).index(shield_cid)])
            continue
        if d["kind"] == "declare_strigger":
            seen.extend(keys)
            hit = [i for i, k in enumerate(keys)
                   if k == f"strigger:{TARGET}:1"]
            assert hit, keys
            resolving = True
            e.answer(hit[:1])
            continue
        if resolving and d["kind"] == "yes_no":
            e.answer([keys.index("no")])   # ドローはしない
            continue
        if resolving:
            if e.s.cards[shield_cid].zone == "graveyard" \
                    and not e.bz_tops(1):
                break
            e.answer([0])
            continue
        e.answer(_boring(d))
    assert f"strigger:{TARGET}:1" in seen
    assert e.s.cards[shield_cid].zone == "graveyard"   # 唱えて墓地へ
    assert _defns(e, "bz", 1) == []                    # 攻撃側が戻された
    assert "T1090" in _defns(e, "hand", 1)
