import math
import logging
import numpy as np
from scipy.spatial import Delaunay
from typing import Dict, List, Tuple
from collections import defaultdict

from ..core.ids import WorldId, LaneId
from ..world.model import World, Lane

logger = logging.getLogger(__name__)

def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculates the Euclidean distance between two 2D points."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

class DisjointSetUnion:
    """A Disjoint Set Union (DSU) data structure for Kruskal's algorithm."""
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, i):
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            if self.rank[root_i] < self.rank[root_j]:
                self.parent[root_i] = root_j
            elif self.rank[root_i] > self.rank[root_j]:
                self.parent[root_j] = root_i
            else:
                self.parent[root_j] = root_i
                self.rank[root_i] += 1
            return True
        return False

def generate_non_intersecting_lanes(worlds: Dict[WorldId, World]) -> List[Dict]:
    """
    Generates non-intersecting lanes ensuring connectivity using Delaunay Triangulation and MST.
    Then adds additional edges to increase node degrees up to a maximum of 3.

    Args:
        worlds: A dictionary of WorldId to World objects, containing x, y coordinates.

    Returns:
        A list of dictionaries, each representing a lane, compatible with app.py's jsonify.
    """
    if not worlds or len(worlds) < 2:
        return []

    # 1. Extract points (coordinates) and map back to WorldIds
    # Ensure points_map is created from a consistent order of worlds.keys()
    world_ids_list = list(worlds.keys())
    points_map = {idx: world_id for idx, world_id in enumerate(world_ids_list)}
    coords = np.array([[worlds[world_id].x, worlds[world_id].y] for world_id in world_ids_list])

    # 2. Perform Delaunay Triangulation
    try:
        tri = Delaunay(coords)
    except Exception as e:
        logger.error("Delaunay triangulation failed: %s", e)
        return []

    # 3. Collect all unique edges from the Delaunay triangulation with their Euclidean distances
    all_delaunay_edges = [] # List of (world_id1, world_id2, distance)
    unique_edge_tuples = set() # To avoid duplicate edges (e.g., (A,B) and (B,A))

    for simplex in tri.simplices:
        for i in range(3): # Each triangle has 3 edges
            p_idx1 = simplex[i]
            p_idx2 = simplex[(i + 1) % 3]

            world_id1 = points_map[p_idx1]
            world_id2 = points_map[p_idx2]

            # Ensure consistent order for unique_edge_tuples set
            edge_key = tuple(sorted((world_id1, world_id2)))

            if edge_key not in unique_edge_tuples:
                unique_edge_tuples.add(edge_key)
                
                coord1 = coords[p_idx1]
                coord2 = coords[p_idx2]
                dist = euclidean_distance(coord1, coord2)
                all_delaunay_edges.append((world_id1, world_id2, dist))
    
    # Sort all Delaunay edges by distance (needed for both MST and greedy additions)
    all_delaunay_edges.sort(key=lambda x: x[2])

    # 4. Compute Minimum Spanning Tree (MST) using Kruskal's algorithm
    mst_edges = []
    dsu = DisjointSetUnion(len(worlds))

    world_id_to_idx = {world_id: idx for idx, world_id in enumerate(world_ids_list)}

    for world_id1, world_id2, dist in all_delaunay_edges:
        idx1 = world_id_to_idx[world_id1]
        idx2 = world_id_to_idx[world_id2]

        if dsu.find(idx1) != dsu.find(idx2): # Use find before union to check if they are already connected
            dsu.union(idx1, idx2)
            mst_edges.append((world_id1, world_id2, dist))

    final_edges = list(mst_edges)
    
    # 5. Add additional edges to increase node degrees up to a maximum of 3
    node_degrees_current = defaultdict(int)
    for w1, w2, _ in mst_edges:
        node_degrees_current[w1] += 1
        node_degrees_current[w2] += 1
    
    # Collect Delaunay edges not in MST
    mst_edge_keys = {tuple(sorted((w1, w2))) for w1, w2, _ in mst_edges}
    remaining_delaunay_edges = [
        (w1, w2, dist) for w1, w2, dist in all_delaunay_edges
        if tuple(sorted((w1, w2))) not in mst_edge_keys
    ]
    
    # Iterate through remaining Delaunay edges (still sorted by distance)
    for w1, w2, dist in remaining_delaunay_edges:
        # Check if adding this edge would increase degrees of both endpoints
        # without exceeding the max degree of 3
        if node_degrees_current[w1] < 3 and node_degrees_current[w2] < 3:
            final_edges.append((w1, w2, dist))
            node_degrees_current[w1] += 1
            node_degrees_current[w2] += 1
            # Optional: break if all nodes have reached desired degree
            # (less efficient to check in a loop, but useful if most nodes are covered early)

    # 6. Convert final edges to Lane dictionaries
    lanes_data = []
    for idx, (world_id1, world_id2, dist) in enumerate(final_edges):
        lanes_data.append({
            "id": f"lane-gen-{idx}", # Unique ID for the lane
            "source": str(world_id1),
            "target": str(world_id2),
            "distance": round(dist, 2),
            "hazard": round(dist / 100, 2), # Simple hazard based on distance for now
        })
    
    return lanes_data
