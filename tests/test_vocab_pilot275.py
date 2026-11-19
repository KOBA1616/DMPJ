"""語彙パイロット第275弾: attack_specific_target（選んだ特定のクリーチャーへの攻撃許可）。

rejects の attack_specific_target 4行のうち3行は同一形:
「相手のタップされていない（アンタップしている）クリーチャーを1体選ぶ。このターン、
自分のクリーチャーはすべて（dmrp06-080 は「自分の他のクリーチャー」）、その
クリーチャーを攻撃できる」（dmr09-102 呪文 / dmr14-050 CIP / dmrp06-080 CIP）。
残る dmrp08-058 は「可能ならパワー2222以下のクリーチャーを攻撃する」という
攻撃強制のフィルタ形で、別ギャップ（must_attack_creature の other フィルタ形）として残す。

新語彙:
- allow / deny 項目の新キー `only: {var: 名前}`。継続的効果の生成時に op_modify の
  _bake_only で束縛変数の参照列へベイクされ、その項目は対象がその列にある時だけ当たる
  （_bake_refs の {var:} は束縛した枚数を返す数式なので、参照そのものは別経路で焼く）。
  使い方: choose で対象を束縛 → modify で
  {allow: [{action: attack_creature, other: {tapped: false}, only: {var: tgt}}]}
  を自分のクリーチャー全員に duration: end_of_turn で与える。
  マッハファイター形（other: {tapped: false} のみ）は従来どおり無条件に当たる。
- 照合は2か所: combat._attack_options のアンタップ攻撃可否と、core.permits の hit。
  判定は core._only_ok に集約した。未ベイク（{var:...} の辞書のまま、常在型に
  書かれた場合など）・対象なしでは当たらない。

Rust は modify の mod {allow: [...]} を単純形に含めない（_simple_effect）ため、
この形を持つカードを含む対局は Python にフォールバックする。新しい GameState
フィールドは無い（state.rs の変更なし）。
"""
import pytest
from tests.conftest import setup
from tests._conv_cache import proto_card

from dmsim.cards.defs import DefError, load_tables, parse_card
from dmsim.engine.rustcore import _simple_effect

TABLES = load_tables()


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, zone, p, defn):
    cids = e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)
    return next(c for c in cids if e.cdef(c).id == defn)


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第271弾のものを流用）。

    choose_defn: choose_cards ではその defn のカードを選ぶ。
    attack_key: 自分（player 0）の攻撃決定でそのキーを一度だけ選ぶ。
    attack_log: (turn, player, keys) を全攻撃決定について記録する。
    """

    def __init__(self, play=None, choose_defn=None, attack_key=None):
        self.play = play
        self.choose_defn = choose_defn
        self.attack_key = attack_key
        self.attack_used = False
        self.attack_log = []

    def run(self, e, stop, limit=800):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            if kind == "choose_cards" and self.choose_defn is not None:
                hit = [i for i, o in enumerate(d["options"])
                       if e.cdef(o["cid"]).id == self.choose_defn]
                if hit:
                    e.answer(hit[:1])
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
            if kind == "attack":
                self.attack_log.append((e.s.turn, d["player"], list(keys)))
                if (d["player"] == 0 and self.attack_key is not None
                        and not self.attack_used and self.attack_key in keys):
                    self.attack_used = True
                    e.answer([keys.index(self.attack_key)])
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


def _play_once(key):
    seen = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None

    return play


def test_pilot275_protos_parse():
    for tid in ("T776", "T777", "T778", "T779"):
        parse_card(proto_card(tid), TABLES)


def test_pilot275_only_validation():
    base = {"id": "X275", "name": "検証用", "types": ["creature"], "civs": ["fire"],
            "cost": 2, "power": 1000,
            "abilities": [{"kind": "static", "affects": "self",
                           "mod": {"allow": [{"action": "attack_creature",
                                              "other": {"tapped": False},
                                              "only": {"var": "tgt"}}]}}]}
    parse_card(base, TABLES)   # {var: 名前} 形は通る
    for bad in ("tgt", {"ref": "tgt"}, {"var": 3}, {}):
        raw = dict(base)
        raw["abilities"] = [{"kind": "static", "affects": "self",
                             "mod": {"allow": [{"action": "attack_creature",
                                                "other": {"tapped": False},
                                                "only": bad}]}}]
        try:
            parse_card(raw, TABLES)
            raise AssertionError(f"only={bad!r} が通ってしまった")
        except DefError:
            pass


def test_pilot275_not_rust_simple():
    assert not _simple_effect(proto_card("T776")["spell"])


def test_no_grant_untapped_not_attackable(rules):
    """対照: 付与が無ければ、アンタップしている相手クリーチャーは攻撃できない。"""
    e = setup(rules, {"bz": ["T779"]}, {"bz": ["T001", "T004"]})
    drv = _Driver()
    drv.run(e, lambda ev: any(t == 1 and p == 0 for t, p, _ in drv.attack_log))
    keys = next(k for t, p, k in drv.attack_log if t == 1 and p == 0)
    assert "attack:T779:player" in keys
    assert "attack:T779:T001" not in keys
    assert "attack:T779:T004" not in keys


def test_spell_grants_attack_on_chosen_untapped(rules):
    """T776（dmr09-102 形）: 選んだ T001 だけが攻撃でき、他のアンタップ T004 は不可。
    実際に攻撃するとバトルが起きる（5000 vs 2000 で T001 が破壊される）。"""
    e = setup(rules, {"hand": ["T776"], "mana": ["T034", "T001"], "bz": ["T779"]},
              {"bz": ["T001", "T004"]})
    drv = _Driver(play=_play_once("play:T776"), choose_defn="T001",
                  attack_key="attack:T779:T001")
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    keys = next(k for t, p, k in drv.attack_log if t == 1 and p == 0)
    assert "attack:T779:T001" in keys        # 選んだクリーチャーは攻撃できる
    assert "attack:T779:T004" not in keys    # 他のアンタップは攻撃できないまま
    assert "T001" in _defns(e, "graveyard", 1)
    assert "T779" in _defns(e, "bz", 0)


def test_grant_expires_next_turn(rules):
    """付与はそのターンだけ: 次の自分のターンには T001 を攻撃できない。"""
    e = setup(rules, {"hand": ["T776"], "mana": ["T034", "T001"], "bz": ["T779"]},
              {"bz": ["T001", "T004"]})
    drv = _Driver(play=_play_once("play:T776"), choose_defn="T001")
    drv.run(e, lambda ev: any(t == 3 and p == 0 for t, p, _ in drv.attack_log))
    k1 = next(k for t, p, k in drv.attack_log if t == 1 and p == 0)
    k3 = next(k for t, p, k in drv.attack_log if t == 3 and p == 0)
    assert "attack:T779:T001" in k1
    assert "attack:T779:T001" not in k3
    assert "attack:T779:player" in k3


def test_cip_grants_attack_on_chosen_untapped(rules):
    """T777（dmr14-050 形）: CIP で同じ付与（自分のクリーチャーすべて）。"""
    e = setup(rules, {"hand": ["T777"], "mana": ["T034", "T001"], "bz": ["T779"]},
              {"bz": ["T001", "T004"]})
    drv = _Driver(play=_play_once("play:T777"), choose_defn="T001",
                  attack_key="attack:T779:T001")
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    keys = next(k for t, p, k in drv.attack_log if t == 1 and p == 0)
    assert "attack:T779:T001" in keys
    assert "attack:T779:T004" not in keys
    assert "T001" in _defns(e, "graveyard", 1)
    assert "T779" in _defns(e, "bz", 0)


def test_cip_grant_excludes_self(rules):
    """T778（dmrp06-080 形）: 付与は「自分の他のクリーチャー」だけ。
    継続的効果の affected と特性の allow の両方で、発生源自身が外れていることを見る。"""
    e = setup(rules, {"hand": ["T778"], "mana": ["T034", "T034", "T001", "T001"],
                      "bz": ["T779"]},
              {"bz": ["T001", "T004"]})
    drv = _Driver(play=_play_once("play:T778"), choose_defn="T001",
                  attack_key="attack:T779:T001")

    def granted(ev):
        return any(isinstance(x, dict) and "only" in x
                   for ce in ev.s.continuous for x in ce["mod"].get("allow", []))

    drv.run(e, granted)
    t001 = _cid(e, "bz", 1, "T001")
    t778 = _cid(e, "bz", 0, "T778")
    t779 = _cid(e, "bz", 0, "T779")
    ce = next(ce for ce in e.s.continuous
              if any(isinstance(x, dict) and "only" in x for x in ce["mod"].get("allow", [])))
    assert [t779, e.s.cards[t779].gen] in ce["affected"]       # 他のクリーチャーは対象
    assert [t778, e.s.cards[t778].gen] not in ce["affected"]   # 発生源自身は対象外
    baked = next(x["only"] for x in ce["mod"]["allow"] if isinstance(x, dict) and "only" in x)
    assert baked == [[t001, e.s.cards[t001].gen]]              # 選んだ T001 にベイク済み
    allow779 = [x for x in e.chars_ro(t779)["allow"] if isinstance(x, dict) and "only" in x]
    allow778 = [x for x in e.chars_ro(t778)["allow"] if isinstance(x, dict) and "only" in x]
    assert allow779 and not allow778
    # 実挙動: T779 は T001 を攻撃でき、バトルで破壊する
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 1)
    assert "T779" in _defns(e, "bz", 0)
