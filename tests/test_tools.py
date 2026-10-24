"""記録の保存・再生、開発者モードのAPI、取得・変換ツール（ネットワークなし）の検証。"""
import json
import random
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from conftest import answer, setup

from dmsim import scenario as sc
from dmsim.devserver import App, Session, set_review
from dmsim.play import default_decks, make_record, random_policy, replay_record, run

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
    from dmsim.play import deck_lists
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
    from dmsim.defs import load_tables
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
    from dmsim.defs import load_tables
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


def test_survey_text_counts_forms():
    import survey_text
    rows = [{"id": "a", "name": "甲", "text": "ブロッカー(説明。)\n甲が出た時、カードを2枚引く。"},
            {"id": "b", "name": "乙", "text": "乙が出た時、カードを3枚引く。"}]
    sv = survey_text.survey(rows)
    assert len(sv["forms"]) == 1 and len(next(iter(sv["forms"].values()))["cards"]) == 2
    assert "ブロッカー" in sv["keywords"]
    assert "| 2 |" in survey_text.render(sv, 5, False)


def test_status_numbers_are_current():
    """docs/STATUS.md の自動生成部がマーカーを持ち、スクリプトが読める。"""
    import gen_status
    text = gen_status.STATUS.read_text(encoding="utf-8")
    assert gen_status.BEGIN in text and gen_status.END in text
    assert "テスト:" in gen_status.build()


def test_opencode_allowlist_and_cost_guard(monkeypatch):
    """OpenCode は許可リストの無料モデルだけ通し、費用の兆候・課金系エラーでは止まる。キーは出力に出さない。"""
    import convert_cards as cc
    import pytest
    for bad in ("glm-5.3", "claude-opus-5-5", "glm-5.3-flash", "x-free"):
        with pytest.raises(cc.Fatal):
            cc.OpenCodeLLM(bad, key="k")
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    with pytest.raises(cc.Fatal):
        cc.OpenCodeLLM()
    llm = cc.OpenCodeLLM(key="SECRET", min_interval=0)
    ok = {"choices": [{"message": {"content": "hi"}}], "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
    monkeypatch.setattr(llm, "_post", lambda payload: (calls.append(payload), ok)[1])
    calls = []
    usage = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
    assert llm.complete("S", [{"role": "user", "content": "u"}], "high", usage) == "hi"
    assert calls[0]["model"] == "glm-5.3-flash-free" and usage["input"] == 3
    monkeypatch.setattr(llm, "_post", lambda payload: {**ok, "usage": {"cost": 0.01}})
    with pytest.raises(cc.Fatal):
        llm.complete("S", [], "high", None)


def test_auto_convert_limit_status_and_retry_only_on_vocab_change(tmp_path, monkeypatch):
    """定期変換: 件数上限・短い順・状態ファイル。語彙が変わらない限り rejects は再試行しない。"""
    import json

    import auto_convert as ac
    import convert_cards as cc
    raw = tmp_path / "raw"
    raw.mkdir()
    ids = ["ta_a", "ta_b", "ta_c"]
    (raw / "o.jsonl").write_text("".join(json.dumps({"id": i, "text": "x" * n}) + "\n"
                                         for i, n in zip(ids, (3, 1, 2))), encoding="utf-8")
    good = "```yaml\nid: {i}\nname: 例\ntypes: [creature]\ncivs: [water]\ncost: 2\npower: 1000\nkeywords: [blocker]\n```"
    seen = []

    class LLM:
        def complete(self, sysp, messages, effort, usage):
            i = messages[0]["content"].split('"id": "')[1].split('"')[0]
            seen.append(i)
            return good.format(i=i)

    monkeypatch.setattr(ac, "RAW", raw)
    monkeypatch.setattr(ac, "STATUS", raw / "convert_status.json")
    monkeypatch.setattr(ac.cc, "make_llm", lambda *a: LLM())
    monkeypatch.setattr(ac, "DATA", tmp_path)
    monkeypatch.setattr(ac, "vocab_hash", lambda: "h1")
    ac.main(["--limit", "2", "--interval", "0"])
    assert seen == ["ta_b", "ta_c"]                      # 短い順に上限まで
    st = json.loads((raw / "convert_status.json").read_text(encoding="utf-8"))
    assert (st["converted"], st["pending"], st["vocab_hash"]) == (2, 1, "h1")
    ac.main(["--limit", "2", "--interval", "0"])
    assert seen[2:] == ["ta_a"]


def test_llm_offload_guards(tmp_path):
    """無料モデル共通層: 秘密を伏せる・切り詰める・キャッシュ・日次上限・失敗は Escalate・課金系は Fatal。"""
    import llm_offload as lo
    import pytest
    assert "SECRET123456789" not in lo.scrub("api_key=SECRET123456789 and sk-abcdefghijklmnop1234")
    assert len(lo.clip("x" * 1000, 100)) < 200

    class LLM:
        model = "glm-5.3-flash-free"
        n = 0

        def complete(self, sysp, messages, effort, usage):
            self.n += 1
            return "要約"
    llm = LLM()
    r = lo.ask("summarize", "text", llm=llm, cache=tmp_path)
    assert r.text == "要約" and not r.cached
    assert lo.ask("summarize", "text", llm=llm, cache=tmp_path).cached and llm.n == 1
    with pytest.raises(lo.Escalate):
        lo.ask("summarize", "other", llm=llm, cache=tmp_path, daily_limit=1)

    class Bad:
        model = "m"

        def complete(self, *a):
            raise RuntimeError("HTTP 429")
    with pytest.raises(lo.Escalate):
        lo.ask("summarize", "t2", llm=Bad(), cache=tmp_path)

    class Paid:
        model = "m"

        def complete(self, *a):
            raise lo.Fatal("billing")
    with pytest.raises(lo.Fatal):
        lo.ask("summarize", "t3", llm=Paid(), cache=tmp_path)
    for p in ("anthropic", "openai"):
        with pytest.raises(lo.Fatal):
            lo.make_llm(p)


def test_llm_offload_rule_based_helpers(tmp_path):
    import llm_offload as lo
    d = lo.digest_pytest("....\nFAILED tests/a.py::t - assert 1\nE   assert 1 == 2\n" + "ok\n" * 100 + "1 failed, 5 passed")
    assert "FAILED tests/a.py::t" in d and "1 failed" in d and d.count("ok") <= 15
    assert lo.affected_tests(["dmsim/engine/core.py"]) is None
    assert "tests/test_dedupe_cards.py" in lo.affected_tests(["tools/dedupe_cards.py"])
