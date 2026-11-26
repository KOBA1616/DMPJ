"""再変換ラウンド448（第413弾 battle_result_destruction）の記録テスト。

- 新規登録1件: dmx03-036 ブラッディ・シンバル
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 闇 / コスト2 / パワー4000 /
  種族 ガーゴイル、mana 1、keywords [blocker,
  cannot_attack] が構築済み〕に第413弾の
  確立形 trigger {when: {event: battle_win,
  subject: self}, effect: [destroy {select:
  {ref: self}}]}（登録済み dm01-026 / dm01-056 /
  dm01-089 / dm06-027 / dm06-087 の5件と完全
  一致）を足し、unsupported を外したもの。
  abilities はこの1件ちょうど、keywords は
  そのまま）。
- 補完なし（partial の text は行の公式テキスト
  全文と一致し、登録後の全文一致も照合済み）。
- split の part[2] 定型所有は空（キーワードのみ
  定型所有で partial と一致）のためツール側
  ブロッカーなし。
- alias 畳み込み0件（alias は dm14-091 /
  dmc42-071 の2件で rejects に独自行は無く、
  登録エントリの source.aliases に validate が
  自動付与。identity 実測で canon_id は対象
  自身、alias 側の canon も dmx03-036、
  aliases_for = [dm14-091, dmc42-071]。
  正本判定は通常型で対象 id と alias 2件を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1181 の notes 内参照のみ、
  converted のヒットは登録済み dm01-026 の
  notes 内の dm14-091 言及のみ〕）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔battle_result_destruction〕の出力は
  対象1件ちょうどで巻き込みなし）。
- converted 10,392→10,393 / rejects
  1,919→1,918、canonical 重なり0・漏れ0。
  battle_result_destruction は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第413弾本体と同形（対象を proto T1181 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（パワー2000バニラ役＝
負ける攻撃側）/ T1139（パワー6000役＝勝つ攻撃側・
味方の勝ち判別）/ T1140（パワー4000ブロッカー
役＝相打ち判別・誘発なし対照）。観測上の注意:
hist:battle_win のカウンタはターン終了で
prev_counters へ退避されるため、両方を見る
（第382・413弾の作法）。
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
from tests.test_vocab_pilot413 import FORM, FULL_TEXT, PARSED_TRIG  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmx03-036"
ALIASES = ["dm14-091", "dmc42-071"]
GAP = "battle_result_destruction"
NAME = "ブラッディ・シンバル"


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


def test_round448_disposition():
    rej = _reject_rows()
    assert len(rej) == 1918
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10393
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    for a in ALIASES:
        assert a not in rej              # alias に独自行なし
        assert _conv_cache.find(CONVERTED, a) is None
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 2 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ガーゴイル"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は誘発1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["blocker", "cannot_attack"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    assert PARSED_TRIG in d.abilities
    assert len(d.abilities) == 3         # キーワード static 2件＋誘発
    assert d.keywords == ["blocker", "cannot_attack"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第413弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")] if "yes" in keys
                 else list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _drive_battle(e, atk_player, atk, blk):
    """第413弾本体と同形: atk がプレイヤーを攻撃し、
    相手が blk でブロックするバトルを1回行い、攻撃側の
    ターンが終わる（防御側の charge）まで進める。"""
    state = {"attacked": False, "blocked": False,
             "win_seen": {0: 0, 1: 0}}
    for _ in range(4000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        for p in (0, 1):
            v = max(e.s.turn_counters.get(f"hist:battle_win:{p}") or 0,
                    e.s.prev_counters.get(f"hist:battle_win:{p}") or 0)
            state["win_seen"][p] = max(state["win_seen"][p], v)
        if state["blocked"] and d["kind"] == "charge" \
                and d.get("player") != atk_player:
            break
        if d["kind"] == "attack" and d.get("player") == atk_player \
                and not state["attacked"]:
            state["attacked"] = True
            e.answer([keys.index(f"attack:{atk}:player")])
            continue
        if d["kind"] == "block":
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blk}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
            continue
        _answer_default(e, d)
    assert state["attacked"] and state["blocked"], state
    return state


def test_cannot_attack(rules):
    """登録カード自身: 攻撃することができない（攻撃
    選択肢に出ず、permits でも不許可。ブロックは可能）。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    assert e._attack_options(0) == []
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == TARGET)
    assert not e.permits(cid, "attack_player")
    assert not e.permits(cid, "attack_creature")
    assert e.permits(cid, "block")


def test_block_win_destroys_self(rules):
    """登録カード自身の判別: パワー2000の攻撃を
    ブロックしてバトルに勝つと、バトルの後に自身が
    破壊される（攻撃側はバトルで破壊、シールド無傷）。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T001"]})
    shields_before = len(e.zlist("shield", 0))
    state = _drive_battle(e, 1, "T001", TARGET)
    assert state["win_seen"][0] == 1
    assert _in_zone(e, 1, "graveyard", "T001")
    assert _in_zone(e, 0, "graveyard", TARGET)
    assert not _in_zone(e, 0, "bz", TARGET)
    assert len(e.zlist("shield", 0)) == shields_before


def test_block_win_control_blocker_survives(rules):
    """対照: 誘発を持たないブロッカー（T1140）が同じ
    攻撃をブロックして勝てば生き残る。"""
    e = _build(rules, {"bz": ["T1140"]}, {"bz": ["T001"]})
    state = _drive_battle(e, 1, "T001", "T1140")
    assert state["win_seen"][0] == 1
    assert _in_zone(e, 1, "graveyard", "T001")
    assert _in_zone(e, 0, "bz", "T1140")
    assert not _in_zone(e, 0, "graveyard", "T1140")


def test_block_lose_destroyed_by_battle_not_trigger(rules):
    """敗北時: パワー6000の攻撃をブロックして負ければ
    バトル自体で破壊される（勝ちは攻撃側のみ）。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1139"]})
    state = _drive_battle(e, 1, "T1139", TARGET)
    assert state["win_seen"][0] == 0
    assert state["win_seen"][1] == 1
    assert _in_zone(e, 0, "graveyard", TARGET)
    assert _in_zone(e, 1, "bz", "T1139")


def test_block_draw_both_destroyed_by_battle(rules):
    """相打ち（4000 vs 4000）: 両者ともバトル自体で
    破壊され、勝ちはどちらにも記録されない。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1140"]})
    state = _drive_battle(e, 1, "T1140", TARGET)
    assert state["win_seen"][0] == 0
    assert state["win_seen"][1] == 0
    assert _in_zone(e, 0, "graveyard", TARGET)
    assert _in_zone(e, 1, "graveyard", "T1140")


def test_ally_win_does_not_destroy_self(rules):
    """subject: self の判別: 味方（T1139）が相手の
    ブロッカー（T1140）に勝っても、バトルをしていない
    登録カードは破壊されず場に残る。"""
    e = _build(rules, {"bz": [TARGET, "T1139"]}, {"bz": ["T1140"]})
    state = _drive_battle(e, 0, "T1139", "T1140")
    assert state["win_seen"][0] == 1
    assert _in_zone(e, 1, "graveyard", "T1140")
    assert _in_zone(e, 0, "bz", "T1139")
    assert _in_zone(e, 0, "bz", TARGET)
    assert not _in_zone(e, 0, "graveyard", TARGET)
