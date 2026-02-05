import pytest
import random

from src.starsim.core.ids import WorldId, LaneId
from src.starsim.core.rng import get_seeded_rng
from src.starsim.core.state import UniverseState
from src.starsim.world.model import World, Lane


def test_universe_state_initialization():
    state = UniverseState(seed=123)
    assert state.seed == 123
    assert state.tick == 0
    assert isinstance(state.rng, random.Random)


def test_rng_determinism():
    seed = 42
    rng1 = get_seeded_rng(seed)
    rng2 = get_seeded_rng(seed)

    draws1 = [rng1.randint(0, 100) for _ in range(10)]
    draws2 = [rng2.randint(0, 100) for _ in range(10)]

    assert draws1 == draws2


def test_universe_state_rng_determinism():
    seed = 123
    state1 = UniverseState(seed=seed)
    state2 = UniverseState(seed=seed)

    draws1 = [state1.rng.randint(0, 100) for _ in range(10)]
    draws2 = [state2.rng.randint(0, 100) for _ in range(10)]

    assert draws1 == draws2


def test_rebuild_adjacency_correctness():
    world1 = World(id=WorldId("w1"), name="World 1")
    world2 = World(id=WorldId("w2"), name="World 2")
    world3 = World(id=WorldId("w3"), name="World 3")

    lane1 = Lane(id=LaneId("l1"), a=WorldId("w1"), b=WorldId("w2"))
    lane2 = Lane(id=LaneId("l2"), a=WorldId("w2"), b=WorldId("w3"))
    lane3 = Lane(id=LaneId("l3"), a=WorldId("w1"), b=WorldId("w3"))

    state = UniverseState(
        seed=1,
        worlds={world1.id: world1, world2.id: world2, world3.id: world3},
        lanes={lane1.id: lane1, lane2.id: lane2, lane3.id: lane3}
    )

    # After __post_init__, adjacency should be built
    assert set(state._adj[WorldId("w1")]) == {LaneId("l1"), LaneId("l3")}
    assert set(state._adj[WorldId("w2")]) == {LaneId("l1"), LaneId("l2")}
    assert set(state._adj[WorldId("w3")]) == {LaneId("l2"), LaneId("l3")}


def test_neighbors():
    world1 = World(id=WorldId("w1"), name="World 1")
    world2 = World(id=WorldId("w2"), name="World 2")
    world3 = World(id=WorldId("w3"), name="World 3")
    world4 = World(id=WorldId("w4"), name="World 4") # Unconnected

    lane1 = Lane(id=LaneId("l1"), a=WorldId("w1"), b=WorldId("w2"))
    lane2 = Lane(id=LaneId("l2"), a=WorldId("w2"), b=WorldId("w3"))

    state = UniverseState(
        seed=1,
        worlds={world1.id: world1, world2.id: world2, world3.id: world3, world4.id: world4},
        lanes={lane1.id: lane1, lane2.id: lane2}
    )

    assert set(state.neighbors(WorldId("w1"))) == {WorldId("w2")}
    assert set(state.neighbors(WorldId("w2"))) == {WorldId("w1"), WorldId("w3")}
    assert set(state.neighbors(WorldId("w3"))) == {WorldId("w2")}
    assert state.neighbors(WorldId("w4")) == []


def test_lanes_from():
    world1 = World(id=WorldId("w1"), name="World 1")
    world2 = World(id=WorldId("w2"), name="World 2")
    world3 = World(id=WorldId("w3"), name="World 3")

    lane1 = Lane(id=LaneId("l1"), a=WorldId("w1"), b=WorldId("w2"), distance=10.0)
    lane2 = Lane(id=LaneId("l2"), a=WorldId("w2"), b=WorldId("w3"), distance=5.0)

    state = UniverseState(
        seed=1,
        worlds={world1.id: world1, world2.id: world2, world3.id: world3},
        lanes={lane1.id: lane1, lane2.id: lane2}
    )

    lanes_w1 = state.lanes_from(WorldId("w1"))
    assert len(lanes_w1) == 1
    assert lanes_w1[0].id == LaneId("l1")
    assert lanes_w1[0].distance == 10.0

    lanes_w2 = state.lanes_from(WorldId("w2"))
    assert len(lanes_w2) == 2
    lane_ids_w2 = {lane.id for lane in lanes_w2}
    assert lane_ids_w2 == {LaneId("l1"), LaneId("l2")}

    assert state.lanes_from(WorldId("non_existent")) == []
