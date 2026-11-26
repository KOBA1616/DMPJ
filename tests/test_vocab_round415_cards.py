"""再変換ラウンド415（第380弾 up_to_cost_reduction 残り1件）の記録テスト。

- 新規登録1件: dm23rp4x-tf03 西南の超人 /
  断断打つべしナウ（ツインパクト。登録形は提出形と
  完全一致: partial の組立て済み部分〔クリーチャー面の
  セイバー置換・呪文面の choose→tap→modify 3 op〕に
  第347弾の確立形 static〔affects {zone: hand,
  owner: you, filter {races: [ジャイアント]}},
  mod {cost: -2}〕（登録済み dmbd02-014 西南の超人＝
  同一カードの単体版と同文同形）をクリーチャー面の
  条項順どおりセイバー置換の前に足し、unsupported を
  外したもの。クリーチャー面の abilities はこの2件
  ちょうど、呪文面の spell は3 op ちょうど。補完あり:
  top の text は行にクリーチャー面分しか無いため、
  面テキストを「 ／ 」で連結した全文を入れた
  〔クリーチャー面は「。/ セイバー」を dmbd02-014
  登録形に倣い「。セイバー」に直し、呪文面は
  「S・トリガー 自分…」の平坦形〕）。
- alias 畳み込み0件（alias 5件 dm23rp4-t03 /
  dm23rp4-tf03 / dmex04-017 / dmex13-017 /
  dmex15-b073 はいずれも rejects に独自行が無く、
  登録形の source.aliases に入っている）。正本判定:
  対象 id と全 alias を real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / proto.yaml /
  converted.yaml と照合し、いずれにも登録なし
  （proto.yaml のヒットは T1134 の notes 内参照のみ）。
  identity 実測で canon_id は対象・全 alias とも
  dm23rp4x-tf03、aliases_for がこの5件を返す
  （partial の source.aliases と一致）。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [up_to_cost_reduction] のため
  reopen で外してから submit（reopen の出力は対象
  1件ちょうど）。
- converted 10,359→10,360 / rejects 1,953→1,952、
  canonical 重なり0・漏れ0。up_to_cost_reduction は
  ファミリーがこの1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第380弾本体と同形（対象を proto T1134 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T356（ジャイアント・コスト7）/
T341（ジャイアント・コスト3）/ T005（非ジャイアント・
スピードアタッカー）/ T001（自然の素）/ T710
（単体破壊呪文）。
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
from tests.test_vocab_pilot380 import (  # noqa: E402
    COST_STATIC, FACE0, FACE1, SABER, SPELL_OPS, TOP_TEXT)

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm23rp4x-tf03"
GAP = "up_to_cost_reduction"
ALIASES = ["dm23rp4-t03", "dm23rp4-tf03", "dmex04-017",
           "dmex13-017", "dmex15-b073"]
NAME = "西南の超人 / 断断打つべしナウ"


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


def test_round415_disposition():
    rej = _reject_rows()
    assert len(rej) == 1952
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10360
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0（aliases 欄）
    assert TARGET not in rej             # 対象行は解消
    for a in ALIASES:
        assert a not in rej              # alias に rejects の独自行は無い
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert not c.get("aliases")
    # alias 5件は source.aliases に入っている
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: faces・mana・text が
    # プロト T1134（＝第380弾の確立形）と同一
    assert c["faces"] == [FACE0, FACE1]
    assert c["mana"] == 1
    assert c["text"] == TOP_TEXT        # 連結全文（補完あり）
    f0, f1 = c["faces"]
    assert f0["abilities"] == [COST_STATIC, SABER]
    assert len(f0["abilities"]) == 2     # クリーチャー面は2件ちょうど
    assert f1["spell"] == SPELL_OPS
    assert len(f1["spell"]) == 3         # 呪文面は3 op ちょうど
    assert f1["keywords"] == ["s_trigger"]
    d = parse_card(c, TABLES)
    assert d is not None
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第380弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive_to_main(e, player=0, limit=300):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "main" and d.get("player") == player:
            return d, _keys(d)
        if "pass" in _keys(d):
            e.answer([_keys(d).index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("main never came")


def test_registered_giant_discount(rules):
    # ジャイアント T356（コスト7）が 5 で召喚できる
    e = _build(rules, {"bz": [TARGET], "hand": ["T356"],
                       "mana": ["T001"] * 5}, {})
    d, keys = _drive_to_main(e)
    assert "play:T356" in keys
    # マナ4では届かない
    e = _build(rules, {"bz": [TARGET], "hand": ["T356"],
                       "mana": ["T001"] * 4}, {})
    d, keys = _drive_to_main(e)
    assert "play:T356" not in keys


def test_registered_non_giant_not_discounted(rules):
    # ジャイアントでない T005（火・コスト3）は軽減を受けない
    e = _build(rules, {"bz": [TARGET], "hand": ["T005"],
                       "mana": ["T005", "T001"]}, {})
    d, keys = _drive_to_main(e)
    assert "play:T005" not in keys


def test_registered_pay_cost_values(rules):
    # T341（ジャイアント・コスト3）の pay_cost が発生源ありで 1、
    # T356（コスト7）は 5
    e = _build(rules, {"bz": [TARGET], "hand": ["T341", "T356"]}, {})
    for defn, want in (("T341", 1), ("T356", 5)):
        cid = next(c for c in e.zlist("hand", 0)
                   if e.s.cards[c].defn == defn)
        assert e.chars_ro(cid)["pay_cost"] == want


def _saber_game(rules, accept):
    """p1 の T710 が p0 の T356 を破壊する場面を作り、
    セイバー置換の判断で accept / decline を選んで結果を返す。"""
    e = _build(rules, {"bz": [TARGET, "T356"]},
               {"hand": ["T710"], "mana": ["T005"]})
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        k = _keys(d)
        if d["kind"] == "main" and d.get("player") == 1 \
                and "play:T710" in k:
            e.answer([k.index("play:T710")])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards" \
                and any(x.startswith("bz:T356") for x in k):
            e.answer([k.index(next(x for x in k
                                   if x.startswith("bz:T356")))])
        elif d["kind"] == "choose_replacement":
            assert d.get("player") == 0
            assert any(x.startswith(f"replace:{TARGET}") for x in k), k
            e.answer([k.index(next(x for x in k
                                   if x.startswith(f"replace:{TARGET}")))]
                     if accept else [k.index("decline")])
            for _ in range(60):
                d2 = e.advance()
                if d2 is None:
                    break
                if "pass" in _keys(d2):
                    e.answer([_keys(d2).index("pass")])
                else:
                    e.answer(list(range(d2["min"])))
            return e
        elif "pass" in k:
            e.answer([k.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("replacement decision never came")


def test_registered_saber_accept(rules):
    # セイバーを使う: T356 は残り、かわりに登録カードが破壊される
    e = _saber_game(rules, accept=True)
    assert "T356" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert TARGET in [e.s.cards[c].defn
                      for c in e.zlist("graveyard", 0)]


def test_registered_saber_decline(rules):
    # セイバーを使わない: T356 が破壊され、登録カードは残る
    e = _saber_game(rules, accept=False)
    assert TARGET in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert "T356" in [e.s.cards[c].defn
                      for c in e.zlist("graveyard", 0)]


def _p1_attack_options(rules, cast):
    """p0 が呪文面を唱えた（または唱えなかった）後、
    p1 の T005 の攻撃選択肢と T001 のタップ状態を返す。"""
    p0 = {"bz": ["T001"], "mana": ["T001"]}
    if cast:
        p0["hand"] = [TARGET]
    e = _build(rules, p0, {"bz": ["T005"]})
    done = False
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        k = _keys(d)
        if cast and not done and d["kind"] == "main" \
                and d.get("player") == 0 and f"play:{TARGET}:1" in k:
            done = True
            e.answer([k.index(f"play:{TARGET}:1")])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif cast and done and any(x.startswith("bz:T001") for x in k) \
                and d.get("player") == 0:
            e.answer([k.index(next(x for x in k
                                   if x.startswith("bz:T001")))])
        elif d["kind"] == "attack" and d.get("player") == 1:
            cid = next(c for c in e.bz_tops(0)
                       if e.s.cards[c].defn == "T001")
            return [x for x in k if x.startswith("attack:T005:")], \
                e.s.cards[cid].tapped
        elif "pass" in k:
            e.answer([k.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("p1 attack decision never came")


def test_registered_spell_face_taunt(rules):
    # 唱えた場合: 選んだ T001 がタップし、相手は可能なら
    # そのクリーチャーを攻撃しなければならない
    opts, tapped = _p1_attack_options(rules, cast=True)
    assert tapped
    assert "attack:T005:T001" in opts, opts
    assert "attack:T005:player" not in opts, opts
    # 唱えない場合: 誘引は無くプレイヤーを攻撃できる
    opts, tapped = _p1_attack_options(rules, cast=False)
    assert not tapped
    assert "attack:T005:player" in opts, opts
