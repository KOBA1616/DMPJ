"""語彙パイロット第7弾（2026-10-31）の検証。

能力の `id` と mod の `ignore_ids`: 特定の能力だけを無視する（rejects: oni_time の
「真上の▪️能力を無視する」系）。変換では無視したい能力に id を付け、無視する側の
常在型が mod {ignore_ids: [...]} を持つ。種類単位の ignore（608.4）とは別に、
abilities() の収集時点で id 一致の能力を落とす。
"""
from conftest import setup


def test_ignore_ids_lifts_disadvantage_when_oni_time(rules):
    """シールド合計7以上では「攻撃できない」が効き、6以下では無視されて攻撃できる。"""
    e = setup(rules, {"bz": ["T041"], "shield": ["T001"] * 4}, {"shield": ["T001"] * 4})
    cid = e.bz_tops(0)[0]
    assert "attack_player" in e.chars(cid)["deny"]            # 合計8: デメリットが有効
    e = setup(rules, {"bz": ["T041"], "shield": ["T001"] * 3}, {"shield": ["T001"] * 3})
    cid = e.bz_tops(0)[0]
    assert "attack_player" not in e.chars(cid)["deny"]        # 合計6: 無視される
    # 実際に攻撃の選択肢にも現れる
    d = None
    for _ in range(30):
        d = e.advance()
        if d is None or d["kind"] == "attack":
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert d is not None and any(o["key"].startswith("attack:T041:") for o in d["options"])
