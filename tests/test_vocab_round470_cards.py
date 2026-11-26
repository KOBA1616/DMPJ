"""再変換ラウンド470（第436弾 mana_tap_trigger）の記録テスト。

- 新規登録1件: dmx08-010 大喰の超人
  （提出形は partial そのもの〔クリーチャー / 自然 /
  コスト8 / パワー8000 / 種族 ジャイアント/ハンター、
  mana 1〕＋abilities 2件〔static mana_boost
  {values: [2, 3]}（第212弾・ラウンド248の確立形）と
  trigger {when: {event: tap, subject: {owner: you,
  zone: mana}}, effect: [move {select: {ref: subject},
  to: graveyard, reason: put}]}〕から unsupported を
  外したもの。登録形は提出形と完全一致〔source 以外の
  全フィールドを照合〕、abilities は static＋trigger の
  2件ちょうど、text は公式全文）。
- 補完なし（text は partial の時点で公式全文、
  abilities 完備）。
- alias 畳み込み0件（alias 無し。正本判定は通常型で
  対象 id を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1226 の notes 内参照のみ〕、
  identity 実測で canon_id は対象自身、
  aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔mana_tap_trigger〕の出力は対象1件ちょうど）。
- converted 10,415→10,416 / rejects 1,896→1,895、
  canonical 重なり0・漏れ0。mana_tap_trigger は完全解消。
- 第436弾はエンジン変更（支払い・コストのマナタップ
  6か所のイベント化＋_match_when の tap/untap subject
  ゾーン既定規則）を含むため verified_engine のハッシュが
  ずれ Rust は自動無効化・Python のみ動作（rust_stamp は
  先例どおり据え置き）。本ラウンドではエンジンに触っていない。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ（第387弾で
  観察）・distinct_type_count の count_spec 未同期
  （第405弾で観察）は本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは第436弾
本体と同形（対象を proto T1226 から登録カードに
差し替えたもの）で、tests.conftest は import しない
（第319弾以降の作法）。判別役は既存 proto を流用:
T001・T002（バニラ）/ T109（tap_mana 起動）/
T062（クロスギア）。
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
from tests.test_vocab_pilot436_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot436 import FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmx08-010"
GAP = "mana_tap_trigger"


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


def test_round470_disposition():
    rej = _reject_rows()
    assert len(rej) == 1895
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10416
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # mana_tap_trigger 完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 2      # abilities は static＋trigger の2件ちょうど
    assert [a["kind"] for a in c["abilities"]] == ["static", "trigger"]
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    assert d.types == ["creature"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第436弾本体と同形、対象は登録カード） ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _zone_defns(e, zone, player=0):
    return sorted(e.s.cards[c].defn for c in e.zlist(zone, player))


def test_payment_tap_goes_to_graveyard(rules):
    """登録カード: 通常支払いでタップしたマナはプレイ完了後に墓地へ。
    タップしていないマナは残る。"""
    e = scenario.build(rules, {"p0": {"bz": [TARGET], "hand": ["T001"],
                                      "mana": ["T001", "T001", "T001"]},
                              "filler": "T002"})
    played = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not played and d["kind"] == "main" and "play:T001" in keys:
            e.answer([keys.index("play:T001")])
            played = True
            continue
        if d["kind"] == "pay_mana":
            two = [i for i, o in enumerate(d["options"]) if len(o["cids"]) == 2]
            assert two, keys
            e.answer([two[0]])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert played
    assert _zone_defns(e, "bz") == ["T001", TARGET]
    assert _zone_defns(e, "graveyard") == ["T001", "T001"]   # 支払った2枚は墓地
    assert _zone_defns(e, "mana") == ["T001"]               # 残り1枚はマナに残る


def test_payment_tap_boost_still_works(rules):
    """ブースト併用: マナ3枚（通常合計3）では足りないコスト8を 3+3+2 で
    支払え、タップした3枚すべてが墓地へ行く。"""
    e = scenario.build(rules, {"p0": {"bz": [TARGET], "hand": [TARGET],
                                      "mana": ["T001", "T001", "T001"]},
                              "filler": "T002"})
    played = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not played and d["kind"] == "main" and f"play:{TARGET}" in keys:
            e.answer([keys.index(f"play:{TARGET}")])
            played = True
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert played   # ブーストが無ければ play 自体が出ない（判別）
    assert _zone_defns(e, "bz") == [TARGET, TARGET]
    assert _zone_defns(e, "graveyard") == ["T001", "T001", "T001"]
    assert _zone_defns(e, "mana") == []


def test_opponent_watcher_does_not_fire(rules):
    """相手の登録カードは、自分のマナタップでは誘発しない
    （owner: you は発生源側）。"""
    e = scenario.build(rules, {"p0": {"hand": ["T001"], "mana": ["T001", "T001"]},
                               "p1": {"bz": [TARGET]}, "filler": "T002"})
    played = False
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T001" in keys:
            e.answer([keys.index("play:T001")])
            played = True
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if played and d["kind"] == "charge" and d.get("player") == 1:
            break   # プレイ完了後の相手ターン開始で止める
    assert played
    assert _zone_defns(e, "graveyard") == []
    tapped = [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert len(tapped) == 2   # 支払ったマナはタップされたままマナに残る


def test_bz_creature_tap_does_not_fire(rules):
    """バトルゾーンのクリーチャーのタップ（攻撃）では誘発しない（zone の判別）。"""
    e = scenario.build(rules, {"p0": {"bz": [TARGET], "mana": ["T001"]},
                              "filler": "T002"})
    attacked = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not attacked and d["kind"] == "attack" \
                and f"attack:{TARGET}:player" in keys:
            e.answer([keys.index(f"attack:{TARGET}:player")])
            attacked = True
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if attacked and any(e.s.cards[c].defn == TARGET and e.s.cards[c].tapped
                            for c in e.zlist("bz", 0)):
            break
    assert attacked
    assert _zone_defns(e, "mana") == ["T001"]
    assert _zone_defns(e, "graveyard") == []


def test_activate_tap_mana_goes_to_graveyard(rules):
    """起動コストの tap_mana: タップしたマナ2枚が墓地へ行き、
    効果（ドロー）も解決する。"""
    e = scenario.build(rules, {"p0": {"bz": [TARGET, "T109"],
                                      "mana": ["T001", "T001", "T001"],
                                      "hand": ["T001"]}, "filler": "T002"})
    hand0 = len(e.zlist("hand", 0))
    acted = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        hit = next((k for k in keys if k.startswith("activate:T109")), None)
        if not acted and hit:
            e.answer([keys.index(hit)])
            acted = True
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if acted and _zone_defns(e, "graveyard") == ["T001", "T001"]:
            break   # 誘発が解決した時点で止める
    assert acted
    assert _zone_defns(e, "graveyard") == ["T001", "T001"]
    assert _zone_defns(e, "mana") == ["T001"]
    assert len(e.zlist("hand", 0)) == hand0 + 1   # ドローが解決した


def test_cross_payment_goes_to_graveyard(rules):
    """クロスの支払い: タップしたマナが墓地へ行き、クロス自体も成立する。"""
    e = scenario.build(rules, {"p0": {"bz": [TARGET, "T001", "T062"],
                                      "mana": ["T001", "T001", "T001"]},
                              "filler": "T002"})
    crossed = False
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not crossed and d["kind"] == "main" and "cross:T062:T001" in keys:
            e.answer([keys.index("cross:T062:T001")])
            crossed = True
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert crossed
    gear = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T062")
    assert e.s.cards[gear].crossed is not None
    grave = _zone_defns(e, "graveyard")
    assert grave and all(g == "T001" for g in grave)
    assert len(_zone_defns(e, "mana")) + len(grave) == 3
