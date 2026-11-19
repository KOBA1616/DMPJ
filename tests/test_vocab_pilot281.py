"""語彙パイロット第281弾: leave_replacement_shield_to_hand
（自分のクリーチャーが離れる時、かわりにシールドを手札に戻す置換）。

rejects の leave_replacement_shield_to_hand 純粋3件:
- dm23ex3-tf03 「終焉」の頂 オーエン・ザ・ロード
  （自分のクリーチャーが離れる時、シールド2つを手札に戻してもよい）
- dm24ex4-042 星姫械 エルナドンナ
  （各ターンに一度、自分の他のクリーチャーが離れる時、シールド1つ）
- dmx23-025 若き日の族長 ヘンザ
  （自分のクリーチャーがバトルゾーンを離れる時、シールド2つ）

不足は「離れる時の置換を、自分以外のクリーチャーにも及ぶ発生源から
使う」形だけ。置換の機構そのものは escape（破壊時のみ・自分・1枚）と
第277弾 true_escape（離れる時全般・自分・2枚）で実証済みで、
_replacement の候補走査は発生源プレイヤーの bz_tops 全体を見るため、
発生源と動くカードが別でも諮問される。subject の dict 形
（{owner: you} / {owner: you, other: true}）は _subject_match の既存形。
本弾は新語彙・エンジン変更なしのイディオム弾で、次の形を確立する:

- 基本形（tf03 / ヘンザ）:
  {kind: replace, optional: true,
   when: {event: move, from: bz,
          subject: {owner: you, filter: {types: [creature]}}},
   if: {cmp: [{count: {zone: shield, owner: you}}, ">=", 2]},
   instead: [move シールド2枚 → 手札, reason: return, strigger: "off"]}
  subject は自分を含む「自分のクリーチャー」全般。行き先・理由は問わない
  （true_escape と同じ「離れる時」全般）。if は true_escape と同じ
  cmp/count ゲート（払える時だけ諮問する）。
- 他者・各ターン一度形（dm24ex4-042）:
  subject に other: true（_subject_match の「自分以外」）、
  once_per_turn: true（置換側の対応は第196弾。印は選ばれた時に付き、
  辞退では消費しない）、枚数は1枚で if は >= 1。

dm26rp3-001 ヒトリダチ ケントナーク（ギャップ名
once_per_turn_leave_replacement_shield_to_hand の単独行）も同じ形で
表せる（subject の filter に race_has: ジョーカーズ、once_per_turn、
1枚）。ただし partial に出た時のモード能力（シールド化／Jビッグ1）が
丸ごと欠けているため、本弾の対象3件とは別にラウンド側で判断する。

Rust: どちらの形も optional（エルナドンナ形は once_per_turn も）を含む
ため _simple_replace の対象外（escape / true_escape と同じ）で、
この能力を持つカードを含む対局は Python にフォールバックする。
新しい GameState フィールドは無い（state.rs 変更なし）。スキーマ再生成なし
（when の subject は parse_card のキー検証対象外＝第278弾の確認どおり）。
"""
from dmsim.cards.defs import load_tables, parse_card
from dmsim.engine.rustcore import _simple_replace
from tests.conftest import setup

TABLES = load_tables()

EXPECTED_796 = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "from": "bz",
             "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
    "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">=", 2]},
    "instead": [{"op": "move",
                 "select": {"zone": "shield", "owner": "you", "count": 2},
                 "to": "hand", "reason": "return", "strigger": "off"}],
}

EXPECTED_797 = {
    "kind": "replace", "optional": True, "once_per_turn": True,
    "when": {"event": "move", "from": "bz",
             "subject": {"owner": "you", "other": True,
                         "filter": {"types": ["creature"]}}},
    "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">=", 1]},
    "instead": [{"op": "move",
                 "select": {"zone": "shield", "owner": "you", "count": 1},
                 "to": "hand", "reason": "return", "strigger": "off"}],
}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第277弾のものと同形）。"""

    def __init__(self, play=None, replace="accept", choose=None):
        self.play = play
        self.replace = replace
        self.choose = choose
        self.seen = []

    def run(self, e, stop, limit=800):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen.append(kind)
            if kind == "choose_replacement":
                if self.replace == "accept":
                    hit = [i for i, k in enumerate(keys) if k.startswith("replace:")]
                    assert hit, "置換の諮問に replace 選択肢が無い"
                    e.answer(hit[:1])
                else:
                    e.answer([keys.index("decline")])
                if stop(e):
                    return
                continue
            if kind == "choose_cards" and self.choose is not None:
                ans = self.choose(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "main" and self.play is not None:
                ans = self.play(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "declare_strigger":
                e.answer([])
            elif kind == "declare_sback":
                e.answer([])
            elif kind == "choose_breaker":
                e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
            elif kind == "choose_shields":
                e.answer(list(range(d.get("min", 0))))
            elif kind == "pay_mana":
                e.answer([0])
            elif kind == "yes_no":
                e.answer([keys.index("yes")])
            elif kind == "order_pending":
                e.answer([0])
            elif kind == "block":
                if "no_block" in keys:
                    e.answer([keys.index("no_block")])
                else:
                    e.answer(list(range(d.get("min", 0))))
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            if stop(e):
                return
        raise AssertionError("limit reached")


def _play_times(key, times):
    seen = {"n": 0}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and seen["n"] < times:
            seen["n"] += 1
            return [keys.index(key)]
        return None

    return play


def _play_once(key):
    return _play_times(key, 1)


def _choose_targets(*defns):
    """choose_cards で、指定した defn のカードを順に選ぶフック。

    対象選択以外の choose_cards（シールドの支払い等）には None を返し、
    ドライバの既定処理に任せる。"""
    queue = list(defns)

    def choose(e, d):
        if not queue:
            return None
        for i, o in enumerate(d["options"]):
            if e.cdef(o["cid"]).id == queue[0]:
                queue.pop(0)
                return [i]
        return None

    return choose


# ---------- parse / validation ----------

def test_pilot281_protos_parse():
    from dmsim.cards.defs import load_rules
    rules = load_rules()
    t796 = rules.cards["T796"]
    assert [ab for ab in t796.abilities if ab["kind"] == "replace"] == [EXPECTED_796]
    t797 = rules.cards["T797"]
    assert [ab for ab in t797.abilities if ab["kind"] == "replace"] == [EXPECTED_797]
    # 生の辞書でも両形とも parse できる
    for ab in (EXPECTED_796, EXPECTED_797):
        d = parse_card({"id": "TX281", "name": "x", "types": ["creature"],
                        "civs": ["light"], "cost": 5, "power": 2000,
                        "abilities": [ab]}, TABLES)
        assert [a for a in d.abilities if a["kind"] == "replace"] == [ab]


def test_pilot281_not_rust_simple():
    # optional / once_per_turn を含むため _simple_replace の対象外
    # （escape / true_escape と同じ Python フォールバック）
    assert not _simple_replace(dict(EXPECTED_796))
    assert not _simple_replace(dict(EXPECTED_797))


# ---------- 実挙動: T796（基本形・2枚） ----------

def test_796_protects_ally_from_destroy(rules):
    """味方が破壊される時、シールド2枚を手札に戻して味方が残る。"""
    e = setup(rules, {"bz": ["T796", "T002"]}, {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T002"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert "T796" in _defns(e, "bz", 0) and "T002" in _defns(e, "bz", 0)
    assert "T002" not in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 3
    assert drv.seen.count("choose_replacement") == 1


def test_796_protects_self_from_destroy(rules):
    """発生源自身が離れる時も（subject は自分を含む）置換できる。"""
    e = setup(rules, {"bz": ["T796"]}, {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "T796" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert "T796" in _defns(e, "bz", 0)
    assert "T796" not in _defns(e, "graveyard", 0)
    assert drv.seen.count("choose_replacement") == 1


def test_796_declined_ally_destroyed(rules):
    """辞退すれば味方は通常どおり破壊され、シールドは減らない。"""
    e = setup(rules, {"bz": ["T796", "T002"]}, {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), replace="decline",
                  choose=_choose_targets("T002"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T002" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 5
    assert drv.seen.count("choose_replacement") == 1


def test_796_protects_ally_from_bounce(rules):
    """「離れる時」全般: バウンス（手札に戻す効果）も置換できる。"""
    e = setup(rules, {"bz": ["T796", "T002"]}, {"hand": ["T140"], "mana": ["T140"] * 3})
    drv = _Driver(play=_play_once("play:T140"), choose=_choose_targets("T002"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert "T002" in _defns(e, "bz", 0)
    assert "T002" not in _defns(e, "hand", 0)
    assert drv.seen.count("choose_replacement") == 1


def test_796_does_not_protect_opponent(rules):
    """相手のクリーチャーが離れる時は諮問されない。"""
    e = setup(rules, {"bz": ["T796"], "hand": ["T056"], "mana": ["T056"] * 3},
              {"bz": ["T002"]})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T002" in _defns(e, "graveyard", 1)
    assert "choose_replacement" not in drv.seen


def test_796_unavailable_with_one_shield(rules):
    """シールド1枚では2枚払えないため、諮問自体が起きず破壊される。"""
    e = setup(rules, {"bz": ["T796", "T002"], "shield": ["T001"]},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T002"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T002" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 1
    assert "choose_replacement" not in drv.seen


def test_796_moved_shields_cannot_strigger(rules):
    """手札に戻したシールドは「S・トリガー」を使えない（strigger: "off"）。"""
    e = setup(rules, {"bz": ["T796", "T002"],
                      "shield": ["T207", "T207", "T001", "T001", "T001"]},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    t207s = [c for c in e.zlist("shield", 0) if e.cdef(c).id == "T207"]
    assert len(t207s) == 2

    def choose(ev, d):
        hit = [i for i, o in enumerate(d["options"]) if o["cid"] in t207s]
        if hit:
            return hit[:d.get("min", 0)]
        for i, o in enumerate(d["options"]):
            if ev.cdef(o["cid"]).id == "T002":
                return [i]
        return None

    drv = _Driver(play=_play_once("play:T056"), choose=choose)
    drv.run(e, lambda ev: "T002" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 3 and _quiet(ev))
    assert _defns(e, "hand", 0).count("T207") == 2
    assert "declare_strigger" not in drv.seen


def test_796_mass_destroy_saves_both(rules):
    """全体破壊: 発生源と味方の両方が諮問され、2枚ずつ払って両方残る。

    同時離脱では置換の諮問が全件ぶん instead の支払いより先に済む
    （capture 相。第277弾の観察と同じエンジン構造）ため、if の枚数判定は
    諮問時点の枚数で読まれる。本テストの範囲（2体・5枚）では逐次処理と
    結果は一致する。"""
    e = setup(rules, {"bz": ["T796", "T002"]}, {"hand": ["T500"], "mana": ["T500"] * 5})
    drv = _Driver(play=_play_once("play:T500"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 1 and _quiet(ev))
    assert "T796" in _defns(e, "bz", 0) and "T002" in _defns(e, "bz", 0)
    assert not _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 1
    assert drv.seen.count("choose_replacement") == 2


# ---------- 実挙動: T797（他者・各ターン一度・1枚） ----------

def test_797_protects_ally_with_one_shield(rules):
    """味方が破壊される時、シールド1つを手札に加えて味方が残る。"""
    e = setup(rules, {"bz": ["T797", "T002"]}, {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T002"))
    drv.run(e, lambda ev: "T002" in _defns(ev, "bz", 0)
            and len(ev.zlist("shield", 0)) == 4 and _quiet(ev))
    assert "T002" in _defns(e, "bz", 0)
    assert "T002" not in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == 4
    assert drv.seen.count("choose_replacement") == 1


def test_797_does_not_protect_self(rules):
    """「自分の他のクリーチャー」: 発生源自身が離れる時は諮問されない。"""
    e = setup(rules, {"bz": ["T797"]}, {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_once("play:T056"))
    drv.run(e, lambda ev: "T797" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T797" in _defns(e, "graveyard", 0)
    assert "choose_replacement" not in drv.seen


def test_797_once_per_turn(rules):
    """各ターンに一度: 同じターンに2体目が離れる時は諮問されない。"""
    e = setup(rules, {"bz": ["T797", "T002", "T004"]},
              {"hand": ["T056", "T056"], "mana": ["T056"] * 6})
    drv = _Driver(play=_play_times("play:T056", 2),
                  choose=_choose_targets("T002", "T004"))
    drv.run(e, lambda ev: len(_defns(ev, "graveyard", 0)) == 1 and _quiet(ev))
    # 1体は守られ（シールド5→4）、もう1体は破壊される
    assert len(_defns(e, "bz", 0)) == 2
    assert len(_defns(e, "graveyard", 0)) == 1
    assert len(e.zlist("shield", 0)) == 4
    assert drv.seen.count("choose_replacement") == 1
