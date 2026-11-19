"""第246弾（続き）: cause.name_has — 名前に《武者》とある自分のカードの効果で相手が破壊された時の誘発。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def test_musha_caused_destroy_triggers():
    # P0: T668（大和）＋手札に武者バーン、マナ3。P1: T002×2（パワー1000）
    e = setup(_rules(), {"bz": ["T668"], "hand": ["T669"], "mana": ["T060"] * 3},
              {"bz": ["T002", "T002"]})
    victims = [c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T002"]
    assert len(victims) == 2
    for _ in range(200):
        if all(v in e.zlist("graveyard", 1) for v in victims):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        play = next((i for i, k in enumerate(keys) if k == "play:T669"), None)
        if d["kind"] == "main" and play is not None:
            e.answer([play])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    # 呪文で1体、誘発でもう1体が破壊される
    assert all(v in e.zlist("graveyard", 1) for v in victims)


def test_non_musha_destroy_does_not_trigger():
    # T006（S・トリガー火呪文、名前なし）は cause.name_has に一致しない
    e = setup(_rules(), {"bz": ["T668"], "hand": ["T006"], "mana": ["T060"] * 3},
              {"bz": ["T002", "T002"]})
    victims = [c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T002"]
    for _ in range(200):
        if any(v in e.zlist("graveyard", 1) for v in victims) and \
                any(e.s.cards[c].defn == "T006" for c in e.zlist("graveyard", 0)):
            # 呪文解決後しばらく進めても誘発で2体目は落ちないことを確認するため数手進める
            for _ in range(6):
                d = e.advance()
                if d is None:
                    break
                keys = [o["key"] for o in d["options"]]
                if "pass" in keys:
                    e.answer([keys.index("pass")])
                elif "no_block" in keys:
                    e.answer([keys.index("no_block")])
                else:
                    e.answer(list(range(d.get("min", 0))))
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        play = next((i for i, k in enumerate(keys) if k == "play:T006"), None)
        if d["kind"] == "main" and play is not None:
            e.answer([play])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    dead = [v for v in victims if v in e.zlist("graveyard", 1)]
    assert len(dead) == 1   # 呪文で落ちた1体だけ。誘発は起きない
