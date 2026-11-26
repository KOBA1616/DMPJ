"""再変換ラウンド438（第403弾 cast_limit_once_per_turn）の記録テスト。

- 新規登録1件: dmex03-g02 ゴールデン・ザ・ジョニー
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 無色 / コスト7 / パワー10000 /
  種族 ジョーカーズ、mana 1、keywords
  [speed_attacker, double_breaker]、構築済み
  マスター・ブラスター攻撃時誘発1件〕に第403弾の
  確立形 static〔affects {zone: hand, owner: opp,
  filter: {types: [spell]}}, mod {deny: [{action:
  cast, max_per_turn: 1}]}〕1件を足し、unsupported
  を外したもの。abilities はこの2件ちょうど、
  keywords は [speed_attacker, double_breaker]
  のまま。**補完なし**〔partial の text は公式
  全文と一致。登録後の全文一致も照合済み〕）。
- alias 畳み込み0件（alias 2件 dmex01-076 /
  promoy16-063 は rejects に独自行が無く converted
  にも登録なし。登録エントリの source.aliases は
  validate が identity.aliases_for から自動付与
  した2件。正本判定は通常型: 対象 id と alias 2件
  を real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1170 の notes 内参照のみ〕、identity
  実測で canon_id は対象・全 alias とも
  dmex03-g02）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔cast_limit_once_per_turn〕の出力は
  対象1件ちょうど: reopen は gaps ⊆ 指定集合
  かつ reason == "vocab" の行だけを外すため、
  gaps が2件の multi 2件〔一音の妖精
  dm26ex2-pr006 / dm26ex4-cho031、
  opponent_creature_entry_limit_once_per_turn
  との複合〕は巻き込まれず、gaps・partial を
  保ったまま rejects に残留することを実測で
  確認した。差し戻しは発生していない）。
- converted 10,382→10,383 / rejects 1,930→1,929、
  canonical 重なり0・漏れ0。cast_limit_
  once_per_turn は pure は解消するが multi 2件が
  残るため完全解消しない。
- 確立形は第182弾の回数型 deny（modify 形で
  登録済み）を常在型 static に載せたドリフト。
  S・トリガー詠唱も詠唱レコードを通るため上限に
  数えられる（第403弾で実測）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）は本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第403弾本体と同形（対象を proto T1170 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第403弾の proto を流用: T003（相手の詠唱役）/
T001（マナ役・召喚対照役）/ T408（ジョーカーズ
マナ役）/ T960・T961（相手の S・トリガー呪文役）。
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
from tests.test_vocab_pilot403 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex03-g02"
GAP = "cast_limit_once_per_turn"
NAME = "ゴールデン・ザ・ジョニー"
ALIASES = ["dmex01-076", "promoy16-063"]
MULTI = ["dm26ex2-pr006", "dm26ex4-cho031"]


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


def test_round438_disposition():
    rej = _reject_rows()
    assert len(rej) == 1929
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10383
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    # pure は解消、multi 2件は gaps・partial を保って残留
    pure = sorted(rid for rid, r in rej.items()
                  if (r.get("gaps") or []) == [GAP])
    assert pure == []
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == MULTI
    for m in MULTI:
        assert rej[m]["gaps"] == [GAP,
                                  "opponent_creature_entry_limit_once_per_turn"]
        uns = (rej[m]["partial"]["source"].get("unsupported") or [])
        assert [u["need"] for u in uns] == rej[m]["gaps"]
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"]
    assert c["civs"] == ["zero"]
    assert c["cost"] == 7 and c["power"] == 10000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    # 登録形は提出形と完全一致: 誘発＋static の2能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert src.get("aliases") == ALIASES  # validate の自動付与
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    # parse では keyword 2件が派生 static に展開されるため、
    # abilities は [speed_attacker 派生 static,
    # double_breaker 派生 static, 構築済み誘発, 確立形 static]
    assert len(d.abilities) == 4
    assert d.abilities[0].get("keyword") == "speed_attacker"
    assert d.abilities[1].get("keyword") == "double_breaker"
    assert d.abilities[2] == FORM[0]
    assert d.abilities[3] == FORM[1]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第403弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, p, defn, zone):
    return next(c for c in e.zlist(zone, p)
                if e.cdef(c).id == defn
                and e.s.cards[c].controller == p)


def _drive(e, plays0=(), plays1=(), attacker=None, attacker_player=0,
           pick=None, strigger_all=False, stop=None, limit=1200):
    """汎用ドライバ（第403弾本体と同型）。"""
    state = {"attacked": False, "played": []}
    plays = {0: list(plays0), 1: list(plays1)}
    for _ in range(limit):
        if stop is not None and stop():
            return state
        d = e.advance()
        if d is None:
            return state
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and pl in plays and plays[pl]:
            hit = next((k for k in plays[pl] if k in keys), None)
            if hit is not None:
                plays[pl].remove(hit)
                state["played"].append(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("attack", "declare_attack"):
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and pl == attacker_player \
                    and not state["attacked"]:
                state["attacked"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer(list(range(len(keys))) if strigger_all else [])
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


def _cast_first_spell(e):
    """相手（p1）が手札の T003 を1枚唱えて墓地に置かれるまで進める。"""
    _drive(e, plays1=["play:T003"],
           stop=lambda: "T003" in _defns(e, "graveyard", 1))


def _until_main(e, player, limit=600):
    """player のメイン決定を掴んで（答えずに）返す
    （第403弾本体と同方式）。(decision, keys) を返す。"""
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == player:
            return d, keys
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] in ("choose_cards", "choose_shields"):
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("main never came")


def _cast_one_from_main(e, key="play:T003"):
    """現在の p1 メインで key を1回実行し、同じターンの
    次の p1 メイン決定を掴んで返す。"""
    d, keys = _until_main(e, 1)
    assert key in keys
    turn = e.s.turn
    e.answer([keys.index(key)])
    d, keys = _until_main(e, 1)
    assert e.s.turn == turn                      # 同一ターン内
    return d, keys


def test_registered_second_cast_denied_same_turn(rules):
    """実挙動: 登録カードがいる間、相手は1ターンに
    呪文を1枚しか唱えられない。1枚目は解決し、
    2枚目は permits が False でメインの選択肢にも
    出ない。"""
    e = _build(rules, {"bz": [TARGET]},
               {"hand": ["T003", "T003"],
                "mana": ["T003", "T003", "T003", "T001", "T001", "T001"]})
    first = _cid(e, 1, "T003", "hand")
    assert e.permits(first, "cast")              # まだ0枚: 可
    d, keys = _cast_one_from_main(e)
    assert "T003" in _defns(e, "graveyard", 1)   # 1枚目は解決した
    assert e.s.turn_counters.get("hist:cast:1") == 1
    rest = [c for c in e.zlist("hand", 1)
            if e.cdef(c).id == "T003"]
    assert len(rest) == 1
    assert not e.permits(rest[0], "cast")        # 1枚唱えた: 不可
    assert "play:T003" not in keys               # 選択肢にも出ない


def test_registered_limit_resets_next_turn(rules):
    """実挙動（ターン判別）: 制限はターンごとに
    リセットされる。次の相手ターンでは再び呪文を
    1枚唱えられる。"""
    e = _build(rules, {"bz": [TARGET]},
               {"hand": ["T003", "T003"],
                "mana": ["T003", "T001", "T001", "T001", "T001"]})
    d, keys = _cast_one_from_main(e)
    rest = [c for c in e.zlist("hand", 1)
            if e.cdef(c).id == "T003"]
    assert not e.permits(rest[0], "cast")
    t0 = e.s.turn
    _drive(e, stop=lambda: e.s.turn >= t0 + 2)   # 相手→自分→相手
    assert e.permits(rest[0], "cast")            # リセットされた
    _drive(e, plays1=["play:T003"],
           stop=lambda: _defns(e, "graveyard", 1).count("T003") >= 2)
    assert _defns(e, "graveyard", 1).count("T003") == 2


def test_registered_scope_owner_and_summon_unaffected(rules):
    """判別（範囲）: 制限は相手の呪文だけに及ぶ。
    登録カードの持ち主の呪文と、相手のクリーチャー
    の召喚は、相手が1枚唱えた後でも妨げられない。"""
    e = _build(rules,
               {"bz": [TARGET], "hand": ["T003"],
                "mana": ["T003", "T001"]},
               {"hand": ["T003", "T001"],
                "mana": ["T003", "T001", "T001", "T001", "T001"]})
    own_spell = _cid(e, 0, "T003", "hand")
    assert e.permits(own_spell, "cast")          # 持ち主は対象外
    _cast_first_spell(e)
    assert e.permits(own_spell, "cast")          # 唱えた後も対象外
    opp_creature = _cid(e, 1, "T001", "hand")
    assert e.permits(opp_creature, "summon")     # 召喚は制限されない


def test_registered_strigger_casts_count_toward_limit(rules):
    """実挙動（S・トリガー判別）: 登録カード自身の
    W・ブレイカーで割れた相手の S・トリガー呪文
    2枚を両方宣言すると、1枚目は解決するが2枚目は
    そのターンの上限に達して実行されず手札に残る
    （S・トリガー詠唱も「呪文を唱える」に数えられる）。"""
    e = _build(rules, {"bz": [TARGET]},
               {"shield": ["T960", "T961"]})
    st = _drive(e, attacker=TARGET, attacker_player=0,
                strigger_all=True, stop=lambda: e.s.turn >= 3)
    assert st["attacked"]
    zones = {d: [z for z in ("shield", "hand", "graveyard")
                 if d in _defns(e, z, 1)] for d in ("T960", "T961")}
    assert zones["T961"] == ["graveyard"]        # 1枚目: 解決
    assert zones["T960"] == ["hand"]             # 2枚目: 上限で不発


def test_registered_master_blaster_still_works(rules):
    """実挙動（partial 構築済み条項の保全）:
    ジョーカーズが bz＋マナ合計4枚以上で攻撃すると、
    マスター・ブラスターが相手のカードを山札の
    一番下に置く。合計3枚では発火しない。"""
    e = _build(rules,
               {"bz": [TARGET], "mana": ["T408", "T408", "T408"]},
               {"bz": ["T001"]})
    st = _drive(e, attacker=TARGET, attacker_player=0,
                pick="bz:T001", stop=lambda: e.s.turn >= 2)
    assert st["attacked"]
    assert "T001" not in _defns(e, "bz", 1)
    assert "T001" in _defns(e, "deck", 1)        # 山札へ（下）
    # 対照: 合計3枚（マナ2枚）では発火しない
    e = _build(rules,
               {"bz": [TARGET], "mana": ["T408", "T408"]},
               {"bz": ["T001"]})
    st = _drive(e, attacker=TARGET, attacker_player=0,
                pick="bz:T001", stop=lambda: e.s.turn >= 2)
    assert st["attacked"]
    assert "T001" in _defns(e, "bz", 1)
