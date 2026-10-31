"""
frontend_streamlit.py: Web-based interactive dashboard for Dijkstra Map Routing.
Visualizes procedural maps, calculates geometric intersections, compares Python
vs Cython C++ execution speeds, and exports/downloads the path as JSON.

Run with:
    streamlit run frontend_streamlit.py
"""

import sys
import os
import time
import json
import streamlit as st
import matplotlib.pyplot as plt

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dijkstra_fast_cpp.map_generator import RoadNetwork, generate_random_map
from dijkstra_fast_cpp.dijkstra_pure import dijkstra_cover_waypoints_python
from dijkstra_fast_cpp.json_exporter import export_path_to_json

try:
    from dijkstra_fast_cpp._dijkstra_cython import dijkstra_cover_waypoints_cython, FastGraph
    CYTHON_AVAILABLE = True
except ImportError:
    CYTHON_AVAILABLE = False


# Page setup
st.set_page_config(
    page_title="Dijkstra Map Routing — Python vs Cython",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Dijkstra Map Routing: Python vs. Cython C++")
st.markdown(
    "Procedural map generation, geometric road line intersection detection, "
    "and ultra-fast shortest path computation covering random waypoints."
)

# Sidebar Controls
st.sidebar.header("⚙️ Map & Graph Settings")

seed = st.sidebar.number_input("Random Seed", min_value=1, max_value=99999, value=42, step=1)
num_roads = st.sidebar.slider("Number of Arterial Roads", min_value=6, max_value=28, value=14, step=2)
num_waypoints = st.sidebar.slider("Waypoints to Cover", min_value=2, max_value=8, value=4, step=1)

# Generate or fetch cached map
@st.cache_data
def get_map(seed_val, roads_val, wp_val):
    return generate_random_map(width=800, height=600, num_roads=roads_val, num_waypoints=wp_val, seed=seed_val)

network = get_map(seed, num_roads, num_waypoints)

col_map, col_metrics = st.columns([2.5, 1.2])

with col_metrics:
    st.subheader("⚡ Performance Benchmark")

    n = len(network.nodes)
    edges = network.edges
    wps = network.waypoints

    # Execute and time Pure Python Dijkstra
    t0 = time.perf_counter()
    py_dist, py_path, py_reach = dijkstra_cover_waypoints_python(n, edges, wps)
    py_time_ms = (time.perf_counter() - t0) * 1000.0

    # Execute and time Cython C++ Dijkstra
    if CYTHON_AVAILABLE:
        # Pre-built FastGraph query
        fast_g = FastGraph(n)
        fast_g.add_edges_from_list(edges)

        t1 = time.perf_counter()
        cy_dist, cy_path, cy_reach = fast_g.cover_waypoints(wps)
        cy_time_ms = (time.perf_counter() - t1) * 1000.0
        speedup = py_time_ms / cy_time_ms if cy_time_ms > 0 else 1.0

        st.metric("Pure Python (heapq)", f"{py_time_ms:.3f} ms")
        st.metric("Cython C++ (std::priority_queue)", f"{cy_time_ms:.3f} ms", delta=f"{speedup:.1f}x faster")
        st.metric("Total Path Distance", f"{cy_dist:.2f} px")

        timing_data = {
            "python_time_ms": round(py_time_ms, 4),
            "cython_time_ms": round(cy_time_ms, 4),
            "speedup_factor": f"{speedup:.1f}x"
        }
        active_path = cy_path
        active_dist = cy_dist
    else:
        st.metric("Pure Python (heapq)", f"{py_time_ms:.3f} ms")
        st.warning("Cython extension not built.")
        st.metric("Total Path Distance", f"{py_dist:.2f} px")
        timing_data = {"python_time_ms": round(py_time_ms, 4)}
        active_path = py_path
        active_dist = py_dist

    st.markdown("---")
    st.subheader("📊 Graph Statistics")
    st.write(f"- **Intersections (Nodes)**: `{len(network.nodes)}`")
    st.write(f"- **Road Edges**: `{len(network.edges)}`")
    st.write(f"- **Waypoints**: `{len(network.waypoints)}`")
    st.write(f"- **Nodes in Path**: `{len(active_path)}`")

    # JSON Export & Download
    json_output = export_path_to_json(
        network_nodes=network.nodes,
        network_edges=network.edges,
        path_node_ids=active_path,
        total_distance=active_dist,
        waypoints=network.waypoints,
        timing_info=timing_data
    )

    st.download_button(
        label="💾 Download Path as JSON",
        data=json_output,
        file_name=f"dijkstra_path_seed_{seed}.json",
        mime="application/json",
        use_container_width=True
    )

with col_map:
    st.subheader("🗺️ Road Map & Shortest Path Visualization")

    fig, ax = plt.subplots(figsize=(10, 7.5), facecolor='#11111b')
    ax.set_facecolor('#181825')

    # Draw Road Segments
    for p1, p2 in network.road_segments:
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#313244', linewidth=2.5, zorder=1)

    # Draw Graph Edges
    node_map = {node['id']: (node['x'], node['y']) for node in network.nodes}
    for u, v, _ in network.edges:
        if u < v:
            p1 = node_map[u]
            p2 = node_map[v]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#45475a', linewidth=1.2, linestyle=':', zorder=2)

    # Draw Intersections (Nodes)
    xs = [node['x'] for node in network.nodes]
    ys = [node['y'] for node in network.nodes]
    ax.scatter(xs, ys, color='#89b4fa', s=25, zorder=3, alpha=0.8, edgecolors='#181825', label='Intersections')

    # Draw Highlighted Shortest Path
    if len(active_path) >= 2:
        path_x = [node_map[nid][0] for nid in active_path]
        path_y = [node_map[nid][1] for nid in active_path]
        ax.plot(path_x, path_y, color='#a6e3a1', linewidth=4.5, zorder=4, label='Dijkstra Shortest Path')

    # Draw Waypoints
    for idx, wp_id in enumerate(network.waypoints):
        wx, wy = node_map[wp_id]
        color = '#f9e2af' if idx == 0 else ('#f38ba8' if idx == len(network.waypoints) - 1 else '#fab387')
        ax.scatter([wx], [wy], color=color, s=160, zorder=5, edgecolors='#11111b', linewidth=2)
        ax.text(wx, wy, str(idx + 1), color='#11111b', fontsize=10, fontweight='bold',
                ha='center', va='center', zorder=6)

    ax.set_xlim(-10, 810)
    ax.set_ylim(-10, 610)
    ax.invert_yaxis()  # Canvas top-down coordinates
    ax.axis('off')
    ax.legend(loc='upper right', facecolor='#1e1e2e', edgecolor='#45475a', labelcolor='#cdd6f4')

    st.pyplot(fig)

with st.expander("📄 View Exported Path JSON Preview"):
    st.json(json.loads(json_output))
