"""第2段・小パイロットその1: unpaid 潜在バグ修正（move レコードへの unpaid 複写）。

- 症状: イベント（ev）の unpaid は実行側で立てられていた（turn.py の h_play が
  「free かつ as_paid でない」時に付け、ops.py の summon_on 等も付ける）が、
  _apply_one が作る move の収集レコードと、置換照合用の _record_for のレコードに
  複写されていなかった。そのため when {event: move, unpaid: true} の誘発
  （登録済み dm26rp1-038、dm26ex2-041 極限龍神ヘヴィ等）がすべて不発だった
  （ラウンド187の精査で実証）。summon レコードには従来から unpaid が載っていたため、
  「召喚した時」形の照合だけが動き、move 形が死んでいた。
- 修正: events.py の _record_for / _apply_one で、via・alt・vivid と同じ並びで
  ev の unpaid をレコードへ複写する（立っている時だけ True を載せる従来形式。
  照合は _match_when の既存の unpaid 分岐が bool で見る）。
- 発火の観測はエンジンの trace（解決された誘発の因果記録）で T206 の解決回数を数える。
- proto は第155弾が T205 まで使ったため、本一連（unpaid／unblocked／bundles）で T206〜T212 を使う。
  T206 が番人（自分の無償召喚を観測する形）、T207 が S・トリガー持ちの試験兵。
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _setup(*args, **kwargs):
    e = setup(*args, **kwargs)
    e.s.trace = []      # 誘発の因果記録を有効にする（発火回数の実測用）
    return e


def _fires(e, defn):
    return Counter(t["src"] for t in e.s.trace if t["ev"] == "move")[defn]


def _settle(e, done, drive=None, max_steps=300):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive and drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def _flush(e, steps=60):
    """待機中の誘発が解決しきるまでだけ進める（ターンを進めない）。"""
    for _ in range(steps):
        if not e.s.pending:
            return
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))


def _play_drive(want_key):
    def drive(e, d, keys):
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == want_key]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    return drive


def test_proto_parse(rr):
    """T206／T207 が parse でき、unpaid の when が検証を通る。"""
    for cid in ("T206", "T207"):
        parse_card(_proto_card(cid), TABLES)
    card = next(c for c in rr.cards.values() if c.id == "T206")
    assert card.face(None).abilities[0]["when"]["unpaid"] is True


def test_unpaid_move_trigger_fires_on_strigger_summon(rr):
    """判別: S・トリガーでコストを支払わずに出たクリーチャーは unpaid の move になり、
    番人 T206 の「コストを支払わずに出した時」が誘発する。
    （修正前は move レコードに unpaid が無く、この誘発は絶対に発火しなかった）"""
    e = _setup(rr, {"bz": ["T001"]},
               {"bz": ["T206"], "shield": ["T207", "T001", "T001", "T001", "T001"]})

    def drive(e, d, keys):
        if d["kind"] == "attack":
            e.answer([keys.index("attack:T001:player")])
            return True
        if d["kind"] == "choose_shields":
            idx = next(i for i, c in enumerate(e.zlist("shield", 1)) if e.s.cards[c].defn == "T207")
            e.answer([idx])   # T207 のシールドをブレイクする
            return True
        if d["kind"] == "declare_strigger":
            e.answer([keys.index("strigger:T207")])
            return True
        if d["kind"] == "block":
            e.answer([keys.index("no_block")])
            return True
        return False

    # 相手（P1）の最初のチャージ判断が出るまで＝P0 のターンが終わるまで進める
    for _ in range(300):
        d = e.advance()
        if d is None or (d["player"] == 1 and d["kind"] == "charge"):
            break
        keys = [o["key"] for o in d["options"]]
        if not drive(e, d, keys):
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert any(e.s.cards[c].defn == "T207" for c in e.zlist("bz", 1))   # S・トリガーで出た
    assert _fires(e, "T206") == 1                                       # 番人が1回誘発した
    assert len(e.zlist("hand", 1)) == 2   # 番人の引き1枚＋ターン開始のドロー1枚


def test_paid_summon_does_not_fire(rr):
    """通常の支払い召喚では unpaid 誘発は発火しない（出した分だけ手札が減り、引かない）。"""
    e = _setup(rr, {"bz": ["T206"], "hand": ["T207"], "mana": ["T004"] * 6}, {})
    done = lambda: any(e.s.cards[c].defn == "T207" for c in e.zlist("bz", 0))
    assert _settle(e, done, _play_drive("play:T207"))
    _flush(e)
    assert _fires(e, "T206") == 0
    assert len(e.zlist("hand", 0)) == 0


def test_existing_move_trigger_unaffected(rr):
    """回帰: unpaid でない通常の move 誘発（T002 の出た時マナ加速）は従来どおり発火する。"""
    e = _setup(rr, {"hand": ["T002"], "mana": ["T001", "T001"]}, {})
    done = lambda: any(e.s.cards[c].defn == "T002" for c in e.zlist("bz", 0))
    assert _settle(e, done, _play_drive("play:T002"))
    _flush(e)
    assert len(e.zlist("mana", 0)) == 3   # 支払いの2枚＋CIP で山札から1枚
