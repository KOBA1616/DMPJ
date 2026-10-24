"""取得済みの原文から、凡庸なカードを除き、ピーキーなカードを選ぶ（変換前の絞り込み）。基準は docs/card-selection.md。

    python tools/select_cards.py data/cards/raw/official_*.jsonl              # 点数順の一覧（理由つき）
    python tools/select_cards.py raw.jsonl --min-score 3 --ids > ids.txt      # 変換に回すIDだけ
    python tools/select_cards.py raw.jsonl --excluded                         # 除外されたものと理由

点数は原文の文字列だけで付ける粗い見積もり。LLM 変換のコストをかける価値があるかの足切りに使い、
最終的なコンボの強さの判断ではない（見落としを避けるため、迷う場合は点数を足す側に倒してある）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 括弧書きの注釈（キーワード能力の説明など）は点数に数えない
_PAREN = re.compile(r"[（(][^（()）]*[）)]")
KEYWORD_LINES = re.compile(
    r"^(ブロッカー|スピードアタッカー|W・ブレイカー|T・ブレイカー|Q・ブレイカー|S・トリガー|パワーアタッカー[+＋]?\d*|"
    r"マッハファイター|スレイヤー|シールド・トリガー|アンブロッカブル|ガードマン|革命0トリガー|"
    r"ジャストダイバー|ハンター|ブレイカー)\s*(\(.*\))?$")

# (名前, 正規表現, 点数)。ゾーン間移動は「移動の種類」ごとに別々に数える（補完し合う組み合わせを探すため）。
ZONE_MOVES = [
    ("墓地へ送る/置く", r"墓地に置|墓地へ", 1),
    ("墓地から戻す", r"墓地から.*(バトルゾーンに出|手札に|マナゾーンに|山札)", 2),
    ("マナ操作", r"マナゾーンから|マナゾーンに(置|加え)|マナを(破壊|墓地)", 1),
    ("シールド操作", r"シールド(ゾーン)?(から|に(置|加え)|を(手札|墓地|ブレイク))|シールドを.*見", 1),
    ("山札操作", r"山札の上から|山札を(見|シャッフル)|山札の(下|上)に置|山札から.*(出|置|加え)", 1),
    ("手札に戻す", r"手札に戻|持ち主の手札", 1),
    ("踏み倒し", r"コストを支払わずに|バトルゾーンに出(す|して|さ)", 2),
]
PEAKY = [
    ("自己再利用", r"(このクリーチャー|この呪文|このカード)[^。]*(墓地から|手札に戻)", 2),
    ("置換", r"かわりに|代わりに|置く時.*(置く|かわり)", 2),
    ("追加ターン/ターン操作", r"ターンを追加|追加の.*ターン|ターンの残り", 3),
    ("回数を数える/大量に", r"好きな数|すべて(の|を)|同じ数|枚数分|数だけ", 1),
    ("勝敗・山札切れ", r"ゲームに(負け|勝)|山札(が|の枚数が)(ない|0)|山札を.*すべて", 3),
    ("誘発の連鎖", r"(出た時|出たとき|破壊された時|破壊されたとき|攻撃する時|攻撃するとき|墓地に置かれた時|墓地に置かれたとき|ターンの終わり|ターン終了時)", 1),
    ("手札を増やす/タップ解除", r"(カードを|枚)[^。]*引|アンタップ|タップせずに", 1),
]
DEMERIT = [
    ("デメリット(禁止)", r"できない|できなくなる|使えない|出せない", 1),
    ("デメリット(自損)", r"自分の(クリーチャー|シールド|マナ|山札|手札)[^。]*(破壊|墓地|捨て|ブレイク)|捨てる|自分は[^。]*負け", 2),
    ("強いが縛り", r"このクリーチャーは[^。]*(攻撃|ブロック)できない|タップして置|出た時[^。]*(自分|このクリーチャー)を(破壊|墓地)", 1),
]
# 凡庸扱い: 能力が次のどれか1つだけ（点数が付いていても、これだけなら除外する）
PLAIN = [
    ("バニラ/キーワードのみ", None),
    ("単純なドロー", r"^カードを[１-９1-9]枚引(く|いてもよい)。?$"),
    ("単純な除去", r"^[^。]*(クリーチャー|相手のクリーチャー)を[１-９1-9]体(選び、)?(破壊する|持ち主の手札に戻す|タップする)。?$"),
    ("単純なマナ加速", r"^(自分の)?山札の上から[１-９1-9]枚をマナゾーンに置く。?$"),
    ("単純なパワー修整", r"^(このクリーチャーのパワーは|自分のクリーチャー(は|を))[^。]*[+＋]\d+。?$"),
]


def body_lines(text: str) -> list[str]:
    """括弧書きを除き、キーワード能力だけの行を落とした効果行を返す。"""
    out = []
    for line in text.splitlines():
        s = _PAREN.sub("", line).strip()
        if s and not KEYWORD_LINES.match(s):
            out.append(s)
    return out


def score(row: dict) -> tuple[int, list[str], str]:
    """(点数, 点数の理由, 除外理由)。除外理由が空でなければ除外。"""
    lines = body_lines(row.get("text", ""))
    if not lines:
        return 0, [], PLAIN[0][0]
    joined = "".join(lines)
    for name, pat in PLAIN[1:]:
        if len(lines) == 1 and re.match(pat, lines[0]):
            return 0, [], name
    pts, why = 0, []
    moves = []
    for name, pat, w in ZONE_MOVES:
        if re.search(pat, joined):
            pts += w
            moves.append(name)
            why.append(f"{name}+{w}")
    if len(moves) >= 2:    # 複数のゾーンをつなぐカードは補完の起点になる
        pts += len(moves) - 1
        why.append(f"複数ゾーン+{len(moves) - 1}")
    for name, pat, w in PEAKY + DEMERIT:
        if re.search(pat, joined):
            pts += w
            why.append(f"{name}+{w}")
    return pts, why, ("" if pts else "対象の語彙なし")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", nargs="+", type=Path, help="fetch_cards.py の出力（jsonl）")
    ap.add_argument("--min-score", type=int, default=3, help="この点数以上を選ぶ（既定 3）")
    ap.add_argument("--ids", action="store_true", help="選ばれたIDだけを出力する")
    ap.add_argument("--excluded", action="store_true", help="除外されたものと理由を出力する")
    a = ap.parse_args(argv)
    rows = {}
    for f in a.raw:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    scored = [(r, *score(r)) for r in rows.values()]
    if a.excluded:
        for r, pts, why, ex in scored:
            if ex or pts < a.min_score:
                print(f"{r['id']}\t{r.get('name', '')}\t{ex or f'{pts}点（足切り未満）'}")
        return
    picked = sorted((t for t in scored if not t[3] and t[1] >= a.min_score), key=lambda t: (-t[1], t[0]["id"]))
    for r, pts, why, _ in picked:
        print(r["id"] if a.ids else f"{r['id']}\t{pts}\t{r.get('name', '')}\t{' '.join(why)}")
    print(f"選択 {len(picked)}/{len(scored)} 件（--min-score {a.min_score}）", file=sys.stderr)


if __name__ == "__main__":
    main()
