"""
frontend_gui.py: Interactive Desktop GUI (Tkinter) for Dijkstra Map Routing.
Visualizes roads, finds geometric intersections, marks waypoints, calculates
shortest path comparing Python vs Cython C++, and exports results to JSON.
"""

import sys
import os
import time
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Add package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dijkstra_fast_cpp.map_generator import RoadNetwork, generate_random_map, euclidean_distance
from dijkstra_fast_cpp.dijkstra_pure import dijkstra_cover_waypoints_python
from dijkstra_fast_cpp.json_exporter import export_path_to_json

try:
    from dijkstra_fast_cpp._dijkstra_cython import dijkstra_cover_waypoints_cython, FastGraph
    CYTHON_AVAILABLE = True
except ImportError:
    CYTHON_AVAILABLE = False


class DijkstraMapApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dijkstra Map Routing — Python vs Cython C++")
        self.geometry("1180x780")
        self.configure(bg="#1e1e2e")

        self.network = RoadNetwork()
        self.path_nodes = []
        self.total_distance = 0.0
        self.timing_info = {}

        self._init_ui()
        self.generate_new_map(seed=42)

    def _init_ui(self):
        # Header Frame
        header = tk.Frame(self, bg="#181825", height=60)
        header.pack(fill=tk.X, side=tk.TOP)

        title = tk.Label(
            header,
            text="⚡ Dijkstra Map Routing & Intersection Solver",
            font=("Segoe UI", 16, "bold"),
            fg="#cdd6f4",
            bg="#181825"
        )
        title.pack(side=tk.LEFT, padx=20, pady=12)

        status_cy = "Active (Compiled C++)" if CYTHON_AVAILABLE else "Disabled"
        cy_badge = tk.Label(
            header,
            text=f"Cython C++: {status_cy}",
            font=("Segoe UI", 10, "bold"),
            fg="#a6e3a1" if CYTHON_AVAILABLE else "#f38ba8",
            bg="#313244",
            padx=10,
            pady=4
        )
        cy_badge.pack(side=tk.RIGHT, padx=20, pady=14)

        # Main Layout: Canvas on Left, Controls & Metrics on Right
        main_frame = tk.Frame(self, bg="#1e1e2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Left: Map Canvas
        canvas_card = tk.Frame(main_frame, bg="#181825", bd=1, relief=tk.SOLID)
        canvas_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_card, bg="#11111b", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # Right: Sidebar Panel
        sidebar = tk.Frame(main_frame, bg="#181825", width=340)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        sidebar.pack_propagate(False)

        # Controls Section
        lbl_ctrl = tk.Label(sidebar, text="MAP & GRAPH CONTROLS", font=("Segoe UI", 11, "bold"), fg="#89b4fa", bg="#181825")
        lbl_ctrl.pack(anchor=tk.W, padx=15, pady=(15, 8))

        # Sliders
        f_roads = tk.Frame(sidebar, bg="#181825")
        f_roads.pack(fill=tk.X, padx=15, pady=4)
        tk.Label(f_roads, text="Road Lines:", fg="#a6adc8", bg="#181825").pack(side=tk.LEFT)
        self.road_slider = tk.Scale(f_roads, from_=6, to=30, orient=tk.HORIZONTAL, bg="#181825", fg="#cdd6f4", highlightthickness=0)
        self.road_slider.set(14)
        self.road_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        f_wp = tk.Frame(sidebar, bg="#181825")
        f_wp.pack(fill=tk.X, padx=15, pady=4)
        tk.Label(f_wp, text="Waypoints:", fg="#a6adc8", bg="#181825").pack(side=tk.LEFT)
        self.wp_slider = tk.Scale(f_wp, from_=2, to=8, orient=tk.HORIZONTAL, bg="#181825", fg="#cdd6f4", highlightthickness=0)
        self.wp_slider.set(4)
        self.wp_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # Action Buttons
        btn_gen = tk.Button(sidebar, text="🎲 Generate Random Map", bg="#313244", fg="#cdd6f4",
                            font=("Segoe UI", 10, "bold"), command=lambda: self.generate_new_map(), relief=tk.FLAT, pady=6)
        btn_gen.pack(fill=tk.X, padx=15, pady=(10, 5))

        btn_solve = tk.Button(sidebar, text="🚀 Solve Shortest Path (Benchmark)", bg="#89b4fa", fg="#11111b",
                              font=("Segoe UI", 10, "bold"), command=self.solve_and_benchmark, relief=tk.FLAT, pady=6)
        btn_solve.pack(fill=tk.X, padx=15, pady=5)

        btn_export = tk.Button(sidebar, text="💾 Export Path to JSON", bg="#a6e3a1", fg="#11111b",
                               font=("Segoe UI", 10, "bold"), command=self.export_json, relief=tk.FLAT, pady=6)
        btn_export.pack(fill=tk.X, padx=15, pady=5)

        btn_clear_wp = tk.Button(sidebar, text="📍 Clear Custom Waypoints", bg="#45475a", fg="#cdd6f4",
                                 font=("Segoe UI", 9), command=self.clear_waypoints, relief=tk.FLAT, pady=4)
        btn_clear_wp.pack(fill=tk.X, padx=15, pady=5)

        sep = tk.Frame(sidebar, bg="#313244", height=1)
        sep.pack(fill=tk.X, padx=15, pady=15)

        # Performance Metrics Section
        lbl_perf = tk.Label(sidebar, text="PERFORMANCE COMPARISON", font=("Segoe UI", 11, "bold"), fg="#fab387", bg="#181825")
        lbl_perf.pack(anchor=tk.W, padx=15, pady=(0, 8))

        self.lbl_py_time = tk.Label(sidebar, text="Python Dijkstra: -- ms", font=("Consolas", 10), fg="#cdd6f4", bg="#181825")
        self.lbl_py_time.pack(anchor=tk.W, padx=15, pady=2)

        self.lbl_cy_time = tk.Label(sidebar, text="Cython C++ Dijkstra: -- ms", font=("Consolas", 10), fg="#cdd6f4", bg="#181825")
        self.lbl_cy_time.pack(anchor=tk.W, padx=15, pady=2)

        self.lbl_speedup = tk.Label(sidebar, text="Speedup Factor: --", font=("Segoe UI", 11, "bold"), fg="#a6e3a1", bg="#181825")
        self.lbl_speedup.pack(anchor=tk.W, padx=15, pady=(6, 12))

        # Graph Summary
        self.lbl_stats = tk.Label(
            sidebar,
            text="Nodes (Intersections): 0\nEdges: 0\nPath Distance: 0.0",
            font=("Segoe UI", 9),
            justify=tk.LEFT,
            fg="#9399b2",
            bg="#181825"
        )
        self.lbl_stats.pack(anchor=tk.W, padx=15, pady=4)

        hint = tk.Label(
            sidebar,
            text="Tip: Click anywhere on the map\nto place custom waypoints!",
            font=("Segoe UI", 8, "italic"),
            fg="#6c7086",
            bg="#181825",
            justify=tk.LEFT
        )
        hint.pack(side=tk.BOTTOM, anchor=tk.W, padx=15, pady=15)

    def generate_new_map(self, seed=None):
        w = max(400, self.canvas.winfo_width()) if self.canvas.winfo_width() > 1 else 760
        h = max(300, self.canvas.winfo_height()) if self.canvas.winfo_height() > 1 else 620

        num_roads = self.road_slider.get()
        num_wp = self.wp_slider.get()

        self.network = generate_random_map(width=w, height=h, num_roads=num_roads, num_waypoints=num_wp, seed=seed)
        self.path_nodes = []
        self.total_distance = 0.0
        self.timing_info = {}

        self.lbl_py_time.config(text="Python Dijkstra: -- ms")
        self.lbl_cy_time.config(text="Cython C++ Dijkstra: -- ms")
        self.lbl_speedup.config(text="Speedup Factor: --")

        self.draw_map()

    def draw_map(self):
        self.canvas.delete("all")

        # 1. Draw Road Segments (Lines)
        for (p1, p2) in self.network.road_segments:
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#313244", width=3)

        # 2. Draw Graph Edges between intersections
        node_map = {n['id']: (n['x'], n['y']) for n in self.network.nodes}
        for (u, v, w) in self.network.edges:
            if u < v:  # Draw each edge once
                p1 = node_map[u]
                p2 = node_map[v]
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#45475a", width=1.5, dash=(2, 2))

        # 3. Draw Intersections (Nodes)
        for node in self.network.nodes:
            x, y = node['x'], node['y']
            r = 3.5
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#89b4fa", outline="#181825", width=1)

        # 4. Draw Shortest Path (Highlighted)
        if len(self.path_nodes) >= 2:
            for i in range(len(self.path_nodes) - 1):
                u = self.path_nodes[i]
                v = self.path_nodes[i + 1]
                p1 = node_map[u]
                p2 = node_map[v]
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#a6e3a1", width=4)

        # 5. Draw Waypoints (Ordered Markers)
        for idx, wp_id in enumerate(self.network.waypoints):
            pt = node_map[wp_id]
            x, y = pt[0], pt[1]
            r = 9
            color = "#f9e2af" if idx == 0 else ("#f38ba8" if idx == len(self.network.waypoints) - 1 else "#fab387")
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="#11111b", width=2)
            self.canvas.create_text(x, y, text=str(idx + 1), font=("Segoe UI", 9, "bold"), fill="#11111b")

        # Update Statistics Label
        self.lbl_stats.config(
            text=f"Nodes (Intersections): {len(self.network.nodes)}\n"
                 f"Edges: {len(self.network.edges)}\n"
                 f"Waypoints: {len(self.network.waypoints)}\n"
                 f"Shortest Path Distance: {self.total_distance:.2f} px"
        )

    def on_canvas_click(self, event):
        """Add clicked location as custom waypoint by snapping to nearest node."""
        if not self.network.nodes:
            return

        cx, cy = event.x, event.y
        nearest_node = min(
            self.network.nodes,
            key=lambda n: math.hypot(n['x'] - cx, n['y'] - cy)
        )

        if nearest_node['id'] not in self.network.waypoints:
            self.network.waypoints.append(nearest_node['id'])
            self.solve_and_benchmark()

    def clear_waypoints(self):
        self.network.waypoints.clear()
        self.path_nodes = []
        self.total_distance = 0.0
        self.draw_map()

    def solve_and_benchmark(self):
        if len(self.network.waypoints) < 2:
            messagebox.showinfo("Need More Waypoints", "Please ensure at least 2 waypoints are placed on the map.")
            return

        n = len(self.network.nodes)
        edges = self.network.edges
        wps = self.network.waypoints

        # 1. Pure Python Dijkstra
        t0 = time.perf_counter()
        py_dist, py_path, py_reach = dijkstra_cover_waypoints_python(n, edges, wps)
        t_py = (time.perf_counter() - t0) * 1000.0

        # 2. Cython C++ Dijkstra
        if CYTHON_AVAILABLE:
            t1 = time.perf_counter()
            cy_dist, cy_path, cy_reach = dijkstra_cover_waypoints_cython(n, edges, wps)
            t_cy = (time.perf_counter() - t1) * 1000.0

            speedup = t_py / t_cy if t_cy > 0 else 1.0
            self.lbl_cy_time.config(text=f"Cython C++: {t_cy:.3f} ms")
            self.lbl_speedup.config(text=f"Speedup Factor: {speedup:.1f}x faster 🚀")
            self.timing_info = {
                "python_time_ms": round(t_py, 3),
                "cython_time_ms": round(t_cy, 3),
                "speedup_factor": f"{speedup:.1f}x"
            }
            self.path_nodes = cy_path
            self.total_distance = cy_dist if cy_reach else 0.0
        else:
            self.lbl_cy_time.config(text="Cython C++: Not available")
            self.path_nodes = py_path
            self.total_distance = py_dist if py_reach else 0.0
            self.timing_info = {"python_time_ms": round(t_py, 3)}

        self.lbl_py_time.config(text=f"Python Dijkstra: {t_py:.3f} ms")
        self.draw_map()

    def export_json(self):
        if not self.path_nodes:
            messagebox.showwarning("No Path", "Please compute a shortest path before exporting.")
            return

        default_name = f"dijkstra_path_{int(time.time())}.json"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile=default_name,
            title="Save Shortest Path JSON"
        )

        if filepath:
            json_str = export_path_to_json(
                network_nodes=self.network.nodes,
                network_edges=self.network.edges,
                path_node_ids=self.path_nodes,
                total_distance=self.total_distance,
                waypoints=self.network.waypoints,
                timing_info=self.timing_info,
                output_filepath=filepath
            )
            messagebox.showinfo("Export Successful", f"Shortest path successfully exported to:\n{filepath}")


if __name__ == "__main__":
    app = DijkstraMapApp()
    app.mainloop()
