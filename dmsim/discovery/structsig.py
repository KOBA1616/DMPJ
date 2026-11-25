"""構造署名: 束（bundle）の移動・誘発構造から部分署名を抽出し、共有するカードを探す。

属性ベクトル（294次元）の近傍置換では新規エンジンが見つからなかった（docs/combo-hunt-v3.md
「モデル提案」節）。ループの相互作用は効果の正確な配線（どの誘発が・どのゾーン移動を・
どの対象に）に依存するため、ここでは束そのものの構造で類似を見る。

署名は Premise（誘発イベント frm→to、主体 subject、能力の働くゾーン zone）と
Move（src→dst、ref_self、draw、対象フィルタ）の組で表す。部分署名の共有＝
「その束が含むべき前提と移動の部分集合を持つ」ことで判定する（余分な移動があってもよい）。

既知エンジンから抽出した2つの署名:

1. 傍受者（interceptor）: サガの回帰の出力を墓地から手札に変える XENARCH の配線。
   サガの周回には「手札→墓地」の移動（捨てる）が毎周含まれ、墓地にいる XENARCH が
   そのイベントで誘発して自分を墓地→手札に戻す。捨てられた札が手札に戻るため
   墓地は増えず、ドロー分だけ手札が単調に増える。
   署名: prem=(move, hand→graveyard, subject∈{owner:you, self}, zone=graveyard)、
         moves に (graveyard→hand, ref_self) を含む、ターン1回制限なし。

2. 自己回帰（saga-like）: サガ単独の回帰の配線。
   署名: prem=(move→bz, subject=self) または (turn_start, player=you)、zone=bz の束が
         draw (deck→hand)、(hand→graveyard)、(graveyard→bz, フィルタF) を含む。
         層: strict = (bz→graveyard, ref_self) もあり、かつカード自身が F に適合
         （サガ本人と同型。自分の効果で自分を蘇生できる。2枚が交互に回る前提）。
         no_self_gy = 自己適合だが自分が墓地へ行く移動が無い。
         no_self / no_self_gy_no_self = 蘇生フィルタが自分に合わない。
         draw＋discard だけの束は116件あり緩すぎるため対象にしない。
"""
from __future__ import annotations


def prem_key(prem) -> tuple | None:
    if prem is None:
        return None
    subj = prem.subject
    if isinstance(subj, dict):
        subj_key = ("dict", tuple(sorted((k, str(v)) for k, v in subj.items())))
    else:
        subj_key = subj
    return (prem.kind, prem.frm, prem.to, subj_key, prem.player, prem.zone)


def move_key(m) -> tuple:
    flt = tuple(sorted((k, str(v)) for k, v in (m.flt or {}).items()))
    return (m.src, m.dst, bool(m.ref_self), bool(m.draw), m.owner, flt)


def bundle_signature(b) -> dict:
    """記録用の署名（前提＋移動の組）。"""
    return {"prem": prem_key(b.prem), "once": bool(getattr(b, "once", False)),
            "origin": b.origin, "moves": [move_key(m) for m in b.moves]}


# ---------------------------------------------------------------- 傍受者（XENARCH 型）

def _subject_is_you_or_self(prem) -> str | None:
    """前提の主体が「自分の札（群）」ならその種別を返す。"""
    s = prem.subject
    if s == "self":
        return "self"
    if isinstance(s, dict) and s.get("owner") == "you" and "filter" not in s:
        return "you"
    return None


def interceptor_kind(b) -> str | None:
    """束が XENARCH 型の傍受配線なら種別を返す。

    - "self_return": 前提 (hand→graveyard の移動、自分の札) を墓地で受け、
      自分を墓地→手札に戻す（XENARCH 本人の配線）。
    - "self_return_bz": 戻し先が手札でなく場（出力が盤面に変わる変種）。
    - "any_source_return": 前提の移動元が不問（→graveyard 全般）。捨てる行為も
      その部分集合なので傍受できるはずの変種。戻し先は手札。
    - "any_source_return_bz": 移動元不問＋戻し先が場の変種。
    - "any_return": 自分でなく墓地の札を手札に戻す（蓄積が要る弱い変種）。
    ターン1回制限（once）の束は、同一ターン内の多周回に追随できないため対象外。
    置換（kind=replace）型の「手札→墓地なら代わりに〜」は束に現れないが、全件が
    「相手に捨てさせられた時（by: opp）」条件で自分の捨てる行為には反応せず、
    戻し先も手札でないため、傍受の代替にはならない（2026-11-25 走査で確認）。
    """
    p = b.prem
    if p is None or getattr(b, "once", False):
        return None
    if p.kind != "move" or p.to != "graveyard" or p.zone != "graveyard":
        return None
    if _subject_is_you_or_self(p) is None:
        return None
    if p.frm not in ("hand", None):
        return None
    src_tag = "" if p.frm == "hand" else "any_source_"
    for m in b.moves:
        if m.src == "graveyard" and m.dst == "hand" and m.ref_self:
            return src_tag + "self_return" if src_tag else "self_return"
    for m in b.moves:
        if m.src == "graveyard" and m.dst == "bz" and m.ref_self:
            return src_tag + "self_return_bz"
    for m in b.moves:
        if m.src == "graveyard" and m.dst == "hand" and not m.ref_self:
            return src_tag + "any_return"
    return None


def find_interceptors(by_card: dict) -> dict[str, list[dict]]:
    """傍受配線を持つカードを全カードから探す。{cid: [{kind, signature}]}。"""
    out: dict[str, list[dict]] = {}
    for cid, bundles in by_card.items():
        hits = []
        for b in bundles:
            k = interceptor_kind(b)
            if k:
                hits.append({"kind": k, "signature": bundle_signature(b)})
        if hits:
            out[cid] = hits
    return out


# ---------------------------------------------------------------- 自己回帰（サガ型）

def _filter_matches(flt: dict, card) -> bool:
    """カード自身が移動の対象フィルタに適合するか（自分を蘇生できるか）。"""
    if not flt:
        return True
    types = set(card.types or [])
    if "types" in flt and not set(flt["types"]) <= types:
        return False
    if "races" in flt and not set(flt["races"]) & set(card.races or []):
        return False
    if "civs" in flt and not set(flt["civs"]) & set(card.civs or []):
        return False
    cost = card.cost
    if "cost_le" in flt and (cost is None or cost > flt["cost_le"]):
        return False
    if "cost_ge" in flt and (cost is None or cost < flt["cost_ge"]):
        return False
    if "cost_eq" in flt and cost != flt["cost_eq"]:
        return False
    return True


def saga_like(b, card) -> dict | None:
    """束がサガ型の自己回帰配線なら、適合の内訳を返す。

    必要な移動: draw (deck→hand)、(hand→graveyard)、(graveyard→bz)、
    (bz→graveyard, ref_self)。前提は「出た時」(move→bz, self) か「自分のターン開始」。
    蘇生フィルタへの自己適合は別に判定して self_ok に入れる（不適合でも配線としては記録する）。
    """
    p = b.prem
    if p is None or p.zone != "bz":
        return None
    if not ((p.kind == "move" and p.to == "bz" and p.subject == "self")
            or (p.kind == "turn_start" and p.player == "you")):
        return None
    has_draw = any(m.src == "deck" and m.dst == "hand" and m.draw for m in b.moves)
    has_discard = any(m.src == "hand" and m.dst == "graveyard" for m in b.moves)
    reanimate = [m for m in b.moves if m.src == "graveyard" and m.dst == "bz"]
    has_self_gy = any(m.src == "bz" and m.dst == "graveyard" and m.ref_self for m in b.moves)
    if not (has_draw and has_discard and reanimate):
        return None
    flt = reanimate[0].flt or {}
    self_ok = _filter_matches(flt, card)
    if has_self_gy and self_ok:
        tier = "strict"          # サガ本人と同型（全配線＋自己適合）
    elif self_ok:
        tier = "no_self_gy"      # 蘇生は自己適合だが、自分が墓地へ行く移動が無い
    elif has_self_gy:
        tier = "no_self"         # 配線はあるが蘇生フィルタが自分に合わない
    else:
        tier = "no_self_gy_no_self"
    return {"signature": bundle_signature(b), "reanimate_filter": flt,
            "self_ok": self_ok, "tier": tier}


def find_saga_like(by_card: dict, rules) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for cid, bundles in by_card.items():
        card = rules.cards[cid]
        hits = [h for b in bundles if (h := saga_like(b, card))]
        if hits:
            out[cid] = hits
    return out
