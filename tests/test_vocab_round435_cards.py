"""再変換ラウンド435（第400弾 untap_restriction）の記録テスト。

- 新規登録1件: dmrp21-t14 ブルース・ガー
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 火 / コスト1 / パワー1000 /
  種族 ファイアー・バード、mana 1、keywords・
  abilities ともに無し〕に第400弾の確立形 static
  {affects: self, mod: {deny: [untap_at_start]}}
  を足し、unsupported を外したもの。abilities は
  この1件ちょうど、keywords は無いまま。
  **補完あり: races と text のみ** — 【K・ソウル】は
  種族特性で、登録先例 dmex01-043 / dm36-032 と
  同様に races へ 'K・ソウル' を入れて
  [ファイアー・バード, K・ソウル] とした（partial の
  races は [ファイアー・バード] のみ）。text には
  公式テキスト全文を入れた（partial の text は
  断片「アンタップしない」））。
- alias 畳み込み0件（alias 2件 dm38-029 /
  dmrp21-tf14 はいずれも rejects に独自行が無く
  converted にも登録なし。登録エントリの
  source.aliases は validate が identity.aliases_for
  から自動付与した2件。正本判定は通常型: 対象 id と
  alias 2件を real / real_akashic / real_vocab /
  real_zone / proto / converted と照合し登録なし
  （proto のヒットは T1167 の notes 内参照のみ）、
  identity 実測で canon_id は対象・全 alias とも
  dmrp21-t14）。stale クリーンアップ0件。
- **差し戻し2件**: reopen（untap_restriction）の
  出力は3件ちょうどで、残り2件（dm26rp1-td004 /
  dmx15-011）は形が異なるため登録せず、unsupported
  を残した partial のまま差し戻した（登録後に
  rejects へ gaps・partial を保ったまま残留して
  いることを実測確認済み）。untap_restriction は
  残り2件が残るため完全解消しない。
- converted 10,379→10,380 / rejects 1,933→1,932、
  canonical 重なり0・漏れ0。
- 確立形は登録済み dmrp06-027（第397弾・
  ラウンド432）の登録形そのもの（登録先例
  dmrp18-025 も同形。新規フィールドではない。
  回帰に test_data_audit と第397弾本体・cards を
  含めて確認済み）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）は本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第400弾本体と同形（対象を proto T1167 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第400弾の proto を流用: T001（通常クリーチャー＝
対照役・マナ役）/ T1090（火マナ役）。
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
from tests.test_vocab_pilot400 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmrp21-t14"
GAP = "untap_restriction"
NAME = "ブルース・ガー"
REMAINING = ["dm26rp1-td004", "dmx15-011"]


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


def test_round435_disposition():
    rej = _reject_rows()
    assert len(rej) == 1932
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10380
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == REMAINING              # 差し戻し2件が残留（完全解消しない）
    for bid in REMAINING:                # partial・unsupported は保持
        r = rej[bid]
        assert r["gaps"] == [GAP] and r["reason"] == "vocab"
        uns = r["partial"]["source"]["unsupported"]
        assert [u["need"] for u in uns] == [GAP]
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 1 and c["power"] == 1000 and c["mana"] == 1
    # 補完あり: races（K・ソウル）と text（公式テキスト全文）
    assert c["races"] == ["ファイアー・バード", "K・ソウル"]
    assert c["text"] == FULL_TEXT
    assert not c.get("keywords")         # キーワードは無いまま
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert src.get("aliases") == ["dm38-029", "dmrp21-tf14"]
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    assert FORM[0] in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第400弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "pay_mana":
        e.answer([0])
    elif d["kind"] == "choose_shields":
        e.answer(list(range(d["min"])))
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _mine(e, defn):
    return next(c for c in e.zlist("bz", 0)
                if e.s.cards[c].defn == defn)


def _drive(e, script, max_steps=6000):
    state = {}
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if script(e, d, state):
            if state.get("done"):
                return state
            continue
        _answer_default(e, d)
    raise AssertionError(f"script not finished: {state}")


def _attack_flow(e, defn, cid_box):
    """自ターン1: 召喚。自ターン2: 攻撃してタップし
    シールドを1枚ブレイク。自ターン3のはじめの状態を
    cid_box['at_turn3'] に記録する共通フロー
    （第400弾本体と同形）。"""
    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 0:
            st["charges"] = st.get("charges", 0) + 1
            if st["charges"] == 3:
                cid_box["at_turn3"] = \
                    e.s.cards[cid_box["cid"]].tapped
                st["done"] = True
                return True
            return False
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("summoned"):
            key = f"play:{defn}"
            assert key in keys, keys
            st["summoned"] = True
            e.answer([keys.index(key)])
            return True
        if st.get("summoned") and "cid" not in cid_box:
            cid_box["cid"] = _mine(e, defn)
            return False
        if d["kind"] == "attack" and d.get("player") == 0 \
                and st.get("summoned") and not st.get("attacked"):
            hit = [k for k in keys
                   if k == f"attack:{defn}:player"]
            if hit:
                st["attacked"] = True
                cid_box["shields_before"] = len(e.zlist("shield", 1))
                e.answer([keys.index(hit[0])])
                return True
            return False
        if st.get("attacked") and not st.get("after_attack"):
            if d["kind"] in ("main", "charge", "attack"):
                st["after_attack"] = True
                assert e.s.cards[cid_box["cid"]].tapped is True
                assert len(e.zlist("shield", 1)) \
                    == cid_box["shields_before"] - 1
                return True
            return False
        return False
    return script


def test_registered_stays_tapped_at_own_turn_start(rules):
    """登録カード: 実フローで召喚→次の自ターンに攻撃
    してタップ→さらに次の自ターンのはじめにも
    アンタップしない。"""
    e = _build(rules,
               {"hand": [TARGET],
                "mana": ["T1090", "T001", "T001"]},
               {"bz": []})
    cid_box = {}
    _drive(e, _attack_flow(e, TARGET, cid_box))
    assert cid_box["at_turn3"] is True


def test_registered_control_creature_untaps(rules):
    """対照: deny を持たない通常クリーチャーは同じ
    フローで自ターン3のはじめにアンタップしている。"""
    e = _build(rules,
               {"hand": ["T001"],
                "mana": ["T001", "T001", "T001"]},
               {"bz": []})
    cid_box = {}
    _drive(e, _attack_flow(e, "T001", cid_box))
    assert cid_box["at_turn3"] is False


def test_registered_permits_discrimination(rules):
    """登録カード: 特性判別 — deny は発生源自身の
    untap_at_start だけに付き、同じバトルゾーンの
    他のクリーチャーには付かない。攻撃の許可は
    奪わない。"""
    e = _build(rules,
               {"bz": [TARGET, "T001"]},
               {"bz": []})
    cid = _mine(e, TARGET)
    other = _mine(e, "T001")
    assert e.permits(cid, "untap_at_start") is False
    assert e.permits(other, "untap_at_start") is True
    assert e.permits(cid, "attack_player") is True
    assert e.permits(cid, "attack_creature") is True
