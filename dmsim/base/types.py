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
    payer: int                           # 攻撃先変更（第171弾）: コストでアンタップするクリーチャー
    player: int                          # choose_player 決定（第192弾）: その選択肢が指すプレイヤー
    tap_mana: int                        # 起動型能力の複合コストで追加でタップするマナの枚数
    under_cost: int                      # 起動型能力のコストで墓地に置く下のカードの枚数（第53弾）
    grave_evo: bool                      # 墓地進化（自分の墓地のクリーチャーの上に重ねて出す選択肢）
    once_src: int                        # 回数制限つき許可（ターン1回）の発生源カード
    free: bool                           # コストを支払わずに実行する選択肢（G・ゼロ）
    rush: bool                           # アビスラッシュ（墓地から召喚する選択肢）
    gshield: bool                        # ギャラクシールド（表向きにシールド化する選択肢）
    neo: bool                            # NEO進化（進化元に重ねて出す選択肢）
    hyper_act: NotRequired[bool]         # ハイパーモード解放（メインステップの行動）
    climb: NotRequired[bool]             # ムゲンクライム（タップ+代替コストで実行する選択肢）
    alt: NotRequired[bool]               # 代替コストで実行する選択肢
    vivid: NotRequired[bool]             # ビビッドロー（代替コストで実行する選択肢）
    reveal: NotRequired[bool]            # ビビッドロー（表向きにする選択肢）
    fushigi: NotRequired[bool]           # フシギバース（墓地から召喚する選択肢）
    recycle: NotRequired[bool]           # リサイクル（墓地から代替コストで唱える選択肢。第172弾）
    grave_cast: NotRequired[bool]        # 墓地から通常コストで唱える選択肢（第226弾）
    rinne: NotRequired[bool]             # 輪廻∞: 呪文側をバトルゾーンに置いたまま唱える選択肢（第267弾）
    bakutan: NotRequired[bool]           # マナ爆誕（マナゾーンから固定コストで召喚する選択肢。第191弾）


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
    hands: list[str]                     # ジャンケン（第271弾）: プレイヤー順の手 ["rock"/"scissors"/"paper"]
    winner: int | None                   # ジャンケンの勝者（あいこは None）


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
    kind: Literal["normal", "strigger", "delayed", "double_ask"]
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
    target: NotRequired[int]             # double_ask（第264弾）: 2度トリガーさせる対象の pending pid
    td: NotRequired[dict]                # double_ask: 適用する trigger_double の仕様
    once_key: NotRequired[str]           # double_ask: 適用時に立てる once_per_turn の印（無ければ None）
    cost: NotRequired[list[dict]]        # double_ask: 適用時に解決するコスト ops


class Continuous(TypedDict):
    id: int
    affected: list[Ref] | None           # None なら filter で毎回範囲を見る（プレイヤー対象など）
    mod: dict
    duration: str
    controller: int
    filter: NotRequired[dict]
    src: NotRequired[int]                # 発生源カードの cid（回数制限つき allow の帰属用、第50弾）


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


class UntapLimitTask(TypedDict):
    t: Literal["untap_limit"]
    player: int
    caps: dict          # {"bz": int, "mana": int}（上限があるゾーンだけ）
    bz: list[int]       # アンタップ候補（bz のクリーチャー）
    mana: list[int]     # アンタップ候補（マナゾーン）
    os: NotRequired[dict]
    answer: NotRequired[list[int]]


class ActivateTask(TypedDict):
    t: Literal["activate"]
    cid: int
    player: int
    ab: int
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
    cancelled: NotRequired[bool]         # 攻撃の中止（第251弾）: バトルもブレイクも行わず攻撃を終わる
    g_break: NotRequired[bool]           # G・ブレイカーを使った（第252弾）: 相手ブレイクの後に自分のシールドもすべてブレイクする
    ano: NotRequired[int]                # このターン何回目の攻撃か（キリフダッシュの「その攻撃中に」判定）
    end_fired: NotRequired[bool]         # attack_end イベントを発火済みか
    through_fired: NotRequired[bool]     # attack_unblocked イベントを発火済みか（第229弾）
    decl: NotRequired[int]               # 使用宣言の段階（506.3b〜）
    subbed: NotRequired[list[int]]       # 身代わりバトルの置換を済ませた側（0=攻撃側, 1=攻撃先）
    redirect_done: NotRequired[bool]     # 攻撃先変更（第171弾）の諮問を済ませたか
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
    brk_list: NotRequired[list[int]]        # 置換の諮問対象のシールド（chosen の写し。第146弾）
    brk_i: NotRequired[int]                 # 諮問中のシールドの添字
    brk_p: NotRequired[int]                 # 諮問中のプレイヤーの添字（ターン・プレイヤーから）
    brk_cancelled: NotRequired[list[int]]   # 置換でブレイクが取り消されたシールド
    brk_waiting: NotRequired[list]          # instead を実行中の [シールドの cid, continue か]
    brk_done: NotRequired[bool]             # 諮問が終わったか
    strigger: NotRequired[str]              # 手札に加わるカードへの S・トリガーの印（"off" / "on"。op move の strigger 引数から。バンドC2 U68）


class CrossTask(TypedDict):
    t: Literal["cross"]
    gear: Ref                            # クロスするクロスギア（バトルゾーン）
    target: Ref                          # クロス先のクリーチャー
    player: int
    free: NotRequired[bool]              # コストを支払わないクロス（第195弾。cross_free 許可）
    answer: NotRequired[list[int]]


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
    launcher: NotRequired[list]          # ランチャーEでタップしたクリーチャーの参照（第233弾）
    launcher_done: NotRequired[bool]
    reduced: NotRequired[bool]           # B・A・D / J・O・E: コストを減らして実行する
    reduce_done: NotRequired[bool]
    fuel: NotRequired[list[int]]         # 支払い時の行動（opt_reduce.do）で選んだカード
    fuel_done: NotRequired[bool]
    fuel_idx: NotRequired[int]           # 第189弾: 複数選択（do.selects）で次に選ぶ項目の番号（再入時の再開位置）
    fuel_asked: NotRequired[bool]        # 第189弾: 燃料の選択肢を一度でも提示したか（選ばなかった場合との区別用）
    cost_may_i: NotRequired[int]         # cost_may の確認が済んだ発生源の数
    cost_may_total: NotRequired[int]     # cost_may で得た軽減の合計
    cost_may_min: NotRequired[int]       # cost_may の下限（使った発生源の最大）
    cost_may_done: NotRequired[bool]
    rush: NotRequired[bool]              # アビスラッシュ（墓地からの召喚）
    once_src: NotRequired[int]           # 回数制限つき許可（ターン1回）の発生源。使用したら記録する
    evo_mode: NotRequired[bool]          # NEO進化として重ねて出す
    to_shield: NotRequired[bool]         # ギャラクシールド（代替コストで表向きにシールド化する）
    as_paid: NotRequired[bool]           # コストを支払ったものとして実行する（ギャラクシールドのターン開始時召喚）
    cost_override: NotRequired[int]      # 代替コスト（キリフダッシュ等）: 通常コストの代わりに払う総額
    cost_civs: NotRequired[list]         # 代替コストで必要な文明（省略時はカードの文明）
    st: NotRequired[bool]                # S・トリガーとして実行する（101.4g）
    paid_done: NotRequired[bool]         # 本体のコストを支払い済み（後段の決定での再入対策）
    summon_paid: NotRequired[list[int]]  # フォートE（第168弾）: 召喚コストとしてタップしたマナ
    bz_done: NotRequired[bool]           # バズレンダ: 追加支払いの確認が終わった
    bz_count: NotRequired[int]           # バズレンダ: 追加で支払った回数
    alt: NotRequired[bool]               # 代替コストで実行する
    vivid: NotRequired[bool]             # ビビッドローで実行する（第54弾: イベント・条件への伝播用）
    via: NotRequired[str]                # 出し方の印（第149弾: play_self の via。イベント・条件への伝播用）
    alt_step: NotRequired[int]           # 代替コスト（行動形式）で済んだ段階
    evo_v: NotRequired[list]             # 進化V: フィルタごとに選んだ進化元
    evo_civs_sel: NotRequired[list]      # 超無限進化の文明条件: 選択途中の進化元（第218弾）
    evo_cost_sel: NotRequired[list]      # 超無限進化のコスト合計条件: 選択途中の進化元（第236弾）
    fushigi: NotRequired[bool]           # フシギバースとして実行する
    fushigi_done: NotRequired[bool]      # フシギバース: 進化元代わりのクリーチャーをマナに置いた
    alt_done: NotRequired[bool]          # 代替コスト（行動形式）の支払いが終わった
    bz_yn_for: NotRequired[int]          # バズレンダ: 「追加で支払うか」を確認済みの回数
    bz_pay: NotRequired[bool]            # バズレンダ: その回は追加で支払う
    bz_paid_for: NotRequired[int]        # バズレンダ: 追加支払いが済んだ回数
    od_yn: NotRequired[bool]             # O・ドライブ: 追加でタップするか
    od_done: NotRequired[bool]           # O・ドライブ: 確認済み
    odrive: NotRequired[bool]            # O・ドライブ: 追加でタップして召喚した
    od_idx: NotRequired[int]             # O・ドライブ: 処理中のステップ（文明）番号
    od_sub: NotRequired[int]             # O・ドライブ: ステップ内で処理中の文明番号
    od_civs_done: NotRequired[list]      # O・ドライブ: 実際にタップした文明
    odrive_civs: NotRequired[list]       # O・ドライブ: タップした文明（イベント/印への引き渡し用）
    climb: NotRequired[bool]             # ムゲンクライムとして実行する
    climb_done: NotRequired[bool]        # ムゲンクライム: クリーチャーのタップが済んだ
    recycle: NotRequired[bool]           # リサイクルとして実行する（第172弾: 解決後は山札の一番下へ）
    grave_cast: NotRequired[bool]        # 墓地から唱えた（第226弾: 解決後は山札の一番下へ）
    rinne: NotRequired[bool]             # 輪廻∞で唱えた（第267弾: カードはバトルゾーンに残る）
    bakutan: NotRequired[bool]           # マナ爆誕として実行する（第191弾: マナゾーンから固定コストで召喚）
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
    strigger: NotRequired[bool]          # S・トリガー宣言経由（True の時だけ use_s_trigger レコードを出す。S・バック経由は付けない。バンドB U7）


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


class LoseReplaceTask(TypedDict):
    """敗北の置換（S-MAX進化など）: 敗北が確定する前に、置換できるかを敗北するプレイヤーに諮る。"""
    t: Literal["lose_replace"]
    loser: int
    reason: str
    phase: int
    answer: NotRequired[list[int]]


class SmaxReduceTask(TypedDict):
    """S-MAX進化の2体制限（状況起因）: 残す1体を選び、残りをすべて手札に戻す。"""
    t: Literal["smax_reduce"]
    player: int
    answer: NotRequired[list[int]]


class DoubleAskTask(TypedDict):
    """任意の2度トリガー（第264弾）: 対象の誘発がまだ待機していれば「２度トリガーするか」を尋ねる。"""
    t: Literal["double_ask"]
    target: int
    controller: int
    src: Ref | None
    once_key: str | None
    cost: list[dict] | None
    env: Env
    answer: NotRequired[list[int]]


class GachaTask(TypedDict):
    """ドギラゴン・ガチャ（第268弾）: 残り回数ぶん 1d6 を振り、出目ごとの効果を子タスクで解決する。
    spin は解決中の出目（子タスクが終わるまで残し、次の呼び出しで消してから次を振る）。"""
    t: Literal["gacha"]
    kind: str
    remaining: int
    controller: int
    env: Env
    spin: NotRequired[int]
    answer: NotRequired[list[int]]


class JankenTask(TypedDict):
    """ジャンケン（第271弾）: 両プレイヤーがグー/チョキ/パーを同時に選び、あいこなら
    勝敗が決まるまで繰り返す。各投は janken イベントとして発表する（手の誘発用）。
    mine / opp は今の投で選んだ手（次の呼び出しで使う）。done は勝敗分岐の子タスクを
    積んだ印（子タスクが終わって戻ってきたら自分を pop する）。"""
    t: Literal["janken"]
    controller: int
    env: Env
    win: list[dict]
    lose: list[dict]
    mine: NotRequired[str]
    opp: NotRequired[str]
    done: NotRequired[bool]
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


class InvadeFixTask(TypedDict):
    t: Literal["invade_fix"]
    cid: int
    onto: Ref
    tapped: bool


class SummonOnFixTask(TypedDict):
    t: Literal["summon_on_fix"]
    cid: int
    tapped: bool


class PutUnderTask(TypedDict):
    t: Literal["put_under"]
    cid: int
    gen: int
    onto: Ref


class PutStackedTask(TypedDict):
    t: Literal["put_stacked"]
    cids: list[int]              # 残りのカード（選んだ順に1体ずつ出す）
    all_cids: list[int]          # 選んだ全体（bind 用）
    player: int
    env: Env
    reason: str
    tapped: bool
    face_up: bool
    seal: NotRequired[int]       # 封印を付けた状態で出す（move の seal の転送）
    bind: NotRequired[str]       # move の as の転送（全員出し終わった後に bind する）
    evo_v: NotRequired[list]     # 進化V: フィルタごとに選んだ進化元
    evo_source: NotRequired[list]  # 固定の進化元（第173弾。move の evo_source の転送）
    answer: NotRequired[list[int]]


class SlayerTask(TypedDict):
    t: Literal["slayer"]
    pairs: list[list[Ref]]               # [スレイヤーを持っていた負けたクリーチャー, バトル相手]


class SealReleaseTask(TypedDict):
    t: Literal["seal_release"]
    player: int
    civs: list[str]


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
