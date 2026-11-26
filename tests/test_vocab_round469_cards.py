"""再変換ラウンド469（第434弾
keyword_exists_condition）の記録テスト。

- 新規登録1件: dmr07-010 マネコン
  （partial の骨格〔クリーチャー / 水 / コスト4 /
  パワー1000 / 種族 サイバーロード/アンノイズ、
  mana 1〕に第434弾の確立形 abilities 2件
  〔trigger {when: {event: attack, subject: self},
  if: {exists: {zone: bz, owner: any, filter:
  {types: [creature], keyword: double_breaker}}},
  effect: [modify {select: {ref: self}, mod:
  {power: 5000, breaks: 2}, duration: end_of_turn}]}
  と triple_breaker 版〔modify {power: 11000,
  breaks: 3}〕〕（exists＋keyword フィルタは登録済み
  dmd05-015 / dmrp08-002 の確立形。selector の
  keyword 照合は付与分を含む現在特性で見るため
  第398弾の affects base 照合制限は及ばない。
  modify の power と breaks の併記は登録済み
  dm39-033 / dmsp01-012 / promoy5-037 の確立形）を
  足したもの。登録形は提出形と完全一致〔source
  以外の全フィールドを照合〕、abilities は
  trigger 2件ちょうど、text は公式全文）。
- 補完あり: text（公式全文。partial の text は
  断片「「W・ブレイカー」を持つクリーチャーが
  あれば」）＋abilities。
- alias 畳み込み0件（alias 無し。正本判定は
  通常型で対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1223 の notes
  内参照のみ〕、identity 実測で canon_id は対象
  自身、aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔keyword_exists_condition〕の出力は
  対象1件ちょうど）。
- converted 10,414→10,415 / rejects
  1,897→1,896、canonical 重なり0・漏れ0。
  keyword_exists_condition は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第434弾本体と同形（対象を proto T1223 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1224（W・ブレイカー持ち）/
T1225（T・ブレイカー持ち）/ T001（バニラ）/
T004（パワー3000ブロッカー）。
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
from tests.test_vocab_pilot434_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot434 import FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr07-010"
GAP = "keyword_exists_condition"
ATK = f"attack:{TARGET}:player"


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


def test_round469_disposition():
    rej = _reject_rows()
    assert len(rej) == 1896
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10415
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # keyword_exists_condition 完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 2      # abilities は trigger 2件ちょうど
    assert [a["kind"] for a in c["abilities"]] == ["trigger", "trigger"]
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    assert d.types == ["creature"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第434弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _drive(e, attacker=None, blocker=None, stop=None, limit=900,
           breaker=None):
    """attacker（攻撃キー）を一度だけ攻撃させ、blocker
    （proto id）がいればブロックさせる。stop(e) が真に
    なるまで進める。発生源は召喚酔いがあるため、攻撃
    キーが現れるまで（次の自分のターンまで）進める。
    breaker を指定すると、複数のブレイカー能力を得た時の
    509.2c の選択（choose_breaker）でその枚数を選ぶ。"""
    st = {"attacked": False, "breaker_options": None}
    for _ in range(limit):
        if stop and stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if attacker and not st["attacked"] and d["kind"] == "attack" \
                and attacker in keys:
            e.answer([keys.index(attacker)])
            st["attacked"] = True
            continue
        if d["kind"] == "block" and blocker:
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"bz:{blocker}")]
            if hit:
                e.answer([hit[0]])
                continue
        if d["kind"] == "choose_breaker":
            st["breaker_options"] = keys
            if breaker is not None and f"breaks:{breaker}" in keys:
                e.answer([keys.index(f"breaks:{breaker}")])
                continue
        _answer_default(e, d)
    return st


def test_w_breaker_present_breaks_two(rules):
    """登録カード: W・ブレイカー持ちが場にいれば、攻撃時に
    パワー+5000・W・ブレイカーを得てシールドを2枚ブレイクする。"""
    e = _build(rules, {"bz": [TARGET, "T1224"]}, {"bz": []})
    src = _cid(e, 0, TARGET)
    st = _drive(e, attacker=ATK,
                stop=lambda: len(e.zlist("shield", 1)) <= 3)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 3    # 2枚ブレイク
    assert e.s.cards[src].zone == "bz"


def test_w_breaker_present_power_wins_battle(rules):
    """パワー判別: +5000 で 6000 になり、パワー3000の
    ブロッカーに勝つ（素のパワー1000では負ける）。"""
    e = _build(rules, {"bz": [TARGET, "T1224"]}, {"bz": ["T004"]})
    src = _cid(e, 0, TARGET)
    blk = _cid(e, 1, "T004")
    st = _drive(e, attacker=ATK, blocker="T004",
                stop=lambda: e.s.cards[blk].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[blk].zone == "graveyard"
    assert e.s.cards[src].zone == "bz"
    assert len(e.zlist("shield", 1)) == 5    # ブロックされたので無傷


def test_t_breaker_present_breaks_three(rules):
    """T・ブレイカー持ちだけが場にいれば、パワー+11000・
    T・ブレイカーを得てシールドを3枚ブレイクする
    （triple_breaker は double_breaker 条件を満たさない）。"""
    e = _build(rules, {"bz": [TARGET, "T1225"]}, {"bz": []})
    src = _cid(e, 0, TARGET)
    st = _drive(e, attacker=ATK,
                stop=lambda: len(e.zlist("shield", 1)) <= 2)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 2    # 3枚ブレイク
    assert e.s.cards[src].zone == "bz"


def test_no_breaker_no_bonus(rules):
    """判別: ブレイカー持ちが場にいなければ何も得ず、
    ブレイクは1枚・パワーは素の1000のまま。"""
    e = _build(rules, {"bz": [TARGET, "T001"]}, {"bz": []})
    st = _drive(e, attacker=ATK,
                stop=lambda: len(e.zlist("shield", 1)) <= 4)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4    # 1枚だけブレイク
    e2 = _build(rules, {"bz": [TARGET, "T001"]}, {"bz": ["T004"]})
    src = _cid(e2, 0, TARGET)
    st = _drive(e2, attacker=ATK, blocker="T004",
                stop=lambda: e2.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e2.s.cards[src].zone == "graveyard"   # 1000 < 3000 で敗北


def test_opponent_w_breaker_counts(rules):
    """owner: any の判別: 相手の W・ブレイカー持ちでも
    条件を満たし、2枚ブレイクする。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1224"]})
    st = _drive(e, attacker=ATK,
                stop=lambda: len(e.zlist("shield", 1)) <= 3)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 3


def test_both_present_breaker_choice(rules):
    """W と T の両方が場にいれば両方の誘発が立ち、使う
    ブレイカー能力は 509.2c で攻撃側が選ぶ（breaks:2 と
    breaks:3 の選択が提示される）。3を選べば3枚ブレイク。"""
    e = _build(rules, {"bz": [TARGET, "T1224", "T1225"]}, {"bz": []})
    st = _drive(e, attacker=ATK, breaker=3,
                stop=lambda: len(e.zlist("shield", 1)) <= 2)
    assert st["attacked"]
    assert st["breaker_options"] == ["breaks:2", "breaks:3"]
    assert len(e.zlist("shield", 1)) == 2    # 3枚ブレイク
