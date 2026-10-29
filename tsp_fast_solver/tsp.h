#ifndef TSP_H
#define TSP_H

#include <vector>

/**
 * Solves the Traveling Salesperson Problem (TSP) using a brute-force approach
 * with std::next_permutation.
 *
 * @param dist_matrix 1D vector representing the flattened N x N distance matrix.
 * @param n Number of cities / nodes in the graph.
 * @return The minimum tour cost visiting every node once and returning to the origin.
 */
int tsp_cpp(const std::vector<int>& dist_matrix, int n);

#endif // TSP_H
