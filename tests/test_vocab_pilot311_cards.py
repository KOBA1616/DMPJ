"""語彙パイロット第311弾の対象カード検証（ラウンド346で登録済み）。

dm17-s04 ネオウェーブ・カタストロフィー は
gaps = [evolution_cross_gear, reveal_and_cast_free] の1件だった。
evolution_cross_gear は第304弾で実装済み（これが同ギャップの
最後の併記行）。残余は攻撃誘発の
「自分の山札の上から３枚を表向きにする。その中から、
「S・トリガー」付き呪文を好きなだけ選び、コストを支払わずに
唱えてもよい。その後、唱えなかったカードを自分の山札の
一番下に好きな順番で戻す」だけだった。

第311弾の結論は **ドリフト**（新規語彙・エンジン変更なし）:
第267弾 輪廻虹災（T740）の choose {from_top, look, count: all,
reveal: true, as: pile} ＋残りの move {position: bottom,
order: choose} に、「好きなだけ選び」を
choose {ref: pile, filter: {types: [spell], keyword: s_trigger},
count: all, up_to: true, as: casts}（selectors の any_n 形）、
「唱える」を第233弾の repeat {over: casts, body: [play_free
{select: {ref: it}}]} で繋ぐ。実挙動は第311弾本体の
プロト T958 で固定し、ラウンド346で登録した。本ファイルは
登録形の固定に書き換えた（実挙動は
test_vocab_round346_cards.py が登録カード自身で固定）。

登録形は partial ＋ types [cross_gear, evolution] ＋
evolve_from {civs: [light, water]} ＋ 攻撃誘発で、
abilities は [ブロッカー常在型, 攻撃誘発] の2件ちょうど
（連結・merge_split 由来の混入なし）。正本判定は identity の
実データ照合による: canon_id は dm17-s04 自身＝独立正本、
aliases は無い。text は reject 行の正式本文（\\n 区切り）と同一。
本件の登録で reveal_and_cast_free は解消し、
evolution_cross_gear の併記は dmc66-034 の1行だけが残る。

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

TARGET = "dm17-s04"

TEXT = ("このクロスギアはマナゾーンにタップして置かれる。\n"
        "進化-自分の光または水のクロスギア１枚の上に置く。\n"
        "これをクロスしたクリーチャーは「ブロッカー」を得る。\n"
        "これをクロスしたクリーチャーが攻撃する時、自分の山札の上から３枚を表向きにする。"
        "その中から、「S・トリガー」付き呪文を好きなだけ選び、コストを支払わずに唱えてもよい。"
        "その後、唱えなかったカードを自分の山札の一番下に好きな順番で戻す。")

BLOCKER_STATIC = {"kind": "static", "affects": "crossed",
                  "mod": {"grant": ["blocker"]}}

ATTACK_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "crossed"},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "from_top": 3,
                    "look": True, "count": "all"},
         "reveal": True, "as": "pile"},
        {"op": "choose",
         "select": {"ref": "pile",
                    "filter": {"types": ["spell"], "keyword": "s_trigger"},
                    "count": "all", "up_to": True},
         "as": "casts"},
        {"op": "repeat", "over": "casts", "as": "it",
         "body": [{"op": "play_free", "select": {"ref": "it"}}]},
        {"op": "move",
         "select": {"ref": "pile", "zone": "deck", "count": "all"},
         "to": "deck", "position": "bottom", "order": "choose",
         "reason": "put"},
    ],
}

FORM = {"id": TARGET,
        "name": "ネオウェーブ・カタストロフィー",
        "types": ["cross_gear", "evolution"],
        "civs": ["light", "water"],
        "cost": 5, "mana": 1,
        "evolve_from": {"civs": ["light", "water"]},
        "text": TEXT,
        "abilities": [BLOCKER_STATIC, ATTACK_TRIGGER]}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_target_registered():
    rows = _rows()
    assert len(rows) <= 2071  # 件数は減る一方（スナップショット固定をやめた）
    assert TARGET not in rows  # 登録により reject 行は外れた
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10250  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    aliases = set()
    for c in conv:
        aliases.update((c.get("source") or {}).get("aliases") or [])
    assert TARGET in ids and TARGET not in aliases
    c = next(c for c in conv if c["id"] == TARGET)
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")   # alias なし
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "mana",
              "evolve_from", "text", "abilities"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2
    # reveal_and_cast_free は解消。evolution_cross_gear は
    # dmc66-034 の1行だけが残る
    assert not {rid for rid, r in rows.items()
                if "reveal_and_cast_free" in (r.get("gaps") or [])}
    evo = {rid for rid, r in rows.items()
           if "evolution_cross_gear" in (r.get("gaps") or [])}
    assert evo == {"dmc66-034"}, evo


def test_established_form_parses():
    d = parse_card(FORM, TABLES)
    assert d.types == ["cross_gear", "evolution"]
    assert d.evolve_from == {"civs": ["light", "water"]}
    assert d.cost == 5
    kinds = [a["kind"] for a in FORM["abilities"]]
    assert kinds == ["static", "trigger"]
    # 登録カード自身も parse できる
    c = _conv_cache.find(CONVERTED, TARGET)
    d2 = parse_card(c, TABLES)
    assert d2.types == ["cross_gear", "evolution"]
    assert d2.cost == 5
