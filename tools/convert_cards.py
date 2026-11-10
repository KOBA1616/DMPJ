"""公式テキスト（fetch_cards.py の jsonl）を効果DSLのカード定義に変換する（Claude API を使う）。

    export ANTHROPIC_API_KEY=...
    pip install anthropic
    python tools/convert_cards.py data/cards/raw/official_YYYYMMDD.jsonl --out data/cards/converted.yaml
    python tools/convert_cards.py data/cards/raw/by_product --workers 4 --order short --limit 200   # 大量変換
    python tools/convert_cards.py data/cards/raw --retry-rejects     # 語彙を足したあと、落ちたカードだけやり直す
    python tools/convert_cards.py raw.jsonl --only dm01-001 --dry-run     # プロンプトだけ表示

- 出力は defs.parse_card で検査する。通らなければエラー文を返して1回だけ直させ、それでも駄目なら
  --rejects のファイルに原文とエラーを書いて人に回す。
- 出力カードは source.review: pending。開発者モード（python -m dmsim.devserver）で動かして確かめ、
  approved / rejected を付ける。
- システムプロンプト（スキーマ・語彙・既存カードの例）は全カードで同じなのでキャッシュする。
- 既に data/cards/*.yaml にあるIDは飛ばす（途中で止めても続きから再開できる）。1枚ごとに保存する。
- 結果は --report（既定 data/cards/raw/convert_report.json）に件数・トークン・失敗理由の種類別集計を残す。
  API の一時的な失敗（レート制限など）は rejects に入れず、再実行で拾う。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from dmsim import cardstore, identity, schema  # noqa: E402
from dmsim.defs import DATA, DefError, dedupe_list, load_tables, parse_card  # noqa: E402
import rule_convert  # noqa: E402
from llm_offload.providers import CallTimeout  # noqa: E402
from llm_offload.providers import (  # noqa: E402,F401  無料モデル呼び出しは llm_offload に集約
    OPENCODE_DEFAULT, OPENCODE_FREE_MODELS, OPENCODE_URL, BadResponse, Fatal, OpenCodeCLI, OpenCodeLLM, Chain, GeminiLLM, LLM7LLM, OpenRouterLLM, check_free_model)

MODEL = "claude-opus-5-5"

INSTRUCTIONS = """\
あなたはデュエル・マスターズのカードテキストを、シミュレーター dmsim のカード定義（YAML）に変換する。

規則:
- 出力は ```yaml で囲んだ1枚分のカード定義（`cards:` の下の1要素と同じ形。先頭の `- ` は付けない）だけ。
- 語彙は下の JSON Schema・キーワード・マクロ・許可/禁止できる行為の一覧にあるものだけを使う。無い語を作らない。
- キーワード能力（ブロッカー、S・トリガー、W・ブレイカー など）は keywords に書き、説明文の括弧書きは無視する。
- known_keywords があるときは、それらのキーワードはルールで処理済み（text から除いてある）。keywords に入れ直さず、残りの text だけを変換する。
- 「〜できない」は static の mod.deny、「〜できる」は mod.allow。「〜してもよい」は op: may。
- 進化は types に evolution を含め evolve_from に進化元の条件を書く。ツインパクトは faces に2面を書く。
- カードの種類: クリーチャーは creature、呪文は spell、タマシードは tamaseed、フィールドは field、クロスギアは cross_gear（実行するとバトルゾーンに出る）。D2フィールドは ["field", "d2_field"] と併記する（D2だけを指すフィルタは {types: [d2_field]}。一意性はルール側の処理）。「タマシード/クリーチャー」は両方を types に書く。サイキック・GR・超次元・ドラグハートはオリジナルフォーマットでは使わないので変換しない（取り込み側で飛ばす）。他の種類（オーラ・城 など）は未対応なので、近似せず source.unsupported に書く。
- 革命チェンジ・ニンジャ・ストライク等の宣言は kind: declare（既存カードの例に倣う）。
- 「このクリーチャーで攻撃する代わりに、タップして次の能力を使ってもよい」（タップ能力）は kind: activate、cost: {tap: self}、effect に続く効果文の ops（攻撃ができない間は使えない。召喚酔い含む）。「バトルゾーンにある自分の光のクリーチャーをタップし、攻撃する代わりに次の能力を使ってもよい」は cost: {tap: {civs: [light]}}（条件に合う自分のクリーチャー1体をタップ）。
- クロスギアは types: [cross_gear]。「クロスギア:このカードをバトルゾーンに置く。…コストをもう一度支払う。…バトルゾーンに残る。」の定型文はエンジンの規則（303）で処理済みなので abilities に書かない（text には残す）。「これをクロスしたクリーチャー」は、常在型が `kind: static, affects: crossed, mod: {...}`（パワー修整・キーワード付与）、誘発型が `when: {…, subject: crossed}`、効果の対象が `select: {ref: crossed}`。
- ウェーブストライカーは keywords: [wave_striker]（印だけ）。続く能力は、能力ごとに `if: {cmp: [{count: {zone: bz, owner: any, other: true, filter: {keyword: wave_striker}}}, ">=", 2]}` を付けて書く（常在型・誘発型どちらも。「他に」の数は原文に「自分の」が無いので owner: any）。
- known_keywords に wave_striker があるときは、残りの text の能力すべてに上記の if を付ける（付け忘れると常時働く誤変換になる）。
- サイレントスキルは keywords: [silent_skill]（印）と、続く効果文を `kind: silent, effect: [...]`（自分のターンのはじめにタップされていたら、アンタップしないかわりに使ってもよい。ルール 501.1a で処理済み）。
- ターボラッシュは keywords: [turbo_rush]（印。ルール側が「自分の他のクリーチャーがシールドをブレイクしたあと」にそのターン中だけ印を付ける）。続く能力すべてに `if: {self_marked: turbo_rush}` を付ける（付け忘れると常時働く誤変換になる）。
- 「攻撃された時」は `when: {event: attack, target: self}`（このクリーチャーが攻撃先）、「自分のクリーチャーが攻撃された時」は `target: {owner: you}`（他のクリーチャーだけなら other: true も）。攻撃された側は `select: {ref: event.target}`。「ブロックされた時」は `when: {event: block, attacker: self}`、攻撃クリーチャーは `ref: event.attacker`。
- サイクロンは keywords: [cyclone]（呪文。エンジンが「唱える直前に召喚していたか」を見て、唱えた後に手札へ戻す）。「自分が唱える呪文はすべてサイクロンを得る」は static、affects: {zone: hand, owner: you, filter: {types: [spell]}}、mod: {grant: [cyclone]}。
- S・バックは文明ごとのキーワード（s_back_light / s_back_water / s_back_darkness / s_back_fire / s_back_nature）を keywords に書く（実行は召喚か詠唱かカードの種類で決まる）。続く能力・呪文はそのまま書く。
- キズナプラスは keywords: [kizuna_plus] と書き、自身の[P]能力は `kind: partner, effect: [...]` で書く（キズナと同じ。[P]は単独では機能せず、キズナ／キズナプラスで「使う」ことで解決する）。
- 「このクリーチャーがリンクした時／ゴッドとリンクした時」は `kind: trigger, when: {event: link_established, subject: self}` と書く（リンク手順の完了後に、リンクされる側＝既に場にいたゴッドも含めグループ全員が誘発する）。「カードN枚でリンクした時」は能力の `if: {cmp: [{link_count: self}, ">=", N]}` を付ける。ただし「バトルゾーンに出した時、またはこのクリーチャーがゴッドとリンクした時」のように出た時と一体の能力は、リンクした状態で出た時の誘発回数（1回か2回か）の公式裏取りが取れていないため変換しない（能力ごと source.unsupported に need: link_establish_event で残す）。
- 進化GV（進化元をちょうどN体重ねる）は evolve_from に条件（races に複数並べると「いずれか」）を書き、`evolve_count: 3` を付ける。
- 水晶ソウルN（このカードを召喚／唱える時、自分のマナゾーンにある裏向きのカードのマナの数字はNになる）は面の宣言 `crystal_soul: N` と書く（キーワード欄には書かない。裏向きマナは無色のまま＝文明は得ない）。「自分の手札にある〜すべてに『水晶ソウルN』を与える」は常在型 `kind: static, affects: {zone: hand, owner: you, filter: {...}}, mod: {crystal_soul: N}` と書く。
- メテオバーン（下のカードを墓地に置いてもよい。そうした場合〜）は trigger の effect に `op: may` を置き、body の最初に `{op: move, select: {under_of: self, count: 1}, to: graveyard, reason: put, as: paid}`、続けて `{op: if, cond: {exists: {ref: paid}}, then: [...]}` で「そうした場合」の効果を書く（下のカードが無ければ後続は行わない）。条件のない「下のカードを出す／手札に加えてもよい」は may の body に move だけ。発動の時期は when で表す（「このクリーチャーが攻撃する時」= subject: self、「クリーチャーが攻撃する時」= subject: {owner: any}、「相手のクリーチャーが攻撃する時」= subject: {owner: opp}）。「攻撃できる時」「呪文の効果が実行される時」は語彙が無いので unsupported。
- ダイナモは keywords: [dynamo]（攻撃できる時の起動と、バトルが始まる時の誘発はルール側が持つ。パワーと能力はそのターンの終わりまで他のダイナモ1体に加わる）。カード側に書くのは残りの能力だけ。「ブロックされなかった時」は語彙が無いので unsupported。
- 攻撃・ブロックの強制は static の mod.require（[attack] / [block]）。「毎ターン攻撃しなければならない」「相手のクリーチャーが攻撃する時、可能であればブロックする」はルールで変換済み。条件つきの強制（次のターンだけ等）は mod.require に条件が書けないので unsupported。
- text には原文から括弧書きの注釈を除いたものを「 / 」区切りで書く。
- 「コストを支払わずに召喚する／唱える」は op: play_free（召喚・唱えたことになり、「召喚した時」「唱えた時」が誘発する）。「バトルゾーンに出す／置く」（ヘブンズ・ゲート型、墓地・マナ・手札から出す、置換で出す）は召喚ではないので op: move, to: bz, reason: put（play_free や reason: summon は使わない。112.3g, 603.5a）。
- 近似・代用はしない。語彙で原文どおりに表せない効果は、似た別の語彙（op・mod・条件）で置き換えて書かない。その能力は abilities に書かず、source.unsupported に [{need: <足せばよい op・語彙の案（英語の識別子）>, text: <該当する原文>}] で書く。表せる他の能力は通常どおり変換する。
  「ほぼ同じ」「この場面では同じ結果」と思っても代用しない（例: 他のカードの効果の対象条件を書き換える置換を、無条件の置換や別の効果で書かない）。語彙の追加は人が行い、足りない語彙は unsupported の集計から決める。unsupported があるカードは登録されず（rejects に vocab として残る）、語彙が足りるようになってから変換し直す。
- 表せない能力を黙って落とさない。落とした能力は必ず unsupported に残す。source.notes には、原文の曖昧さや確認してほしい点だけを日本語で具体的に書く（近似の言い訳には使わない）。
- source は {official: <id>, review: pending} とし、必要なら notes を足す。
- 「攻撃中、パワー+N」は mod.power_when（when: attacking）、「ブロック中、パワー+N」は when: blocking（プレイヤーを攻撃している間も含む。count で「1体につき」）。「バトル中」だけ上がる（ハンティング等）は mod.battle_power。
- 原文の表現が古い（例: 「墓地に置く」）場合も原文どおりに変換し、気づいた点は notes に書く。
"""


def _rules_text(name: str) -> str:
    return (DATA / "rules" / name).read_text(encoding="utf-8")


def _strip_yaml_comments(text: str) -> str:
    """YAML のコメント行（インデントの後に # で始まる行）を取り除く。コメントは人間向けの
    注釈でデータではないので、パース結果は変わらない（tests/test_tools.py で照合している）。"""
    return "".join(l for l in text.splitlines(keepends=True) if not l.strip().startswith("#"))


def _prompt_rules_text(name: str) -> str:
    """プロンプトに埋める用。ルールのデータはそのままに、コメント行だけ除いて量を減らす。"""
    return _strip_yaml_comments(_rules_text(name))


def examples_text(exclude: frozenset = frozenset()) -> str:
    """例に載せる既存カード。exclude の ID は除く（一致率の測定で答えを見せないため）。"""
    raw = (DATA / "cards" / "real.yaml").read_text(encoding="utf-8")
    if not exclude:
        return raw
    cards = [c for c in yaml.safe_load(raw)["cards"] if c["id"] not in exclude]
    return yaml.safe_dump({"cards": cards}, allow_unicode=True, sort_keys=False)


def _bigrams(t: str) -> set:
    t = re.sub(r"\s+", "", t or "")
    return {t[i:i + 2] for i in range(len(t) - 1)}


def examples_for(row: dict, n: int, exclude: frozenset = frozenset()) -> str:
    """原文が近い既存カードを n 枚だけ選ぶ（文字2-gram の重なり）。無料モデルに渡す量を減らすため。"""
    cards = [c for c in yaml.safe_load((DATA / "cards" / "real.yaml").read_text(encoding="utf-8"))["cards"]
             if c["id"] not in exclude and c["id"] != row.get("id")]
    q = _bigrams(" ".join(filter(None, [row.get("text", ""), *[f.get("text", "") for f in row.get("faces") or []]])))

    def score(c):
        b = _bigrams(c.get("text", ""))
        return len(q & b) / (len(q | b) or 1)
    top = sorted(cards, key=score, reverse=True)[:n]
    return yaml.safe_dump({"cards": top}, allow_unicode=True, sort_keys=False)


def system_prompt(exclude: frozenset = frozenset(), row: dict | None = None, n_examples: int = 0) -> str:
    """共通の部分。row と n_examples を渡すと、例をそのカードに近い n 枚だけにする（0 なら全部。全カード同じ文字列になる）。"""
    ex = examples_for(row, n_examples, exclude) if row is not None and n_examples else examples_text(exclude)
    parts = [INSTRUCTIONS,
             "## JSON Schema\n" + json.dumps(schema.build(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
             *[f"## data/rules/{n}\n{_prompt_rules_text(n)}" for n in
               ("zones.yaml", "keywords.yaml", "op_macros.yaml", "permissions.yaml", "turn.yaml")],
             "## 変換済みカードの例（data/cards/real.yaml）\n" + ex]
    return "\n\n".join(parts)


# モデルに渡す項目。フレーバー・イラストレーター・レアリティ・取得時の印などは効果と無関係なので渡さない
PROMPT_FIELDS = ("id", "name", "card_type", "civilization", "cost", "power", "race", "mana", "text", "known_keywords")


def prompt_row(row: dict) -> dict:
    out = {k: row[k] for k in PROMPT_FIELDS if k in row}
    if row.get("faces"):
        out["faces"] = [{k: f[k] for k in PROMPT_FIELDS if k in f} for f in row["faces"]]
    return out


def user_prompt(row: dict) -> str:
    return "次のカードを変換してください。\n\n" + json.dumps(prompt_row(row), ensure_ascii=False, indent=1)


def extract(text: str) -> dict:
    m = re.search(r"```ya?ml\s*\n(.*?)```", text, re.S)
    raw = yaml.safe_load(m.group(1) if m else text)
    if isinstance(raw, list) and len(raw) == 1:
        raw = raw[0]
    if isinstance(raw, dict) and "cards" in raw:
        raw = raw["cards"][0]
    if not isinstance(raw, dict):
        raise DefError("出力が1枚分のカード定義（mapping）になっていない")
    return raw


def validate(raw: dict, row: dict, tables) -> dict:
    if raw.get("id") != row["id"]:
        raise DefError(f"id が {row['id']} になっていない: {raw.get('id')}")
    if raw.get("abilities"):
        raw["abilities"] = dedupe_list(raw["abilities"])    # 同じ能力が二重に入る変換（誘発が2回起きる）を、どの変換経路でも入口で除く
    parse_card(raw, tables)
    src = raw.setdefault("source", {})
    src["official"] = row["id"]
    src["review"] = "pending"      # LLM の出力は必ず人の確認待ちにする
    al = identity.aliases_for(row.get("name", ""), row["id"])
    if al:
        src["aliases"] = al        # 同名の古い版のID（旧IDから最新版を引くため）
    return raw


class AnthropicLLM:
    name = "anthropic"

    def __init__(self, model: str = MODEL, client=None):
        if client is None:
            import anthropic    # 変換するときだけ必要
            client = anthropic.Anthropic()
        self.client, self.model = client, model

    def complete(self, sysp: str, messages: list[dict], effort: str, usage: dict | None) -> str:
        with self.client.messages.stream(
            model=self.model, max_tokens=16000,
            system=[{"type": "text", "text": sysp, "cache_control": {"type": "ephemeral"}}],
            thinking={"type": "adaptive"}, output_config={"effort": effort}, messages=messages,
        ) as stream:
            msg = stream.get_final_message()
        if msg.stop_reason == "refusal":
            raise DefError("モデルが変換を断った")
        u = msg.usage
        if usage is not None:
            usage["input"] += u.input_tokens
            usage["cache_read"] += u.cache_read_input_tokens or 0
            usage["cache_write"] += u.cache_creation_input_tokens or 0
            usage["output"] += u.output_tokens
        return "".join(b.text for b in msg.content if b.type == "text")


def make_llm(provider: str, model: str | None, interval: float):
    if provider == "opencode":
        return OpenCodeLLM(model or OPENCODE_DEFAULT, interval)
    if provider == "opencode-cli":
        llm = OpenCodeCLI(model or OPENCODE_DEFAULT, interval)
        # OpenCode 全滅時の切り替え先。Gemini・OpenRouter はキーがあるときだけ、LLM7 は匿名で（DMPJ_NO_LLM7=1 で無効）
        llm.external = Chain(GeminiLLM(interval) if os.environ.get("GEMINI_API_KEY") else None,
                             OpenRouterLLM(interval) if os.environ.get("OPENROUTER_API_KEY") else None,
                             None if os.environ.get("DMPJ_NO_LLM7") else LLM7LLM(interval))
        return llm
    return AnthropicLLM(model or MODEL)


def pack_prompt(rows: list[dict]) -> str:
    return (f"次の{len(rows)}枚のカードをまとめて変換してください。出力は ```yaml の中に cards: のリストを1つだけ書き、"
            "各要素を1枚分のカード定義にする（id は入力と同じ。順番も同じ）。\n\n"
            + "\n\n".join(json.dumps(prompt_row(r), ensure_ascii=False, indent=1) for r in rows))


def convert_pack(llm, rows: list[dict], sysp, effort: str, usage: dict | None = None) -> dict[str, str]:
    """複数枚を1回の呼び出しで変換する。返すのは {id: そのカード1枚分の YAML 文}（検査はしない。呼び出し側が1枚ずつ検査する）。
    読み取れなかったカードは含めない（呼び出し側が単独の呼び出しにフォールバックする）。"""
    text = llm.complete(sysp(rows[0]) if callable(sysp) else sysp, [{"role": "user", "content": pack_prompt(rows)}], effort, usage)
    m = re.search(r"```ya?ml\s*\n(.*?)```", text, re.S)
    try:
        raw = yaml.safe_load(m.group(1) if m else text)
    except yaml.YAMLError:
        return {}
    items = raw.get("cards") if isinstance(raw, dict) else raw
    want = {r["id"] for r in rows}
    out = {}
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict) and it.get("id") in want and it["id"] not in out:
            out[it["id"]] = yaml.safe_dump(it, allow_unicode=True, sort_keys=False)
    print(f"  まとめ変換 {len(rows)}枚 → {len(out)}枚読み取り", file=sys.stderr)
    return out


def convert(llm, row: dict, tables, sysp: str, effort: str, usage: dict | None = None, first: str | None = None) -> dict:
    """first: まとめ変換で得た1枚分の出力。あれば最初の呼び出しの代わりに使い、検査に落ちたときだけ単独の呼び出しで直す。"""
    messages = [{"role": "user", "content": user_prompt(row)}]
    err = None
    for attempt in range(2):
        if attempt == 0 and first is not None:
            text = first
        else:
            text = llm.complete(sysp(row) if callable(sysp) else sysp, messages, effort, usage)
        print(f"  {row['id']}: {len(text)}文字", file=sys.stderr)
        try:
            return validate(extract(text), row, tables)
        except (DefError, yaml.YAMLError, KeyError, TypeError) as e:
            err = e
            messages += [{"role": "assistant", "content": text},
                         {"role": "user", "content": f"検査でエラーになった。直した定義だけを出力して。\n{e}"}]
    raise DefError(f"2回とも検査を通らなかった: {err}")


def merge_split(card: dict, r: dict, part) -> dict:
    """ルールで先に処理したキーワード・能力（rule_convert.split の結果）を、モデルが返したカードに戻す。"""
    card["keywords"] = [*part[0], *[k for k in card.get("keywords") or [] if k not in part[0]]]
    if not card["keywords"]:
        del card["keywords"]
    if part[2]:
        card["abilities"] = dedupe_list([*part[2], *(card.get("abilities") or [])])     # モデルがルール処理済みの能力を重ねて返しても二重にしない
    card["text"] = r["text"]
    return card


def load_rows(inputs: list[str]) -> list[dict]:
    """jsonl のパス・ディレクトリ・glob から原文の行を読む（同じIDは後のものを採る）。rejects は入力に含めない。"""
    files: list[Path] = []
    for spec in inputs:
        p = Path(spec)
        if p.is_dir():
            files += sorted(p.rglob("*.jsonl"))
        elif p.exists():
            files.append(p)
        else:
            files += sorted(Path(".").glob(spec))
    rows: dict[str, dict] = {}
    for f in files:
        if f.name.startswith("rejects"):
            continue
        for s in f.read_text(encoding="utf-8").splitlines():
            if s.strip():
                r = json.loads(s)
                r.pop("error", None)
                rows[r["id"]] = r
    return identity.canonical_rows(list(rows.values()))      # 同名の古い版は変換しない（最新版だけ）


def known_ids(out: Path) -> set[str]:
    ids: set[str] = set()
    from dmsim.cardfiles import card_files
    for f in card_files():
        ids |= {c["id"] for c in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("cards") or []}
    return ids


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()] if path.exists() else []


def write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def triage(rejects: list[dict]) -> dict:
    """検査を通らなかった理由を種類ごとに数える（足すべき語彙の見当をつける）。"""
    from report_gaps import categorize
    by_kind: dict[str, dict] = {}
    for r in rejects:
        for part in filter(None, (p.strip() for p in r.get("error", "").split("\n"))):
            kind, term = categorize(part)
            by_kind.setdefault(f"{kind}:{term}", {"n": 0, "ids": []})
            g = by_kind[f"{kind}:{term}"]
            if r["id"] not in g["ids"]:
                g["n"] += 1
                g["ids"].append(r["id"])
    return dict(sorted(by_kind.items(), key=lambda kv: -kv[1]["n"]))


def classify(error: str) -> dict:
    """検査落ちの理由を返す。語彙が足りない(未知の op・キー・名前など)なら reason=vocab_gap と不足語彙 gaps を付ける。"""
    from report_gaps import categorize
    gaps = []
    for part in filter(None, (p.strip() for p in error.split("\n"))):
        kind, term = categorize(part)
        if kind not in ("拒否", "id不一致", "その他"):
            gaps.append(f"{kind}:{term}")
    return {"reason": "vocab_gap", "gaps": gaps} if gaps else {"reason": "other", "gaps": []}


OUT_OF_FORMAT = ("サイキック", "GR", "ドラグハート", "超次元")      # オリジナルフォーマットでは使わない種類（実装しない）


def vocab_reject(card: dict, row: dict) -> dict | None:
    """語彙が足りず表せない効果（source.unsupported）のあるカードは、converted に登録せず rejects へ回す（定義は partial に残す）。"""
    gaps = [str(u.get("need", "?")) for u in (card.get("source") or {}).get("unsupported") or [] if isinstance(u, dict)]
    if not (card.get("source") or {}).get("unsupported"):
        return None
    return {**row, "reason": "vocab", "gaps": gaps, "partial": card,
            "error": "\n".join(f"語彙不足: {g}" for g in gaps) or "語彙不足（unsupported の申告あり）"}


def precheck(row: dict) -> dict | None:
    """モデルを呼ぶ前に、原文がそもそも変換できる状態か見る。ダメなら理由を返す（API も時間も使わない）。

    fetch_incomplete: 取得が空ページ・項目欠け（名前・種類・文明・コストが無い）→ 再取得が要る。
    no_text: どの面にも能力文が無い → 変換の対象外（語彙不足ではない）。
    2026-10-26 のタイムアウト8件はすべてこの状態だった（応答を待って20分ずつ無駄にした）。
    """
    if {"name", "card_type", "civilization", "cost"} & set(row.get("missing") or []):
        return {"reason": "fetch_incomplete", "gaps": [], "error": "原文の取得が空ページ・項目欠け（再取得が必要）"}
    types = [row.get("card_type", ""), *[f.get("card_type", "") for f in row.get("faces") or []]]
    if any(k in str(t) for t in types for k in OUT_OF_FORMAT):
        return {"reason": "out_of_format", "gaps": [], "error": "オリジナルフォーマットでは使わない種類（サイキック・GR・超次元・ドラグハート）。変換しない"}
    if not row.get("text") and not any(f.get("text") for f in row.get("faces") or []):
        return {"reason": "no_text", "gaps": [], "error": "能力文が無い（変換対象外。語彙不足ではない）"}
    return None


CONVERTED_HEADER = "# convert_cards.py の出力（review: pending）。確認後に real.yaml へ移す。\n"


def run_rules(rows: list[dict], tables, out: Path, rejects_path: Path) -> dict:
    """ルールだけで完全に変換できる行（辞書のキーワード・定型文・同一原文の写し）を、モデルを呼ばずにまとめて out へ登録する。
    変換済み・検査落ちの行は対象にしない（検査落ちでもルール変換できるようになったものは戻す）。
    モデルのジョブに積む前の前処理で、枚数の上限は設けない。"""
    cards = cardstore.read(out)
    done = known_ids(out) | {c["id"] for c in cards}
    rejects = {r["id"]: r for r in read_jsonl(rejects_path)}
    stats = {"requested": 0, "ok": 0, "by_rule": 0, "by_copy": 0, "invalid": 0}
    for r in rows:
        if r["id"] in done:
            continue
        if (precheck(r) or {}).get("reason") == "out_of_format":
            continue
        stats["requested"] += 1
        rc, kind = rule_convert.convert(r), "by_rule"
        if rc is None:
            rc, kind = rule_convert.reuse_same_text(r, cards), "by_copy"
        if rc is None:
            continue
        try:
            rc = validate(rc, r, tables)
        except DefError as e:
            stats["invalid"] += 1
            print(f"  {r['id']}: ルール変換が検査を通らなかったのでモデルへ回す: {e}", file=sys.stderr)
            continue
        cards.append(rc)
        done.add(r["id"])
        rejects.pop(r["id"], None)
        stats["ok"] += 1
        stats[kind] += 1
    if stats["ok"]:
        cardstore.write(out, cards, CONVERTED_HEADER)
        write_jsonl(rejects_path, list(rejects.values()))
    return stats


def run(rows: list[dict], client, tables, sysp: str, effort: str, out: Path, rejects_path: Path,
        workers: int = 1, report_path: Path | None = None, pack: int = 1) -> dict:
    """rows を変換して out に追記する。1枚ごとに保存するので途中で止まっても続きから再開できる。
    検査を通らなかったカードは rejects に（成功したIDは rejects から消す）、APIの一時的な失敗は数えるだけで記録しない。"""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock()
    cards = cardstore.read(out)
    rejects = {r["id"]: r for r in read_jsonl(rejects_path)}
    usage = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
    stats = {"ok": 0, "rejected": 0, "api_error": 0}
    api_errors: list[dict] = []

    def save():
        cardstore.write(out, cards, CONVERTED_HEADER)
        write_jsonl(rejects_path, list(rejects.values()))

    pending_timeouts: list[dict] = []   # 次のカードが成功したら reason: timeout で確定する（連続2回なら障害とみなして確定しない）
    streak = {"n": 0}      # 連続したAPI失敗（2回で打ち切り）。無料枠の制限(429)に当たったら残りを打たずに止める

    packed: dict[str, str] = {}      # まとめ変換で得た {id: 1枚分の出力}

    def model_row(r):
        part = rule_convert.split(r)
        return {**r, "text": part[1], "known_keywords": part[0]} if part else r

    def prefetch():
        """ルール・写し・事前検査で片づかないカードを pack 枚ずつ1回の呼び出しで変換する（失敗した分は単独の呼び出しに回る）。"""
        todo = []
        for r in rows:
            if rule_convert.convert(r) is not None or precheck(r) or rule_convert.reuse_same_text(r, cards) is not None:
                continue
            todo.append(model_row(r))
        for i in range(0, len(todo), pack):
            grp = todo[i:i + pack]
            if len(grp) < 2:
                break
            try:
                packed.update(convert_pack(client, grp, sysp, effort, usage))
            except Fatal:
                raise
            except Exception as e:      # noqa: BLE001  まとめが使えない時は単独に任せる（API 失敗の数え方は単独側に任せる）
                print(f"  まとめ変換に失敗したので単独で続ける: {type(e).__name__}", file=sys.stderr)
                return

    def one(r):
        rc = rule_convert.convert(r)      # キーワードだけ・バニラは、辞書のルールで作る（モデルを呼ばない＝トークン0）
        if rc is not None:
            try:
                rc = validate(rc, r, tables)
            except DefError as e:
                print(f"  {r['id']}: ルール変換が検査を通らなかったのでモデルへ回す: {e}", file=sys.stderr)
            else:
                with lock:
                    stats["ok"] += 1
                    print(f"✓ {r['id']} {r.get('name', '')} (ルール変換・モデル不使用)", file=sys.stderr, flush=True)
                    cards.append(rc)
                    rejects.pop(r["id"], None)
                    save()
                return
        with lock:
            same = rule_convert.reuse_same_text(r, cards)      # 原文が同じ変換済みカードがあれば能力を写す（モデルを呼ばない）
        if same is not None:
            try:
                same = validate(same, r, tables)
            except DefError as e:
                print(f"  {r['id']}: 同一原文の写しが検査を通らなかったのでモデルへ回す: {e}", file=sys.stderr)
            else:
                with lock:
                    stats["ok"] += 1
                    print(f"✓ {r['id']} {r.get('name', '')} (同一原文の写し・モデル不使用)", file=sys.stderr, flush=True)
                    cards.append(same)
                    rejects.pop(r["id"], None)
                    save()
                return
        if streak["n"] >= 2:
            return
        pre = precheck(r)
        if pre:
            with lock:
                stats["rejected"] += 1
                rejects[r["id"]] = {**r, **pre}
                print(f"- {r['id']} {r.get('name', '')}: {pre['reason']}（モデルは呼ばない）", file=sys.stderr, flush=True)
                save()
            return
        print(f"… {r['id']} {r.get('name', '')} 変換中", file=sys.stderr, flush=True)
        part = rule_convert.split(r)      # キーワード能力はルールで処理し、残りの原文だけをモデルに渡す
        try:
            card = convert(client, {**r, "text": part[1], "known_keywords": part[0]} if part else r, tables, sysp, effort, usage,
                           first=packed.pop(r["id"], None))
            if part:
                merge_split(card, r, part)
            validate(card, r, tables)
            vr = vocab_reject(card, r)
            if vr:      # 語彙が足りないカードは登録しない（近似した定義で動かさない）。足りない語彙は gaps に出る
                with lock:
                    stats["rejected"] += 1
                    streak["n"] = 0
                    rejects[r["id"]] = vr
                    print(f"- {r['id']} {r.get('name', '')}: {vr['error']}（登録しない）", file=sys.stderr, flush=True)
                    save()
                return
        except DefError as e:
            with lock:
                stats["rejected"] += 1
                rejects[r["id"]] = {**r, "error": str(e), **classify(str(e))}
                print(f"✗ {r['id']} {r.get('name', '')}: {e}", file=sys.stderr)
                save()
            return
        except Fatal:
            raise
        except CallTimeout as e:    # 長い上限でも終わらない。無料枠の停止と区別するため、次のカードが成功するまで確定しない
            with lock:
                stats["api_error"] += 1
                streak["n"] += 1
                pending_timeouts.append({**r, "error": str(e), "reason": "timeout", "gaps": []})
                api_errors.append({"id": r["id"], "error": f"CallTimeout: {e}"[:300]})
                print(f"⏱ {r['id']} {r.get('name', '')}: {e}", file=sys.stderr, flush=True)
            return
        except Exception as e:      # noqa: BLE001  API の一時的な失敗。カードの問題ではないので rejects には入れない
            with lock:
                stats["api_error"] += 1
                streak["n"] += 1
                api_errors.append({"id": r["id"], "error": f"{type(e).__name__}: {e}"[:300]})
                print(f"! {r['id']} API失敗: {type(e).__name__}" + (f"（{e}）" if type(e).__name__ == "FreeLimit" else ""), file=sys.stderr)
            return
        with lock:
            stats["ok"] += 1
            streak["n"] = 0
            for t in pending_timeouts:
                stats["rejected"] += 1
                rejects[t["id"]] = t
            pending_timeouts.clear()
            print(f"✓ {r['id']} {r.get('name', '')} ({stats['ok'] + stats['rejected'] + stats['api_error']}/{len(rows)})", file=sys.stderr, flush=True)
            cards.append(card)
            rejects.pop(r["id"], None)
            save()

    if pack > 1:
        prefetch()
    if workers > 1:
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(one, rows))
    else:
        for r in rows:
            one(r)
    report = {"requested": len(rows), **stats, "usage": usage, "triage": triage(list(rejects.values())),
              "api_errors": api_errors}
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", nargs="+", help="原文の jsonl（複数・ディレクトリ・glob 可。data/cards/raw/by_product など）")
    ap.add_argument("--out", default=str(cardstore.converted_path(DATA)))
    ap.add_argument("--rejects", default=str(DATA / "cards" / "raw" / "rejects.jsonl"))
    ap.add_argument("--report", default=str(DATA / "cards" / "raw" / "convert_report.json"),
                    help="実行結果（件数・トークン・失敗の種類別集計）の出力先")
    ap.add_argument("--only", nargs="*", help="このIDだけ変換する")
    ap.add_argument("--retry-rejects", action="store_true", help="前回検査を通らなかったカードだけをもう一度変換する")
    ap.add_argument("--limit", type=int, help="この枚数まで変換する（試運転・予算の上限用）")
    ap.add_argument("--order", choices=["file", "short"], default="file", help="short: 原文の短い順（簡単なものから）")
    ap.add_argument("--workers", type=int, default=1, help="並列数（API のレート制限に合わせる）")
    ap.add_argument("--pack", type=int, default=1, help="1回の呼び出しでまとめて変換する枚数（1=従来どおり1枚ずつ。指示文を共有してトークンを減らす）")
    ap.add_argument("--provider", choices=["anthropic", "opencode", "opencode-cli"], default="anthropic",
                    help="opencode は無料モデル専用（OPENCODE_API_KEY、許可リスト外のモデルは拒否）")
    ap.add_argument("--model", help="モデルID（既定: anthropic は claude-opus-5-5、opencode は glm-5.3-flash-free）")
    ap.add_argument("--interval", type=float, default=3.0, help="opencode のリクエスト間隔（秒、全ワーカー合計）")
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--dry-run", action="store_true", help="API を呼ばずにプロンプトと対象枚数を表示する")
    a = ap.parse_args(argv)
    rows = load_rows(a.raw)
    out, rejects_path = Path(a.out), Path(a.rejects)
    if a.only:
        rows = [r for r in rows if r["id"] in a.only]
    if a.retry_rejects:
        failed = {r["id"] for r in read_jsonl(rejects_path)}
        rows = [r for r in rows if r["id"] in failed]
    else:
        done = known_ids(out) | {c["id"] for c in cardstore.read(out)}
        rows = [r for r in rows if r["id"] not in done]
    if a.order == "short":
        rows.sort(key=lambda r: len(r.get("text", "")))
    if a.limit:
        rows = rows[:a.limit]
    sysp = system_prompt()
    if a.dry_run:
        print(sysp)
        for r in rows:
            print("\n---\n" + user_prompt(r))
        print(f"\n対象 {len(rows)} 枚（システムプロンプト {len(sysp)} 文字）", file=sys.stderr)
        return
    try:
        llm = make_llm(a.provider, a.model, a.interval)
        report = run(rows, llm, load_tables(), sysp, a.effort, out, rejects_path,
                     a.workers, Path(a.report), pack=a.pack)
    except Fatal as e:
        sys.exit(f"停止: {e}")
    print(f"変換 {report['ok']}/{report['requested']} 件、検査を通らず {report['rejected']} 件（{a.rejects}）、"
          f"API失敗 {report['api_error']} 件（再実行で続きから）。不足語彙の集計: python tools/report_gaps.py", file=sys.stderr)


if __name__ == "__main__":
    main()
