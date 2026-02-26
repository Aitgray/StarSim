import importlib


def _reset_visualizer_state():
    vis = importlib.import_module("visualizer.app")
    if vis.sim_controller is not None:
        vis.sim_controller.pause()
        vis.sim_controller.stop()
    vis.sim_controller = None
    vis.universe = None
    vis.cached_nodes = []
    vis.cached_edges = []
    vis.cached_factions = []
    return vis


def test_sim_state_endpoint():
    vis = _reset_visualizer_state()
    client = vis.app.test_client()
    resp = client.get("/sim/state")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert "nodes" in payload
    assert "edges" in payload
    assert "factions" in payload
    assert "meta" in payload
    assert "tick" in payload["meta"]


def test_sim_step_and_rewind():
    vis = _reset_visualizer_state()
    client = vis.app.test_client()
    step_resp = client.post("/sim/step", json={"steps": 2})
    assert step_resp.status_code == 200
    step_payload = step_resp.get_json()
    assert step_payload["steps"] == 2
    tick_after_step = step_payload["tick"]
    assert tick_after_step >= 2

    rewind_resp = client.post("/sim/rewind", json={"steps": 1})
    assert rewind_resp.status_code == 200
    rewind_payload = rewind_resp.get_json()
    assert rewind_payload["steps"] == 1
    tick_after_rewind = rewind_payload["tick"]
    assert tick_after_rewind == max(0, tick_after_step - 1)


def test_sim_play_pause():
    vis = _reset_visualizer_state()
    client = vis.app.test_client()
    play_resp = client.post("/sim/play")
    assert play_resp.status_code == 200
    play_payload = play_resp.get_json()
    assert play_payload["status"] == "playing"

    pause_resp = client.post("/sim/pause")
    assert pause_resp.status_code == 200
    pause_payload = pause_resp.get_json()
    assert pause_payload["status"] == "paused"
