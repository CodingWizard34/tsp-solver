# cython: language_level = 3
from libcpp.vector cimport vector

cdef extern from "tsp.h":
    int tsp_cpp(const vector[int]& dist_matrix, int n)
