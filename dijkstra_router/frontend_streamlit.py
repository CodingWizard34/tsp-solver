"""
frontend_streamlit.py: Web-based interactive dashboard for Dijkstra Map Routing.
Supports real-world OpenStreetMap navigation (e.g. UPES to Premnagar, Dehradun)
with interactive Leaflet map, turn-by-turn directions, Python vs Cython benchmarks,
and JSON path export.
"""

import sys
import os
import time
import json
import streamlit as st
import streamlit.components.v1 as components

# Ensure local package path is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dijkstra_fast_cpp.real_map_router import RealWorldMapGraph, LANDMARKS, haversine_distance
from dijkstra_fast_cpp.map_generator import RoadNetwork, generate_random_map
from dijkstra_fast_cpp.dijkstra_pure import dijkstra_python, dijkstra_cover_waypoints_python
from dijkstra_fast_cpp.json_exporter import export_path_to_json

try:
    from dijkstra_fast_cpp._dijkstra_cython import dijkstra_cython, FastGraph
    CYTHON_AVAILABLE = True
except ImportError:
    CYTHON_AVAILABLE = False


st.set_page_config(
    page_title="Dijkstra Real-World Map Router — UPES to Premnagar",
    page_icon="🗺️",
    layout="wide"
)

# Custom header styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e2e;
        border-radius: 8px;
        padding: 12px;
        border-left: 4px solid #89b4fa;
        margin-bottom: 10px;
    }
    .direction-step {
        padding: 8px 12px;
        border-radius: 6px;
        background: #181825;
        margin-bottom: 6px;
        border-left: 3px solid #a6e3a1;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

st.title("🗺️ Real-World Dijkstra Map Router")
st.caption("C++ (Cython) vs. Pure Python Shortest Path Solver on OpenStreetMap Dehradun Road Network")

# Mode selector in sidebar
mode = st.sidebar.radio(
    "Routing Mode",
    ["📍 Real-World Map (Dehradun: UPES to Premnagar)", "🎲 Procedural Line-Intersection Grid"]
)


# -------------------------------------------------------------
# MODE 1: REAL-WORLD MAP (UPES TO PREMNAGAR)
# -------------------------------------------------------------
if "Real-World" in mode:
    st.sidebar.header("📍 Trip Waypoints")

    landmark_names = list(LANDMARKS.keys())
    origin_name = st.sidebar.selectbox("Start Location", landmark_names, index=0)
    dest_name = st.sidebar.selectbox("Destination", landmark_names, index=5) # Premnagar

    add_stop = st.sidebar.checkbox("Add Intermediate Waypoint", value=False)
    via_name = None
    if add_stop:
        via_name = st.sidebar.selectbox("Via Stop", landmark_names, index=2) # Pondha

    # Cache real road network
    @st.cache_resource
    def load_real_graph():
        g = RealWorldMapGraph()
        fg = None
        if CYTHON_AVAILABLE and g.loaded:
            fg = FastGraph(len(g.osm_id_to_idx))
            fg.add_edges_from_list(g.edges)
        return g, fg

    real_graph, c_graph = load_real_graph()

    if not real_graph.loaded:
        st.error("Real-world OSM road network could not be loaded. Please ensure data/dehradun_roads.json is present.")
        st.stop()

    # Resolve Landmark coordinates to nearest graph node
    start_coord = LANDMARKS[origin_name]
    end_coord = LANDMARKS[dest_name]

    start_idx = real_graph.find_nearest_node(start_coord)
    end_idx = real_graph.find_nearest_node(end_coord)

    waypoints_indices = [start_idx]
    if add_stop and via_name and via_name not in [origin_name, dest_name]:
        via_coord = LANDMARKS[via_name]
        waypoints_indices.append(real_graph.find_nearest_node(via_coord))
    waypoints_indices.append(end_idx)

    # 1. Benchmark Cython C++ vs Pure Python
    t0 = time.perf_counter()
    if len(waypoints_indices) == 2:
        py_dist, py_path, py_reach = dijkstra_python(
            len(real_graph.osm_id_to_idx), real_graph.edges, start_idx, end_idx
        )
    else:
        py_dist, py_path, py_reach = dijkstra_cover_waypoints_python(
            len(real_graph.osm_id_to_idx), real_graph.edges, waypoints_indices
        )
    py_time_ms = (time.perf_counter() - t0) * 1000.0

    if c_graph is not None:
        t1 = time.perf_counter()
        if len(waypoints_indices) == 2:
            cy_dist, cy_path, cy_reach = c_graph.shortest_path(start_idx, end_idx)
        else:
            cy_dist, cy_path, cy_reach = c_graph.cover_waypoints(waypoints_indices)
        cy_time_ms = (time.perf_counter() - t1) * 1000.0
        speedup = py_time_ms / cy_time_ms if cy_time_ms > 0 else 1.0

        active_path = cy_path
        active_dist_m = cy_dist
        active_reach = cy_reach
    else:
        cy_time_ms = 0.0
        speedup = 1.0
        active_path = py_path
        active_dist_m = py_dist
        active_reach = py_reach

    # Layout: Map on left (2.5), Directions & Stats on right (1.2)
    col_map, col_info = st.columns([2.5, 1.2])

    with col_info:
        st.subheader("⚡ Performance Delta")
        dist_km = active_dist_m / 1000.0

        m1, m2 = st.columns(2)
        m1.metric("Distance", f"{dist_km:.2f} km")
        m2.metric("Speedup", f"{speedup:.1f}x faster" if CYTHON_AVAILABLE else "N/A")

        st.metric("Pure Python (heapq)", f"{py_time_ms:.2f} ms")
        if CYTHON_AVAILABLE:
            st.metric("Cython C++ (FastGraph)", f"{cy_time_ms:.3f} ms")

        st.caption(f"Network: **{len(real_graph.osm_id_to_idx):,}** real nodes, **{len(real_graph.edges):,}** edges")

        # Turn-by-turn directions
        st.subheader("🧭 Turn-by-Turn Directions")
        directions = real_graph.generate_directions(active_path)
        with st.container(height=260):
            if directions:
                for idx, step in enumerate(directions):
                    st.markdown(
                        f"<div class='direction-step'>"
                        f"<b>{idx + 1}.</b> {step['instruction']} "
                        f"<span style='color: #89b4fa; float: right;'>{step['distance_km']} km</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.info("Direct route without road splits.")

        # Export to JSON
        path_coords = [real_graph.get_node_coord(nid) for nid in active_path]
        json_payload = {
            "origin": origin_name,
            "destination": dest_name,
            "total_distance_km": round(dist_km, 3),
            "total_nodes_traversed": len(active_path),
            "runtime_benchmark": {
                "python_ms": round(py_time_ms, 3),
                "cython_ms": round(cy_time_ms, 3),
                "speedup_factor": f"{speedup:.1f}x"
            },
            "turn_by_turn_directions": directions,
            "path_gps_coordinates": [{"lat": lat, "lon": lon} for lat, lon in path_coords]
        }
        json_str = json.dumps(json_payload, indent=2)

        st.download_button(
            label="💾 Export Real Path to JSON",
            data=json_str,
            file_name=f"route_{origin_name.split()[0]}_to_{dest_name.split()[0]}.json",
            mime="application/json",
            use_container_width=True
        )

    with col_map:
        st.subheader(f"🗺️ Real Route: {origin_name} ➔ {dest_name}")

        # Extract lat/lon list for Leaflet Polyline
        lat_lons = [[lat, lon] for lat, lon in path_coords]
        center_lat = (start_coord[0] + end_coord[0]) / 2.0
        center_lon = (start_coord[1] + end_coord[1]) / 2.0

        # Construct Leaflet.js HTML with real OpenStreetMap tiles
        leaflet_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                html, body {{ height: 100%; margin: 0; padding: 0; background: #11111b; }}
                #map {{ width: 100%; height: 580px; border-radius: 8px; }}
                .leaflet-popup-content-wrapper {{ background: #181825; color: #cdd6f4; font-family: sans-serif; }}
                .leaflet-popup-tip {{ background: #181825; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{center_lat}, {center_lon}], 12);
                
                // OpenStreetMap Standard Street Tile Layer
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    maxZoom: 19,
                    attribution: '© OpenStreetMap contributors'
                }}).addTo(map);

                var routePoints = {json.dumps(lat_lons)};

                // Glowing Shortest Path Polyline
                var pathPolyline = L.polyline(routePoints, {{
                    color: '#00E5FF',
                    weight: 6,
                    opacity: 0.9,
                    lineJoin: 'round'
                }}).addTo(map);

                // Start Marker (UPES)
                var startMarker = L.circleMarker([{start_coord[0]}, {start_coord[1]}], {{
                    radius: 9,
                    fillColor: '#00E676',
                    color: '#ffffff',
                    weight: 2,
                    fillOpacity: 1
                }}).addTo(map).bindPopup("<b>🟢 Start: {origin_name}</b><br>{start_coord[0]:.4f}, {start_coord[1]:.4f}").openPopup();

                // Destination Marker (Premnagar)
                var endMarker = L.circleMarker([{end_coord[0]}, {end_coord[1]}], {{
                    radius: 9,
                    fillColor: '#FF1744',
                    color: '#ffffff',
                    weight: 2,
                    fillOpacity: 1
                }}).addTo(map).bindPopup("<b>🔴 Destination: {dest_name}</b><br>{end_coord[0]:.4f}, {end_coord[1]:.4f}");

                // Fit map to route bounds
                if (routePoints.length > 0) {{
                    map.fitBounds(pathPolyline.getBounds(), {{ padding: [30, 30] }});
                }}
            </script>
        </body>
        </html>
        """

        components.html(leaflet_html, height=600)


# -------------------------------------------------------------
# MODE 2: PROCEDURAL LINE-INTERSECTION GRID
# -------------------------------------------------------------
else:
    st.sidebar.header("⚙️ Procedural Settings")
    seed = st.sidebar.number_input("Random Seed", min_value=1, max_value=99999, value=42, step=1)
    num_roads = st.sidebar.slider("Number of Arterial Roads", min_value=6, max_value=28, value=14, step=2)
    num_waypoints = st.sidebar.slider("Waypoints to Cover", min_value=2, max_value=8, value=4, step=1)

    network = generate_random_map(width=800, height=600, num_roads=num_roads, num_waypoints=num_waypoints, seed=seed)

    col_map, col_metrics = st.columns([2.5, 1.2])

    with col_metrics:
        st.subheader("⚡ Performance Benchmark")
        n = len(network.nodes)
        edges = network.edges
        wps = network.waypoints

        t0 = time.perf_counter()
        py_dist, py_path, py_reach = dijkstra_cover_waypoints_python(n, edges, wps)
        py_time_ms = (time.perf_counter() - t0) * 1000.0

        if CYTHON_AVAILABLE:
            fast_g = FastGraph(n)
            fast_g.add_edges_from_list(edges)
            t1 = time.perf_counter()
            cy_dist, cy_path, cy_reach = fast_g.cover_waypoints(wps)
            cy_time_ms = (time.perf_counter() - t1) * 1000.0
            speedup = py_time_ms / cy_time_ms if cy_time_ms > 0 else 1.0

            st.metric("Pure Python (heapq)", f"{py_time_ms:.3f} ms")
            st.metric("Cython C++ (FastGraph)", f"{cy_time_ms:.3f} ms", delta=f"{speedup:.1f}x faster")
            st.metric("Total Path Distance", f"{cy_dist:.2f} px")
            active_path = cy_path
            active_dist = cy_dist
            timing_data = {"python_ms": round(py_time_ms, 3), "cython_ms": round(cy_time_ms, 3), "speedup": f"{speedup:.1f}x"}
        else:
            st.metric("Pure Python (heapq)", f"{py_time_ms:.3f} ms")
            st.metric("Total Path Distance", f"{py_dist:.2f} px")
            active_path = py_path
            active_dist = py_dist
            timing_data = {"python_ms": round(py_time_ms, 3)}

        st.caption(f"Generated: **{len(network.nodes)}** intersections, **{len(network.edges)}** road edges")

        json_out = export_path_to_json(
            network_nodes=network.nodes,
            network_edges=network.edges,
            path_node_ids=active_path,
            total_distance=active_dist,
            waypoints=network.waypoints,
            timing_info=timing_data
        )

        st.download_button(
            label="💾 Download Path as JSON",
            data=json_out,
            file_name=f"procedural_dijkstra_path_{seed}.json",
            mime="application/json",
            use_container_width=True
        )

    with col_map:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 7.5), facecolor='#11111b')
        ax.set_facecolor('#181825')

        for p1, p2 in network.road_segments:
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#313244', linewidth=2.5, zorder=1)

        node_map = {node['id']: (node['x'], node['y']) for node in network.nodes}
        for u, v, _ in network.edges:
            if u < v:
                p1 = node_map[u]
                p2 = node_map[v]
                ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#45475a', linewidth=1.2, linestyle=':', zorder=2)

        xs = [node['x'] for node in network.nodes]
        ys = [node['y'] for node in network.nodes]
        ax.scatter(xs, ys, color='#89b4fa', s=25, zorder=3, alpha=0.8, edgecolors='#181825')

        if len(active_path) >= 2:
            path_x = [node_map[nid][0] for nid in active_path]
            path_y = [node_map[nid][1] for nid in active_path]
            ax.plot(path_x, path_y, color='#a6e3a1', linewidth=4.5, zorder=4, label='Dijkstra Path')

        for idx, wp_id in enumerate(network.waypoints):
            wx, wy = node_map[wp_id]
            color = '#f9e2af' if idx == 0 else ('#f38ba8' if idx == len(network.waypoints) - 1 else '#fab387')
            ax.scatter([wx], [wy], color=color, s=160, zorder=5, edgecolors='#11111b', linewidth=2)
            ax.text(wx, wy, str(idx + 1), color='#11111b', fontsize=10, fontweight='bold', ha='center', va='center', zorder=6)

        ax.set_xlim(-10, 810)
        ax.set_ylim(-10, 610)
        ax.invert_yaxis()
        ax.axis('off')
        st.pyplot(fig)
