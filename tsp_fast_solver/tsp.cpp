#include "tsp.h"
#include <vector>
#include <numeric>
#include <algorithm>
#include <climits>

int tsp_cpp(const std::vector<int>& dist_matrix, int n) {
    if (n <= 1) {
        return 0;
    }
    if (n == 2) {
        return dist_matrix[0 * n + 1] + dist_matrix[1 * n + 0];
    }

    // Cities 1 to n - 1 (origin is fixed at 0)
    std::vector<int> cities(n - 1);
    for (int i = 0; i < n - 1; ++i) {
        cities[i] = i + 1;
    }

    int min_cost = INT_MAX;
    const int* matrix_data = dist_matrix.data();
    const int num_intermediate = n - 2;

    do {
        // Distance from origin 0 to first visited city
        int current_cost = matrix_data[cities[0]];

        // Distance between intermediate cities
        for (int i = 0; i < num_intermediate; ++i) {
            current_cost += matrix_data[cities[i] * n + cities[i + 1]];
        }

        // Return distance from last city back to origin 0
        current_cost += matrix_data[cities[n - 2] * n];

        if (current_cost < min_cost) {
            min_cost = current_cost;
        }
    } while (std::next_permutation(cities.begin(), cities.end()));

    return min_cost;
}
