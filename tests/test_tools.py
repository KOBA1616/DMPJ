"""記録の保存・再生、開発者モードのAPI、取得・変換ツール（ネットワークなし）の検証。"""
import json
import random
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from conftest import answer

from dmsim.engine import scenario as sc
from dmsim.devserver import App, set_review
from dmsim.engine.play import default_decks, make_record, random_policy, replay_record, run

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def test_record_roundtrip(rules):
    """シード＋選択ログの記録は JSON を通しても同じ最終状態（digest）に戻る。"""
    decks = default_decks(rules, "dm")
    from dmsim import Engine
    eng = Engine.new_game(rules, decks, 5)
    rng = random.Random(5)
    run(eng, [random_policy(rng), random_policy(rng)])
    rec = json.loads(json.dumps(make_record(eng, decks, 5)))
    assert replay_record(rules, rec).s.digest() == rec["digest"]
    rec["log"][-1]["choice"] = [0] if rec["log"][-1]["choice"] != [0] else [1]
    with pytest.raises((ValueError, RuntimeError, Exception)):
        replay_record(rules, rec)


def test_record_from_scenario(rules):
    """シナリオから始めた対戦も記録から再現できる。途中（LKI を含む状態）でも digest を取れる。"""
    spec = sc.try_card(rules, "dm01-080")
    e = sc.build(rules, spec)
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm01-080")
    e.advance()
    e.s.digest()                         # 誘発の待機中（LKI がタスクに入っている）
    from dmsim.engine.play import deck_lists
    rec = json.loads(json.dumps(make_record(e, deck_lists(e), 1, scenario=spec)))
    assert replay_record(rules, rec, strict=False).s.digest() == rec["digest"]


def test_devserver_session_and_undo(rules):
    """開発者モード: 相手は自動で何もしない。1手戻すと同じ局面に戻る。"""
    app = App()
    v = app.handle("/api/new", {"scenario": sc.try_card(rules, "dm01-080")})
    gid = v["gid"]
    keys = lambda v: [o["key"] for o in v["decision"]["options"]]  # noqa: E731
    v = app.handle("/api/answer", {"gid": gid, "choice": [keys(v).index("pass")]})
    v = app.handle("/api/answer", {"gid": gid, "choice": [keys(v).index("play:dm01-080")]})
    assert v["decision"]["kind"] == "yes_no"
    before = v["digest"]
    v = app.handle("/api/answer", {"gid": gid, "choice": [keys(v).index("yes")]})
    assert v["decision"]["player"] == 0 and v["turn"] == 3       # 相手のターンは自動で進む
    assert any("hand → bz" in c for h in v["history"] for c in h["changes"])
    v = app.handle("/api/undo", {"gid": gid})
    assert v["digest"] == before and v["decision"]["kind"] == "yes_no"
    rec = app.handle("/api/record", {"gid": gid})
    v2 = app.handle("/api/load", {"record": json.loads(json.dumps(rec))})
    assert v2["digest"] == before


def test_set_review_keeps_file(tmp_path):
    """レビュー状態の書き換えはコメントや他のカードを壊さない（1行形式・ブロック形式の両方）。"""
    f = tmp_path / "real.yaml"
    shutil.copy(ROOT / "data" / "cards" / "real.yaml", f)
    set_review("dm01-001", "approved", 'メモ "引用" 付き', path=f)
    set_review("dm29-037", "rejected", "", path=f)
    set_review("dm01-001", "approved", "", path=f)
    text = f.read_text(encoding="utf-8")
    assert text.startswith("# 実カード")
    cards = {c["id"]: c for c in yaml.safe_load(text)["cards"]}
    assert cards["dm01-001"]["source"] == {"official": "dm01-001", "review": "approved"}
    assert cards["dm29-037"]["source"]["review"] == "rejected" and "notes" in cards["dm29-037"]["source"]
    assert cards["dm01-027"]["source"]["review"] == "pending"
    set_review("dm01-027", "approved", "動作確認済み", path=f)
    assert yaml.safe_load(f.read_text(encoding="utf-8"))["cards"][1]["source"]["review_note"] == "動作確認済み"


def test_fetch_parser():
    """公式ページの見出し（th）と値（td）の並びから項目を拾う。"""
    import fetch_cards
    page = """<html><head><title>アクア・ハルカス | カード検索</title></head><body><table>
    <tr><th>カードの種類</th><td>クリーチャー</td><th>文明</th><td>水</td></tr>
    <tr><th>コスト</th><td>3</td><th>パワー</th><td>2000</td></tr>
    <tr><th>特殊能力</th><td>このクリーチャーがバトルゾーンに出たとき、<br>カードを１枚引いてよい。</td></tr>
    </table></body></html>"""
    row = fetch_cards.parse("dm01-080", page)
    assert row["name"] == "アクア・ハルカス" and row["civilization"] == "水" and row["power"] == "2000"
    assert row["text"] == "このクリーチャーがバトルゾーンに出たとき、\nカードを１枚引いてよい。"


class _FakeStream:
    def __init__(self, text):
        from types import SimpleNamespace as N
        self.msg = N(stop_reason="end_turn", content=[N(type="text", text=text)],
                     usage=N(input_tokens=1, cache_read_input_tokens=0, cache_creation_input_tokens=0, output_tokens=1))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.msg


def test_convert_retries_once_with_error():
    """LLM の出力は parse_card で検査し、通らなければエラーを返して1回だけ直させる。review は必ず pending。"""
    import convert_cards
    from dmsim.cards.defs import load_tables
    bad = "```yaml\nid: x001\nname: 例\ntypes: [creature]\ncivs: [water]\ncost: 2\npower: 1000\nkeywords: [no_such]\n```"
    good = "```yaml\nid: x001\nname: 例\ntypes: [creature]\ncivs: [water]\ncost: 2\npower: 1000\n" \
           "keywords: [blocker]\nsource: {official: x001, review: approved}\n```"
    calls = []

    class Msgs:
        def stream(self, **kw):
            calls.append(kw)
            return _FakeStream(bad if len(calls) == 1 else good)

    client = type("C", (), {"messages": Msgs()})()
    out = convert_cards.convert(convert_cards.AnthropicLLM(client=client), {"id": "x001", "text": "ブロッカー"}, load_tables(), "SYS", "high")
    assert out["keywords"] == ["blocker"] and out["source"]["review"] == "pending"
    assert len(calls) == 2 and "no_such" in calls[1]["messages"][-1]["content"]
    assert calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert calls[0]["model"] == "claude-opus-5-5" and calls[0]["output_config"] == {"effort": "high"}


def test_convert_prompt_is_stable():
    """システムプロンプトは毎回同じ文字列（キャッシュが効く）で、スキーマと既存カードを含む。"""
    import convert_cards
    a, b = convert_cards.system_prompt(), convert_cards.system_prompt()
    assert a == b and "JSON Schema" in a and "dm01-080" in a


def test_fetch_parser_real_layout():
    """実ページの並び: 名前は h3「名前(収録番号)」、値が空のセル、ツインパクト（表が2組）。"""
    import fetch_cards
    page = """<h3>ヘル・スラッシュ(DM6 57/110)</h3><table><tr><th>カードの種類</th><th>呪文</th><th>文明</th><th>闇</th></tr>
    <tr><th>レアリティ</th><td>U</td><th>パワー</th><td></td></tr><tr><th>コスト</th><td>8</td><th>マナ</th><td>1</td></tr>
    <tr><th>種族</th><td></td></tr></table><table><tr><th>特殊能力</th></tr><tr><td>相手の山札を見る。</td></tr></table>
    <table><tr><th>フレーバー</th></tr><tr><td>骨を斬らせて。</td></tr></table>"""
    row = fetch_cards.parse("dm06-057", page)
    assert row["name"] == "ヘル・スラッシュ" and row["set_no"] == "DM6 57/110"
    assert row["card_type"] == "呪文" and row["power"] == "" and row["race"] == "" and row["cost"] == "8"
    assert row["text"] == "相手の山札を見る。" and fetch_cards.missing_fields(row) == []
    twin = ("<h3>A(DM1 1/9)</h3><table><tr><th>カードの種類</th><td>クリーチャー</td><th>文明</th><td>火</td></tr>"
            "<tr><th>パワー</th><td>1000</td></tr><tr><th>特殊能力</th><td>a</td></tr></table>"
            "<h3>B(DM1 1/9)</h3><table><tr><th>カードの種類</th><td>呪文</td><th>文明</th><td>水</td></tr>"
            "<tr><th>特殊能力</th><td>b</td></tr></table>")
    row = fetch_cards.parse("x", twin)
    assert [f["name"] for f in row["faces"]] == ["A", "B"] and row["faces"][1]["text"] == "b"
    assert "cost" in fetch_cards.missing_fields(row)      # 取れなかった項目は自己点検で分かる


def test_report_gaps_categorizes_errors():
    """検査エラー文を「足すべき語彙」ごとに分類して集計する。"""
    import report_gaps
    c = report_gaps.categorize
    assert c("abilities[0].effect[1]: unknown op 'reveal'") == ("op", "reveal")
    assert c("x: op 'draw' has unknown arg 'foo' (allowed: ['count'])") == ("op引数", "draw.foo")
    assert c("a: unknown zone 'trash'") == ("zone", "trash")
    assert c("2回とも検査を通らなかった: a: unknown selector keys ['bar']") == ("selectorのキー", "bar")
    gaps = report_gaps.collect([], [ROOT / "data" / "cards" / "real.yaml"])
    assert ("注意書き", "未実装/近似") in gaps
    assert "| 枚数 |" in report_gaps.render(gaps, 5)


def test_select_cards_excludes_plain_keeps_peaky():
    """バニラ・単純なドロー/除去は除外、複数ゾーンをつなぐ・デメリット付きは残る。"""
    import select_cards as sel
    plain = [{"id": "a", "text": "ブロッカー\nW・ブレイカー"},
             {"id": "b", "text": "カードを２枚引く。"},
             {"id": "c", "text": "相手のクリーチャーを１体選び、破壊する。"},
             {"id": "d", "text": "S・トリガー（この呪文をシールドゾーンから手札に加える時、コストを支払わずにすぐ唱えてもよい）"}]
    assert all(sel.score(r)[2] for r in plain)
    peaky = {"id": "e", "text": "自分の山札の上から２枚を墓地に置き、墓地からクリーチャーを１体バトルゾーンに出す。"
                                "自分のクリーチャーを１体破壊する。"}
    pts, why, ex = sel.score(peaky)
    assert not ex and pts >= 3 and any("複数ゾーン" in w for w in why)


def test_set_review_finds_file_and_converted_format(tmp_path, monkeypatch):
    """レビュー状態は、そのカードが書かれたファイル（converted.yaml のブロック形式）を自動で探して書き換える。"""
    import dmsim.devserver as ds
    (tmp_path / "converted.yaml").write_text(yaml.safe_dump({"cards": [
        {"id": "x001", "name": "例", "source": {"official": "x001", "review": "pending"}}]},
        allow_unicode=True, sort_keys=False), encoding="utf-8")
    (tmp_path / "real.yaml").write_text("cards:\n  - id: y001\n    source: {review: pending}\n", encoding="utf-8")
    monkeypatch.setattr(ds, "DATA", tmp_path.parent)
    assert ds.locate_card("x001", tmp_path).name == "converted.yaml"
    set_review("x001", "approved", "ok", path=ds.locate_card("x001", tmp_path))
    src = yaml.safe_load((tmp_path / "converted.yaml").read_text(encoding="utf-8"))["cards"][0]["source"]
    assert src["review"] == "approved" and src["review_note"] == "ok"
    with pytest.raises(KeyError):
        ds.locate_card("nope", tmp_path)


def test_convert_run_triage_and_resume(tmp_path):
    """バッチ変換: 成功は保存、検査落ちは rejects と種類別集計、API失敗は記録せず再実行で拾う。"""
    import convert_cards
    from dmsim.cards.defs import load_tables
    good = "```yaml\nid: {i}\nname: 例\ntypes: [creature]\ncivs: [water]\ncost: 2\npower: 1000\nkeywords: [blocker]\n```"
    bad = "```yaml\nid: {i}\nname: 例\ntypes: [creature]\ncivs: [water]\ncost: 2\npower: 1000\nkeywords: [no_such]\n```"

    class Msgs:
        def stream(self, **kw):
            i = kw["messages"][0]["content"].split('"id": "')[1].split('"')[0]
            if i == "t_api":
                raise RuntimeError("overloaded")
            return _FakeStream((bad if i == "t_bad" else good).format(i=i))

    client = type("C", (), {"messages": Msgs()})()
    rows = [{"id": i, "text": "x"} for i in ("t_ok", "t_bad", "t_api")]
    out, rej, rep = tmp_path / "c.yaml", tmp_path / "rej.jsonl", tmp_path / "rep.json"
    r = convert_cards.run(rows, convert_cards.AnthropicLLM(client=client), load_tables(), "SYS", "low", out, rej, workers=2, report_path=rep)
    assert (r["ok"], r["rejected"], r["api_error"]) == (1, 1, 1)
    assert [c["id"] for c in yaml.safe_load(out.read_text(encoding="utf-8"))["cards"]] == ["t_ok"]
    assert [x["id"] for x in convert_cards.read_jsonl(rej)] == ["t_bad"]
    assert any(k.startswith("keyword") or "no_such" in k for k in r["triage"]) and rep.exists()
    # 語彙を足した想定: 再実行で t_bad が通ると rejects から消える
    class Msgs2(Msgs):
        def stream(self, **kw):
            return _FakeStream(good.format(i=kw["messages"][0]["content"].split('"id": "')[1].split('"')[0]))
    client.messages = Msgs2()
    convert_cards.run(rows[1:], convert_cards.AnthropicLLM(client=client), load_tables(), "SYS", "low", out, rej)
    assert convert_cards.read_jsonl(rej) == [] and len(yaml.safe_load(out.read_text(encoding="utf-8"))["cards"]) == 3


def test_convert_pack_shares_one_call_and_falls_back_per_card(tmp_path):
    """pack=3: 1回の呼び出しで3枚。1枚は検査落ち→単独で直す、1枚は応答に無い→単独の呼び出し。"""
    import convert_cards
    from dmsim.cards.defs import load_tables
    card = "- id: {i}\n  name: 例\n  types: [creature]\n  civs: [water]\n  cost: 2\n  power: 1000\n  keywords: [{k}]\n"
    single = "```yaml\nid: {i}\nname: 例\ntypes: [creature]\ncivs: [water]\ncost: 2\npower: 1000\nkeywords: [blocker]\n```"
    calls = []

    class Msgs:
        def stream(self, **kw):
            calls.append(kw["messages"][0]["content"])
            if "まとめて" in calls[-1]:
                return _FakeStream("```yaml\ncards:\n" + card.format(i="p1", k="blocker") + card.format(i="p2", k="no_such") + "```")
            i = calls[-1].split('"id": "')[1].split('"')[0]
            return _FakeStream(single.format(i=i))

    client = type("C", (), {"messages": Msgs()})()
    rows = [{"id": i, "text": "x"} for i in ("p1", "p2", "p3")]
    out, rej = tmp_path / "c.yaml", tmp_path / "rej.jsonl"
    r = convert_cards.run(rows, convert_cards.AnthropicLLM(client=client), load_tables(), "SYS", "low", out, rej, pack=3)
    assert (r["ok"], r["rejected"]) == (3, 0)
    assert len(calls) == 1 + 2                   # まとめ1回 + p2(検査落ちの直し)・p3(応答に無い)の単独
    assert sorted(c["id"] for c in yaml.safe_load(out.read_text(encoding="utf-8"))["cards"]) == ["p1", "p2", "p3"]


@pytest.mark.slow
def test_agent_convert_next_and_submit(tmp_path, monkeypatch, capsys):
    """AI が API なしで変換する経路: next が依頼文を出し、submit が検査して合格分だけ登録する。"""
    import json as _json

    import agent_convert as ac
    raw = tmp_path / "raw"
    raw.mkdir()
    rows = [{"id": "z1", "name": "甲", "card_type": "クリーチャー", "civilization": "水", "cost": "2", "power": "1000",
             "race": "x", "text": "甲が出た時、カードを1枚引く。この能力は独自の複雑な文。"},
            {"id": "z2", "name": "乙", "card_type": "クリーチャー", "civilization": "水", "cost": "2", "power": "1000",
             "race": "x", "text": "乙が出た時、相手の山札を見て、好きな順に入れ替える。独自の文。"}]
    (raw / "a.jsonl").write_text("\n".join(_json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    monkeypatch.setattr(ac, "RAW", raw)
    monkeypatch.setattr(ac, "OUT", tmp_path / "converted.yaml")
    monkeypatch.setattr(ac, "REJ", raw / "rejects.jsonl")
    assert ac.cmd_next(2, "id") == 0
    out = capsys.readouterr().out
    assert "z1" in out and "z2" in out
    ans = tmp_path / "answer.yaml"
    ans.write_text("cards:\n- id: z1\n  name: 甲\n  types: [creature]\n  civs: [water]\n  cost: 2\n  power: 1000\n"
                   "- id: z2\n  name: 乙\n  types: [creature]\n  civs: [water]\n  cost: 2\n  power: 1000\n  keywords: [no_such]\n"
                   "- id: nope\n  name: 無\n", encoding="utf-8")
    assert ac.cmd_submit(str(ans)) == 1                      # z2 と nope は不合格
    got = yaml.safe_load((tmp_path / "converted.yaml").read_text(encoding="utf-8"))["cards"]
    assert [c["id"] for c in got] == ["z1"] and got[0]["source"]["review"] == "pending"
    assert ac.cmd_submit(str(ans)) == 1 and len(yaml.safe_load((tmp_path / "converted.yaml").read_text(encoding="utf-8"))["cards"]) == 1


def test_out_of_format_and_vocab_gap_cards_are_not_registered(tmp_path):
    """サイキック・GR・超次元・ドラグハートは変換しない。unsupported があるカードは登録せず rejects に vocab で残す。"""
    import convert_cards
    from dmsim.cards.defs import load_tables
    base = {"name": "例", "civilization": "水", "cost": "2", "power": "1000", "text": "x"}
    for t in ("GRクリーチャー", "サイキック・クリーチャー", "ドラグハート・ウエポン", "超次元呪文"):
        assert convert_cards.precheck({**base, "id": "g", "card_type": t})["reason"] == "out_of_format"
    assert convert_cards.precheck({**base, "id": "g", "card_type": "クリーチャー"}) is None
    card = "```yaml\nid: {i}\nname: 例\ntypes: [creature]\ncivs: [water]\ncost: 2\npower: 1000\n" \
           "source: {{official: {i}, unsupported: [{{need: some_new_op, text: 原文}}]}}\n```"

    class Msgs:
        def stream(self, **kw):
            return _FakeStream(card.format(i=kw["messages"][0]["content"].split('"id": "')[1].split('"')[0]))

    client = type("C", (), {"messages": Msgs()})()
    out, rej = tmp_path / "c.yaml", tmp_path / "rej.jsonl"
    r = convert_cards.run([{**base, "id": "v1", "card_type": "クリーチャー"}], convert_cards.AnthropicLLM(client=client),
                          load_tables(), "SYS", "low", out, rej)
    assert (r["ok"], r["rejected"]) == (0, 1) and not (yaml.safe_load(out.read_text(encoding="utf-8")) or {}).get("cards")
    got = convert_cards.read_jsonl(rej)
    assert got[0]["id"] == "v1" and got[0]["reason"] == "vocab" and got[0]["gaps"] == ["some_new_op"] and got[0]["partial"]["id"] == "v1"


@pytest.mark.slow
def test_survey_text_counts_forms():
    import survey_text
    rows = [{"id": "a", "name": "甲", "text": "ブロッカー(説明。)\n甲が出た時、カードを2枚引く。"},
            {"id": "b", "name": "乙", "text": "乙が出た時、カードを3枚引く。"}]
    sv = survey_text.survey(rows)
    assert len(sv["forms"]) == 1 and len(next(iter(sv["forms"].values()))["cards"]) == 2
    assert "ブロッカー" in sv["keywords"]
    assert "| 2 |" in survey_text.render(sv, 5, False)


@pytest.mark.slow
def test_status_numbers_are_current():
    """docs/STATUS.md の自動生成部がマーカーを持ち、スクリプトが読める。"""
    import gen_status
    text = gen_status.STATUS.read_text(encoding="utf-8")
    assert gen_status.BEGIN in text and gen_status.END in text
    assert "テスト:" in gen_status.build()


def test_system_prompt_picks_similar_examples():
    """例は原文が近い n 枚だけ。全部入れる版より大幅に短く、近いカードが先頭に来る。"""
    import convert_cards as cc
    row = {"id": "zz-001", "text": "このクリーチャーをバトルゾーンに出した時、相手の手札を見てその中から１枚選び、捨てさせる。"}
    small, full = cc.system_prompt(row=row, n_examples=8), cc.system_prompt()
    # 規則・語彙の固定部（2026-11 時点で約5.5万字）が育つと全体比は縮まらなくなるので、例の部分どうしで比べる
    ex = cc.examples_for(row, 8)
    all_examples = len(full) - len(small) + len(ex)
    assert len(small) < len(full)
    assert len(ex) < all_examples * 0.2
    assert yaml.safe_load(cc.examples_for(row, 8))["cards"][0]["id"] == "dmx03-035"
    assert len(yaml.safe_load(cc.examples_for(row, 8))["cards"]) == 8


def test_prompt_rules_text_strips_only_comments():
    """プロンプト用にコメント行を除いても、ルールのデータ（パース結果）は変わらない。"""
    import convert_cards as cc
    for n in ("zones.yaml", "keywords.yaml", "op_macros.yaml", "permissions.yaml", "turn.yaml"):
        assert yaml.safe_load(cc._prompt_rules_text(n)) == yaml.safe_load(cc._rules_text(n)), n
        assert len(cc._prompt_rules_text(n)) < len(cc._rules_text(n)), n


def test_rule_convert_keyword_only_and_vanilla(tmp_path):
    """キーワードだけ・バニラのクリーチャーは、モデルを呼ばずにルールで変換する。能力文があるものは None。"""
    import convert_cards as cc
    import rule_convert as rc
    from dmsim.cards.defs import load_tables, parse_card
    base = {"card_type": "クリーチャー", "civilization": "光/水", "cost": "3", "power": "2000", "race": "ガーディアン/ナイト", "name": "n"}
    r = rc.convert({**base, "id": "t1", "text": "ブロッカー（相手クリーチャーが攻撃する時、…）\nＷ・ブレイカー（…）\nこのクリーチャーは攻撃されない。 / Q・ブレイカー"})
    assert r["keywords"] == ["blocker", "double_breaker", "cannot_be_attacked", "quad_breaker"] and r["civs"] == ["light", "water"]
    assert r["races"] == ["ガーディアン", "ナイト"]
    parse_card(r, load_tables())
    van = rc.convert({**base, "id": "t2", "text": "", "missing": ["text"]})
    assert van and "keywords" not in van and "バニラ" in van["source"]["notes"]
    assert rc.convert({**base, "id": "t3", "text": "ブロッカー / 出た時、カードを引く。"}) is None      # 能力文あり → モデルへ
    assert rc.convert({**base, "id": "t4", "text": "", "missing": ["text", "cost"]}) is None             # 他の欠落は取得のやり直しが先
    assert rc.convert({**base, "id": "t5", "card_type": "呪文", "text": "ブロッカー"}) is None
    # run(): ルール変換できるカードではモデルを呼ばない
    called = []

    class LLM:
        def complete(self, *a):
            called.append(1)
            raise RuntimeError("呼ばれないはず")

    out, rej = tmp_path / "c.yaml", tmp_path / "r.jsonl"
    rep = cc.run([{**base, "id": "t1", "text": "ブロッカー"}, {**base, "id": "t2", "text": "", "missing": ["text"]}], LLM(), load_tables(),
                 "S", "low", out, rej)
    assert not called and rep["ok"] == 2 and [c["id"] for c in yaml.safe_load(out.read_text(encoding="utf-8"))["cards"]] == ["t1", "t2"]


def test_rule_convert_parameterized_keywords():
    """数値つき・注釈つきキーワード（パワーアタッカー+N、マッハファイター）もルールで変換し、検査に通る。"""
    import rule_convert as rc
    from dmsim.cards.defs import load_tables, parse_card
    base = {"card_type": "クリーチャー", "civilization": "火", "cost": "4", "power": "3000", "race": "ドラゴン", "name": "n"}
    r = rc.convert({**base, "id": "p1", "text": "パワーアタッカー＋２０００（攻撃中、…） / マッハファイター（…） / スピードアタッカー"})
    assert r["keywords"] == ["speed_attacker"] and len(r["abilities"]) == 2
    assert r["abilities"][0]["mod"] == {"power_when": {"amount": 2000, "when": "attacking"}}   # 常在型（誘発ではない）
    parse_card(r, load_tables())
    assert rc.convert({**base, "id": "p2", "text": "パワーアタッカー+X"}) is None
    kws, rest, extra = rc.split({"id": "x", "text": "パワーアタッカー+1000 出た時、カードを引く。"})
    assert kws == [] and rest == "出た時、カードを引く。" and extra[0]["kind"] == "static"


def test_rule_split_keywords_and_model_gets_only_the_rest(tmp_path):
    """キーワードはルールで処理し、モデルには残りの原文と known_keywords だけを渡す。結果の keywords はルール分が先。"""
    import convert_cards as cc
    import rule_convert as rc
    from dmsim.cards.defs import load_tables
    assert rc.split({"id": "x", "text": "ブロッカー（…） / 出た時、カードを１枚引く。 チャージャー"}) == (["blocker", "charger"], "出た時、カードを１枚引く。", [])
    assert rc.split({"id": "x", "text": "S・トリガー ブロッカー\nＷ・ブレイカー\nこのクリーチャーが出た時、相手の手札を１枚捨てさせる。"}) == (
        ["s_trigger", "blocker", "double_breaker"], "このクリーチャーが出た時、相手の手札を１枚捨てさせる。", [])
    assert rc.split({"id": "x", "text": "出た時、カードを引く。"}) is None
    seen = []

    class LLM:
        def complete(self, sysp, messages, effort, usage):
            seen.append(messages[0]["content"])
            return "```yaml\nid: t9\nname: n\ntypes: [creature]\ncivs: [water]\ncost: 2\npower: 1000\nabilities:\n- kind: trigger\n  when: {event: move, to: bz, subject: self}\n  effect: [{op: draw, count: 1}]\n```"

    row = {"id": "t9", "name": "n", "card_type": "クリーチャー", "civilization": "水", "cost": "2", "power": "1000",
           "text": "ブロッカー / このクリーチャーが出た時、相手の呪文を１つ唱えられなくする。"}
    out, rej = tmp_path / "c.yaml", tmp_path / "r.jsonl"
    rep = cc.run([row], LLM(), load_tables(), "S", "low", out, rej)
    assert rep["ok"] == 1 and "known_keywords" in seen[0] and "ブロッカー" not in seen[0].split("known_keywords")[0]
    card = yaml.safe_load(out.read_text(encoding="utf-8"))["cards"][0]
    assert card["keywords"] == ["blocker"] and card["text"] == row["text"]


def test_convert_timeout_breaker(tmp_path):
    """タイムアウトは次のカードが成功して初めて reason: timeout で確定。連続2回は障害として打ち切り、記録しない。"""
    import convert_cards
    from dmsim.cards.defs import load_tables
    from convert_cards import CallTimeout
    good = "```yaml\nid: {i}\nname: 例\ntypes: [creature]\ncivs: [water]\ncost: 2\npower: 1000\n```"

    def run(ids, hang):
        class Msgs:
            def stream(self, **kw):
                i = kw["messages"][0]["content"].split('"id": "')[1].split('"')[0]
                if i in hang:
                    raise CallTimeout("t")
                return _FakeStream(good.format(i=i))
        client = type("C", (), {"messages": Msgs()})()
        d = tmp_path / str(len(ids)) / str(sorted(hang))
        return convert_cards.run([{"id": i, "text": "x"} for i in ids], convert_cards.AnthropicLLM(client=client), load_tables(),
                                 "SYS", "low", d / "c.yaml", d / "r.jsonl"), d / "r.jsonl"

    r, rej = run(["a", "b", "c"], {"a"})            # 1回だけ → 次の成功で確定
    assert (r["ok"], r["rejected"]) == (2, 1)
    assert [(x["id"], x["reason"]) for x in convert_cards.read_jsonl(rej)] == [("a", "timeout")]
    r, rej = run(["a", "b", "c", "d"], {"a", "b"})   # 連続2回 → c,d は打たず、a,b も記録しない
    assert (r["ok"], r["rejected"], r["api_error"]) == (0, 0, 2)
    assert not rej.exists() or not convert_cards.read_jsonl(rej)


def test_convert_precheck_skips_model_for_unconvertible_rows():
    """空ページ・能力文なしはモデルを呼ばず reason を付ける。二面カードは面の text があれば通す。"""
    import convert_cards as cc
    assert cc.precheck({"id": "a", "name": "", "missing": ["name", "text"]})["reason"] == "fetch_incomplete"
    assert cc.precheck({"id": "b", "text": "", "faces": [{"text": ""}]})["reason"] == "no_text"
    assert cc.precheck({"id": "c", "text": "", "faces": [{"text": "S・トリガー"}]}) is None
    assert cc.precheck({"id": "d", "text": "ブロッカー"}) is None


def test_user_prompt_omits_flavor_and_non_rule_fields():
    """フレーバー・イラストレーター等はモデルに渡さない（効果の変換に無関係）。面ごとの項目も同様。"""
    import convert_cards as cc
    row = {"id": "x", "name": "n", "text": "ブロッカー", "flavor": "「わかるか。」 -ボーグ", "illustrator": "i", "rarity": "C",
           "missing": ["text"], "faces": [{"name": "a", "text": "t", "flavor": "f2", "illustrator": "i2"}]}
    p = cc.user_prompt(row)
    assert "ブロッカー" in p and '"t"' in p
    for bad in ("flavor", "わかるか", "illustrator", "rarity", "missing", "f2"):
        assert bad not in p


def test_rule_convert_named_effects_with_notes():
    """注釈つきの名前つき効果・{GS} などの記号・句点で終わる文を、ルールだけで変換する（モデル不使用）。"""
    import rule_convert as rc
    base = {"id": "x-001", "name": "テスト", "card_type": "クリーチャー", "civilization": "光", "cost": "3", "power": "3000", "race": "テスト"}
    r = rc.convert({**base, "text": "{GS} G・ストライク（このカードを自分のシールドゾーンから手札に加える時、表向きにし、相手のクリーチャーを１体選んでもよい。このターン、そのクリーチャーは攻撃できない）\nガードマン（このクリーチャーをタップして、…）"})
    assert r and r["keywords"] == ["g_strike", "guardman"]
    r = rc.convert({**base, "text": "マナゾーンに置く時、このカードはタップして置く。 ブロッカー"})
    assert r and r["keywords"] == ["blocker"]       # タップ置きは多色カードのルール。能力にしない
    r = rc.convert({**base, "text": "このクリーチャーは攻撃することができない。"})
    assert r and r["keywords"] == ["cannot_attack"]
    r = rc.convert({**base, "text": "パワード・ブレイカー（このクリーチャーは、そのパワー6000ごとにシールドをもう１つブレイクする）\nシールド・セイバー（…）\nエスケープ"})
    assert r and r["keywords"] == ["powered_breaker", "shield_saver", "escape"]
    kws, rest, _ = rc.split({**base, "text": "{GS} G・ストライク（…）\nこのクリーチャーが出た時、相手の呪文を1つ唱えられなくする。"})
    assert kws == ["g_strike"] and rest == "このクリーチャーが出た時、相手の呪文を1つ唱えられなくする。"


def test_rule_convert_revolution_change_and_ninja_strike():
    """革命チェンジ：<条件> とニンジャ・ストライク N（数字が空白で離れていても）をルールで変換し、検査に通る。"""
    import rule_convert as rc
    from dmsim.cards.defs import load_tables, parse_card
    base = {"card_type": "クリーチャー", "civilization": "火", "cost": "6", "power": "6000", "race": "アーマード・ドラゴン", "name": "n"}
    r = rc.convert({**base, "id": "rc1", "text": "革命チェンジ：光または火の、コスト５以上のドラゴン（…） / W・ブレイカー"})
    f = r["abilities"][0]["when"]["subject"]["filter"]
    assert f == {"civs": ["light", "fire"], "cost_ge": 5, "race_has": "ドラゴン"} and r["keywords"] == ["double_breaker"]
    parse_card(r, load_tables())
    assert rc.convert({**base, "id": "rc2", "text": "革命チェンジ：ファイアー・バードまたはドラゴン"}) is None
    n = rc.convert({**base, "id": "ns", "text": "ニンジャ・ストライク ４（…）"})
    assert [a["when"]["event"] for a in n["abilities"]] == ["attack", "block"]
    assert n["abilities"][0]["if"]["cmp"][2] == 4
    parse_card(n, load_tables())


def test_reuse_same_text_copies_abilities_without_model():
    """原文が同じ変換済みクリーチャーがあれば、能力だけ写して id・名前・ステータスは新しいカードのものにする。"""
    import rule_convert as rc
    from dmsim.cards.defs import load_tables, parse_card
    base = {"card_type": "クリーチャー", "civilization": "水", "cost": "2", "power": "1000", "race": "リキッド・ピープル"}
    donor = {"id": "d1", "name": "元", "types": ["creature"], "civs": ["water"], "cost": 4, "power": 2000, "text": "出た時、カードを1枚引く。",
             "abilities": [{"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"}, "effect": [{"op": "draw", "count": 1}]}],
             "source": {"official": "d1", "review": "approved"}}
    row = {**base, "id": "d2", "name": "再録", "text": "出た時、カードを1枚引く。"}
    r = rc.reuse_same_text(row, [donor])
    assert r["id"] == "d2" and r["cost"] == 2 and r["power"] == 1000 and r["abilities"] == donor["abilities"]
    assert r["source"]["review"] == "pending" and "d1" in r["source"]["notes"]
    parse_card(r, load_tables())
    assert rc.reuse_same_text({**row, "text": "別の原文"}, [donor]) is None
    assert rc.reuse_same_text({**row, "id": "d1"}, [donor]) is None


@pytest.mark.slow
def test_run_rules_registers_rule_convertible_cards_without_model(tmp_path):
    """ルールだけで変換できる行（キーワードのみ・同一原文の写し・定型呪文）はモデルなしで登録し、残りには触らない。再実行しても増えない。"""
    import convert_cards as cc
    from dmsim.cards.defs import load_tables
    base = {"card_type": "クリーチャー", "civilization": "自然", "cost": "3", "power": "2000", "race": "テスト", "mana": "1"}
    rows = [{**base, "id": "r1", "name": "a", "text": "ブロッカー"},
            {**base, "id": "r2", "name": "b", "text": "ブロッカー"},
            {**base, "id": "r3", "name": "c", "text": "未知の効果を行う。"},
            {"id": "r4", "name": "d", "card_type": "呪文", "civilization": "水", "cost": "2", "mana": "1", "text": "S・トリガー\nカードを２枚引く。"}]
    out, rej = tmp_path / "c.yaml", tmp_path / "r.jsonl"
    st = cc.run_rules(rows, load_tables(), out, rej)
    ids = [c["id"] for c in yaml.safe_load(out.read_text(encoding="utf-8"))["cards"]]
    assert ids == ["r1", "r2", "r4"] and st["ok"] == 3
    assert cc.run_rules(rows, load_tables(), out, rej)["ok"] == 0


_META_COND = {"cmp": [{"count": {"zone": "mana", "owner": "you"}}, ">=", 7]}
_META_REPLACE = {"kind": "replace",
                 "when": {"event": "move", "from": "bz", "to": "graveyard", "reason": "destroy", "subject": "self"},
                 "instead": [{"op": "move", "select": {"ref": "self"}, "to": "hand", "reason": "return"}]}


def test_split_metamorph_carries_condition_to_pattern_ability():
    """メタモーフ（クリーチャー形）: ヘッダの条件は、定型が所有する「次の能力」に if として付く。
    ヘッダは rest に残らず、merge では条件つき置換が1件だけになる（第375弾の登録ブロッカーの解消）。"""
    import convert_cards as cc
    import rule_convert as rc
    row = {"id": "m1", "card_type": "クリーチャー",
           "text": "このクリーチャーは、ブロックされない。\n"
                   "メタモーフ(自分のマナゾーンに７枚以上カードがあれば、このクリーチャーは次の能力を得る)\n"
                   "このクリーチャーが破壊される時、墓地に置くかわりに自分の手札に戻す。"}
    part = rc.split(row)
    assert part is not None
    assert part[0] == ["unblockable"]
    assert part[1] == ""                       # ヘッダは条件ごと定型が所有するので rest に残らない
    assert part[2] == [{**_META_REPLACE, "if": _META_COND}]
    # 回答が条件つき置換を返しても二重に付かない（完全一致で dedupe される）
    ans = {"id": "m1", "keywords": ["unblockable"], "abilities": [{**_META_REPLACE, "if": _META_COND}]}
    assert cc.merge_split(ans, row, part)["abilities"] == [{**_META_REPLACE, "if": _META_COND}]
    # 回答が置換を返さなくても、条件つきの形が付く（無条件形にはならない）
    ans2 = {"id": "m1", "keywords": ["unblockable"], "abilities": []}
    assert cc.merge_split(ans2, row, part)["abilities"] == [{**_META_REPLACE, "if": _META_COND}]


def test_split_metamorph_trigger_variant():
    """メタモーフの次の能力が誘発の定型でも条件が付く（dm14-073 型）。"""
    import rule_convert as rc
    row = {"id": "m2", "card_type": "クリーチャー",
           "text": "メタモーフ(自分のマナゾーンに７枚以上カードがあれば、このクリーチャーは次の能力を得る)\n"
                   "このクリーチャーをバトルゾーンに出した時、カードを１枚引いてもよい。"}
    part = rc.split(row)
    assert part is not None and part[1] == ""
    assert part[2] == [{"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
                        "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}], "if": _META_COND}]


def test_split_metamorph_spell_form_and_unowned_ability_untouched():
    """呪文形のメタモーフと、次の能力が定型でない場合は従来どおり（ヘッダは rest に残り、条件は付けない）。"""
    import rule_convert as rc
    spell = {"id": "m3", "card_type": "呪文",
             "text": "S・トリガー\n相手のパワー2000以下のクリーチャーを１体破壊する。\n"
                     "メタモーフ(自分のマナゾーンに７枚以上カードがあれば、この呪文は次の能力を得る)\n"
                     "パワー2000以下のクリーチャーのかわりに、相手のパワー6000以下のクリーチャーを１体破壊する。"}
    part = rc.split(spell)
    assert part is not None and "メタモーフ" in part[1]
    assert all("if" not in a for a in part[2])
    unowned = {"id": "m4", "card_type": "クリーチャー",
               "text": "ブロッカー\nメタモーフ(自分のマナゾーンに７枚以上カードがあれば、このクリーチャーは次の能力を得る)\n"
                       "このクリーチャーのパワーは+2000される。"}
    part = rc.split(unowned)
    assert part is not None and "メタモーフ" in part[1]     # 定型が所有しない能力には条件を付けず、ヘッダはモデルへ残す
    assert all("if" not in a for a in part[2])
