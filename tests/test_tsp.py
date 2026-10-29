import unittest
import random
from tsp_fast_solver.python_solver import tsp_python

try:
    from tsp_fast_solver._tsp_cython import tsp_cython
    CYTHON_AVAILABLE = True
except ImportError:
    CYTHON_AVAILABLE = False


def generate_random_matrix(n, seed=None):
    if seed is not None:
        random.seed(seed)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = random.randint(5, 100)
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


class TestTSPSolvers(unittest.TestCase):

    def test_trivial_cases(self):
        self.assertEqual(tsp_python([]), 0)
        self.assertEqual(tsp_python([[0]]), 0)

        if CYTHON_AVAILABLE:
            self.assertEqual(tsp_cython([]), 0)
            self.assertEqual(tsp_cython([[0]]), 0)

    def test_two_cities(self):
        mat = [
            [0, 15],
            [15, 0]
        ]
        self.assertEqual(tsp_python(mat), 30)
        if CYTHON_AVAILABLE:
            self.assertEqual(tsp_cython(mat), 30)

    def test_three_cities(self):
        mat = [
            [0, 10, 20],
            [10, 0, 15],
            [20, 15, 0]
        ]
        # Only one distinct cycle (both directions have same length): 0 -> 1 -> 2 -> 0 => 10 + 15 + 20 = 45
        self.assertEqual(tsp_python(mat), 45)
        if CYTHON_AVAILABLE:
            self.assertEqual(tsp_cython(mat), 45)

    def test_four_cities_known(self):
        mat = [
            [0, 10, 15, 20],
            [10, 0, 35, 25],
            [15, 35, 0, 30],
            [20, 25, 30, 0]
        ]
        # Best route: 0 -> 1 -> 3 -> 2 -> 0 => 10 + 25 + 30 + 15 = 80
        self.assertEqual(tsp_python(mat), 80)
        if CYTHON_AVAILABLE:
            self.assertEqual(tsp_cython(mat), 80)

    def test_python_and_cython_equivalence(self):
        if not CYTHON_AVAILABLE:
            self.skipTest("Cython extension not built yet")

        for size in [4, 5, 6, 7]:
            mat = generate_random_matrix(size, seed=100 + size)
            py_cost = tsp_python(mat)
            cy_cost = tsp_cython(mat)
            self.assertEqual(py_cost, cy_cost, f"Mismatch on size {size}: Python={py_cost}, Cython={cy_cost}")

    def test_invalid_dimension(self):
        if CYTHON_AVAILABLE:
            with self.assertRaises(ValueError):
                tsp_cython([[0, 10], [10]])


if __name__ == "__main__":
    unittest.main()
