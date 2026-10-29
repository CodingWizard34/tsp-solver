import itertools

def tsp_python(distance_matrix):
    """
    Calculate the shortest path through a fully connected graph represented by a 2D distance matrix.
    Uses itertools.permutations to evaluate all (N-1)! possible routes starting and ending at node 0.

    Parameters:
        distance_matrix (list of list of int/float): 2D distance matrix where distance_matrix[i][j]
                                                     is the distance from city i to city j.

    Returns:
        int/float: Minimum cost of a tour visiting each city exactly once and returning to city 0.
    """
    n = len(distance_matrix)
    if n <= 1:
        return 0
    if n == 2:
        return distance_matrix[0][1] + distance_matrix[1][0]

    cities = list(range(1, n))
    min_cost = float('inf')

    for perm in itertools.permutations(cities):
        current_cost = distance_matrix[0][perm[0]]
        for i in range(len(perm) - 1):
            current_cost += distance_matrix[perm[i]][perm[i + 1]]
        current_cost += distance_matrix[perm[-1]][0]

        if current_cost < min_cost:
            min_cost = current_cost

    return min_cost
