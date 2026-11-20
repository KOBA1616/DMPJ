"""語彙パイロット第319弾: 「攻撃の後、このクリーチャーを破壊する」
（destroy_self_after_attacking）。

センサス（rejects 2,057件を取り直し）: pure 1,908件 /
multi 131件 / 空 gaps 18件（全て第312〜315弾監査で別
ブロッカー確認済み）。pure の大半は範囲外（gr_summon 147 /
aura 108＝未承認 / hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 / out_of_game
23 / duelist_link 20 / outside_game 12 / pandora_shift 4）か
評価済み DEEP・重い・延期。範囲内・未評価で最小の
destroy_self_after_attacking（純粋2件）を選定した:
dm22rp1-038 レター＝ジェンゲガー / dm22rp2x-061
ディッシュ＝ウィッシュ。両行とも partial は骨格
（キーワードのみ）で、未解決は自壊条項のみ。

結論はドリフト（追加語彙なし）。確立形は第315弾
dmex12-s19 の登録形そのもの: 攻撃誘発の中で
delayed_trigger {when: {event: attack_end, subject: self},
duration: during_attack} を登録し、攻撃終了時に解決する。
- 形A（dm22rp1-038）: 攻撃誘発1件のみ。
- 形B（dm22rp2x-061）: 形A ＋ ブロック誘発
  {event: block, subject: self} → delayed_trigger
  {when: {event: attack_end, target: self}, ...}。
  attack_end レコードの target は攻撃対象（ブロックした
  クリーチャー）で、target: self の照合は dm13-040
  （バイバイ・アメーバ）の登録先例がある。

発見: 変換済み9件（dm26-055 / dmex12-094 / dmrp05-074 /
dmex14-075 / dmpcd01-r14 / dmpcd03-b11 / dmr06-043 /
dmrp08-077 / dmsd06-015）が使う旧近似形
delayed_trigger {when: {event: turn_end},
duration: during_attack} は発火しない。during_attack の
遅延誘発は攻撃タスク完了時（combat の 510.2）に
_expire で除去され、turn_end まで残らない。dmex12-094 で
実挙動プローブ済み（攻撃してもターン終了後も場に残る）。
対照プロト T981 で本弾でも固定する。変換済み側の修繕は
本弾の範囲外（別修繕ステージ送り）。

プロト T979（形A）/ T980（形B）/ T981（旧近似形の対照）。
"""
import copy

from dmsim.cards.defs import load_tables, parse_card
from tests.conftest import setup

TABLES = load_tables()

DESTROY_SELF = {"op": "destroy", "select": {"ref": "self"}}
TRIGGER_A = {"kind": "trigger",
             "when": {"event": "attack", "subject": "self"},
             "effect": [{"op": "delayed_trigger",
                         "when": {"event": "attack_end",
                                  "subject": "self"},
                         "duration": "during_attack",
                         "effect": [DESTROY_SELF]}]}
TRIGGER_B_BLOCK = {"kind": "trigger",
                   "when": {"event": "block", "subject": "self"},
                   "effect": [{"op": "delayed_trigger",
                               "when": {"event": "attack_end",
                                        "target": "self"},
                               "duration": "during_attack",
                               "effect": [DESTROY_SELF]}]}
TRIGGER_OLD = {"kind": "trigger",
               "when": {"event": "attack", "subject": "self"},
               "effect": [{"op": "delayed_trigger",
                           "when": {"event": "turn_end"},
                           "duration": "during_attack",
                           "effect": [DESTROY_SELF]}]}

# parse 後は destroy マクロが move（to: graveyard, reason: destroy）
# に展開される。parse 比較は展開形で行う。
PARSED_DESTROY = {"op": "move", "select": {"ref": "self"},
                  "to": "graveyard", "reason": "destroy"}


def _parsed(trig):
    t = copy.deepcopy(trig)
    t["effect"][0]["effect"] = [PARSED_DESTROY]
    return t


EXPECTED = {"T979": [_parsed(TRIGGER_A)],
            "T980": [_parsed(TRIGGER_A), _parsed(TRIGGER_B_BLOCK)],
            "T981": [_parsed(TRIGGER_OLD)]}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive(e, attacker=None, blocker=None, stop_when=None, limit=1500):
    """汎用ドライバ。attacker（defn）でプレイヤーを攻撃し、
    blocker（defn）のブロック肢が現れたらブロックする。
    攻撃したターンの2つ先のターンまで進める（攻撃終了時の
    遅延誘発が解決し切った状態で止まる）。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(limit):
        if stop_when is not None and stop_when(e):
            break
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if blocker and k.startswith(f"bz:{blocker}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


# ---------- parse / validation ----------

def test_pilot319_protos_parse(rules):
    for cid, wants in EXPECTED.items():
        d = rules.cards[cid]
        for want in wants:
            assert want in d.abilities, cid


def test_pilot319_forms_raw_parse():
    for ab in (TRIGGER_A, TRIGGER_B_BLOCK):
        d = parse_card({"id": "TX319", "name": "x",
                        "types": ["creature"], "civs": ["darkness"],
                        "cost": 3, "power": 2000,
                        "abilities": [copy.deepcopy(ab)]}, TABLES)
        assert _parsed(ab) in d.abilities


# ---------- 実挙動: 形A（攻撃のみ） ----------

def test_form_a_destroyed_at_attack_end(rules):
    """T979 が攻撃すると、攻撃の後（攻撃終了時）に破壊される。
    次のターンの最初の決定時点で既に墓地にいる。"""
    e = setup(rules, {"bz": ["T979"]}, {})
    st = _drive(e, attacker="T979")
    assert st["attacked"]
    assert "T979" in _defns(e, "graveyard", 0)
    assert "T979" not in _defns(e, "bz", 0)


def test_form_a_no_attack_no_destroy(rules):
    """攻撃しなければターンが終わっても破壊されない。"""
    e = setup(rules, {"bz": ["T979"]}, {})
    for _ in range(400):
        if e.s.turn >= 2:
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T979" in _defns(e, "bz", 0)
    assert "T979" not in _defns(e, "graveyard", 0)


# ---------- 実挙動: 形B（攻撃またはブロック） ----------

def test_form_b_attack_destroyed_at_attack_end(rules):
    """T980 が攻撃し、相手ブロッカー（T004）とのバトルに
    勝っても、攻撃の後に破壊される。"""
    e = setup(rules, {"bz": ["T980"]}, {"bz": ["T004"]})
    st = _drive(e, attacker="T980", blocker="T004")
    assert st["attacked"]
    assert "T004" in _defns(e, "graveyard", 1)   # バトルで相手が落ちる
    assert "T980" in _defns(e, "graveyard", 0)
    assert "T980" not in _defns(e, "bz", 0)


def test_form_b_block_destroyed_at_attack_end(rules):
    """T980 がブロックし、バトルに勝っても、その攻撃の後に
    破壊される。"""
    e = setup(rules, {"bz": ["T980"]}, {"bz": ["T001"]})
    st = _drive(e, attacker="T001", blocker="T980",
                stop_when=lambda e: "T980" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    assert "T001" in _defns(e, "graveyard", 1)   # 攻撃側はバトルで落ちる
    assert "T980" in _defns(e, "graveyard", 0)   # 勝ったブロッカーも自壊
    assert "T980" not in _defns(e, "bz", 0)


# ---------- 対照: 旧近似形は発火しない ----------

def test_old_form_never_fires(rules):
    """対照 T981（旧近似形 when: turn_end ＋ during_attack）は
    攻撃しても破壊されない。遅延誘発が攻撃終了時の
    _expire で消えるため（変換済み9件の死に形）。"""
    e = setup(rules, {"bz": ["T981"]}, {})
    st = _drive(e, attacker="T981")
    assert st["attacked"]
    # 攻撃したターンの2つ先まで進めても場に残り続ける
    assert e.s.turn >= st["attack_turn"] + 2
    assert "T981" in _defns(e, "bz", 0)
    assert "T981" not in _defns(e, "graveyard", 0)
