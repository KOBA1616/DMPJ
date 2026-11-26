"""再変換ラウンド468（第433弾
opponent_mana_trigger）の記録テスト。

- 新規登録1件: dm39-015 穿神兵ジェットドリル
  （partial の骨格〔クリーチャー / 火 / コスト3 /
  パワー2000 / 種族 アーマロイド、mana 1〕に
  第433弾の確立形 ability 1件〔trigger {when:
  {event: move, to: mana, from: [deck, graveyard],
  subject: {owner: opp}}, effect: [move {select:
  {zone: mana, owner: opp, count: 1, chooser: opp},
  to: deck, reason: put, position: bottom}]}〕
  （to: mana の監視誘発は第397弾の確立形、from の
  リスト指定は defs の when 検証とエンジン
  _match_when の両側で対応済み、手札からの
  マナチャージは from: hand のため文面どおり
  対象外、chooser: opp は selector の既存キー、
  山札の一番下への move は登録済みニンジャ・
  ストライク形の確立形）を足したもの。登録形は
  提出形と完全一致〔source 以外の全フィールドを
  照合〕、abilities は trigger 1件ちょうど、text は
  公式全文）。
- 補完あり: text（公式全文。partial の text は
  断片「相手の山札または墓地から、カードが
  マナゾーンに置かれた時」）＋abilities。
- alias 畳み込み0件（alias 無し。正本判定は
  通常型で対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1217 の notes
  内参照のみ〕、identity 実測で canon_id は対象
  自身、aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔opponent_mana_trigger〕の出力は対象
  1件ちょうど）。
- converted 10,413→10,414 / rejects
  1,898→1,897、canonical 重なり0・漏れ0。
  opponent_mana_trigger は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第433弾本体と同形（対象を proto T1217 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1218（自分の山札の上から
相手のマナへ置く呪文）/ T1219（自分の墓地から
相手のマナへ置く呪文）/ T1220（相手の手札を
相手のマナへ置く呪文＝from: hand の判別）/
T1221（自分の山札から自分のマナへ置く呪文＝
subject の判別）/ T1222（自分の山札から相手の
マナへ2枚置く呪文＝2回誘発の判別）。
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
from tests.test_vocab_pilot433_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot433 import FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm39-015"
GAP = "opponent_mana_trigger"


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


def test_round468_disposition():
    rej = _reject_rows()
    assert len(rej) == 1897
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10414
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # opponent_mana_trigger 完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 1      # abilities は trigger 1件ちょうど
    assert c["abilities"][0]["kind"] == "trigger"
    assert c["abilities"][0]["when"] == {"event": "move", "to": "mana",
                                         "from": ["deck", "graveyard"],
                                         "subject": {"owner": "opp"}}
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    assert d.types == ["creature"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第433弾本体と同形、対象は登録カード） ----------

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


def _play_and_settle(e, player, play_key, choose=None, record=None,
                     limit=600):
    """player の main 判断で play_key を一度だけ使い、
    解決が終わって通常判断（main / charge / attack）に
    戻るまで進める。choose(d, keys) がインデックス列を
    返せば choose_cards 決定にそれで答える。record には
    choose_cards 決定の提示先プレイヤーを記録する。"""
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
        if cast and d["kind"] == "choose_cards":
            if record is not None:
                record.append(d.get("player"))
            if choose is not None:
                ans = choose(d, keys)
                if ans is not None:
                    e.answer(ans)
                    continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            return True
        _answer_default(e, d)
    return cast


def _pick_defn(defn):
    """相手（player 1）の選択で defn を含むキーを選ぶ。"""
    def choose(d, keys):
        if d.get("player") != 1:
            return None
        hit = [i for i, k in enumerate(keys) if f":{defn}:" in k]
        return hit[:1] or None
    return choose


def test_deck_to_mana_triggers_and_opp_chooses_bottom(rules):
    """登録カード: 相手の山札からカードが相手の
    マナゾーンに置かれると誘発し、相手自身が選んだ
    マナのカードが山札の一番下に置かれる（マナ
    3+1-1=3、山札は枚数不変で一番下が選んだ T001 に
    なる。選択決定は相手に提示される＝chooser: opp
    の判別）。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1218"],
                       "mana": ["T002"] * 2},
               {"mana": ["T001", "T002", "T002"]})
    deck_before = len(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1218",
                            choose=_pick_defn("T001"), record=record)
    assert record == [1]                 # 選択は相手に1回だけ提示
    assert len(e.zlist("mana", 1)) == 3
    assert len(e.zlist("deck", 1)) == deck_before
    bottom = e.zlist("deck", 1)[-1]
    assert e.s.cards[bottom].defn == "T001"   # 選んだカードが一番下
    assert all(e.s.cards[c].defn != "T001"
               for c in e.zlist("mana", 1))


def test_graveyard_to_mana_triggers(rules):
    """相手の墓地からカードが相手のマナゾーンに置かれて
    も誘発する（墓地 1→0、マナ 2+1-1=2、置かれた
    カード自体も選択肢に入り、一番下に置ける）。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1219"],
                       "mana": ["T002"] * 2},
               {"mana": ["T002", "T002"], "graveyard": ["T001"]})
    deck_before = len(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1219",
                            choose=_pick_defn("T001"), record=record)
    assert record.count(1) == 1 and record[-1] == 1
    assert len(e.zlist("graveyard", 1)) == 0
    assert len(e.zlist("mana", 1)) == 2
    assert len(e.zlist("deck", 1)) == deck_before + 1
    bottom = e.zlist("deck", 1)[-1]
    assert e.s.cards[bottom].defn == "T001"


def test_hand_to_mana_does_not_trigger(rules):
    """判別: 相手の手札からカードが相手のマナゾーンに
    置かれても、from: hand は from リストに無いため
    誘発しない（マナは+1、山札は枚数・一番下とも
    不変で、相手への選択提示も無い）。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1220"],
                       "mana": ["T002"] * 2},
               {"mana": ["T002", "T002"], "hand": ["T002"]})
    deck_before = list(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1220", record=record)
    assert 1 not in record               # 相手への選択提示なし
    assert len(e.zlist("mana", 1)) == 3
    assert e.zlist("deck", 1) == deck_before


def test_own_deck_to_mana_does_not_trigger(rules):
    """判別: 自分の山札から自分のマナゾーンに置いても、
    subject {owner: opp} に一致しないため誘発しない
    （相手のマナ・山札は不変）。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1221"],
                       "mana": ["T002"] * 2},
               {"mana": ["T002", "T002"]})
    p1_mana = list(e.zlist("mana", 1))
    p1_deck = list(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1221", record=record)
    assert 1 not in record
    assert len(e.zlist("mana", 0)) == 3   # 自分のマナは+1
    assert e.zlist("mana", 1) == p1_mana
    assert e.zlist("deck", 1) == p1_deck


def test_two_puts_trigger_twice(rules):
    """相手の山札から2枚置かれれば2回誘発し、相手は
    2回選んで2枚を山札の一番下に置く（マナ 3+2-2=3、
    山札は枚数不変）。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1222"],
                       "mana": ["T002"] * 2},
               {"mana": ["T002"] * 3})
    deck_before = len(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1222", record=record)
    assert record == [1, 1]              # 誘発ごとに相手が選ぶ
    assert len(e.zlist("mana", 1)) == 3
    assert len(e.zlist("deck", 1)) == deck_before


def test_no_source_no_trigger(rules):
    """発生源がバトルゾーンに無ければ誘発しない
    （相手のマナは+1、山札は-1で、一番下への
    移動は起きない）。"""
    e = _build(rules, {"hand": ["T1218"], "mana": ["T002"] * 2},
               {"mana": ["T002", "T002"]})
    deck_before = list(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1218", record=record)
    assert record == []
    assert len(e.zlist("mana", 1)) == 3
    # 山札の一番下は不変（場に発生源が無いため、攻撃
    # ステップが自動で進み相手のターンドローが挟まる
    # ので、枚数ではなく一番下の cid で判別する）
    assert e.zlist("deck", 1)[-1] == deck_before[-1]
