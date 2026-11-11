from dmsim.plan import PlanSpec, from_hunt_record, is_verified, register_verified

REC = {"cards": ["a", "b"], "names": ["A", "B"], "period": "lock", "delta": {}, "opp_delta": {"deck": -1},
       "games": 24, "kills": 3, "kill_rate": 0.125, "turns": 4, "deck": ["a"] * 4, "score": 8.0}


def test_only_verified_registered():
    assert is_verified(REC)
    assert not is_verified({**REC, "kills": 0})
    assert is_verified({**REC, "kills": 0, "lock_wins": 2})
    assert len(register_verified([REC, {**REC, "kills": 0}])) == 1


def test_roundtrip_and_stages():
    p = from_hunt_record(REC)
    q = PlanSpec.from_json(p.to_json())
    assert q.kind == "combo_sequence" and q.plan_id == p.plan_id
    assert q.params["stages"][0]["target"] == {"hand": {"a": 1, "b": 1}}


def test_dedupe_and_source_ignored():
    a, b = from_hunt_record(REC), from_hunt_record({**REC, "deck": ["z"], "score": 1.0})
    assert a.plan_id == b.plan_id
    assert len(register_verified([REC, {**REC, "deck": ["z"]}])) == 1
