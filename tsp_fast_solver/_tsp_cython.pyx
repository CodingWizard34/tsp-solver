# distutils: language = c++
# cython: language_level = 3

from libcpp.vector cimport vector
from tsp_fast_solver.c_tsp cimport tsp_cpp

def tsp_cython(list_of_lists):
    """
    Calculate the optimal TSP path cost using the native C++ solver.

    Parameters:
        list_of_lists (list of list of int): 2D Python list representing the N x N distance matrix.

    Returns:
        int: The minimal cost to visit all cities once and return to the origin.
    """
    cdef int n = len(list_of_lists)
    if n <= 1:
        return 0

    cdef vector[int] flat_matrix
    flat_matrix.reserve(n * n)

    for row in list_of_lists:
        if len(row) != n:
            raise ValueError(f"Distance matrix must be square (N x N). Row has {len(row)} elements, expected {n}.")
        for val in row:
            flat_matrix.push_back(int(val))

    return tsp_cpp(flat_matrix, n)
