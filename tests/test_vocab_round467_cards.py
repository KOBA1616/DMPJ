"""再変換ラウンド467（第432弾
mana_leave_trigger）の記録テスト。

- 新規登録1件: dmr05-032 メガンス・ワイバーン
  （partial の骨格〔クリーチャー / 火 / コスト5 /
  パワー5000 / 種族 アーマード・ワイバーン/
  アンノイズ、mana 1〕に第432弾の確立形 ability 1件
  〔trigger {when: {event: move, from: mana,
  subject: {owner: opp}}, if: {is_turn: opp},
  effect: [move {select: {zone: shield, owner:
  opp, count: 1}, to: hand, reason: return}]}〕
  （from: mana の監視誘発は登録済み dm28-014 /
  dm17-030、if {is_turn: opp} は登録済み dm23-027 /
  dm21-006、シールド→手札の move は登録済み
  dmex13-073 の確立形。選択主体は既定の
  コントローラー）を足したもの。登録形は提出形と
  完全一致〔source 以外の全フィールドを照合〕、
  abilities は trigger 1件ちょうど、text は公式
  全文）。
- 補完あり: text（公式全文。partial の text は
  断片「マナゾーンからカードが離れる時」）
  ＋abilities。
- alias 畳み込み0件（alias 無し。正本判定は
  通常型で対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1213 の notes
  内参照のみ〕、identity 実測で canon_id は対象
  自身、aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔mana_leave_trigger〕の出力は対象
  1件ちょうど）。
- converted 10,412→10,413 / rejects
  1,899→1,898、canonical 重なり0・漏れ0。
  mana_leave_trigger は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第432弾本体と同形（対象を proto T1213 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1214（相手が自分のマナを
手札に戻す呪文＝相手ターン中の離脱）/ T1215
（自分のターンに相手のマナを墓地に置く呪文＝
is_turn の判別）/ T1216（相手が自分のマナ2枚を
戻す呪文＝2回誘発の判別）/ T001（通常召喚＝
タップだけでは離脱しない判別）。
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
from tests.test_vocab_pilot432_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot432 import FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr05-032"
GAP = "mana_leave_trigger"


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


def test_round467_disposition():
    rej = _reject_rows()
    assert len(rej) == 1898
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10413
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # mana_leave_trigger 完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 1      # abilities は trigger 1件ちょうど
    assert c["abilities"][0]["kind"] == "trigger"
    assert c["abilities"][0]["when"] == {"event": "move", "from": "mana",
                                         "subject": {"owner": "opp"}}
    assert c["abilities"][0]["if"] == {"is_turn": "opp"}
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    assert d.types == ["creature"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第432弾本体と同形、対象は登録カード） ----------

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


def _play_and_settle(e, player, play_key, limit=600):
    """player の main 判断で play_key を一度だけ使い、
    解決が終わって通常判断（main / charge / attack）に
    戻るまで進める。使えたかどうかを返す。"""
    cast = False
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if not cast and d["kind"] == "main" \
                and d.get("player") == player and play_key in keys:
            e.answer([keys.index(play_key)])
            cast = True
            continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            return True
        _answer_default(e, d)
    return cast


def test_opp_mana_leaves_on_opp_turn_adds_shield_to_hand(rules):
    """登録カード: 相手のターンに相手のマナゾーンから
    カードが離れると、相手のシールドを1つ選んで持ち主の
    手札に加える（シールド5→4、手札は開始1＋ドロー1
    −呪文1＋マナ回収1＋シールド1＝3、マナ4→3）。"""
    e = _build(rules, {"bz": [TARGET]},
               {"hand": ["T1214"], "mana": ["T002"] * 4})
    assert _play_and_settle(e, 1, "play:T1214")
    assert len(e.zlist("shield", 1)) == 4
    assert len(e.zlist("hand", 1)) == 3
    assert len(e.zlist("mana", 1)) == 3


def test_opp_mana_leaves_on_your_turn_no_trigger(rules):
    """判別: 自分のターンに相手のマナゾーンから
    カードが離れても、is_turn: opp でないため誘発
    しない（相手のシールドは5枚のまま）。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1215"],
                       "mana": ["T002"] * 2},
               {"mana": ["T002"] * 3})
    assert _play_and_settle(e, 0, "play:T1215")
    assert len(e.zlist("mana", 1)) == 2        # マナは墓地に置かれた
    assert len(e.zlist("graveyard", 1)) == 1
    assert len(e.zlist("shield", 1)) == 5      # 誘発していない


def test_tapping_mana_does_not_trigger(rules):
    """判別: 相手が通常召喚でマナをタップしただけ
    ではカードはマナゾーンを離れないので誘発しない
    （シールド5枚・マナ4枚のまま）。"""
    e = _build(rules, {"bz": [TARGET]},
               {"hand": ["T001"], "mana": ["T002"] * 4})
    assert _play_and_settle(e, 1, "play:T001")
    assert len(e.bz_tops(1)) == 1             # 召喚は成立している
    assert len(e.zlist("mana", 1)) == 4
    assert len(e.zlist("shield", 1)) == 5


def test_two_mana_leaves_trigger_twice(rules):
    """相手のマナゾーンから2枚離れれば2回誘発し、
    シールドは2枚手札に加わる（5→3）。"""
    e = _build(rules, {"bz": [TARGET]},
               {"hand": ["T1216"], "mana": ["T002"] * 4})
    assert _play_and_settle(e, 1, "play:T1216")
    assert len(e.zlist("shield", 1)) == 3
    assert len(e.zlist("mana", 1)) == 2
    assert len(e.zlist("hand", 1)) == 5   # 開始1＋ドロー1−1呪文＋2マナ＋2シールド


def test_no_target_in_bz_no_trigger(rules):
    """発生源がバトルゾーンに無ければ誘発しない
    （相手のシールドは5枚のまま）。"""
    e = _build(rules, {},
               {"hand": ["T1214"], "mana": ["T002"] * 4})
    assert _play_and_settle(e, 1, "play:T1214")
    assert len(e.zlist("shield", 1)) == 5
    assert len(e.zlist("mana", 1)) == 3
    assert len(e.zlist("hand", 1)) == 2   # 開始1＋ドロー1−1呪文＋1マナのみ


def test_no_shields_no_error(rules):
    """相手のシールドが0枚でも誘発は空振りして
    ゲームは正常に進む。"""
    e = _build(rules, {"bz": [TARGET]},
               {"hand": ["T1214"], "mana": ["T002"] * 4,
                "shield": []})
    assert _play_and_settle(e, 1, "play:T1214")
    assert len(e.zlist("shield", 1)) == 0
    assert len(e.zlist("mana", 1)) == 3
    assert len(e.zlist("hand", 1)) == 2   # 開始1＋ドロー1−1呪文＋1マナのみ
