"""
tsp-fast-solver: High-performance Traveling Salesperson Problem (TSP) solver
comparing pure Python against Cython-wrapped C++ std::next_permutation.
"""

from .python_solver import tsp_python

try:
    from ._tsp_cython import tsp_cython
except ImportError:
    # Fallback for environments where the compiled C-extension has not been built yet
    tsp_cython = None

__version__ = "0.1.0"
__all__ = ["tsp_python", "tsp_cython"]
