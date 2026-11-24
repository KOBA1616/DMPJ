"""Phase 8 の盤面指紋キャッシュの回帰: _mana_boost_sources のキャッシュ
ヒット時に、_mana_choices が前提とする _mac_defns がそのインスタンスに
用意されていないと AttributeError になる不具合（Phase 11 で発見・修正）。
シナリオ構築したエンジンの複製で探索すると踏む。"""
from pathlib import Path

import yaml

from dmsim.engine import scenario as sc


def test_mb_src_cache_hit_still_prepares_mac_defns(rules):
    spec = yaml.safe_load(
        (Path(__file__).parent / "saga_loop_first_setup.yaml")
        .read_text(encoding="utf-8"))
    eng = sc.build(rules, spec)
    eng._mana_boost_sources(0)                    # フレッシュ計算でキャッシュ登録
    clone = eng.clone()
    if hasattr(clone, "_mac_defns"):
        del clone._mac_defns                      # シナリオ構築直後の状態を再現
    clone._mana_boost_sources(0)                  # キャッシュヒットの経路
    assert hasattr(clone, "_mac_defns")
    assert hasattr(clone, "_mb_defns")
