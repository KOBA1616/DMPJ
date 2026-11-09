"""エンジン状態の読み取り専用アクセサ（疑似API v0.1 の `read` 系を Engine 直渡しで使うための薄い層）。

探索・評価・自動診断・発見は、GameState（eng.s）の中身を直接読まず、ここを通す。Rust 版エンジンへ差し替える時は、
この1ファイルの実装を差し替えるだけで済む（呼び出し側は変えない）。状態を変える操作はここに置かない（engine_api の apply / fork 等を使う）。
依存を持たない（循環 import を避けるため engine_api とは別ファイルにしてある。engine_api からも再公開する）。"""
from __future__ import annotations


def result_of(e):
    """終局なら {winner, reason, turn...}、そうでなければ None。"""
    return e.s.result


def active_of(e) -> int:
    return e.s.active


def turn_of(e) -> int:
    return e.s.turn


def pending_of(e) -> list:
    """待機中の誘発（読み取り専用として扱う）。"""
    return e.s.pending


def defn_of(e, cid) -> str:
    return e.s.cards[cid].defn


def tapped_of(e, cid) -> bool:
    return e.s.cards[cid].tapped


def zone_of(e, zone: str, p: int):
    """ゾーンの札 id の並び（読み取り専用として扱う。変更しない）。"""
    return e.s.zones[zone][p]


def defns_of(e, zone: str, p: int) -> list[str]:
    """ゾーンの札の定義 ID の並び。"""
    return [e.s.cards[c].defn for c in e.s.zones[zone][p]]


def digest_of(e) -> str:
    return e.s.digest()
