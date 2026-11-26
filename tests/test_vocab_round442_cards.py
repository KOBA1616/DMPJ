"""再変換ラウンド442（第407弾 summoning_attack_rule）の記録テスト。

- 新規登録1件: dmex02-011 超絶特Q ダンガンテイオー
  （登録形は提出形と完全一致〔差分は validate が
  identity.aliases_for から自動付与した
  source.aliases のみ〕: partial の骨格
  〔クリーチャー / ゼロ / コスト8 / パワー8000 /
  種族 ジョーカーズ、mana 1、keywords
  [double_breaker]、abilities 無し〕に第407弾の
  確立形 static 2件〔付与: affects {zone: bz,
  owner: you, filter: {types: [creature],
  entered_this_turn: true}}, mod: {player_rush:
  true}／deny: affects {zone: bz, owner: opp,
  filter: {types: [creature], entered_this_turn:
  true}}, mod: {deny: [attack_player]}〕を足し、
  unsupported を外したもの。abilities はこの
  2件ちょうど、keywords は [double_breaker]
  のまま。補完なし〔partial の text は公式
  テキスト全文と一致し、登録後の全文一致も
  照合済み〕）。
- alias 畳み込み1件: promoy16-008 の独自行
  （gap entered_turn_attack）。同カードの別版で、
  骨格（ゼロ / コスト8 / パワー8000 / 種族
  ジョーカーズ / mana 1 / keywords
  [double_breaker]）とイラストレーター（lack）が
  一致し、テキストは版差の文面差
  （「プレイヤーを攻撃できる」⇔「相手プレイヤーを
  攻撃できる」、「プレイヤーを攻撃できない」⇔
  「自分を攻撃できない」）のみで指す対象が同一
  ＝意味が同一であることを実測確認したため、
  reopen（entered_turn_attack）を併用して行を
  解消し、登録エントリの source.aliases に
  validate が自動付与する形で畳み込んだ。
  identity 実測で canon_id は対象・alias とも
  dmex02-011、aliases_for = [promoy16-008]。
- stale クリーンアップ0件。
- 差し戻し2件: reopen（summoning_attack_rule）の
  出力は2件で、dmex07-s01 は partial が素で
  他条項が未構築のため unsupported を残した
  partial のまま差し戻し（gaps・partial は
  HEAD と深比較で完全一致を確認）。reopen
  （entered_turn_attack）の出力は2件で、別
  カード dmbd11-d05 も同様に差し戻し。
  summoning_attack_rule は dmex07-s01 が残り
  完全解消しない。entered_turn_attack は
  dmbd11-d05 が残る。
- converted 10,386→10,387 / rejects 1,926→1,924、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第407弾本体と同形（対象を proto T1175 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1090（スピードアタッカー役）/
T1091（通常クリーチャー役）/ T314（スピード
アタッカー自己付与役）。バトルゾーンは共有
ゾーンなので所有は bz_tops(p) で見る。
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
from tests.test_vocab_pilot407 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex02-011"
GAP = "summoning_attack_rule"
NAME = "超絶特Q ダンガンテイオー"
ALIASES = ["promoy16-008"]
OTHER = "dmex07-s01"
OTHER2 = "dmbd11-d05"


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


def test_round442_disposition():
    rej = _reject_rows()
    assert len(rej) == 1924
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10387
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    # alias 畳み込み: promoy16-008 の独自行は解消し、
    # 登録エントリにもならない（漏れ0）
    for a in ALIASES:
        assert a not in rej
        assert a not in ids
    # 差し戻し2件は gaps・reason を保って残留
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == [OTHER]                # ファミリーは解消しない
    assert rej[OTHER]["gaps"] == [GAP]
    assert rej[OTHER]["reason"] == "vocab"
    uns = (rej[OTHER]["partial"].get("source") or {}).get("unsupported") or []
    assert [u.get("need") for u in uns] == [GAP]
    et = sorted(rid for rid, r in rej.items()
                if "entered_turn_attack" in (r.get("gaps") or []))
    assert et == [OTHER2]
    assert rej[OTHER2]["gaps"] == ["entered_turn_attack"]
    assert rej[OTHER2]["reason"] == "vocab"
    uns2 = (rej[OTHER2]["partial"].get("source") or {}).get("unsupported") or []
    assert [u.get("need") for u in uns2] == ["entered_turn_attack"]
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"]
    assert c["civs"] == ["zero"]
    assert c["cost"] == 8 and c["power"] == 8000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は確立形 static 2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["keywords"] == ["double_breaker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    own = [a for a in d.abilities if not a.get("keyword")]
    assert own == FORM
    assert d.keywords == ["double_breaker"]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第407弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


def _drive(e, player, play=None, attack=None):
    """player の最初の main のターンだけを対象に進める
    ドライバ（第407弾本体と同型）。"""
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


def test_registered_own_vanilla_entered_this_turn_can_attack_player(rules):
    """付与の判別: 登録カードがいれば、通常クリーチャー
    でも出たターンにプレイヤーを攻撃できる（シールド
    1枚減る）。クリーチャーへの攻撃は解放されない。"""
    e = _build(rules,
               {"bz": [TARGET], "hand": ["T1091"],
                "mana": ["T1091", "T1091"]},
               {"bz": ["T1091"]})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T1091", attack="T1091")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 1
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1091:T")]


def test_registered_opp_speed_attacker_entered_this_turn_cannot_attack_player(rules):
    """deny の判別: 相手のスピードアタッカーも、出た
    ターンにはプレイヤーを攻撃できない。"""
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


def test_registered_opp_speed_attacker_from_previous_turn_can_attack(rules):
    """前ターンからいる相手のスピードアタッカーには
    deny が及ばず、登録カードがいてもプレイヤーを
    攻撃できる（entered_this_turn の判別）。"""
    e = _build(rules,
               {"bz": [TARGET]},
               {"bz": ["T1090"]})
    before = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, attack="T1090")
    assert seen["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1


def test_registered_chars_grant_and_deny_discrimination(rules):
    """特性レベルの判別: 出たターンの自軍クリーチャー
    （発生源自身を含む）には player_rush が付き、
    出たターンの相手クリーチャーには attack_player
    の deny だけが付く。前ターンからいるものには
    どちらも付かない。"""
    e = _build(rules,
               {"bz": [TARGET, "T1091"]},
               {"bz": ["T1090"]})
    src = _cid(e, TARGET, 0)
    own = _cid(e, "T1091", 0)
    opp = _cid(e, "T1090", 1)
    for c in (src, own, opp):
        e.s.mut_card(c).entered_turn = e.s.turn
    assert e.chars(own)["player_rush"] is True
    assert e.chars(src)["player_rush"] is True   # 発生源自身も対象
    deny = e.chars(opp)["deny"]
    assert "attack_player" in deny
    assert "attack_creature" not in deny
    assert e.chars(opp)["player_rush"] is False  # 付与は自軍だけ
    for c in (own, opp):
        e.s.mut_card(c).entered_turn = e.s.turn - 1
    assert e.chars(own)["player_rush"] is False
    assert "attack_player" not in e.chars(opp)["deny"]


def test_registered_attack_options_source_and_granted_sa(rules):
    """攻撃選択肢レベルの判別: (1) 発生源自身も、出た
    ターンはプレイヤーへの攻撃だけが提示される。
    (2) 付与されたスピードアタッカー（T314）にも
    deny が掛かる（フィルタに keyword を含まない
    ため第398弾の base 照合の制限は及ばない）。"""
    e = _build(rules,
               {"bz": [TARGET, "T1091"]},
               {"bz": ["T314"]})
    src = _cid(e, TARGET, 0)
    own = _cid(e, "T1091", 0)
    granted = _cid(e, "T314", 1)
    for c in (src, own, granted):
        e.s.mut_card(c).entered_turn = e.s.turn
    ch = e.chars(granted)
    assert "speed_attacker" in ch["keywords"]   # 付与自体は有効
    assert "attack_player" in ch["deny"]
    e.s.mut_card(own).tapped = True             # 相手の攻撃先用
    keys1 = [o["key"] for o in e._attack_options(1)]
    assert "attack:T314:player" not in keys1
    assert "attack:T314:T1091" in keys1         # クリーチャー攻撃は可
    keys0 = [o["key"] for o in e._attack_options(0)]
    assert f"attack:{TARGET}:player" in keys0
    assert not [k for k in keys0 if k.startswith(f"attack:{TARGET}:T")]
