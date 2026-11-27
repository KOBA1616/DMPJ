"""再変換ラウンド478（第444弾 attacker_cost_restriction）の記録テスト。

- 新規登録2件: dmr05-098 ヨケッピ・チョーナン と
  dmr06-028 ボルカニック・ザウルス（提出形は
  いずれも partial の骨格〔text 公式全文〕に
  第444弾の確立形 abilities を足し、unsupported
  を外したもの。共通条項「コスト6以下のクリー
  チャーに攻撃されない」= static {affects: self,
  mod: {deny: [{action: be_attacked, other:
  {cost_le: 6}}]}}。dmr05-098 は deny static
  1件のみ、dmr06-028 は power_when static
  〔定型所有形、partial の trigger 下書きを置換〕
  ＋deny static の2件。登録形は提出形と完全一致
  〔source 以外の全フィールドを照合〕、
  dmr05-098 は abilities 1件ちょうど・keywords
  [speed_attacker]、dmr06-028 は abilities 2件
  ちょうど・keywords [double_breaker]、text は
  両件とも公式全文）。
- 補完あり: 両件とも abilities のみ（text・
  keywords は partial の時点で公式全文・完備）。
- alias 畳み込み0件（両件とも alias 無し。正本
  判定: 対象2件の id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1234 /
  T1235 の notes 内参照のみ〕、identity 実測で
  canon_id は対象自身・aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔attacker_cost_restriction〕の出力は
  対象2件ちょうど＝巻き込みなし。
  attacker_cost_restriction は完全解消）。
- converted 10,423→10,425 / rejects 1,888→1,886、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from 同期
  漏れ（第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第444弾本体と同形（対象を proto T1234 / T1235
から登録カードに差し替えたもの）で、
tests.conftest は import しない（第319弾以降の
作法）。判別役は既存 proto を流用: T021（コスト6
＝境界・パワー5000）/ T040（コスト7・パワー
6000）/ T004（ブロッカー・パワー3000）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402
from tests.test_vocab_pilot444_cards import SUBMIT_A, SUBMIT_B  # noqa: E402
from tests.test_vocab_pilot444 import NAME_A, NAME_B, TEXT_A, TEXT_B  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET_A = "dmr05-098"
TARGET_B = "dmr06-028"
GAP = "attacker_cost_restriction"


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


def test_round478_disposition():
    rej = _reject_rows()
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    for tid, submit, name, text, kw, n_ab in (
            (TARGET_A, SUBMIT_A, NAME_A, TEXT_A, ["speed_attacker"], 1),
            (TARGET_B, SUBMIT_B, NAME_B, TEXT_B, ["double_breaker"], 2)):
        assert tid not in rej            # 対象行は登録で解消（漏れ0）
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        reg = {k: v for k, v in c.items() if k != "source"}
        assert reg == submit             # 登録形 == 提出形
        assert len(c["abilities"]) == n_ab
        assert c["keywords"] == kw       # keywords そのまま
        assert c["text"] == text         # text は公式全文
        assert not (c.get("source") or {}).get("unsupported")
        assert canon_id(tid) == tid
        assert aliases_for(name, tid) == []
        d = parse_card(c, TABLES)
        assert d.name == name
    # dmr06-028 の abilities 順は power_when が先頭（第444弾 FORM の順）
    cb = _conv_cache.find(CONVERTED, TARGET_B)
    assert [next(iter(a["mod"])) for a in cb["abilities"]] == [
        "power_when", "deny"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第444弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif d["kind"] in ("declare_strigger", "declare_sback"):
        e.answer([])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _drive(e, attacks=(), arrange=None, finish_player=None,
           block=False, limit=1500):
    st = {"done": [], "attack_options": [], "blocked": False}
    queue = list(attacks)
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if arrange:
            arrange(e, d)
        if not queue and finish_player is not None \
                and d["kind"] == "charge" \
                and d.get("player") == finish_player:
            return st
        if d["kind"] == "attack":
            st["attack_options"].append((d.get("player"), keys))
        if d["kind"] == "block" and block:
            pick = next(k for k in keys if k != "no_block")
            e.answer([keys.index(pick)])
            st["blocked"] = True
            continue
        if queue and d["kind"] == "attack" and queue[0] in keys:
            e.answer([keys.index(queue[0])])
            st["done"].append(queue.pop(0))
            continue
        _answer_default(e, d)
    raise AssertionError("driver limit reached")


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == p)


def _zone(e, cid):
    return e.s.cards[cid].zone


def _tap_on_opp_turn(e, p, defn):
    def arrange(eng, d):
        if eng.s.active == p and d["kind"] in ("charge", "main"):
            for c in eng.zlist("bz", p):
                if eng.s.cards[c].defn == defn \
                        and eng.s.cards[c].controller == p:
                    eng.s.cards[c].tapped = True
    return arrange


def _opp_attack_keys(st, player, attacker):
    out = []
    for p, keys in st["attack_options"]:
        if p == player:
            out += [k for k in keys
                    if k and k.startswith(f"attack:{attacker}:")]
    return out


# ---------- dmr05-098（登録カード） ----------

def test_a_cost6_attacker_cannot_attack_but_can_attack_player(rules):
    """登録カード dmr05-098: コスト6の T021（境界）は
    タップした対象を攻撃できないが、プレイヤーは
    攻撃でき自分のシールドが1枚割れる。対象は場に残る。"""
    e = _build(rules, {"bz": [TARGET_A]}, {"bz": ["T021"]})
    tgt = _cid(e, 0, TARGET_A)
    st = _drive(e, attacks=[f"attack:{TARGET_A}:player",
                            "attack:T021:player"],
                finish_player=0)
    assert st["done"] == [f"attack:{TARGET_A}:player",
                          "attack:T021:player"]
    keys = _opp_attack_keys(st, 1, "T021")
    assert f"attack:T021:{TARGET_A}" not in keys
    assert "attack:T021:player" in keys
    assert _zone(e, tgt) == "bz"
    assert len(e.zlist("shield", 0)) == 4


def test_a_cost7_attacker_can_attack(rules):
    """登録カード dmr05-098: コスト7の T040 はタップ
    した対象を攻撃でき、バトル（6000 vs 2000）で
    対象は破壊される（境界の判別）。"""
    e = _build(rules, {"bz": [TARGET_A]}, {"bz": ["T040"]})
    tgt = _cid(e, 0, TARGET_A)
    atk = _cid(e, 1, "T040")
    st = _drive(e, attacks=[f"attack:{TARGET_A}:player",
                            f"attack:T040:{TARGET_A}"],
                finish_player=0)
    assert st["done"] == [f"attack:{TARGET_A}:player",
                          f"attack:T040:{TARGET_A}"]
    keys = _opp_attack_keys(st, 1, "T040")
    assert f"attack:T040:{TARGET_A}" in keys
    assert _zone(e, tgt) == "graveyard"
    assert _zone(e, atk) == "bz"


def test_a_protected_creature_can_be_blocked(rules):
    """登録カード dmr05-098: deny は be_attacked
    だけなので、対象の攻撃は通常どおりブロック
    される（T004 がブロックしバトルで対象は破壊）。"""
    e = _build(rules, {"bz": [TARGET_A]}, {"bz": ["T004"]})
    src = _cid(e, 0, TARGET_A)
    blk = _cid(e, 1, "T004")
    st = _drive(e, attacks=[f"attack:{TARGET_A}:player"],
                block=True, finish_player=1)
    assert st["done"] == [f"attack:{TARGET_A}:player"]
    assert st["blocked"]
    assert _zone(e, src) == "graveyard"
    assert _zone(e, blk) == "bz"
    assert len(e.zlist("shield", 1)) == 5


# ---------- dmr06-028（登録カード） ----------

def test_b_power_attacker_beats_cost6(rules):
    """登録カード dmr06-028: タップした T021（5000）を
    攻撃し、power_when で攻撃中6000になって破壊し
    場に残る（定型所有の power_when 形であることの
    判別を兼ねる）。"""
    e = _build(rules, {"bz": [TARGET_B]}, {"bz": ["T021"]})
    src = _cid(e, 0, TARGET_B)
    tgt = _cid(e, 1, "T021")
    st = _drive(e, attacks=[f"attack:{TARGET_B}:T021"],
                arrange=_tap_on_opp_turn(e, 1, "T021"),
                finish_player=1)
    assert st["done"] == [f"attack:{TARGET_B}:T021"]
    assert _zone(e, tgt) == "graveyard"
    assert _zone(e, src) == "bz"


def test_b_cost6_attacker_cannot_attack(rules):
    """登録カード dmr06-028: プレイヤーを攻撃して
    タップした対象を、コスト6の T021 は攻撃できない
    （プレイヤー攻撃は可能）。対象は場に残る。"""
    e = _build(rules, {"bz": [TARGET_B]}, {"bz": ["T021"]})
    tgt = _cid(e, 0, TARGET_B)
    st = _drive(e, attacks=[f"attack:{TARGET_B}:player",
                            "attack:T021:player"],
                finish_player=0)
    assert st["done"] == [f"attack:{TARGET_B}:player",
                          "attack:T021:player"]
    keys = _opp_attack_keys(st, 1, "T021")
    assert f"attack:T021:{TARGET_B}" not in keys
    assert "attack:T021:player" in keys
    assert _zone(e, tgt) == "bz"
