import heapq
import math
import time


# ============================================================
# Euristica
# ============================================================

def heuristic(a, b):
    """
    Distanza di Manhattan.

    Il movimento è consentito nelle quattro direzioni:
    alto, basso, sinistra, destra.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ============================================================
# Vicini
# ============================================================

def get_neighbors(grid, node):
    """
    Restituisce le celle libere adiacenti al nodo.

    Convenzione:
        0 = cella libera
        1 = ostacolo
    """

    rows = len(grid)
    cols = len(grid[0])

    r, c = node

    directions = [
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
    ]

    neighbors = []

    for dr, dc in directions:

        nr = r + dr
        nc = c + dc

        if (
            0 <= nr < rows
            and 0 <= nc < cols
            and grid[nr][nc] == 0
        ):
            neighbors.append((nr, nc))

    return neighbors


# ============================================================
# A*
# ============================================================

def astar(grid, start, goal):
    """
    Calcola un percorso mediante algoritmo A*.

    Parameters
    ----------
    grid : list[list[int]]
        Griglia di occupazione.
        0 = libero
        1 = ostacolo.

    start : tuple[int, int]
        Cella iniziale.

    goal : tuple[int, int]
        Cella obiettivo.

    Returns
    -------
    dict
        path
        path_length
        expanded_nodes
    """

    if not grid or not grid[0]:
        raise ValueError("Griglia vuota")

    rows = len(grid)
    cols = len(grid[0])

    # Controllo griglia rettangolare
    for row in grid:
        if len(row) != cols:
            raise ValueError(
                "La griglia deve essere rettangolare"
            )

    start = tuple(start)
    goal = tuple(goal)

    # Controllo coordinate
    for name, node in [
        ("start", start),
        ("goal", goal),
    ]:

        r, c = node

        if not (
            0 <= r < rows
            and 0 <= c < cols
        ):
            raise ValueError(
                f"{name} fuori dalla griglia"
            )

        if grid[r][c] != 0:
            raise ValueError(
                f"{name} si trova su un ostacolo"
            )

    # Caso banale
    if start == goal:

        return {
            "path": [list(start)],
            "path_length": 1,
            "expanded_nodes": 0,
        }

    # --------------------------------------------------------
    # Strutture A*
    # --------------------------------------------------------

    open_heap = []

    counter = 0

    heapq.heappush(
        open_heap,
        (
            heuristic(start, goal),
            counter,
            start
        )
    )

    came_from = {}

    g_score = {
        start: 0
    }

    closed = set()

    expanded_nodes = 0

    # --------------------------------------------------------
    # Ricerca
    # --------------------------------------------------------

    while open_heap:

        _, _, current = heapq.heappop(
            open_heap
        )

        if current in closed:
            continue

        if current == goal:

            path = [current]

            while current in came_from:

                current = came_from[current]
                path.append(current)

            path.reverse()

            return {
                "path": [
                    list(node)
                    for node in path
                ],
                "path_length": len(path),
                "expanded_nodes":
                    expanded_nodes,
            }

        closed.add(current)
        expanded_nodes += 1

        for neighbor in get_neighbors(
            grid,
            current
        ):

            if neighbor in closed:
                continue

            tentative_g = (
                g_score[current] + 1
            )

            if tentative_g < g_score.get(
                neighbor,
                math.inf
            ):

                came_from[neighbor] = current

                g_score[neighbor] = (
                    tentative_g
                )

                f_score = (
                    tentative_g
                    +
                    heuristic(
                        neighbor,
                        goal
                    )
                )

                counter += 1

                heapq.heappush(
                    open_heap,
                    (
                        f_score,
                        counter,
                        neighbor
                    )
                )

    # Nessun percorso
    return {
        "path": [],
        "path_length": 0,
        "expanded_nodes":
            expanded_nodes,
    }


# ============================================================
# Test standalone
# ============================================================

if __name__ == "__main__":

    test_grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 0, 1, 0],
        [1, 1, 0, 1, 0],
        [0, 0, 0, 0, 0],
    ]

    start = [0, 0]
    goal = [4, 4]

    start_time = time.perf_counter()

    result = astar(
        test_grid,
        start,
        goal
    )

    end_time = time.perf_counter()

    processing_time_ms = (
        end_time - start_time
    ) * 1000.0

    print()
    print("Task C - test A*")
    print("----------------")
    print(f"Start: {start}")
    print(f"Goal:  {goal}")
    print()
    print(
        f"Path length: "
        f"{result['path_length']}"
    )
    print(
        f"Expanded nodes: "
        f"{result['expanded_nodes']}"
    )
    print(
        f"Processing time: "
        f"{processing_time_ms:.6f} ms"
    )
    print()
    print("Path:")

    for node in result["path"]:
        print(node)
