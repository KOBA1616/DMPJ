"""～地獄帰りの騎士～ と DARK MEMORY CONTAINER: 盾が置かれた時に墓地から出る。"""
from pathlib import Path

from conftest import setup
from dmsim.cardfiles import card_files
from dmsim.defs import DATA, load_rules

K, D = "dm25ex3-028", "dm25ex3-055"


def _small_rules(tmp_path):
    """converted.yaml（巨大）から2枚の記述だけ切り出し、実カード＋この2枚で規則を作る。"""
    import re
    text = (DATA / "cards" / "converted.yaml").read_text(encoding="utf-8")
    out = []
    for cid in (K, D):
        i = text.index(f"- id: {cid}\n")
        m = re.search(r"\n- id: ", text[i + 5:])
        out.append(text[i:i + 5 + m.start()] if m else text[i:])
    f = tmp_path / "two.yaml"
    f.write_text("cards:\n" + "\n".join("  " + ln if ln else ln for blk in out for ln in blk.splitlines()) + "\n", encoding="utf-8")
    return load_rules([x for x in card_files() if x.name != "converted.yaml" and x.parent.name != "converted"] + [f])


def test_knight_shield_pulls_dmc_from_graveyard(tmp_path):
    rules = _small_rules(tmp_path)
    e = setup(rules, {"hand": [K], "graveyard": [D], "mana": [D] * 3}, {"bz": ["T001"]}, deck_size=20)
    for _ in range(60):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and f"play:{K}" in keys:
            e.answer([keys.index(f"play:{K}")])
        elif d["kind"] == "yesno" or "yes" in keys:
            e.answer([keys.index("yes")])
        elif any(e.s.cards[c].defn == D for c in e.bz_tops(0)):
            break
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert any(e.s.cards[c].defn == D for c in e.bz_tops(0))
