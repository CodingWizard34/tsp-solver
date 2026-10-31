"""
real_map_router.py: Real-world geographic road network router for Dehradun.
Routes from actual landmarks (e.g. UPES to Premnagar) using Cython C++ Dijkstra,
extracts street names, and computes turn-by-turn navigation directions.
"""

import json
import math
import os
from typing import List, Dict, Any, Tuple, Optional

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "dehradun_roads.json")

# Prominent Dehradun Landmarks with real coordinates (Lat, Lon)
LANDMARKS = {
    "UPES Bidholi (Campus)": (30.41761, 77.96827),
    "UPES Kandoli (Campus)": (30.40420, 77.97340),
    "Pondha": (30.38050, 77.96320),
    "Dunga": (30.39510, 77.93920),
    "Nanda Ki Chowki": (30.35410, 77.96450),
    "Premnagar (Market)": (30.33522, 77.96400),
    "Suddhowala": (30.34400, 77.95500),
    "Manduwala": (30.39800, 77.92500)
}


def haversine_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculates haversine distance in meters between two (lat, lon) coordinates."""
    R = 6371000.0  # Earth radius in meters
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2.0)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0)**2
    return 2.0 * R * math.asin(math.sqrt(max(0.0, a)))


def calculate_bearing(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculates compass bearing from p1 to p2 in degrees (0 = North)."""
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0


def bearing_to_direction(deg: float) -> str:
    dirs = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"]
    idx = int((deg + 22.5) / 45.0) % 8
    return dirs[idx]


class RealWorldMapGraph:
    """
    Manages the OpenStreetMap Dehradun road graph, nodes, edges, street names,
    and integrates with Cython C++ FastGraph.
    """
    def __init__(self, osm_json_path: str = DATA_PATH):
        self.osm_json_path = osm_json_path
        self.node_coords: Dict[int, Tuple[float, float]] = {}  # osm_id -> (lat, lon)
        self.osm_id_to_idx: Dict[int, int] = {}
        self.idx_to_osm_id: Dict[int, int] = {}
        self.edges: List[Tuple[int, int, float]] = []          # [(u_idx, v_idx, dist_meters)]
        self.edge_street_names: Dict[Tuple[int, int], str] = {}
        self.loaded = False

        self._load_network()

    def _load_network(self):
        if not os.path.exists(self.osm_json_path):
            print(f"Warning: OSM data file not found at {self.osm_json_path}")
            return

        with open(self.osm_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        all_nodes = {}
        for el in data.get("elements", []):
            if el["type"] == "node":
                all_nodes[el["id"]] = (float(el["lat"]), float(el["lon"]))

        ways = [el for el in data.get("elements", []) if el["type"] == "way"]

        # Collect unique nodes used in ways
        used_nodes = set()
        for w in ways:
            used_nodes.update(w.get("nodes", []))

        # Assign 0..N-1 indices
        for i, nid in enumerate(used_nodes):
            if nid in all_nodes:
                self.node_coords[nid] = all_nodes[nid]
                self.osm_id_to_idx[nid] = len(self.osm_id_to_idx)
                self.idx_to_osm_id[self.osm_id_to_idx[nid]] = nid

        # Build edges with haversine distances
        for w in ways:
            wnodes = w.get("nodes", [])
            tags = w.get("tags", {})
            street_name = tags.get("name", tags.get("ref", tags.get("highway", "Unnamed Road")))
            oneway = tags.get("oneway", "no") in ["yes", "1", "true"]

            for k in range(len(wnodes) - 1):
                u, v = wnodes[k], wnodes[k + 1]
                if u in self.osm_id_to_idx and v in self.osm_id_to_idx:
                    u_idx = self.osm_id_to_idx[u]
                    v_idx = self.osm_id_to_idx[v]
                    p1 = self.node_coords[u]
                    p2 = self.node_coords[v]
                    d = round(haversine_distance(p1, p2), 2)

                    self.edges.append((u_idx, v_idx, d))
                    self.edge_street_names[(u_idx, v_idx)] = street_name
                    if not oneway:
                        self.edges.append((v_idx, u_idx, d))
                        self.edge_street_names[(v_idx, u_idx)] = street_name

        self.loaded = True

    def find_nearest_node(self, target_coord: Tuple[float, float]) -> int:
        """Finds closest node index in road graph to a given (lat, lon)."""
        best_idx = 0
        min_d = float("inf")
        for osm_id, p in self.node_coords.items():
            d = haversine_distance(target_coord, p)
            if d < min_d:
                min_d = d
                best_idx = self.osm_id_to_idx[osm_id]
        return best_idx

    def get_node_coord(self, idx: int) -> Tuple[float, float]:
        osm_id = self.idx_to_osm_id[idx]
        return self.node_coords[osm_id]

    def generate_directions(self, path_indices: List[int]) -> List[Dict[str, Any]]:
        """Generates step-by-step turn directions along the shortest path."""
        if len(path_indices) < 2:
            return []

        steps = []
        current_street = None
        accum_dist = 0.0
        start_pt = self.get_node_coord(path_indices[0])

        for i in range(len(path_indices) - 1):
            u = path_indices[i]
            v = path_indices[i + 1]
            p1 = self.get_node_coord(u)
            p2 = self.get_node_coord(v)
            d = haversine_distance(p1, p2)
            street = self.edge_street_names.get((u, v), "Road")

            if current_street is None:
                current_street = street
                accum_dist = d
            elif street == current_street:
                accum_dist += d
            else:
                bearing = calculate_bearing(p1, p2)
                direction = bearing_to_direction(bearing)
                steps.append({
                    "instruction": f"Continue along {current_street}",
                    "distance_meters": round(accum_dist, 1),
                    "distance_km": round(accum_dist / 1000.0, 2),
                    "heading": direction
                })
                current_street = street
                accum_dist = d

        if current_street is not None:
            steps.append({
                "instruction": f"Follow {current_street} to destination",
                "distance_meters": round(accum_dist, 1),
                "distance_km": round(accum_dist / 1000.0, 2),
                "heading": "Destination"
            })

        return steps
