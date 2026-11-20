"""語彙パイロット第320弾: 「ブロックした時／ブロックされた時」
（trigger_when_blocked）。

センサス（rejects 2,055件を取り直し）: pure 1,906件 /
multi 131件 / 空 gaps 18件（全て第312〜315弾の監査で別
ブロッカー確認済み）。pure の大半は範囲外（gr_summon 147 /
aura 108＝未承認 / hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 / out_of_game
23 / duelist_link 20 / outside_game 12 / pandora_shift 4）か
評価済み DEEP・重い・延期。範囲内・未評価の候補
（negate_effects / effect_negation＝攻撃できない効果の無効化で
negate_cannot_attack 系の機構が要る、opponent_choice_branch＝
3件とも相手の選択の構造が相異なる、shield_grant＝付与の持続と
発生源が3件で相異なる、cost_matching_selection＝コスト参照
フィルタ＋件数連動で均一でない、per_civilization_selection＝
文明別 distinct 選択の機構が要る、flying＝攻撃／ブロック制限の
エンジン作業＋他節が重い、delayed_return / draw_up_to＝対象行の
他節が重い、look_reorder＝dmrp06-071 の実ブロッカーは partial
側の self_return でギャップ名とずれる）を却下し、最小の
trigger_when_blocked（純粋2件）を選定した。

結論はドリフト（追加語彙なし）。block レコードは combat が
{ev: block, subject: ブロッカー, attacker: 攻撃クリーチャー,
controller: 防御側} で発行し、when 照合は subject / attacker
の両方を既に扱う（events._match_when の attacker 節には
「self なら『このクリーチャーがブロックされた時』」と明記）。
- 形A（dm26rp1-074 ノーガルディ・ネギオ＆ガルダンディ・
  ナスオ、「ブロックされた時」）: trigger {event: block,
  attacker: self} → break {player: opp, count: 2}。
  when の形は第280弾（dm06-101 / dm06-032 の cancel_attack
  形、プロト T793 / T794）の登録先例そのもの。
- 形B（dm26ex2-068 ワダウザノミコト、「ブロックした時」）:
  trigger {event: block, subject: self} → move {ref: self}
  と move {ref: event.attacker} を持ち主の手札へ
  （subject＝ブロッカーは dm20-045 の登録先例＋その
  source.notes「block イベントの subject はブロッカー自身」）。
  併記される離脱条項「離れた時、山札の上から4枚を見て
  1枚を手札に加え、残りを好きな順序で山札の上か下に置く」も
  既存部品で構成できる: choose {from_top: 4, look: true,
  count: all} as pile（第311弾形）→ choose {ref: pile,
  count: 1} as pick → move {ref: pick} to hand
  （reason: draw）→ repeat {times: {count: {ref: pile,
  zone: deck}}} [choose {ref: pile, zone: deck, count: 1}
  as c → modal [move to deck position: top / position:
  bottom]]。1枚ごとの上／下配置は dm24ex1-054 の登録形
  （repeat ＋ choose ＋ modal）の山札内版で、置いたカードは
  gen 切れで以降の choose {ref: pile} から落ちる
  （第287弾の残り処理と同じ原理）。

両行とも partial は骨格（dm26rp1-074 は text も切れており、
提出時は reject 行の公式全文を使う）。

プロト T982（形B、dm26ex2-068 型）/ T983（形A、
dm26rp1-074 型）。
"""
import copy

from dmsim.cards.defs import load_tables, parse_card
from tests._conv_cache import proto_card
from tests.conftest import setup

TABLES = load_tables()

TRIGGER_BLOCKED_BREAK = {
    "kind": "trigger",
    "when": {"event": "block", "attacker": "self"},
    "effect": [{"op": "break", "player": "opp", "count": 2}]}
TRIGGER_BLOCK_BOUNCE = {
    "kind": "trigger",
    "when": {"event": "block", "subject": "self"},
    "effect": [
        {"op": "move", "select": {"ref": "self"},
         "to": "hand", "reason": "return"},
        {"op": "move", "select": {"ref": "event.attacker"},
         "to": "hand", "reason": "return"}]}
TRIGGER_LEAVE_LOOK = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "from_top": 4,
                    "look": True, "count": "all"},
         "as": "pile"},
        {"op": "choose", "select": {"ref": "pile", "count": 1},
         "as": "pick"},
        {"op": "move", "select": {"ref": "pick", "count": "all"},
         "to": "hand", "reason": "draw"},
        {"op": "repeat",
         "times": {"count": {"ref": "pile", "zone": "deck"}},
         "body": [
             {"op": "choose",
              "select": {"ref": "pile", "zone": "deck", "count": 1},
              "as": "c"},
             {"op": "modal",
              "modes": [
                  [{"op": "move",
                    "select": {"ref": "c", "count": "all"},
                    "to": "deck", "position": "top",
                    "reason": "put"}],
                  [{"op": "move",
                    "select": {"ref": "c", "count": "all"},
                    "to": "deck", "position": "bottom",
                    "reason": "put"}]]}]}]}

FORM_074 = {"id": "dm26rp1-074",
            "name": "ノーガルディ・ネギオ＆ガルダンディ・ナスオ",
            "types": ["creature"], "civs": ["nature"], "cost": 2,
            "power": 3000, "races": ["ワイルド・ベジーズ"],
            "mana": 1,
            "text": "このクリーチャーがブロックされた時、"
                    "このクリーチャーは相手のシールドを"
                    "２つブレイクする。",
            "abilities": [TRIGGER_BLOCKED_BREAK]}
FORM_068 = {"id": "dm26ex2-068", "name": "ワダウザノミコト",
            "types": ["creature"], "civs": ["light", "water"],
            "cost": 4, "power": 1000,
            "races": ["ミズガミ", "ロスト・クルセイダー"],
            "mana": 1, "keywords": ["s_trigger", "blocker"],
            "text": ("S・トリガー（このカードを自分のシールドゾーン"
                     "から手札に加える時、コストを支払わずにすぐ"
                     "実行してもよい）\n"
                     "ブロッカー（このクリーチャーをタップして、"
                     "相手クリーチャーの攻撃先をこのクリーチャーに"
                     "変更してもよい）\n"
                     "このクリーチャーがブロックした時、この"
                     "クリーチャーと攻撃しているクリーチャーを"
                     "持ち主の手札に戻す。\n"
                     "このクリーチャーが離れた時、自分の山札の"
                     "上から４枚を見る。その中から１枚を手札に加え、"
                     "残りを好きな順序で山札の上か下に置く。"),
            "abilities": [TRIGGER_BLOCK_BOUNCE, TRIGGER_LEAVE_LOOK]}

# 山札 spec は末尾が一番上: 上から T002 / T003 / T007 / T008 /
# T010 / T034（ドローでずれるため、束は決定時点のスナップ
# ショットで読む）
DECK_SPEC = ["T002"] * 10 + ["T034", "T010", "T008",
                             "T007", "T003", "T002"]


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _deck_defns(e, p):
    return [e.s.cards[c].defn for c in e.zlist("deck", p)]


class _LeavePlan:
    """離脱条項の決定プラン。pick_pos: 束の何枚目を手札に加えるか。
    placements: (束の位置, モード0=上/1=下) を置く順に並べた列。
    残り1枚の choose は自動決定され決定として現れない（その場合は
    choose_mode だけが来る）ため、モードは位置ごとに引けるように
    保持し、未消費の最後の1件へ対応づける。"""

    def __init__(self, e, pick_pos, placements):
        self.e = e
        self.pick_pos = pick_pos
        self.mode_by_pos = dict(placements)
        self.order = [pos for pos, _ in placements]
        self.pile = None
        self.consumed = set()
        self._pending_mode = None
        self.modes_answered = 0

    def choose(self, d):
        opts = d["options"]
        offered = [self.e.s.cards[o["cid"]].defn for o in opts]
        if self.pile is None:
            self.pile = _deck_defns(self.e, 0)[:4]
            self.consumed.add(self.pick_pos)
            want = self.pile[self.pick_pos]
        else:
            pos = next(p for p in self.order
                       if p not in self.consumed
                       and self.pile[p] in offered)
            self.consumed.add(pos)
            self._pending_mode = self.mode_by_pos[pos]
            want = self.pile[pos]
        return [offered.index(want)]

    def mode(self, d):
        if self._pending_mode is None:
            # choose が自動決定された（残り1枚）: 未消費の最後の1件
            rest = [p for p in self.order if p not in self.consumed]
            assert len(rest) == 1, rest
            self.consumed.add(rest[0])
            m = self.mode_by_pos[rest[0]]
        else:
            m = self._pending_mode
            self._pending_mode = None
        self.modes_answered += 1
        keys = [o["key"] for o in d["options"]]
        return [keys.index(f"mode:{m}")]

    @property
    def done(self):
        return self.pile is not None \
            and self.modes_answered >= len(self.order)


def _drive(e, attacker=None, attacker_player=1, blocker=None,
           plan=None, stop_when=None, limit=900):
    """汎用ドライバ。attacker_player の attacker（defn）で
    プレイヤーを攻撃させ、blocker（defn）のブロック肢が
    現れたらブロックする。plan がある間は choose_cards /
    choose_mode を plan に委ね、plan 完了後の最初の決定で止まる。
    stop_when を渡した場合は、その述語が立った最初の決定で止まる
    （攻撃の解決が終わった局面で止め、次ターンのドロー等で
    観測が汚れないようにする）。"""
    state = {"attacked": False}
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if stop_when is not None and stop_when(e):
            return state
        if plan is not None and plan.done \
                and kind not in ("choose_cards", "choose_mode"):
            return state
        if kind in ("attack", "declare_attack"):
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and d["player"] == attacker_player \
                    and not state["attacked"]:
                state["attacked"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("block", "declare_block"):
            hit = [i for i, k in enumerate(keys)
                   if blocker and k.startswith(f"bz:{blocker}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_cards" and plan is not None:
            e.answer(plan.choose(d))
        elif kind == "choose_mode" and plan is not None:
            e.answer(plan.mode(d))
        elif kind == "choose_shields":
            # ブレイクするシールドの選択（先頭から必要枚数）
            e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


# ---------- parse / validation ----------

def test_pilot320_protos_parse(rules):
    d982 = rules.cards["T982"]
    assert d982.abilities == parse_card(
        copy.deepcopy(FORM_068), TABLES).abilities
    d983 = rules.cards["T983"]
    assert d983.abilities == parse_card(
        copy.deepcopy(FORM_074), TABLES).abilities


def test_pilot320_forms_raw_parse():
    for form, proto in ((FORM_068, "T982"), (FORM_074, "T983")):
        d = parse_card(copy.deepcopy(form), TABLES)
        p = parse_card(proto_card(proto), TABLES)
        assert d.abilities == p.abilities, form["id"]


# ---------- 実挙動: 形A（ブロックされた時、2ブレイク） ----------

def test_form_a_breaks_two_when_blocked(rules):
    """T983 が攻撃してブロックされると、バトルの前に相手の
    シールドを2つブレイクする（バトル自体も通常どおり行われる）。"""
    # シールドは識別できるよう T007 で固める（ドローと区別する）
    e = setup(rules, {"bz": ["T983"]},
              {"bz": ["T004"], "shield": ["T007"] * 5})
    shields0 = len(e.zlist("shield", 1))
    st = _drive(e, attacker="T983", attacker_player=0,
                blocker="T004",
                stop_when=lambda e: "T983" in _defns(e, "graveyard", 0)
                and "T004" in _defns(e, "graveyard", 1))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == shields0 - 2
    # ブレイクした2枚（T007）は相手の手札へ（S・トリガーは無い）
    assert _defns(e, "hand", 1).count("T007") == 2
    # バトルは行われ、3000 同士で相打ちになる
    assert "T983" in _defns(e, "graveyard", 0)
    assert "T004" in _defns(e, "graveyard", 1)


def test_form_a_no_break_when_other_creature_blocked(rules):
    """別のクリーチャーがブロックされても T983 は誘発しない
    （attacker: self の照合）。"""
    e = setup(rules, {"bz": ["T983", "T001"]}, {"bz": ["T004"]})
    shields0 = len(e.zlist("shield", 1))
    st = _drive(e, attacker="T001", attacker_player=0,
                blocker="T004",
                stop_when=lambda e: "T001" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == shields0
    assert "T001" in _defns(e, "graveyard", 0)   # バトルで落ちる
    assert "T983" in _defns(e, "bz", 0)


# ---------- 実挙動: 形B（ブロックした時、両方手札へ） ----------

def test_form_b_block_bounces_both_and_leave_looks(rules):
    """T982 がブロックすると、自身と攻撃クリーチャーが持ち主の
    手札に戻り、離脱条項（上4枚を見て1枚を手札、残りを上下に
    配置）も連鎖する。"""
    e = setup(rules, {"bz": ["T982"], "deck": DECK_SPEC},
              {"bz": ["T001"]})
    # 束[1]を手札へ。残りは 束[0]を下、束[2]を上、束[3]を上の順
    plan = _LeavePlan(e, pick_pos=1,
                      placements=[(0, 1), (2, 0), (3, 0)])
    st = _drive(e, attacker="T001", attacker_player=1,
                blocker="T982", plan=plan)
    assert st["attacked"] and plan.done
    pile = plan.pile
    assert pile is not None and len(pile) == 4
    # ブロックした T982 と攻撃していた T001 が持ち主の手札へ
    assert "T982" in _defns(e, "hand", 0)
    assert "T982" not in _defns(e, "bz", 0)
    assert "T001" in _defns(e, "hand", 1)
    assert "T001" not in _defns(e, "bz", 1)
    # 選んだ1枚が手札へ
    assert pile[1] in _defns(e, "hand", 0)
    deck = _deck_defns(e, 0)
    # 束[0] は山札の一番下。束[3]・束[2] はこの順で一番上に
    # 置かれたが、解決後の最初の決定は自分のターン開始ドローを
    # 済ませた後になるため、一番上の束[3] はドローで手札へ
    # （＝一番上に置かれたことの証明）、次が束[2]
    assert pile[3] in _defns(e, "hand", 0)
    assert deck[-1] == pile[0]
    assert deck[0] == pile[2]


def test_form_b_destroyed_leave_looks_without_bounce(rules):
    """T982 が攻撃してブロックされバトルで破壊された場合は、
    ブロック条項（形Bの第1誘発）は発火せず、離脱条項だけが
    発火する。"""
    e = setup(rules, {"bz": ["T982"], "deck": DECK_SPEC},
              {"bz": ["T004"]})
    # 束[0]を手札へ。残りは全て下へ（束[1]→束[2]→束[3] の順）
    plan = _LeavePlan(e, pick_pos=0,
                      placements=[(1, 1), (2, 1), (3, 1)])
    st = _drive(e, attacker="T982", attacker_player=0,
                blocker="T004", plan=plan)
    assert st["attacked"] and plan.done
    pile = plan.pile
    # T982 は墓地へ（手札に戻らない）、ブロッカーは場に残る
    assert "T982" in _defns(e, "graveyard", 0)
    assert "T982" not in _defns(e, "hand", 0)
    assert "T004" in _defns(e, "bz", 1)
    # 離脱条項: 選んだ1枚が手札へ、残りは置いた順に下側へ
    assert pile[0] in _defns(e, "hand", 0)
    deck = _deck_defns(e, 0)
    assert deck[-3:] == [pile[1], pile[2], pile[3]]


def test_form_b_no_trigger_when_other_creature_blocks(rules):
    """別のクリーチャーがブロックしても T982 は誘発しない
    （subject: self の照合）。バトルは通常どおり行われる。"""
    e = setup(rules, {"bz": ["T982", "T004"], "deck": DECK_SPEC},
              {"bz": ["T001"]})
    st = _drive(e, attacker="T001", attacker_player=1,
                blocker="T004",
                stop_when=lambda e: "T001" in _defns(e, "graveyard", 1))
    assert st["attacked"]
    assert "T982" in _defns(e, "bz", 0)
    assert "T982" not in _defns(e, "hand", 0)
    assert "T001" in _defns(e, "graveyard", 1)   # バトルで落ちる
    assert "T004" in _defns(e, "bz", 0)
