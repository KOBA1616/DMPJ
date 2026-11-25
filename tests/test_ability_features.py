"""拡張可能特徴量（dmsim/ai/ability_features.py）のテスト。

- スキーマ: 決定性・名前一意性・レジストリ網羅
- 末尾追加のみ: 語彙へ偽プリミティブを足しても旧スキーマが
  接頭辞として保たれ、既存カードのベクトルの接頭辞も一致する
- 形状: ブロック列／プーリング済みベクトル／全カード行列
- その他枠: 未知プリミティブが黙って落ちず other として数わる
- 判別可能性: 条件付き無料詠唱・cast_limit・置換・no_leave を
  持つ実カードで、特徴が中身を区別できること
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.ai import ability_features as AF  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.cards import defs as card_defs  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _full_cards():
    # conftest の DMSIM_SKIP_CONVERTED=1 を rules 読込より先に外す
    import os
    saved = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    yield
    if saved is not None:
        os.environ["DMSIM_SKIP_CONVERTED"] = saved


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture(scope="module")
def schema(rules):
    return AF.default_schema(rules)


@pytest.fixture(scope="module")
def voc(schema):
    return AF._voc_of(schema)


def _blocks(rules, voc, defn):
    return AF._card_blocks_as_dicts(rules.cards[defn], voc)


def _find_block(blocks, key):
    for b in blocks:
        if b.get(key):
            return b
    return None


# ------------------------------------------------------------------
# スキーマ
# ------------------------------------------------------------------
def test_schema_deterministic_and_unique(rules, schema):
    again = AF.default_schema(rules)
    assert again.block_names == schema.block_names
    assert again.card_names == schema.card_names
    assert len(set(schema.block_names)) == len(schema.block_names)
    assert len(set(schema.card_names)) == len(schema.card_names)
    assert schema.block_dim > 1000
    assert schema.card_dim == len(schema.card_names)


def test_registry_covers_defs_constants(rules):
    voc = AF.current_vocabularies(rules)
    assert set(card_defs.ABILITY_KINDS) <= set(voc["kind"])
    assert set(card_defs.TURN_COUNT_KINDS) <= set(voc["tc_kind"])
    assert set(card_defs.SELECTOR_KEYS) <= set(voc["selector_key"])
    assert set(card_defs.FILTER_KEYS) <= set(voc["filter_key"])
    assert set(card_defs.MOD_KEYS) <= set(voc["mod_key"])
    from dmsim.base.opvocab import OP_ARGS
    _zones, _keywords, macros, _actions, _steps = \
        card_defs.load_tables()
    ops = set(OP_ARGS) | set(macros)
    assert ops <= set(voc["op"])
    events = {e for e in card_defs.EVENTS if e != "any"}
    assert events <= set(voc["event"])


def test_append_only_schema(rules, schema):
    """語彙が増えても旧スキーマは接頭辞のまま保たれる。"""
    voc = AF.current_vocabularies(rules)
    ext = {g: list(v) for g, v in voc.items()}
    ext["kind"] = ext["kind"] + ["zz_fake_kind"]
    ext["op"] = ext["op"] + ["zz_fake_op"]
    ext["tc_kind"] = ext["tc_kind"] + ["zz_fake_tc"]
    ext["mod_key"] = ext["mod_key"] + ["zz_fake_mod"]
    new = AF.FeatureSchema(ext)
    assert new.block_names[:len(schema.block_names)] \
        == schema.block_names
    assert new.card_names[:len(schema.card_names)] == schema.card_names
    # 既存カードのベクトルも接頭辞が一致する（新特徴は末尾だけ）
    cd = rules.cards["dm38-014"]
    old_v = AF.card_vector(cd, schema)
    new_v = AF.card_vector(cd, new)
    assert new_v.shape[0] > old_v.shape[0]
    np.testing.assert_allclose(new_v[:old_v.shape[0]], old_v)
    old_b = AF.card_ability_blocks(cd, schema)
    new_b = AF.card_ability_blocks(cd, new)
    np.testing.assert_allclose(
        new_b[:, :old_b.shape[1]], old_b)


# ------------------------------------------------------------------
# 形状と行列
# ------------------------------------------------------------------
def test_shapes(rules, schema, voc):
    cd = rules.cards["dm38-014"]
    blocks = AF.card_ability_blocks(cd, schema)
    assert blocks.ndim == 2 and blocks.shape[1] == schema.block_dim
    assert blocks.shape[0] == len(_blocks(rules, voc, "dm38-014"))
    v = AF.card_vector(cd, schema)
    assert v.shape == (schema.card_dim,)
    assert np.isfinite(v).all()


def test_matrix(rules, schema):
    vocab = Vocab(rules)
    mat, names, version = AF.build_card_matrix(rules, vocab, schema)
    assert mat.shape == (len(vocab), schema.card_dim)
    assert names == schema.card_names
    assert version == schema.version
    assert np.all(mat[0] == 0)  # PAD 行
    assert np.isfinite(mat).all()
    assert (mat[1:] != 0).any(axis=1).all()  # 全カードに特徴がある


def test_emitted_keys_within_schema(rules, schema, voc):
    names = set(schema.card_names)
    sample = list(rules.cards.values())[::37]  # 約300枚を抽出
    for cd in sample:
        extra = set(AF._card_as_dict(cd, voc)) - names
        assert not extra, f"{cd.defn}: {sorted(extra)[:5]}"


# ------------------------------------------------------------------
# その他枠
# ------------------------------------------------------------------
def test_unknown_primitives_fall_into_other(voc):
    face = SimpleNamespace(
        abilities=[{
            "kind": "zz_unknown_kind",
            "when": {"event": "zz_unknown_event"},
            "effect": [{"op": "zz_unknown_op"}],
            "mod": {"zz_unknown_mod": True},
        }],
        keywords=[], types=["creature"], civs=["fire"],
        cost=5, power=5000, races=[])
    cd = SimpleNamespace(faces=[face], types=["creature"],
                         civs=["fire"], mana=1)
    blocks = AF._card_blocks_as_dicts(cd, voc)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.get("ab.kind.other")
    assert b.get("ab.when.event.other")
    assert b.get("ab.fx.op.other")
    assert b.get("ab.mod.key.other")


# ------------------------------------------------------------------
# 判別可能性
# ------------------------------------------------------------------
def test_discriminate_turn_end_free_cast(rules, voc):
    """(a) 相手ターン終了時誘発＋履歴カウンタ条件＋条件付き無料詠唱。"""
    kuma = _find_block(_blocks(rules, voc, "dm38-014"),
                       "ab.when.event.turn_end")
    assert kuma is not None
    # 条件: 相手がこのターン3体以上出した（turn_count enter/opp, >=, 3）
    assert kuma.get("ab.if.tc.enter")
    assert kuma.get("ab.if.tc_owner.opp")
    assert kuma.get("ab.if.cmp.ge")
    assert kuma.get("ab.if.num.3")
    # 効果: 無料で唱える/出す（may + play_free）、手札から
    assert kuma.get("ab.fx.op.play_free")
    assert kuma.get("ab.zone.hand")
    # 似た輪郭（ターン終了時誘発＋turn_count 条件）だが中身が違う
    turtle = _find_block(_blocks(rules, voc, "dmrp01-s02"),
                         "ab.when.event.turn_end")
    assert turtle is not None
    assert turtle.get("ab.if.tc.attack")       # 攻撃回数の条件
    assert turtle.get("ab.if.cmp.eq")
    assert turtle.get("ab.if.num.0")
    assert not turtle.get("ab.fx.op.play_free")  # 無料詠唱ではない
    assert turtle.get("ab.fx.op.tap")            # 効果は全タップ


def test_discriminate_cast_limit(rules, voc):
    """(b) cast_limit を持つ常在効果は上限値まで区別できる。"""
    blocks = _blocks(rules, voc, "dm26ex4-cho005")
    blk = _find_block(blocks, "ab.key.cast_limit")
    assert blk is not None
    assert blk.get("ab.kind.static")
    assert blk.get("ab.limit.cast_limit.1")  # 次の相手ターンは1体まで


def test_discriminate_replace_to_mana(rules, voc):
    """(c) 「場に出る代わりにマナ」と「破壊される代わりにマナ」。"""
    toko = _find_block(_blocks(rules, voc, "dm26sd1-q013"),
                       "ab.kind.replace")
    assert toko is not None
    assert toko.get("ab.ins.move_to.mana")        # 置換先はマナ
    assert toko.get("ab.when.to.bz")              # 場に出る移動が対象
    assert toko.get("ab.when.subj.owner.opp")     # 相手のカード
    assert toko.get("ab.when.from.graveyard")
    assert not toko.get("ab.when.reason.destroy")
    broc = _find_block(_blocks(rules, voc, "dm10-035"),
                       "ab.kind.replace")
    assert broc is not None
    assert broc.get("ab.ins.move_to.mana")        # 置換先は同じくマナ
    assert broc.get("ab.when.reason.destroy")     # だが文脈は破壊
    assert broc.get("ab.when.from.bz")
    assert not broc.get("ab.when.to.bz")


def test_discriminate_no_leave(rules, voc):
    """(d) no_leave（破壊以外で離れない）を持つ常在効果。"""
    blocks = _blocks(rules, voc, "dm22rp1-010")
    blk = _find_block(blocks, "ab.mod.key.no_leave")
    assert blk is not None
    assert blk.get("ab.mod.no_leave.except_destroy")
    assert blk.get("ab.kind.static")
