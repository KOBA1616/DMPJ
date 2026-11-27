"""再変換ラウンド473（第439弾 untap_prevention）の記録テスト。

- 新規登録1件: dmr14-006 聖霊龍王 スタグネイト
  （提出形は partial〔骨格: 進化クリーチャー / 光 /
  コスト5 / パワー10500 / 種族 エンジェル・コマンド・
  ドラゴン、mana 1、evolve_from {civs: [light],
  race_has: ドラゴン}〕に text 公式全文＋keywords
  [double_breaker]＋第439弾の確立形 ability 1件
  〔static {affects: {zone: bz, owner: opp, filter:
  {types: [creature]}}, if: {exists: {ref: self,
  filter: {tapped: true}}}, mod: {deny:
  [untap_at_start]}}〕を足し、unsupported を外した
  もの。登録形は提出形と完全一致〔source 以外の
  全フィールドを照合〕、abilities は static 1件
  ちょうど、keywords は [double_breaker] のまま、
  evolve_from も保持、text は公式全文）。
- 補完あり: text（公式全文。partial は断片
  「アンタップされない」）＋keywords＋abilities。
- alias 畳み込み0件（alias 無し。正本判定は通常型で
  対象 id を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  〔proto のヒットは T1229 の notes 内参照のみ〕、
  identity 実測で canon_id は対象自身、
  aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔untap_prevention〕の出力は対象1件
  ちょうど＝巻き込みなし。untap_prevention は
  完全解消）。
- converted 10,418→10,419 / rejects 1,893→1,892、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ
  （第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第439弾本体と同形（対象を proto T1229 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（相手クリーチャー役・
対照役）/ T189（タマシード＝クリーチャー限定の
範囲判別役）。
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
from tests.test_vocab_pilot439_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot439 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr14-006"
GAP = "untap_prevention"


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


def test_round473_disposition():
    rej = _reject_rows()
    assert len(rej) == 1892
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10419
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 1      # abilities は static 1件ちょうど
    assert c["abilities"][0] == FORM[0]
    assert c["text"] == FULL_TEXT        # 公式全文
    assert c["keywords"] == ["double_breaker"]
    assert c["evolve_from"] == {"civs": ["light"],
                                "race_has": "ドラゴン"}
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    d = parse_card(c, TABLES)
    assert d.types == ["creature", "evolution"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第439弾本体と同形、対象は登録カード） ----------

def _cid(e, defn, player, zone):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == player)


def test_permits_discrimination(rules):
    """特性判別: 発生源（登録カード）がタップしている
    間だけ、相手のクリーチャーの untap_at_start が
    deny される。攻撃許可・タマシード・自分の
    クリーチャーは対象外。"""
    e = scenario.build(rules, {
        "p0": {"bz": [TARGET, "T001"]},
        "p1": {"bz": ["T001", "T189"]},
        "filler": "T002", "seed": 1, "deck_size": 20})
    src = _cid(e, TARGET, 0, "bz")
    own = _cid(e, "T001", 0, "bz")
    opp = _cid(e, "T001", 1, "bz")
    seed = _cid(e, "T189", 1, "bz")
    # 発生源がアンタップ状態では deny は付かない
    assert e.permits(opp, "untap_at_start") is True
    e.s.cards[src].tapped = True
    assert e.permits(opp, "untap_at_start") is False
    # deny は untap_at_start だけ（攻撃許可は奪わない）
    assert e.permits(opp, "attack_player") is True
    assert e.permits(opp, "attack_creature") is True
    # クリーチャー限定: タマシードには付かない
    assert e.permits(seed, "untap_at_start") is True
    # 自分のクリーチャーには付かない
    assert e.permits(own, "untap_at_start") is True
    # 発生源自身にも付かない（affects は owner: opp）
    assert e.permits(src, "untap_at_start") is True
    # 発生源がアンタップに戻れば deny は消える
    e.s.cards[src].tapped = False
    assert e.permits(opp, "untap_at_start") is True


def _keys(d):
    return [o.get("key") for o in d["options"]]


def _drive(e, want=None, limit=600):
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if want is not None:
            k = want(d["kind"], keys, d)
            if k is not None:
                e.answer([keys.index(k)])
                continue
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return e


def _flow(rules, source_attacks):
    """共通フロー: 相手の T001 は最初の自ターンに攻撃して
    タップする。発生源（登録カード）は source_attacks の
    時だけ自ターンごとに攻撃してタップし直す。相手
    ターン2の charge（アンタップステップ後）での T001 と、
    自分ターン2の charge での発生源のタップ状態を返す。"""
    e = scenario.build(rules, {
        "p0": {"bz": [TARGET], "shield": ["T002"] * 5},
        "p1": {"bz": ["T001"], "shield": ["T002"] * 5},
        "filler": "T002", "seed": 1, "deck_size": 20})
    src = _cid(e, TARGET, 0, "bz")
    opp = _cid(e, "T001", 1, "bz")
    st = {"charges": {0: 0, 1: 0}, "opp_attacked": False,
          "opp_at_t2": None, "src_at_t2": None}
    atk_key = f"attack:{TARGET}:player"

    def want(kind, keys, d):
        pl = d.get("player")
        if kind == "charge" and pl in (0, 1):
            st["charges"][pl] += 1
            if pl == 1 and st["charges"][1] == 2 \
                    and st["opp_at_t2"] is None:
                st["opp_at_t2"] = e.s.cards[opp].tapped
            if pl == 0 and st["charges"][0] == 2 \
                    and st["src_at_t2"] is None:
                st["src_at_t2"] = e.s.cards[src].tapped
            return None
        if kind == "attack" and pl == 1 \
                and not st["opp_attacked"] \
                and "attack:T001:player" in keys:
            st["opp_attacked"] = True
            return "attack:T001:player"
        if kind == "attack" and pl == 0 and source_attacks \
                and atk_key in keys:
            return atk_key
        return None

    _drive(e, want, limit=600)
    assert st["opp_attacked"], "相手の T001 が攻撃しなかった"
    assert st["opp_at_t2"] is not None, "相手ターン2に届かなかった"
    assert st["src_at_t2"] is not None, "自分ターン2に届かなかった"
    return st


def test_flow_opponent_stays_tapped_when_source_tapped(rules):
    """発生源がタップしている間、相手のクリーチャーは
    相手のターンのはじめにアンタップしない。発生源自身は
    自分のターンのはじめに通常どおりアンタップする
    （affects は owner: opp の判別）。"""
    st = _flow(rules, source_attacks=True)
    assert st["src_at_t2"] is False  # 自分のはじめに起きた
    assert st["opp_at_t2"] is True   # 相手は起きない


def test_flow_opponent_untaps_when_source_untapped(rules):
    """対照: 発生源がタップしていなければ、相手の
    クリーチャーは通常どおりアンタップする。"""
    st = _flow(rules, source_attacks=False)
    assert st["src_at_t2"] is False
    assert st["opp_at_t2"] is False
