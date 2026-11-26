"""再変換ラウンド447（第412弾 turn_count_free）の記録テスト。

- 新規登録1件: dmex19-028 超宮兵 マノミ
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 水 / コスト5 / パワー4000 /
  種族 ムートピア、mana 1、keywords 無し〕に
  第412弾の確立形 free_if {cmp: [{turn_count:
  {kind: cast, owner: you}}, ">=", 3]}
  （カードフィールド。登録済み dmrp06-038
  〔>= 2〕/ dmpcd02-b18〔>= 1〕と同形で
  閾値のみ違い）を足し、abilities は partial
  構築済みの CIP 誘発1件のまま、unsupported を
  外したもの。abilities はこの1件ちょうど、
  keywords は無いまま、free_if は保持）。
- 補完なし（partial の text は行の公式テキスト
  全文と一致し、登録後の全文一致も照合済み）。
- split の part[2] 定型所有は CIP 誘発1件のみで
  提出形と完全一致し dedupe された（G・ゼロは
  free_if フィールドで定型所有の対象外。
  convert は None）。
- alias 畳み込み0件（alias は dmrp06-016 の
  1件で rejects に独自行は無く、登録エントリの
  source.aliases に validate が自動付与。
  identity 実測で canon_id は対象自身、alias
  側の canon も dmex19-028、aliases_for =
  [dmrp06-016]。正本判定は通常型で対象 id と
  alias を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し
  登録なし〔proto のヒットは T1180 の notes
  内参照のみ〕）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔turn_count_free〕の出力は対象
  1件ちょうどで巻き込みなし）。
- converted 10,391→10,392 / rejects
  1,920→1,919、canonical 重なり0・漏れ0。
  turn_count_free は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第412弾本体と同形（対象を proto T1180 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T012（コスト1水呪文役＝
唱える判別。相手が1枚引く効果は無害）/
T009（水マナ役）。観測上の注意: 選択肢が
pass のみの決定はエンジンが自動で進めるため、
main 決定の観測は有料の play 選択肢が残る
マナ構成（8枚）で行う（第412弾と同種）。
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
from tests.test_vocab_pilot412 import FORM, FREE_IF, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex19-028"
ALIAS = "dmrp06-016"
GAP = "turn_count_free"
NAME = "超宮兵 マノミ"


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


def test_round447_disposition():
    rej = _reject_rows()
    assert len(rej) == 1919
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10392
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    assert ALIAS not in rej              # alias に独自行なし
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert _conv_cache.find(CONVERTED, ALIAS) is None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ムートピア"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: free_if が保持され、
    # abilities は CIP 誘発1件ちょうど
    assert c["free_if"] == FREE_IF
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")          # text 由来キーワードは union されない
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]  # validate の自動付与
    d = parse_card(c, TABLES)
    assert d.free_if == FREE_IF
    assert d.abilities == FORM
    assert not d.keywords
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第412弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _in_bz(e, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist("bz", p))


def _main_keys(e, player, casts):
    """player の main まで進め、casts を順に唱えた後の
    main 選択肢キーを返す（第412弾と同形）。"""
    casts = list(casts)
    for _ in range(900):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player:
            if casts:
                k = f"play:{casts[0]}"
                assert k in keys, f"{k} not in {keys}"
                casts.pop(0)
                e.answer([keys.index(k)])
                continue
            return keys
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def _play_and_settle(e, player, key, done):
    """player の main で key を選び、done() になるまで
    進める（第412弾と同形）。"""
    played = False
    for _ in range(600):
        if played and done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" \
                and d.get("player") == player and key in keys:
            played = True
            e.answer([keys.index(key)])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return done()


def test_no_free_without_casts(rules):
    """0枚唱えた状態では無料選択肢は出ず、有料だけが
    出る（登録カード自身で固定）。"""
    e = _build(rules, {"hand": [TARGET], "mana": ["T009"] * 8}, {})
    keys = _main_keys(e, 0, [])
    assert f"play:{TARGET}" in keys
    assert f"play:{TARGET}:free" not in keys


def test_no_free_after_two_spells(rules):
    """2枚では閾値3に届かず、無料選択肢は出ない
    （有料は残る）。"""
    e = _build(rules,
               {"hand": [TARGET, "T012", "T012"], "mana": ["T009"] * 8},
               {})
    keys = _main_keys(e, 0, ["T012", "T012"])
    assert f"play:{TARGET}" in keys
    assert f"play:{TARGET}:free" not in keys
    assert _tapped_mana(e, 0) == 2


def test_free_after_three_spells_and_cip(rules):
    """3枚唱えると無料選択肢が出る。無料で召喚すると
    マナは呪文の3枚分しかタップされず、CIP で2枚引く。"""
    e = _build(rules,
               {"hand": [TARGET, "T012", "T012", "T012"],
                "mana": ["T009"] * 8},
               {})
    keys = _main_keys(e, 0, ["T012", "T012", "T012"])
    assert f"play:{TARGET}:free" in keys
    assert _tapped_mana(e, 0) == 3
    hand_before = len(e.zlist("hand", 0))
    assert hand_before == 1            # 手札は登録カードのみ
    ok = _play_and_settle(e, 0, f"play:{TARGET}:free",
                          lambda: _in_bz(e, 0, TARGET))
    assert ok
    assert _tapped_mana(e, 0) == 3     # 無料召喚で追加タップなし
    # CIP: 召喚で -1、ドローで +2
    assert len(e.zlist("hand", 0)) == hand_before - 1 + 2


def test_paid_summon_and_cip(rules):
    """通常の支払いでも召喚でき、CIP は同様に発火する
    （free_if は支払い経路を妨げない）。"""
    e = _build(rules, {"hand": [TARGET], "mana": ["T009"] * 5}, {})
    ok = _play_and_settle(e, 0, f"play:{TARGET}",
                          lambda: _in_bz(e, 0, TARGET))
    assert ok
    assert _tapped_mana(e, 0) == 5
    assert len(e.zlist("hand", 0)) == 2   # CIP の2ドロー


def test_opponent_casts_do_not_enable(rules):
    """相手が自分のターンに呪文を3枚唱えても、自分の
    次のターンでは無料にならない（owner: you の判別）。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": ["T009"] * 5},
               {"hand": ["T012", "T012", "T012"], "mana": ["T009"] * 3})
    keys = _opp_casts_then_my_main(e)
    assert keys is not None
    assert f"play:{TARGET}" in keys
    assert f"play:{TARGET}:free" not in keys


def _opp_casts_then_my_main(e):
    """自分の1ターン目の main は pass で終え、相手
    （player 1）に T012 を3枚唱えさせ、その後の自分
    （player 0）の main 選択肢キーを返す
    （第412弾と同形）。"""
    casts = ["T012", "T012", "T012"]
    phase = "first"    # 自分の1ターン目 → 相手 → 自分の2ターン目
    for _ in range(1200):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == 0 \
                and phase == "first":
            phase = "opp"            # 何もせずターンを終える
        elif d["kind"] == "main" and d.get("player") == 1 \
                and phase == "opp":
            if casts:
                k = f"play:{casts[0]}"
                assert k in keys, f"{k} not in {keys}"
                casts.pop(0)
                e.answer([keys.index(k)])
                if not casts:
                    phase = "mine"
                continue
        elif d["kind"] == "main" and d.get("player") == 0 \
                and phase == "mine":
            return keys
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None
