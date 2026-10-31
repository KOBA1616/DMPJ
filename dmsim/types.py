"""状態の中を流れる辞書の形（TypedDict）。

状態は純データ（JSON にそのまま出せる dict / list / int / str）のまま保ち、形だけをここで宣言する。
- 静的には型チェッカが、実行時には Engine(check=True)（テストでは常に有効）が check_shape でキーを検査する。
- Rust 移行時はこの定義がそのまま enum / struct の一覧になる。
"""

from typing import Any, Literal, NotRequired, TypedDict, get_type_hints

Ref = list[int]                          # [cid, gen]


# ---- Decision ----
class Option(TypedDict, total=False):
    key: str                             # 意味キー（ログ再生・ループ検出で使う。同名カードは同じキー）
    cid: int
    cids: list[int]
    name: str
    target: Any
    pid: int
    ab: int
    face: int
    shield: int                     # S・バック: 捨てるシールドのカード
    tap: int                             # 起動型能力のコストでタップするクリーチャー
    free: bool                           # コストを支払わずに実行する選択肢（G・ゼロ）
    rush: bool                           # アビスラッシュ（墓地から召喚する選択肢）
    gshield: bool                        # ギャラクシールド（表向きにシールド化する選択肢）
    neo: bool                            # NEO進化（進化元に重ねて出す選択肢）
    hyper_act: NotRequired[bool]         # ハイパーモード解放（メインステップの行動）


class Decision(TypedDict):
    player: int
    kind: str
    options: list[Option]
    min: int
    max: int
    prompt: str


class LogEntry(TypedDict):
    p: int
    kind: str
    choice: list[int]
    keys: list[str]


# ---- イベント ----
class Event(TypedDict, total=False):
    ev: str                              # move / draw / tap / untap / attack / block / cast / summon / break / turn_start / turn_end
    subject: Ref
    to: str
    reason: str
    position: str
    controller: int
    player: int
    target: Any
    attacker: Ref
    count: int
    replaced: bool
    stack_on: Ref                        # 進化: このクリーチャーの上に重ねて出す
    stack_more: NotRequired[list]        # 進化元の追加（超無限墓地進化などで同時に重ねる分）
    face: int                            # ツインパクト等: 実行する面
    card_only: bool                      # カードとして動かす（109.2a, 再構築 801.4）


Event.__optional_keys__ = Event.__optional_keys__ | {"from"}   # "from" は予約語なので後から足す


class EventRecord(TypedDict, total=False):
    """適用後のイベント（誘発・置換・遅延誘発の照合に使う）。"""
    ev: str
    subject: Ref
    lki: dict | None
    to: str
    reason: str
    controller: int
    player: int
    target: Any
    attacker: Ref
    count: int
    stack_on: Ref


# ---- 効果の環境 ----
class Env(TypedDict, total=False):
    you: int
    self: Ref | None
    event: EventRecord
    vars: dict[str, list[Ref]]
    no_replace: bool
    in_st: bool                          # S・トリガーとして解決中の呪文の効果（101.4g）
    eng: Ref


# ---- 待機・継続的効果 ----
class Pending(TypedDict):
    pid: int
    kind: Literal["normal", "strigger", "delayed"]
    win: int
    controller: int
    src: Ref | None
    defn: str
    ab: int
    env: Env
    face: NotRequired[int]
    delayed: NotRequired[int]            # 遅延誘発型能力の id
    effect: NotRequired[list[dict]]      # 遅延誘発型能力の効果
    inline: NotRequired[dict]            # 継続的効果で得た能力（mod.gain）


class Continuous(TypedDict):
    id: int
    affected: list[Ref] | None           # None なら filter で毎回範囲を見る（プレイヤー対象など）
    mod: dict
    duration: str
    controller: int
    filter: NotRequired[dict]


class Delayed(TypedDict):
    """遅延誘発型能力（603.6）。生成された後のイベントだけを見る。"""
    id: int
    controller: int
    when: dict
    effect: list[dict]
    env: Env
    duration: str
    once: bool


class StepMod(TypedDict):
    player: int
    step: str
    mode: Literal["skip", "extra"]
    turns: int                           # 何回分のターンに効くか（使うたび 1 減る）


# ---- タスク ----
class EventTask(TypedDict):
    t: Literal["event"]
    evs: list[Event]
    i: int
    rp: int
    skip: list[int]
    instead: list[dict]
    captured: list[Event]
    applying: bool
    answer: NotRequired[list[int]]
    link_i: NotRequired[int]             # G・リンクの離脱置換: 処理済みのイベント位置
    link_chosen: NotRequired[list[int]]  # G・リンクの離脱置換: 離れることが決まったカード


class GLinkTask(TypedDict):
    t: Literal["g_link"]
    cid: int
    player: int
    step: str
    answer: NotRequired[list[int]]


class HyperTask(TypedDict):
    t: Literal["hyper"]
    cid: int
    player: int
    answer: NotRequired[list[int]]


class CaptureTask(TypedDict):
    t: Literal["capture"]
    evs: list[Event]


class EffectTask(TypedDict):
    t: Literal["effect"]
    ops: list[dict]
    pc: int
    env: Env
    os: dict
    answer: NotRequired[list[int]]


class TurnTask(TypedDict):
    t: Literal["turn"]
    steps: list[str]
    i: int
    sub: int
    cp: bool
    answer: NotRequired[list[int]]


class AttackTask(TypedDict):
    t: Literal["attack"]
    attacker: Ref
    target: Any
    phase: int
    cp: bool
    blocked: NotRequired[bool]
    ano: NotRequired[int]                # このターン何回目の攻撃か（キリフダッシュの「その攻撃中に」判定）
    end_fired: NotRequired[bool]         # attack_end イベントを発火済みか
    decl: NotRequired[int]               # 使用宣言の段階（506.3b〜）
    subbed: NotRequired[list[int]]       # 身代わりバトルの置換を済ませた側（0=攻撃側, 1=攻撃先）
    answer: NotRequired[list[int]]


class BreakTask(TypedDict):
    t: Literal["break"]
    victim: int
    by: int
    count: int
    phase: int
    in_effect: bool
    chosen: NotRequired[list[int]]
    answer: NotRequired[list[int]]
    reason: NotRequired[str]         # 手札へ加える理由（既定は break）。効果で加える時は効果の reason
    breaker: NotRequired[Ref]        # ブレイクしたクリーチャー（攻撃、またはクリーチャーの効果）
    declared: NotRequired[list]      # 宣言済みの S・トリガー [[cid, face | None]]
    fire_break: NotRequired[bool]    # ブレイクのイベントを起こすか（効果でシールドを手札に加える時は起こさない）


class CrossTask(TypedDict):
    t: Literal["cross"]
    gear: Ref                            # クロスするクロスギア（バトルゾーン）
    target: Ref                          # クロス先のクリーチャー
    player: int


class PlayTask(TypedDict):
    t: Literal["play"]
    cid: int
    player: int
    free: bool
    phase: str
    gen: int                             # 積んだ時の世代。カードが動いていたら実行しない（400.8）
    face: NotRequired[int]
    evo: NotRequired[list[Ref]]          # 進化元（801）。複数可（超無限墓地進化など）
    tap: NotRequired[list[int]]          # ハイパーエナジーでタップするクリーチャー
    tap_done: NotRequired[bool]
    sac: NotRequired[list[int]]          # ササゲールで破壊するクリーチャー
    sac_done: NotRequired[bool]
    reduced: NotRequired[bool]           # B・A・D / J・O・E: コストを減らして実行する
    reduce_done: NotRequired[bool]
    fuel: NotRequired[list[int]]         # 支払い時の行動（opt_reduce.do）で選んだカード
    fuel_done: NotRequired[bool]
    cost_may_i: NotRequired[int]         # cost_may の確認が済んだ発生源の数
    cost_may_total: NotRequired[int]     # cost_may で得た軽減の合計
    cost_may_min: NotRequired[int]       # cost_may の下限（使った発生源の最大）
    cost_may_done: NotRequired[bool]
    rush: NotRequired[bool]              # アビスラッシュ（墓地からの召喚）
    evo_mode: NotRequired[bool]          # NEO進化として重ねて出す
    to_shield: NotRequired[bool]         # ギャラクシールド（代替コストで表向きにシールド化する）
    as_paid: NotRequired[bool]           # コストを支払ったものとして実行する（ギャラクシールドのターン開始時召喚）
    cost_override: NotRequired[int]      # 代替コスト（キリフダッシュ等）: 通常コストの代わりに払う総額
    cost_civs: NotRequired[list]         # 代替コストで必要な文明（省略時はカードの文明）
    st: NotRequired[bool]                # S・トリガーとして実行する（101.4g）
    resolve_to: NotRequired[str]         # 解決後の置き場所（play_free の resolve_to）
    resolve_position: NotRequired[str]   # resolve_to が山札のときの top / bottom
    answer: NotRequired[list[int]]


class SbackTask(TypedDict):
    t: Literal["sback"]
    pairs: list[list]                    # [S・バックのカード, 捨てるカード]
    player: int


class BattleRunTask(TypedDict):
    t: Literal["battle_run"]
    att: list
    tgt: list


class EnqueueStTask(TypedDict):
    t: Literal["enqueue_st"]
    cids: list[list]                     # [cid, face | None]
    player: int


class OpenWinTask(TypedDict):
    t: Literal["open_win"]
    win: int


class CloseWinTask(TypedDict):
    t: Literal["close_win"]


class ResolvePendingTask(TypedDict):
    t: Literal["resolve_pending"]
    win: int
    only_st: bool
    answer: NotRequired[list[int]]


class DeclareTask(TypedDict):
    """使用宣言（603.2e/f）。手札などの非公開ゾーンから誘発する能力を、宣言したものだけ待機させる。"""
    t: Literal["declare"]
    player: int
    window: str                          # attack / block など、宣言できる場面
    ctx: dict
    answer: NotRequired[list[int]]


class BindTask(TypedDict):
    t: Literal["bind"]
    env: Env
    name: str
    cids: list[int]
    zone: str


SwapInTask = TypedDict("SwapInTask", {"t": Literal["swap_in"], "out": Ref, "out_gen_next": int, "in": Ref,
                                       "tapped": bool, "env": Env})


class SwapFixTask(TypedDict):
    t: Literal["swap_fix"]
    cid: int
    out: Ref
    tapped: bool


class PutUnderTask(TypedDict):
    t: Literal["put_under"]
    cid: int
    gen: int
    onto: Ref


class SlayerTask(TypedDict):
    t: Literal["slayer"]
    pairs: list[list[Ref]]               # [スレイヤーを持っていた負けたクリーチャー, バトル相手]


def check_shape(d: dict, shape) -> None:
    """d が TypedDict shape の形か（必須キーがある・未知のキーがない）を確かめる。"""
    keys = set(d)
    req = shape.__required_keys__
    allowed = req | shape.__optional_keys__
    missing = req - keys
    extra = keys - allowed
    if missing or extra:
        raise TypeError(f"{shape.__name__}: missing={sorted(missing)} extra={sorted(extra)} in {d!r}"[:400])


def hints(shape) -> dict:
    return get_type_hints(shape)
