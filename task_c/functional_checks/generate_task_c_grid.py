import argparse
import json
import math
import os
import xml.etree.ElementTree as ET


# ============================================================
# Configurazione
# ============================================================

DEFAULT_RESOLUTION = 0.10

ROBOT_SIZE_X = 0.60
ROBOT_SIZE_Y = 0.40

SAFETY_MARGIN = 0.05

ROBOT_RADIUS = (
    math.sqrt(
        (ROBOT_SIZE_X / 2.0) ** 2
        +
        (ROBOT_SIZE_Y / 2.0) ** 2
    )
    +
    SAFETY_MARGIN
)


# ============================================================
# Utility
# ============================================================

def parse_pose(text):

    if text is None:
        return [0.0] * 6

    values = [
        float(x)
        for x in text.split()
    ]

    while len(values) < 6:
        values.append(0.0)

    return values


def world_to_grid(
    x,
    y,
    origin_x,
    origin_y,
    resolution
):

    col = int(
        math.floor(
            (x - origin_x)
            /
            resolution
        )
    )

    row = int(
        math.floor(
            (y - origin_y)
            /
            resolution
        )
    )

    return row, col


# ============================================================
# Lettura SDF
# ============================================================

def parse_world(sdf_file):

    tree = ET.parse(
        sdf_file
    )

    root = tree.getroot()

    world = root.find(
        "world"
    )

    if world is None:
        raise RuntimeError(
            "Elemento <world> non trovato"
        )

    # --------------------------------------------------------
    # Dimensione ground plane
    # --------------------------------------------------------

    ground = None

    for model in world.findall(
        "model"
    ):

        if (
            model.get("name")
            ==
            "ground_plane"
        ):

            ground = model
            break

    if ground is None:
        raise RuntimeError(
            "ground_plane non trovato"
        )

    plane_size = ground.find(
        ".//plane/size"
    )

    if plane_size is None:
        raise RuntimeError(
            "Dimensione ground plane non trovata"
        )

    size_x, size_y = [
        float(v)
        for v in plane_size.text.split()
    ]

    # --------------------------------------------------------
    # Robot
    # --------------------------------------------------------

    robot = None

    for model in world.findall(
        "model"
    ):

        if (
            model.get("name")
            ==
            "robot"
        ):

            robot = model
            break

    if robot is None:
        raise RuntimeError(
            "Robot non trovato"
        )

    robot_pose = parse_pose(
        robot.findtext("pose")
    )

    robot_x = robot_pose[0]
    robot_y = robot_pose[1]

    # --------------------------------------------------------
    # Ostacoli statici box
    # --------------------------------------------------------

    obstacles = []

    for model in world.findall(
        "model"
    ):

        name = model.get(
            "name",
            ""
        )

        if name in (
            "ground_plane",
            "robot"
        ):
            continue

        static_text = model.findtext(
            "static",
            default="false"
        )

        if (
            static_text.strip().lower()
            !=
            "true"
        ):
            continue

        model_pose = parse_pose(
            model.findtext("pose")
        )

        box = model.find(
            ".//collision/geometry/box/size"
        )

        if box is None:
            continue

        sx, sy, sz = [
            float(v)
            for v in box.text.split()
        ]

        obstacles.append({
            "name": name,
            "x": model_pose[0],
            "y": model_pose[1],
            "size_x": sx,
            "size_y": sy
        })

    return {
        "world_size_x": size_x,
        "world_size_y": size_y,
        "robot_x": robot_x,
        "robot_y": robot_y,
        "obstacles": obstacles
    }


# ============================================================
# Occupancy grid
# ============================================================

def generate_grid(
    world,
    resolution,
    goal_x,
    goal_y
):

    width = int(
        round(
            world["world_size_x"]
            /
            resolution
        )
    )

    height = int(
        round(
            world["world_size_y"]
            /
            resolution
        )
    )

    origin_x = (
        -world["world_size_x"]
        /
        2.0
    )

    origin_y = (
        -world["world_size_y"]
        /
        2.0
    )

    grid = [
        [0 for _ in range(width)]
        for _ in range(height)
    ]

    # --------------------------------------------------------
    # Ostacoli inflazionati
    # --------------------------------------------------------

    for obstacle in world[
        "obstacles"
    ]:

        half_x = (
            obstacle["size_x"] / 2.0
            +
            ROBOT_RADIUS
        )

        half_y = (
            obstacle["size_y"] / 2.0
            +
            ROBOT_RADIUS
        )

        min_x = (
            obstacle["x"]
            -
            half_x
        )

        max_x = (
            obstacle["x"]
            +
            half_x
        )

        min_y = (
            obstacle["y"]
            -
            half_y
        )

        max_y = (
            obstacle["y"]
            +
            half_y
        )

        min_row, min_col = (
            world_to_grid(
                min_x,
                min_y,
                origin_x,
                origin_y,
                resolution
            )
        )

        max_row, max_col = (
            world_to_grid(
                max_x,
                max_y,
                origin_x,
                origin_y,
                resolution
            )
        )

        min_row = max(
            0,
            min_row
        )

        min_col = max(
            0,
            min_col
        )

        max_row = min(
            height - 1,
            max_row
        )

        max_col = min(
            width - 1,
            max_col
        )

        for row in range(
            min_row,
            max_row + 1
        ):

            for col in range(
                min_col,
                max_col + 1
            ):

                grid[row][col] = 1

    # --------------------------------------------------------
    # Start e goal
    # --------------------------------------------------------

    start = world_to_grid(
        world["robot_x"],
        world["robot_y"],
        origin_x,
        origin_y,
        resolution
    )

    goal = world_to_grid(
        goal_x,
        goal_y,
        origin_x,
        origin_y,
        resolution
    )

    # sicurezza
    grid[start[0]][start[1]] = 0
    grid[goal[0]][goal[1]] = 0

    return {
        "grid": grid,
        "start": list(start),
        "goal": list(goal),
        "resolution": resolution,
        "origin": [
            origin_x,
            origin_y
        ],
        "world_size": [
            world["world_size_x"],
            world["world_size_y"]
        ],
        "robot_radius": ROBOT_RADIUS
    }


# ============================================================
# Salvataggio PGM
# ============================================================

def save_pgm(
    grid,
    filename
):

    height = len(grid)
    width = len(
        grid[0]
    )

    with open(
        filename,
        "w"
    ) as f:

        f.write("P2\n")
        f.write(
            f"{width} {height}\n"
        )
        f.write("255\n")

        # invertiamo verticalmente solo
        # per visualizzazione
        for row in reversed(grid):

            values = []

            for cell in row:

                if cell == 1:
                    values.append(
                        "0"
                    )
                else:
                    values.append(
                        "255"
                    )

            f.write(
                " ".join(values)
                +
                "\n"
            )


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--sdf",
        required=True
    )

    parser.add_argument(
        "--goal-x",
        type=float,
        default=4.0
    )

    parser.add_argument(
        "--goal-y",
        type=float,
        default=0.0
    )

    parser.add_argument(
        "--resolution",
        type=float,
        default=DEFAULT_RESOLUTION
    )

    parser.add_argument(
        "--output",
        required=True
    )

    args = parser.parse_args()

    world = parse_world(
        args.sdf
    )

    result = generate_grid(
        world,
        args.resolution,
        args.goal_x,
        args.goal_y
    )

    os.makedirs(
        os.path.dirname(
            os.path.abspath(
                args.output
            )
        ),
        exist_ok=True
    )

    with open(
        args.output,
        "w"
    ) as f:

        json.dump(
            result,
            f
        )

    pgm_file = (
        os.path.splitext(
            args.output
        )[0]
        +
        ".pgm"
    )

    save_pgm(
        result["grid"],
        pgm_file
    )

    occupied = sum(
        sum(row)
        for row in result["grid"]
    )

    print()
    print(
        "Task C - occupancy grid generata"
    )
    print(
        "--------------------------------"
    )

    print(
        f"Dimensione mondo: "
        f"{result['world_size'][0]} x "
        f"{result['world_size'][1]} m"
    )

    print(
        f"Risoluzione: "
        f"{result['resolution']} m/cella"
    )

    print(
        f"Grid: "
        f"{len(result['grid'])} x "
        f"{len(result['grid'][0])}"
    )

    print(
        f"Start: "
        f"{result['start']}"
    )

    print(
        f"Goal: "
        f"{result['goal']}"
    )

    print(
        f"Robot radius: "
        f"{result['robot_radius']:.3f} m"
    )

    print(
        f"Celle occupate: "
        f"{occupied}"
    )

    print(
        f"JSON: {args.output}"
    )

    print(
        f"Preview PGM: "
        f"{pgm_file}"
    )


if __name__ == "__main__":
    main()
