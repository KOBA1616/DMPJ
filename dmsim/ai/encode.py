"""局面と選択肢のエンコーダ（Phase 4）。

カード1枚＝1トークン（ポケカABC上位の共通形）。トークンは定義IDの埋め込みと
数値特徴（コスト・パワー・タップ状態など）を持ち、ゾーン単位でプーリングして
局面ベクトルを作る。判断するプレイヤー視点で、秘匿情報（相手の手札・山札・
シールドの中身）は枚数だけを全体特徴に入れ、中身はトークン化しない。

encode_state(eng, player) -> {
  "tok_defn": np.int32[T]      定義ID（Vocab の添字、0 は PAD/未知）
  "tok_num":  np.float32[T, TOK_NUM]  トークン数値特徴
  "tok_zone": np.int32[T]      ゾーン区分（プーリング用）
  "glob":     np.float32[GLOB]
}
encode_options(eng, state_enc, decision) -> {
  "opt_defn": np.int32[O]      選択肢が参照する札の定義ID（複数は先頭、無い場合は 0）
  "opt_num":  np.float32[O, OPT_NUM]
  "grp":      np.int32[O]      等価グループ id（意味キーが同じ選択肢は同値、Phase 26）
  "min": int, "max": int, "kind": str
}
"""
from __future__ import annotations

import numpy as np

# ゾーン区分（プーリングの単位）: 自分/相手 × 公開ゾーン＋自分の手札
ZONES = ["my_bz", "my_mana", "my_grave", "my_hand", "my_shield",
         "op_bz", "op_mana", "op_grave", "op_hand", "op_shield"]
ZONE_IDX = {z: i for i, z in enumerate(ZONES)}
# トークン数値特徴: [cost, power, tapped, is_creature, is_spell, civ数, 下敷き数, ゾーン内位置]
TOK_NUM = 8
# 選択肢数値特徴: [動詞ハッシュ帯, cid有無, 参照札数, 位置, 参照札の平均cost, 平均power]
OPT_NUM = 6
# 全体特徴: [turn, 自分が手番か, 自分のマナ数, 相手のマナ数, 自分のシールド数, 相手のシールド数,
#            自分の手札数, 相手の手札数, 自分の山札数, 相手の山札数, 自分の墓地数, 相手の墓地数]
GLOB = 12

_VERBS = ["charge", "play", "attack", "block", "pass", "yes", "no", "mana",
          "shield", "deck", "bz", "graveyard", "hand", "no_block", "decline"]


class Vocab:
    """定義ID → 添字。0 は PAD/未知に予約。"""

    def __init__(self, rules):
        self.ids = sorted(rules.cards.keys())
        self.index = {d: i + 1 for i, d in enumerate(self.ids)}
        # 定義ごとの静的数値特徴 [cost, power, is_creature, is_spell, civ数]
        self.static = np.zeros((len(self.ids) + 1, 5), dtype=np.float32)
        for d, i in self.index.items():
            cd = rules.cards[d]
            self.static[i] = [
                (getattr(cd, "cost", 0) or 0) / 10.0,
                (getattr(cd, "power", 0) or 0) / 10000.0,
                # Phase 7 で発見したバグ修正: 以前は getattr(cd, "is_creature") が
                # メソッドオブジェクト（常に真）を返し、全カードで 1.0 になっていた。
                1.0 if "creature" in (getattr(cd, "types", None) or []) else 0.0,
                1.0 if "spell" in (getattr(cd, "types", None) or []) else 0.0,
                len(getattr(cd, "civs", None) or []) / 2.0,
            ]

    def __len__(self):
        return len(self.ids) + 1

    def idx(self, defn):
        return self.index.get(defn, 0)


def _zone_key(zone: str, owner: int, me: int) -> str | None:
    side = "my" if owner == me else "op"
    if zone == "bz":
        return f"{side}_bz"
    if zone == "mana":
        return f"{side}_mana"
    if zone == "graveyard":
        return f"{side}_grave"
    if zone == "hand":
        return f"{side}_hand"
    if zone == "shield":
        return f"{side}_shield"
    return None


def encode_state(eng, player: int, vocab: Vocab) -> dict:
    s = eng.s
    me, op = player, 1 - player
    tok_defn: list[int] = []
    tok_num: list[list[float]] = []
    tok_zone: list[int] = []

    def add(cid: int, zkey: str, pos: int, hidden: bool):
        c = s.cards[cid]
        st = vocab.static[vocab.idx(c.defn)]
        tok_defn.append(0 if hidden else vocab.idx(c.defn))
        tok_num.append([
            0.0 if hidden else float(st[0]),
            0.0 if hidden else float(st[1]),
            1.0 if c.tapped else 0.0,
            0.0 if hidden else float(st[2]),
            0.0 if hidden else float(st[3]),
            0.0 if hidden else float(st[4]),
            len(c.under) / 4.0,
            pos / 10.0,
        ])
        tok_zone.append(ZONE_IDX[zkey])

    for zone in ("bz", "mana", "graveyard", "hand", "shield"):
        for p in (me, op):
            zkey = _zone_key(zone, p, me)
            cids = s.zones[zone][p] if zone in s.zones else []
            # 秘匿: 相手の手札と両者のシールドの中身は見せない（枚数は glob へ）
            hidden = (zone == "shield") or (zone == "hand" and p != me)
            for pos, cid in enumerate(cids):
                if zone == "hand" and p != me:
                    continue  # 相手の手札はトークン化しない
                add(cid, zkey, pos, hidden)

    def zlen(zone, p):
        return len(s.zones[zone][p]) if zone in s.zones else 0

    glob = np.array([
        s.turn / 20.0,
        1.0 if s.active == me else 0.0,
        zlen("mana", me) / 10.0, zlen("mana", op) / 10.0,
        zlen("shield", me) / 5.0, zlen("shield", op) / 5.0,
        zlen("hand", me) / 10.0, zlen("hand", op) / 10.0,
        zlen("deck", me) / 40.0, zlen("deck", op) / 40.0,
        zlen("graveyard", me) / 20.0, zlen("graveyard", op) / 20.0,
    ], dtype=np.float32)
    return {
        "tok_defn": np.asarray(tok_defn, dtype=np.int32),
        "tok_num": np.asarray(tok_num, dtype=np.float32).reshape(-1, TOK_NUM),
        "tok_zone": np.asarray(tok_zone, dtype=np.int32),
        "glob": glob,
    }


def option_groups(keys) -> np.ndarray:
    """選択肢の意味キー列 → 等価グループ id 列（初出順に 0,1,2,... と採番）。

    等価性の定義は tools/dup_rate.py と同じ「エンジンが付ける option の
    "key" が一致する」こと。そのキーの選択肢同士はエンジンの再生機構が
    同じ手とみなす（盤面上の結果が同一）。
    """
    seen: dict[str, int] = {}
    grp = np.empty(len(keys), dtype=np.int32)
    for i, k in enumerate(keys):
        if k not in seen:
            seen[k] = len(seen)
        grp[i] = seen[k]
    return grp


def _verb_band(key: str) -> float:
    head = key.split(":")[0]
    return (_VERBS.index(head) if head in _VERBS else len(_VERBS)) / len(_VERBS)


def encode_options(eng, decision: dict, vocab: Vocab) -> dict:
    s = eng.s
    opts = decision["options"]
    opt_defn = np.zeros(len(opts), dtype=np.int32)
    opt_num = np.zeros((len(opts), OPT_NUM), dtype=np.float32)
    for i, o in enumerate(opts):
        cids = []
        if "cid" in o:
            cids = [o["cid"]]
        elif "cids" in o:
            cids = list(o["cids"])
        defs = [s.cards[c].defn for c in cids if 0 <= c < len(s.cards)]
        if defs:
            opt_defn[i] = vocab.idx(defs[0])
            st = np.stack([vocab.static[vocab.idx(d)] for d in defs]).mean(axis=0)
            avg_cost, avg_pow = float(st[0]), float(st[1])
        else:
            avg_cost = avg_pow = 0.0
        opt_num[i] = [_verb_band(o.get("key", "")), 1.0 if cids else 0.0,
                      len(cids) / 4.0, i / 10.0, avg_cost, avg_pow]
    return {
        "opt_defn": opt_defn,
        "opt_num": opt_num,
        # キーが無い選択肢は他と衝突しない一意なキーで単独グループにする
        "grp": option_groups([o["key"] if "key" in o else f"\x00{i}"
                              for i, o in enumerate(opts)]),
        "min": int(decision["min"]), "max": int(decision["max"]),
        "kind": decision["kind"],
    }
