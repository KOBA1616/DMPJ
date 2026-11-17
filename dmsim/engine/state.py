"""ゲーム状態。純粋なデータだけで構成する（設計判断⑧）。

- クロージャやオブジェクト参照を持たない。カードは整数 cid、参照は [cid, gen]。
- 乱数の内部状態も state に入れるので、state を複製すれば乱数ごと分岐できる。
- 実行中の処理（タスクスタック）も state に入れるので、決定待ちのどの時点でも複製・保存・再開できる。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, fields, is_dataclass

MASK64 = (1 << 64) - 1


def rng_next(state: "GameState") -> int:
    """splitmix64。Rust 側でも同じ数列を再現できる単純なもの。"""
    state.rng = (state.rng + 0x9E3779B97F4A7C15) & MASK64
    z = state.rng
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    return z ^ (z >> 31)


def rng_below(state: "GameState", n: int) -> int:
    return rng_next(state) % n


@dataclass
class Card:
    """物理カード1枚。ゾーンを移動するたびに gen が増え、別のオブジェクトになる（400.5、設計判断①）。"""
    cid: int
    defn: str
    owner: int
    zone: str = "deck"
    gen: int = 0
    controller: int = 0
    tapped: bool = False
    face_up: bool = False
    face_down: bool = False                            # マナゾーンで裏向き（水晶武装）。マナとしては無色扱い
    entered_turn: int = -1
    under: list[int] = field(default_factory=list)  # 下に重なっているカード（進化元など。設計判断②）
    top_of: int = -1                                  # 自分が下に重なっている場合、その一番上の cid
    seals: list[int] = field(default_factory=list)  # 封印: このカードの上に裏向きで重なっているカード（付けた順）
    seal_of: int = -1                                 # 自分が封印として重なっている場合、その対象の cid
    face: int = -1                                    # ツインパクト等で今使っている面（-1 = カード全体, 810）
    entered_seq: int = 0                              # バトルゾーンに出た時刻（608.5 無視効果の優先）
    crossed: list | None = None                       # クロスギアがクロスしているクリーチャーの参照 [cid, gen]（303.3）。離れていれば無効
    exlife_of: list | None = None                     # 「EXライフ」シールドの紐付け先クリーチャーの参照 [cid, gen]。離れたら外れる
    sforce_of: list | None = None                     # シールド・フォース: このシールドが力を与えているクリーチャーの参照 [cid, gen]。シールドゾーンを離れたら外れる
    fortifies: list | None = None                     # 城（第178弾）: この城が要塞化しているシールドの参照 [cid, gen]。城がゾーンを離れたら外れる
    no_untap_next: bool = False                       # フリーズ等: 次の持ち主のターン開始時にアンタップしない（1回だけ。開始時に消費）
    link: int = 0
    hyper: bool = False                                     # G・リンクのグループID（0=リンクしていない）。同じIDのカード同士がリンクしている
    strigger_off: bool = False                              # S・トリガーの印: 手札にある間、S・トリガーを宣言できない（エメラル／エスケープ等。バンドC2 U68）
    strigger_on: bool = False                               # S・トリガーの印: 手札にある間、本来の定義になくても S・トリガーを宣言できる（バンドC2 U68）
    sst: bool = False                                       # スーパー・S・トリガー: シールド0枚で使った時に追加能力（sst印つき）を得た
    stp: bool = False                                       # S・トリガー・プラス: 条件を満たして使った時に追加能力（stp印つき）を得た
    odrive: bool = False                                    # O・ドライブ: 追加のマナタップをして召喚した
    odrive_civs: list = field(default_factory=list)         # O・ドライブ: 実際にタップした文明（文明別の能力用）
    summon_tapped: list = field(default_factory=list)       # フォートE: 召喚時にタップしたマナ [{ref: [cid, gen], races: [種族...]}]。ゾーン移動で消える
    summon_fuel: list = field(default_factory=list)         # 第189弾: 召喚時の支払い行動（opt_reduce.do）で選んだカード [[cid, gen], ...]。ゾーン移動で消える
    bazurenda: int = 0                                      # バズレンダ: 追加で支払った回数
    drawn_turn: int = -1                                    # このターンにドローしたか（ビビッドロー）
    vivid: bool = False                                     # ビビッドロー: 表向きにした
    dswitched: bool = False                                 # Dスイッチ: ゲーム中で一度上下逆さまにした（使用済み。第151弾）


def _jcopy(v):
    """list / dict / スカラーだけからなる値の深いコピー。"""
    t = type(v)
    if t is dict:
        return {k: _jcopy(x) for k, x in v.items()}
    if t is list:
        return [_jcopy(x) for x in v]
    return v


def _enc_into(v, out: list):
    """fast_key 用の位置符号化。辞書のキー名を位置で表し、JSON 化より安く
    全フィールドを一意に符号化する（型タグ付き、辞書はキー順を正規化）。"""
    t = type(v)
    if t is dict:
        out.append("{")
        for k in sorted(v.keys(), key=repr):
            _enc_into(k, out)
            _enc_into(v[k], out)
        out.append("}")
    elif t is list or t is tuple:
        out.append("[")
        for x in v:
            _enc_into(x, out)
        out.append("]")
    elif t is str:
        out.append("s%d:%s;" % (len(v), v))
    elif t is bool:
        out.append("b1;" if v else "b0;")
    elif t is int:
        out.append("i%d;" % v)
    elif v is None:
        out.append("N;")
    elif is_dataclass(v):
        out.append("(")
        for f in fields(v):
            _enc_into(getattr(v, f.name), out)
        out.append(")")
    else:
        out.append("r%s;" % (repr(v),))


def _copy_card(c: "Card") -> "Card":
    n = Card.__new__(Card)
    d = n.__dict__
    d.update(c.__dict__)
    d["under"] = list(c.under)
    d["seals"] = list(c.seals)
    return n


@dataclass
class GameState:
    cards: list[Card]
    zones: dict[str, list[list[int]]]   # zones[name][player] = cid の列（先頭 = 一番上）。共有ゾーンは player 0 の列を使う
    hold: list[int] = field(default_factory=list)  # 保留状態（409）。元のゾーンから外れ、どこにも数えない
    turn: int = 0
    active: int = 0
    first_player: int = 0
    step: str = "start"
    rng: int = 0
    pending: list[dict] = field(default_factory=list)      # 待機中の効果（101.4）。各要素は win（解決窓）を持つ
    windows: list[int] = field(default_factory=list)       # 開いている解決窓のスタック（バトル 701.13、効果中のS・トリガー 101.4g 等）
    continuous: list[dict] = field(default_factory=list)   # 継続的効果（タイムスタンプ順）
    delayed: list[dict] = field(default_factory=list)      # 遅延誘発型能力（603.6）
    step_mods: list[dict] = field(default_factory=list)    # ターン構造の変更（ステップを飛ばす・追加する）
    tasks: list[dict] = field(default_factory=list)        # 実行中の処理のスタック
    waiting: dict | None = None                            # 決定待ちの Decision（純データ）
    result: dict | None = None
    seq: int = 0                                            # タイムスタンプ／待機順の採番
    extra_turns: list[int] = field(default_factory=list)
    turn_counters: dict = field(default_factory=dict)       # 「このターン N 回目」系
    prev_counters: dict = field(default_factory=dict)       # 前のターンの turn_counters の退避（st_start で消す直前にコピー。「前のターンに〜」の読み口）
    game_counters: dict = field(default_factory=dict)       # ゲーム単位の履歴（ターン開始で消えない。mark の scope: game の置き場所）
    declares: dict = field(default_factory=dict)            # 宣言ストア（choose_number / choose_name / choose_civ が書き、式 {declared: 名前} が読む。バンドC2 基盤B5）
    ev_seq: int = 0                                             # イベントの通し番号（「各ターン、はじめて」の同一イベント判定）
    steps_this_turn: int = 0
    skip_rest: bool = False                                 # 「ターンの残りをとばす」
    deck_emptied: list[int] = field(default_factory=list)   # 山札が一瞬でも0枚になったプレイヤー（104.2b）
    pub: list[dict] = field(default_factory=list)            # 公開イベントの記録（誰が何を見たか）。Engine.note_public が追記する。公平探索の信念更新用
    sba_held: list[list[int]] = field(default_factory=list)   # パワー0以下の破壊を置換で止められたクリーチャー（同じ処理を繰り返さない）
    trace: list | None = None                               # 誘発の因果の記録（None なら記録しない。探索では切っておく）


    # ---- 参照 ----
    def ref(self, cid: int) -> list[int]:
        return [cid, self.cards[cid].gen]

    def alive(self, ref) -> bool:
        """[cid, gen] がまだ同じオブジェクトを指しているか。移動していたら False（400.8）。"""
        return ref is not None and self.cards[ref[0]].gen == ref[1]

    def zone(self, name: str, player: int, shared: bool) -> list[int]:
        return self.zones[name][0 if shared else player]

    def clone(self) -> "GameState":
        """deepcopy の代わり。state は純データ（int/str/bool/None と list/dict）だけなので手書きで複製する。"""
        new = GameState.__new__(GameState)
        d = new.__dict__
        for k, v in self.__dict__.items():
            if k == "cards":
                d[k] = [_copy_card(c) for c in v]
            elif k == "zones":
                d[k] = {n: [list(z) for z in per] for n, per in v.items()}
            else:
                d[k] = _jcopy(v)
        return new

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return hashlib.blake2b(self.to_json().encode(), digest_size=16).hexdigest()

    def fast_key(self) -> str:
        """digest() と同じ全フィールドから作る探索専用の高速キー（位置符号化で
        asdict＋JSON 化を避ける）。記録・再生の同一性には digest() を使い、
        こちらは探索内部の重複統合専用。"""
        out: list = []
        _enc_into(self, out)
        return hashlib.blake2b("".join(out).encode(), digest_size=16).hexdigest()
