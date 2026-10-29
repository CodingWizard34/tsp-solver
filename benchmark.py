"""
benchmark.py: Benchmark pure Python TSP solver vs Cython/C++ TSP solver.

Requirements:
- Generate random distance matrices of sizes N=8, N=10, and N=11.
- Use the timeit module to record the execution time of both solvers.
- Verify equivalence and compare performance.
"""

import sys
import os
import math
import random
import timeit

# Ensure the package is importable from local source
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tsp_fast_solver.python_solver import tsp_python

try:
    from tsp_fast_solver._tsp_cython import tsp_cython
except ImportError:
    print("Error: Cython extension '_tsp_cython' is not built yet.")
    print("Build it locally using: python setup.py build_ext --inplace")
    sys.exit(1)


def generate_random_distance_matrix(n: int, min_dist: int = 10, max_dist: int = 100, seed: int = 42):
    """Generate a symmetric N x N distance matrix with zero diagonal."""
    rng = random.Random(seed)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = rng.randint(min_dist, max_dist)
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


def run_benchmark():
    sizes = [8, 10, 11]
    
    # Configure iterations for timeit
    # For N=11: pure Python takes ~15-30s, so 1 iteration is standard.
    # For N=8, 10: multiple iterations allow precise averaging.
    iterations = {
        8: 5,
        10: 2,
        11: 1,
    }

    results = []

    print("=" * 80)
    print("TSP Benchmark: Pure Python vs Cython + C++ std::next_permutation")
    print("=" * 80)

    for n in sizes:
        routes = math.factorial(n - 1)
        matrix = generate_random_distance_matrix(n, seed=42 + n)

        # 1. Verification of correctness
        py_ans = tsp_python(matrix)
        cy_ans = tsp_cython(matrix)
        assert py_ans == cy_ans, f"Output mismatch at N={n}: Python={py_ans}, Cython={cy_ans}"

        iters = iterations.get(n, 1)

        # 2. Benchmark Pure Python
        py_timer = timeit.Timer(lambda: tsp_python(matrix))
        py_total = py_timer.timeit(number=iters)
        py_avg = py_total / iters

        # 3. Benchmark Cython + C++
        # Because Cython is very fast, run more repeats if needed
        cy_iters = max(iters, 5 if n <= 10 else 2)
        cy_timer = timeit.Timer(lambda: tsp_cython(matrix))
        cy_total = cy_timer.timeit(number=cy_iters)
        cy_avg = cy_total / cy_iters

        speedup = py_avg / cy_avg if cy_avg > 0 else float("inf")

        results.append({
            "n": n,
            "routes": routes,
            "min_cost": py_ans,
            "py_time": py_avg,
            "cy_time": cy_avg,
            "speedup": speedup,
        })

        print(f"N = {n:2d} | Routes: {routes:10,d} | Cost: {py_ans:5d} | "
              f"Python: {py_avg:8.4f}s | Cython: {cy_avg:8.4f}s | Speedup: {speedup:6.1f}x")

    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS TABLE (Markdown)")
    print("=" * 80)
    print("| Graph Size (Nodes) | Possible Routes (N-1)! | Python Time (s) | Cython Time (s) | Speedup Delta |")
    print("|:------------------:|:----------------------:|:---------------:|:---------------:|:-------------:|")
    for r in results:
        print(f"| N = {r['n']:<2d}             | {r['routes']:<22,d} | {r['py_time']:<15.4f} | {r['cy_time']:<15.4f} | {r['speedup']:<13.1f}x |")
    print("=" * 80)

    return results


if __name__ == "__main__":
    run_benchmark()
