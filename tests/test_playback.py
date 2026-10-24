"""再生画面の裏側: 記録からループの骨格・周回数・ストック量・勝ち筋を読み出す（探索ロジックは読むだけ）。"""
import json

from conftest import setup

from dmsim.devserver import App
from dmsim.play import deck_lists, make_record
from dmsim.playback import Playback, analyze_record, cert_from_dict, cert_to_dict, record_with_cert
from dmsim.solitaire import play_game


def _loop_record(rules):
    spec = {"p0": {"bz": ["T010"], "hand": ["T009"], "mana": ["T003"]}, "p1": {}, "filler": "T001", "seed": 1,
            "deck_size": 20, "deck_left": None}
    e = setup(rules, spec["p0"])
    res, end = play_game(rules, None, None, 1, start=e, budget=50)
    assert res.kind == "loop_deck_out"
    return make_record(end, deck_lists(end), 1, 0, scenario=spec), end


def test_analyze_finds_loop_laps_and_stock(rules):
    rec, end = _loop_record(rules)
    info = analyze_record(rules, rec)
    assert info["n"] == len(rec["log"]) and info["result"]["winner"] == 0
    lp = info["loops"][0]
    assert lp["win_by"] == "opp_deck_out" and lp["delta"] == {"deck:1": -1, "graveyard:1": 1}
    assert lp["stock"]["deck:1"] == -lp["laps"] and lp["laps"] >= 2
    assert lp["end"] == lp["start"] + lp["length"] * lp["laps"]
    assert all(info["frames"][k]["loop"] == 0 for k in range(lp["start"], lp["end"]))
    assert any(r["type"] == "loop" for r in info["route"])


def test_view_at_matches_replay_and_marks_choice(rules):
    rec, end = _loop_record(rules)
    pb = Playback(rules, rec)
    assert pb.view_at(pb.info["n"])["digest"] == end.s.digest()
    v = pb.view_at(3)
    assert v["frame"] == 3 and v["chosen"] == rec["log"][3]["choice"] and v["decision"]["kind"] == rec["log"][3]["kind"]
    assert pb.view_at(1)["frame"] == 1            # 戻っても同じ盤面を作り直せる


def test_cert_roundtrip_and_replay(rules):
    rec, _ = _loop_record(rules)
    lp = analyze_record(rules, rec)["loops"][0]
    from dmsim.loop import LoopCertificate
    cert = LoopCertificate("x", lp["actions"], lp["deciders"], lp["delta"], float("inf"), "in_turn")
    cert = cert_from_dict(json.loads(json.dumps(cert_to_dict(cert))))
    assert cert.limit == float("inf") and cert.actions == lp["actions"]
    longer = record_with_cert(rules, rec, lp["start"], cert, 2)
    assert len(longer["log"]) == lp["start"] + lp["length"] * 2     # 勝てる周回数より少なければ、そこで止まる


def test_devserver_playback_api(rules):
    rec, end = _loop_record(rules)
    app = App()
    r = app.handle("/api/pb_open", {"record": json.loads(json.dumps(rec))})
    assert r["loops"] and r["result"]["winner"] == 0
    v = app.handle("/api/pb_frame", {"pid": r["pid"], "i": r["n"]})
    assert v["digest"] == end.s.digest()
