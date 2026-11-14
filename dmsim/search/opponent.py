"""1人回しの相手役（妨害モデル）。既定（None）は solitaire.charge_only_policy で従来どおり何も妨げない。

OppModel は設定で切り替える:
- shields   開始時のシールド枚数（既定 5。山札との間でカードを動かす。足りない分は山札から、余りは手札へ）
- bz        開始時に戦闘ゾーンへ置くカードID（相手の山札から1枚ずつ。ブロッカー等の盤面妨害）
- block     攻撃に対してブロッカーでブロックする
- strigger  シールドが割れた時に S・トリガーを使う
- play      "none" 何も出さない / "blockers" ブロッカーだけ出す / "all" 使えるカードを出す（除去・手札破壊は山札の中身次第）
- attack    "none" 攻撃しない（既定） / "all" 攻撃できる体は全部プレイヤーを攻撃（速攻寄り）
            / "safe" 勝てるバトルならタップした体を攻撃、相手より体が多い時だけプレイヤーを攻撃（受け寄り）
マナチャージは常にする（ロック判定が相手の成長を見分けるため）。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..engine import Engine
from ..engine.play import passive_policy


@dataclass(frozen=True)
class OppModel:
    name: str = "custom"
    shields: int = 5
    bz: tuple = ()
    block: bool = False
    strigger: bool = False
    play: str = "none"
    attack: str = "none"

    def setup(self, eng: Engine, p: int = 1) -> None:
        """開始局面の調整（ゲーム準備用の移動。イベントは起きない）。"""
        s = eng.s
        while len(s.zones["shield"][p]) > self.shields:
            eng._raw_move(s.zones["shield"][p][0], "hand")
        while len(s.zones["shield"][p]) < self.shields and s.zones["deck"][p]:
            eng._raw_move(s.zones["deck"][p][0], "shield")
        for defn in self.bz:
            cid = next((c for c in s.zones["deck"][p] if s.cards[c].defn == defn), None)
            if cid is None:
                raise ValueError(f"相手の山札に {defn} がない")
            eng._raw_move(cid, "bz")

    def policy(self, eng: Engine, d: dict) -> list[int]:
        keys = [o["key"] for o in d["options"]]
        k = d["kind"]
        if k == "charge":
            return [next((i for i, x in enumerate(keys) if x != "pass"), keys.index("pass"))]
        if k == "block" and self.block:
            return [next((i for i, x in enumerate(keys) if x != "no_block"), keys.index("no_block"))]
        if k in ("declare_strigger", "declare_sback") and self.strigger:
            return list(range(len(keys)))
        if k == "attack" and self.attack != "none":
            i = self._pick_attack(eng, d)
            if i is not None:
                return [i]
        if k == "main" and self.play != "none":
            best = self._pick_play(eng, keys)
            if best is not None:
                return [best]
        return passive_policy(eng, d)

    def _pick_attack(self, eng: Engine, d: dict) -> int | None:
        opts = d["options"]
        p = d["player"]
        if self.attack == "all":
            return next((i for i, o in enumerate(opts) if o["key"].endswith(":player")), None)
        pw = lambda cid: eng.chars_ro(cid)["power"]   # noqa: E731
        for i, o in enumerate(opts):   # 勝てるバトル（タップした体への攻撃）
            t = o.get("target")
            if o["key"].startswith("attack:") and isinstance(t, list) and pw(o["cid"]) > pw(t[0]):
                return i
        mine = len(eng.bz_tops(p))
        theirs = sum(1 for c in eng.bz_tops(1 - p) if not eng.s.cards[c].tapped)
        if mine > theirs:
            return next((i for i, o in enumerate(opts) if o["key"].endswith(":player")), None)
        return None

    def _pick_play(self, eng: Engine, keys: list[str]) -> int | None:
        best, score = None, None
        for i, x in enumerate(keys):
            if not x.startswith("play:"):
                continue
            dfn, _, face = x[5:].partition(":")   # ツインパクトは play:<id>:<面>
            c = eng.rules.cards[dfn]
            if face.isdigit() and getattr(c, "faces", None) and int(face) < len(c.faces):
                c = c.faces[int(face)]
            blk = "blocker" in (c.keywords or ())
            if self.play == "blockers" and not blk:
                continue
            sc = (blk, c.cost if isinstance(c.cost, int) else 0)
            if score is None or sc > score:
                best, score = i, sc
        return best


def deck_from_spec(path, known=None, filler: str = "T001") -> tuple[list[str], list[dict]]:
    """スロット形式のデッキ（slots: [{name,id|null,n}]）から (デッキ, 未解決スロット) を作る。

    id が null か known（使えるカードID集合）に無いスロットは filler で埋め、未解決として返す。
    変換が進んだらYAMLの id を埋めるだけで忠実な再現になる。"""
    from pathlib import Path

    import yaml
    y = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    deck, missing = [], []
    for sl in y["slots"]:
        ok = sl.get("id") and (known is None or sl["id"] in known)
        deck += [sl["id"] if ok else filler] * sl["n"]
        if not ok:
            missing.append(sl)
    return deck, missing


# 「ビート」: 使えるカードは全部出し、S・トリガーも使い、ブロックはしない（殴り切る側）。
BEAT = OppModel("beat", strigger=True, play="all")
BEAT_DECK_PATH = "data/decks/beat_fire_gaga.yaml"

PRESETS: dict[str, OppModel | None] = {
    "none": None,
    "shields3": OppModel("shields3", shields=3),
    "blockers": OppModel("blockers", block=True, play="blockers"),
    "strigger": OppModel("strigger", strigger=True),
    "full": OppModel("full", block=True, strigger=True, play="all"),
    "beat": BEAT,
}


# 相手の抵抗の段階（物差し タスク11、docs/combo-ruler-design.md §11-2）。評価用の汎用設定で、コンボ専用にしない。
# 0: 無抵抗（既定。従来の数字と同じ）。1: 盾に実在の S・トリガー（除去・タップ・攻撃禁止・ターンを飛ばす・ブロッカー）が一定割合で入り、
#    相手はトリガーを使いブロッカーでブロックする。自分からは何も出さない。
# 2: 相手が実デッキで普通に動く（マナカーブどおりに出す・ブロック・殴り返し・S・トリガー）。汎用の2種類で、コンボを狙い撃ちしない:
#    "2a"（=2）速攻寄り: 火の軽いクリーチャーとスピードアタッカー、毎ターン全員でプレイヤーを攻撃、ブロックはしない。
#    "2b" 受け寄り: 光・水のブロッカー中心、ブロックし、勝てるバトルと数で勝る時だけ攻撃する。
#    札は効果データのキーワードだけのクリーチャー（テキストどおりの効果欠けがない札）から選んだ。盾には段階1と同じ S・トリガー12枚。
RESIST_TRIGGERS = (          # すべて data/cards/real.yaml（確認済み）の札
    "dm01-027",     # デーモン・ハンド（1体破壊）
    "dm01-086",     # スパイラル・ゲート（1体手札へ）
    "dm01-039",     # ナチュラル・トラップ（1体マナへ）
    "dm01-015",     # ホーリー・スパーク（すべてタップ）
    "dm20-008",     # スローリー・チェーン（このターン攻撃できない）
    "dmr09-021",    # 終末の時計 ザ・クロック（ターンの残りを飛ばす）
    "dmd24-024",    # 埋没のカルマ オリーブオイル（ブロッカー）
    "dmbd21-013",   # 終断γ ドルブロ（ブロッカー）
)
RESIST_COPIES = 12          # 40枚中12枚（盾5枚に平均1.5枚）。実戦のトリガー入りデッキの典型的な枚数
RESIST_FILLER = "T001"
RESIST_LEVELS = {0: "none", 1: "strigger12", 2: "aggro", "2a": "aggro", "2b": "control"}
RESIST_AGGRO = (              # 火。2〜5コスト、スピードアタッカー・W・ブレイカー
    "dm01-097",     # 不死身男爵ボーグ（2）
    "dm23rp2-069",  # 襲撃者 「鎧」ドライブ（2、SA）
    "dm05-049",     # 解体屋ピーカプ（3、SA）
    "dm22rp1-066",  # 斥候の旋風マーサ（3、SA）
    "dm10-096",     # 撃墜団長メッツアー（4、SA）
    "dmrp13-073",   # チューカツ・チュリス（4、W）
    "dm23rp1-066",  # ボルザード・バーンエッジ（5、W・SA）
)
RESIST_CONTROL = (            # 光・水。ブロッカー中心
    "dm01-075",     # 予言者リュゾル（2）
    "dm01-072",     # 弾丸の使徒イーレ（3）
    "dm19-073",     # 霊騎サイヤ（3、ブロッカー）
    "dm01-051",     # キング・クラーケン（3、ブロッカー）
    "dm02-042",     # アクア・シューター（4、ブロッカー）
    "dm05-036",     # 鉄壁の守護者ガリア・ゾールα（5、ブロッカー）
    "dm01-012",     # 粛清の伝道師ラー（5）
)


def resistance(level: int, size: int = 40) -> tuple[OppModel | None, list[str]]:
    """段階 level の (相手モデル, 相手のデッキ)。0 は (None, ダミー40枚) で従来どおり。"""
    if level == 0:
        return None, [RESIST_FILLER] * size
    if level == 1:
        trig = [RESIST_TRIGGERS[i % len(RESIST_TRIGGERS)] for i in range(RESIST_COPIES)]
        return OppModel(RESIST_LEVELS[1], block=True, strigger=True), trig + [RESIST_FILLER] * (size - len(trig))
    if level in (2, "2a", "2b"):
        control = level == "2b"
        trig = [RESIST_TRIGGERS[i % len(RESIST_TRIGGERS)] for i in range(RESIST_COPIES)]
        body = RESIST_CONTROL if control else RESIST_AGGRO
        rest = [body[i % len(body)] for i in range(size - len(trig))]
        m = OppModel(RESIST_LEVELS[level], block=control, strigger=True, play="all", attack="safe" if control else "all")
        return m, sorted(trig + rest)
    raise NotImplementedError(f"相手の段階 {level} は未実装（0, 1, 2/2a, 2b）")
