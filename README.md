# tsp-fast-solver-codingwizard34: Graph Algorithms in Production (TSP)

A high-performance implementation of the Traveling Salesperson Problem (TSP) brute-force solver comparing pure Python against native C++ wrapped with Cython.

## Overview

The Traveling Salesperson Problem (TSP) is an NP-hard combinatorial graph problem: given a list of cities and the distances between each pair of cities, what is the shortest possible route that visits each city exactly once and returns to the origin city?

Because the number of Hamiltonian cycles scales factorially:
$$\text{Possible Routes} = (N - 1)!$$
a pure Python search quickly slows down due to interpreter overhead and dynamic type checking. By offloading the permutation traversal to native C++ using `std::next_permutation` and bridging it with a Cython C-extension, we achieve up to **~90x–100x speedup**.

---

## Architecture & Project Structure

```
tsp-fast-solver/
├── pyproject.toml            # Build system metadata (PEP 517/518)
├── setup.py                  # Setuptools & Cython C++ build configuration
├── benchmark.py              # Benchmarking script comparing both solvers
├── README.md                 # Project documentation and benchmarks
├── .gitignore                # Excludes compiled binaries (.pyd, .so, build/)
├── tests/
│   └── test_tsp.py           # Comprehensive unit tests (correctness & edge cases)
└── tsp_fast_solver/
    ├── __init__.py           # Package exports (tsp_python, tsp_cython)
    ├── python_solver.py      # Pure Python solver using itertools.permutations
    ├── tsp.h                 # C++ header declaring tsp_cpp
    ├── tsp.cpp               # C++ native solver using std::next_permutation
    ├── c_tsp.pxd             # Cython C++ header declaration
    └── _tsp_cython.pyx       # Cython wrapper bridging Python 2D lists to std::vector<int>
```

### Components

1. **Pure Python Solver (`tsp_python`)**:
   - Uses Python's `itertools.permutations` over nodes $\{1, \dots, N-1\}$.
   - Evaluates $(N-1)!$ possible paths starting and ending at node 0.

2. **Native C++ Solver (`tsp_cpp`)**:
   - Implemented in `tsp.h` and `tsp.cpp`.
   - Uses `std::next_permutation` on a flat `std::vector<int>` distance matrix representation with contiguous memory layout and pointer arithmetic.

3. **Cython Wrapper (`tsp_cython`)**:
   - Defined across `c_tsp.pxd` and `_tsp_cython.pyx`.
   - Validates that the input is a square $N \times N$ matrix.
   - Converts the Python list-of-lists into a 1D `std::vector<int>`, delegates to `tsp_cpp`, and returns the optimal cost.

---

## Benchmark Results

Benchmarked on **Python 3.14 (x86_64 Windows)** using `benchmark.py` with reproducible random symmetric distance matrices:

| Graph Size (Nodes) | Possible Routes $(N-1)!$ | Pure Python Time (s) | Cython + C++ Time (s) | Speedup Delta | Deliverable Expected Time |
|:------------------:|:------------------------:|:--------------------:|:---------------------:|:-------------:|:-------------------------:|
| **$N = 8$**        | 5,040                    | 0.0026 s             | 0.00004 s             | **65.2x**     | Python < 0.1s / Instant   |
| **$N = 10$**       | 362,880                  | 0.2208 s             | 0.0022 s              | **98.5x**     | Python ~1–2s / < 0.05s    |
| **$N = 11$**       | 3,628,800                | 3.2364 s             | 0.0359 s              | **90.2x**     | Python ~15–30s / ~ 0.5s   |

*Note: The native C++ implementation solves 3.6+ million permutations in just ~36 milliseconds.*

---

## Quick Start & Usage

### 1. Installation

#### From Source (Local Development)
```bash
# Clone the repository
git clone https://github.com/CodingWizard34/tsp-solver.git
cd tsp-solver

# Build extension in-place
python setup.py build_ext --inplace
```

#### Via pip
```bash
pip install .
# Or once published:
pip install tsp-fast-solver-codingwizard34
```

### 2. Python API

```python
from tsp_fast_solver import tsp_python, tsp_cython

# Define an N x N distance matrix (symmetric or asymmetric)
distance_matrix = [
    [0, 10, 15, 20],
    [10,  0, 35, 25],
    [15, 35,  0, 30],
    [20, 25, 30,  0]
]

# Run pure Python solver
py_cost = tsp_python(distance_matrix)
print("Pure Python optimal cost:", py_cost)  # Output: 80

# Run compiled Cython / C++ solver
cy_cost = tsp_cython(distance_matrix)
print("Cython / C++ optimal cost:", cy_cost)  # Output: 80
```

### 3. Running Tests

```bash
python -m unittest discover -s tests -v
```

### 4. Running Benchmarks

```bash
python benchmark.py
```

---

## Packaging and Publishing to PyPI

### 1. Build Source Distribution (sdist) and Wheel

```bash
# Install the build tool
python -m pip install --upgrade build

# Generate distributions
python -m build --sdist
```

The generated `.tar.gz` archive in `dist/` contains all C++ sources, headers, and Cython `.pyx`/`.pxd` files ready for cross-platform compilation upon `pip install`.

### 2. Upload to PyPI with Twine

```bash
# Install Twine
python -m pip install --upgrade twine

# Upload to TestPyPI (recommended first):
python -m twine upload --repository testpypi dist/*

# Upload to production PyPI:
python -m twine upload dist/*
```

When prompted:
- **Username**: `__token__`
- **Password**: `<your-pypi-api-token>`

### 3. Verifying Installation

In a clean virtual environment:
```bash
pip install tsp-fast-solver-codingwizard34
python -c "import tsp_fast_solver; print('Success! tsp-fast-solver loaded version:', tsp_fast_solver.__version__)"
```

---

## License

MIT License.
