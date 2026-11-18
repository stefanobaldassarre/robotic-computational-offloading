import argparse
import json
import math
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from gz.transport13 import Node
from gz.msgs10.twist_pb2 import Twist
from gz.msgs10.odometry_pb2 import Odometry

parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=["local", "remote"])
args = parser.parse_args()

folder = Path.home() / "tesi_gazebo"
data = json.loads((folder / "task_c/maps/L1.json").read_text())
port = 5200 if args.mode == "local" else 5202
node = Node()
lock = threading.Lock()
state = None
sequence = 0

def callback(msg):
    global state, sequence
    q = msg.pose.orientation
    with lock:
        sequence += 1
        state = {
            "sequence": sequence,
            "received_wall": time.perf_counter(),
            "sim_seconds":
                msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9,
            "x": msg.pose.position.x,
            "y": msg.pose.position.y,
            "yaw": math.atan2(
                2 * (q.w * q.z + q.x * q.y),
                1 - 2 * (q.y*q.y + q.z*q.z),
            ),
            "linear_x": msg.twist.linear.x,
            "angular_z": msg.twist.angular.z,
        }

def fresh():
    with lock:
        current = None if state is None else dict(state)
    if current is None or time.perf_counter() - current["received_wall"] > 1:
        raise RuntimeError("Odometria assente o non aggiornata")
    return current

publisher = node.advertise("/cmd_vel", Twist)

def command(v=0.0, w=0.0):
    msg = Twist()
    msg.linear.x = v
    msg.angular.z = w
    publisher.publish(msg)

def angle(value):
    return math.atan2(math.sin(value), math.cos(value))

def stop():
    current = fresh()
    last = current["sequence"]
    stable = 0
    deadline = time.perf_counter() + 5
    while stable < 5:
        command()
        time.sleep(0.02)
        current = fresh()
        if current["sequence"] != last:
            last = current["sequence"]
            stationary = (
                abs(current["linear_x"]) < 0.005
                and abs(current["angular_z"]) < 0.005
            )
            stable = stable + 1 if stationary else 0
        if time.perf_counter() > deadline:
            raise RuntimeError("Arresto non confermato")
    return fresh()

if not node.subscribe(Odometry, "/model/robot/odometry", callback):
    raise RuntimeError("Sottoscrizione odometria fallita")

report = {"mode": args.mode, "level": "L1", "status": "started"}
trace = []

def main():
    deadline = time.perf_counter() + 10
    while True:
        with lock:
            available = state is not None
        if available:
            break
        if time.perf_counter() > deadline:
            raise RuntimeError("Nessuna odometria")
        time.sleep(0.05)

    for _ in range(20):
        command()
        time.sleep(0.05)
    initial = stop()
    if math.hypot(initial["x"], initial["y"]) > 0.05:
        raise RuntimeError("Riavviare il mondo: robot non vicino a (0,0)")
    if abs(initial["yaw"]) > 0.05:
        raise RuntimeError("Orientamento iniziale diverso da zero")

    start = time.perf_counter()
    response = requests.post(
        f"http://192.168.50.20:{port}/process",
        json={
            "level": "L1", "grid": data["grid"],
            "start": data["start"], "goal": data["goal"],
        },
        timeout=(5, 30),
    )
    received = time.perf_counter()
    response.raise_for_status()
    result = response.json()
    path = result["path"]

    if result["path_length"] != 61 or result["expanded_nodes"] != 450:
        raise RuntimeError("Risultati A* diversi da quelli attesi")
    if len(path) != 61:
        raise RuntimeError("Numero celle incoerente")
    if path[0] != data["start"] or path[-1] != data["goal"]:
        raise RuntimeError("Estremi del percorso errati")

    for row, col in path:
        if not (0 <= row < len(data["grid"])
                and 0 <= col < len(data["grid"][0])):
            raise RuntimeError("Cella fuori mappa")
        if data["grid"][row][col] != 0:
            raise RuntimeError("Percorso su cella occupata")
    for a, b in zip(path, path[1:]):
        if abs(a[0]-b[0]) + abs(a[1]-b[1]) != 1:
            raise RuntimeError("Celle non adiacenti")

    corners = [path[0]]
    for i in range(1, len(path)-1):
        previous = (path[i][0]-path[i-1][0],
                    path[i][1]-path[i-1][1])
        following = (path[i+1][0]-path[i][0],
                     path[i+1][1]-path[i][1])
        if previous != following:
            corners.append(path[i])
    corners.append(path[-1])

    targets = [
        (
            data["origin"][0] + (col+0.5)*data["resolution"],
            data["origin"][1] + (row+0.5)*data["resolution"],
        )
        for row, col in corners
    ]

    ready = fresh()
    if math.hypot(ready["x"]-initial["x"],
                  ready["y"]-initial["y"]) > 0.01:
        raise RuntimeError("Robot spostato durante la richiesta")

    report.update(initial=initial, recognition=result, targets=targets,
                  http_e2e_wall_s=received-start)
    execution_start = time.perf_counter()
    sim_start = ready["sim_seconds"]
    reached = []

    for number, (tx, ty) in enumerate(targets, 1):
        waypoint_start = time.perf_counter()
        last_log = 0.0

        while True:
            current = fresh()
            now = time.perf_counter()
            if current["sim_seconds"] < sim_start:
                raise RuntimeError("Tempo simulato resettato")
            if now - waypoint_start > 120 or now-execution_start > 240:
                raise RuntimeError("Timeout inseguimento percorso")

            dx, dy = tx-current["x"], ty-current["y"]
            distance = math.hypot(dx, dy)
            if distance <= 0.025:
                break

            error = angle(math.atan2(dy, dx)-current["yaw"])
            angular = max(-0.4, min(0.4, 1.5*error))
            linear = min(0.1, 0.7*distance) if abs(error) < 0.12 else 0.0
            command(linear, angular)

            if now-last_log >= 0.1:
                trace.append(dict(current, target=number,
                                  commanded_v=linear, commanded_w=angular))
                last_log = now
            time.sleep(0.02)

        final_waypoint = stop()
        error = math.hypot(tx-final_waypoint["x"], ty-final_waypoint["y"])
        reached.append({"target": number, "error_m": error,
                        "state": final_waypoint})
        print(f"Waypoint {number}/{len(targets)}: errore={error:.4f} m",
              flush=True)
        if error > 0.04:
            raise RuntimeError("Waypoint oltre tolleranza dopo arresto")

    completed = time.perf_counter()
    final = fresh()
    goal_error = math.hypot(
        targets[-1][0]-final["x"], targets[-1][1]-final["y"]
    )
    report.update(
        status="completed", reached=reached, final=final,
        goal_error_m=goal_error, stop_confirmed=True,
        functional_pass=goal_error <= 0.04,
        execution_until_stop_confirmed_wall_s=completed-execution_start,
        execution_until_stop_confirmed_sim_s=final["sim_seconds"]-sim_start,
        total_request_to_completion_wall_s=completed-start,
    )

try:
    main()
except Exception as exc:
    report.update(status="failed", error=str(exc), functional_pass=False)
    raise
finally:
    for _ in range(10):
        command()
        time.sleep(0.05)
    report["trace"] = trace
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
    output = Path(__file__).parent / f"task_c_L1_{args.mode}_{stamp}.json"
    with output.open("x") as stream:
        json.dump(report, stream, indent=2)
    print("Esito:", report["status"])
    print("Errore finale:", report.get("goal_error_m"))
    print("Tempo esecuzione:", report.get("execution_until_stop_confirmed_wall_s"))
    print("Tempo totale:", report.get("total_request_to_completion_wall_s"))
    print("Salvato:", output)
    node.unsubscribe("/model/robot/odometry")
