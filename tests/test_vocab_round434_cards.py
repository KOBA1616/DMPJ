"""再変換ラウンド434（第399弾 summon_turn_attack_restriction）の記録テスト。

- 新規登録1件: dmr22-s04 聖者の精霊龍 セレナーデ
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 光・水 / コスト7 / パワー7500 /
  種族 エンジェル・コマンド・ドラゴン / 革命軍、
  mana 1〕に keywords [blocker, double_breaker]
  と第399弾の確立形 static〔affects {zone: bz,
  owner: any, filter: {types: [creature],
  keyword: speed_attacker, entered_this_turn:
  true}}, mod {deny: [attack_player,
  attack_creature]}〕を足し、unsupported を
  外したもの。abilities はこの1件ちょうど、
  keywords は [blocker, double_breaker]。
  **補完あり: text のみ** — partial の text は
  条項の断片のため、text には行の公式テキスト
  全文を条項ごとに改行したものを入れた。
  「マナゾーンに置く時、このカードはタップして
  置く」の条項にはキーワード・能力を付けない
  （多色カードのルール 405.1 でエンジンが処理し、
  変換済みカードは一貫して text のみ））。
- 正本判定は通常型: 対象 id（alias は無い）を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし（proto の
  ヒットは T1166 の notes 内参照のみ）、identity
  実測で canon_id(dmr22-s04) = dmr22-s04、
  aliases_for = []。alias 畳み込み0件・stale
  クリーンアップ0件・差し戻し0件。
- reopen（summon_turn_attack_restriction）の
  出力は対象1件ちょうど（対象行は
  reason == "vocab"）。
- converted 10,378→10,379 / rejects 1,934→1,933、
  canonical 重なり0・漏れ0。
  summon_turn_attack_restriction は完全解消。
- 確立形は第398弾と同一（第362弾の登録先例の
  owner を any に広げ keyword フィルタを足した
  形。新規フィールドではない。回帰に
  test_data_audit と第398・362弾本体を含めて
  確認済み）。
- 既知の制限: 静的効果の affects 照合は base
  （印刷特性）のため、他の効果で付与された
  スピードアタッカーはフィルタに掛からない。
  keyword フィルタを使う登録済み静的効果と
  共有するエンジン全体の規約で、解消は専用
  ステージ判断（本ラウンドでは扱わない）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）は本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第399弾本体と同形（対象を proto T1166 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第399弾の proto を流用: T1090（スピードアタッカー
役・火マナ役）/ T1091（標的役）/ T314（スピード
アタッカー自己付与役＝付与分の制限確認用）。
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
from tests.test_vocab_pilot399 import FORM, FULL_TEXT, STATIC  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr22-s04"
GAP = "summon_turn_attack_restriction"
NAME = "聖者の精霊龍 セレナーデ"


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


def test_round434_disposition():
    rej = _reject_rows()
    assert len(rej) == 1933
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10379
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == set()                  # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light", "water"]
    assert c["cost"] == 7 and c["power"] == 7500 and c["mana"] == 1
    assert c["races"] == ["エンジェル・コマンド・ドラゴン", "革命軍"]
    assert c["keywords"] == ["blocker", "double_breaker"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり: text のみ）
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("aliases")        # alias は無い
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第399弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


def _drive(e, player, play=None, attack=None):
    """player の最初の main のターンだけを対象に進める
    ドライバ（第399弾と同型）。攻撃できるクリーチャーが
    1体もいない場合、attack 決定自体が提示されない。"""
    seen = {"attack_keys": [], "played": False,
            "attacked": False, "target_turn": None}
    for _ in range(600):
        if seen["target_turn"] is not None \
                and e.s.turn > seen["target_turn"] + 1:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind in ("charge", "main", "attack") \
                and pl == player and seen["target_turn"] is None:
            seen["target_turn"] = e.s.turn
        if kind == "main" and pl == player and play \
                and not seen["played"]:
            hit = [i for i, k in enumerate(keys)
                   if k == f"play:{play}"]
            if hit:
                seen["played"] = True
                seen["target_turn"] = e.s.turn
                e.answer([hit[0]])
                continue
        if kind == "attack" and pl == player \
                and e.s.turn == seen["target_turn"]:
            seen["attack_keys"].extend(keys)
            hit = [i for i, k in enumerate(keys)
                   if attack and k == f"attack:{attack}:player"]
            if hit and not seen["attacked"]:
                seen["attacked"] = True
                e.answer([hit[0]])
                continue
        if kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def test_registered_own_speed_attacker_entered_this_turn_cannot_attack(rules):
    """登録カード: 自分のスピードアタッカーも対象
    （owner: any の判別）: 発生源が自分のバトル
    ゾーンにいても、出たターンには攻撃できない。"""
    e = _build(rules,
               {"bz": [TARGET], "hand": ["T1090"],
                "mana": ["T1090", "T1090"]},
               {"bz": ["T1091"]})
    shields = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T1090", attack="T1090")
    assert seen["played"]
    assert not seen["attacked"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1090:")]
    assert not e.s.cards[_cid(e, "T1090", 0)].tapped
    assert len(e.zlist("shield", 1)) == shields


def test_registered_opp_speed_attacker_entered_this_turn_cannot_attack(rules):
    """登録カード: 相手のスピードアタッカーも、
    出たターンにはプレイヤーへもクリーチャーへも
    攻撃できない。"""
    e = _build(rules,
               {"bz": [TARGET, "T1091"]},
               {"hand": ["T1090"], "mana": ["T1090", "T1090"]})
    shields = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, play="T1090", attack="T1090")
    assert seen["played"]
    assert not seen["attacked"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1090:")]
    assert not e.s.cards[_cid(e, "T1090", 1)].tapped
    assert len(e.zlist("shield", 0)) == shields


def test_registered_speed_attacker_from_previous_turn_can_attack(rules):
    """登録カード: 前ターンからいるスピードアタッカー
    には制限が及ばず、発生源がいても攻撃できる
    （entered_this_turn の判別）。"""
    e = _build(rules,
               {"bz": [TARGET]},
               {"bz": ["T1090"]})
    before = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, attack="T1090")
    assert seen["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1


def test_registered_chars_deny_discrimination(rules):
    """登録カード: 特性レベルの判別 — deny の両方が
    付くのは「スピードアタッカーを持ち、entered_turn
    が現在のターンと一致する」クリーチャーだけ
    （所有者は問わない）。"""
    e = _build(rules,
               {"bz": [TARGET, "T1090", "T1091"]},
               {"bz": ["T1090"]})
    own_sa = _cid(e, "T1090", 0)
    opp_sa = _cid(e, "T1090", 1)
    vanilla = _cid(e, "T1091", 0)
    for c in (own_sa, opp_sa, vanilla):
        e.s.mut_card(c).entered_turn = e.s.turn
    for c in (own_sa, opp_sa):
        deny = e.chars(c)["deny"]
        assert "attack_player" in deny
        assert "attack_creature" in deny
    deny_v = e.chars(vanilla)["deny"]
    assert "attack_player" not in deny_v
    assert "attack_creature" not in deny_v
    e.s.mut_card(own_sa).entered_turn = e.s.turn - 1
    deny_prev = e.chars(own_sa)["deny"]
    assert "attack_player" not in deny_prev
    assert "attack_creature" not in deny_prev


def test_registered_source_keywords_blocker_and_double_breaker(rules):
    """登録カード: 発生源自身の条項 — ブロッカーと
    W・ブレイカーをキーワードとして持つ。"""
    e = _build(rules, {"bz": [TARGET]}, {})
    src = _cid(e, TARGET, 0)
    kw = e.chars(src)["keywords"]
    assert "blocker" in kw
    assert "double_breaker" in kw


def test_registered_granted_speed_attacker_not_caught_by_base_scope(rules):
    """登録カード: 既知の制限の固定 — 静的効果の
    affects 照合は base（印刷特性）のため、他の
    効果で付与されたスピードアタッカー（T314 の
    自己付与）は本フィルタに掛からず deny は
    付かない。"""
    e = _build(rules,
               {"bz": [TARGET, "T314"]},
               {})
    granted = _cid(e, "T314", 0)
    e.s.mut_card(granted).entered_turn = e.s.turn
    ch = e.chars(granted)
    assert "speed_attacker" in ch["keywords"]   # 付与自体は有効
    assert "attack_player" not in ch["deny"]
    assert "attack_creature" not in ch["deny"]


def _charge(e, player, tid):
    """player の最初の charge で tid を選んで置く。
    置けたら True を返す（第399弾本体と同型）。"""
    for _ in range(300):
        d = e.advance()
        if d is None:
            return False
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and d.get("player") == player:
            hit = [i for i, k in enumerate(keys) if tid in k]
            if hit:
                e.answer([hit[0]])
                for _ in range(4):
                    if any(e.cdef(c).id == tid
                           for c in e.zlist("mana", player)):
                        break
                    d2 = e.advance()
                    if d2 is None:
                        break
                    keys2 = [o["key"] for o in d2["options"]]
                    if "pass" in keys2:
                        e.answer([keys2.index("pass")])
                    elif "no_block" in keys2:
                        e.answer([keys2.index("no_block")])
                    elif d2["kind"] == "declare_strigger":
                        e.answer([])
                    else:
                        e.answer(list(range(d2.get("min", 0))))
                return True
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
    return False


def test_registered_multicolor_card_enters_mana_tapped(rules):
    """登録カード: 「マナゾーンに置く時、このカードは
    タップして置く」は多色カードのルール（405.1）で
    text のみ — 光・水の2文明を持つ登録カードを
    手札からマナに置くとタップ状態で置かれる。
    対照として単色の T1090（火）はアンタップで
    置かれる。"""
    e = _build(rules, {"hand": [TARGET]}, {})
    assert _charge(e, 0, TARGET)
    mana = [c for c in e.zlist("mana", 0) if e.cdef(c).id == TARGET]
    assert len(mana) == 1
    assert e.s.cards[mana[0]].tapped
    e2 = _build(rules, {"hand": ["T1090"]}, {})
    assert _charge(e2, 0, "T1090")
    mana2 = [c for c in e2.zlist("mana", 0) if e2.cdef(c).id == "T1090"]
    assert len(mana2) == 1
    assert not e2.s.cards[mana2[0]].tapped
