import argparse
import hashlib
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

dataset = Path.home() / "tesi_gazebo/task_b_audio/Task_B_sequenze_pilot"
items = json.loads((dataset / "manifest.json").read_text())
item = next(x for x in items if x["file"] == "S5_01.wav")
raw = (dataset / "wav" / item["file"]).read_bytes()

if hashlib.sha256(raw).hexdigest() != item["sha256"]:
    raise RuntimeError("Checksum audio errato")

url = (
    "http://192.168.50.20:5300/process"
    if args.mode == "local"
    else "http://192.168.50.20:5302/process"
)

node = Node()
lock = threading.Lock()
state = None
sequence = 0

def on_odom(msg):
    global state, sequence
    with lock:
        sequence += 1
        state = {
            "sequence": sequence,
            "received_wall": time.perf_counter(),
            "sim_seconds":
                msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9,
            "x": msg.pose.position.x,
            "y": msg.pose.position.y,
            "linear_x": msg.twist.linear.x,
            "angular_z": msg.twist.angular.z,
            "yaw": math.atan2(
                2 * (
                    msg.pose.orientation.w * msg.pose.orientation.z
                    + msg.pose.orientation.x * msg.pose.orientation.y
                ),
                1 - 2 * (
                    msg.pose.orientation.y ** 2
                    + msg.pose.orientation.z ** 2
                ),
            ),
        }

def snapshot():
    with lock:
        return None if state is None else dict(state)

def fresh_state():
    current = snapshot()
    if current is None or time.perf_counter() - current["received_wall"] > 1:
        raise RuntimeError("Odometria assente o non aggiornata")
    return current

publisher = node.advertise("/cmd_vel", Twist)

def command(linear, angular=0.0):
    msg = Twist()
    msg.linear.x = linear
    msg.angular.z = angular
    publisher.publish(msg)

if not node.subscribe(Odometry, "/model/robot/odometry", on_odom):
    raise RuntimeError("Sottoscrizione odometria fallita")


def stop_and_confirm():
    reference = fresh_state()
    last = reference["sequence"]
    stable = 0
    deadline = time.perf_counter() + 5
    while stable < 5:
        command(0.0)
        time.sleep(0.02)
        current = fresh_state()
        if current["sequence"] != last:
            last = current["sequence"]
            stopped = (
                abs(current["linear_x"]) < 0.005
                and abs(current["angular_z"]) < 0.005
            )
            stable = stable + 1 if stopped else 0
        if time.perf_counter() > deadline:
            raise RuntimeError("Arresto non confermato")
    return fresh_state()

def main():
    deadline = time.perf_counter() + 10
    while snapshot() is None:
        if time.perf_counter() > deadline:
            raise RuntimeError("Nessuna odometria")
        time.sleep(0.05)

    for _ in range(20):
        command(0.0)
        time.sleep(0.05)
    initial = stop_and_confirm()

    start = time.perf_counter()
    response = requests.post(
        url, data=raw, headers={"Content-Type": "audio/wav"},
        timeout=(5, 60),
    )
    received = time.perf_counter()
    response.raise_for_status()
    result = response.json()
    expected = ["avanti", "indietro", "sinistra", "destra", "stop"]
    if result.get("commands") != expected:
        raise RuntimeError(f"Sequenza inattesa: {result}")

    ready = fresh_state()
    if math.hypot(ready["x"] - initial["x"],
                  ready["y"] - initial["y"]) > 0.01:
        raise RuntimeError("Robot spostato durante il riconoscimento")

    actions = {
        "avanti": (0.1, 0.0),
        "indietro": (-0.1, 0.0),
        "sinistra": (0.0, 0.5),
        "destra": (0.0, -0.5),
        "stop": (0.0, 0.0),
    }
    records = []
    execution_start = time.perf_counter()

    for word in result["commands"]:
        before = fresh_state()
        action_start = time.perf_counter()
        linear, angular = actions[word]
        if word != "stop":
            while True:
                current = fresh_state()
                elapsed = current["sim_seconds"] - before["sim_seconds"]
                if elapsed < 0:
                    raise RuntimeError("Tempo simulato resettato")
                if elapsed >= 2.0:
                    break
                if time.perf_counter() - action_start > 15:
                    raise RuntimeError("Timeout movimento")
                command(linear, angular)
                time.sleep(0.02)

        final = stop_and_confirm()
        dx = final["x"] - before["x"]
        dy = final["y"] - before["y"]
        forward = dx * math.cos(before["yaw"]) + dy * math.sin(before["yaw"])
        lateral = -dx * math.sin(before["yaw"]) + dy * math.cos(before["yaw"])
        yaw_change = math.atan2(
            math.sin(final["yaw"] - before["yaw"]),
            math.cos(final["yaw"] - before["yaw"]),
        )

        if word in ("avanti", "indietro"):
            target = 0.2 if word == "avanti" else -0.2
            passed = (
                abs(forward - target) < 0.03
                and abs(lateral) < 0.03
                and abs(yaw_change) < 0.1
            )
        elif word in ("sinistra", "destra"):
            target = 1.0 if word == "sinistra" else -1.0
            passed = (
                abs(yaw_change - target) < 0.1
                and math.hypot(dx, dy) < 0.03
            )
        else:
            passed = (
                math.hypot(dx, dy) < 0.01
                and abs(yaw_change) < 0.05
            )

        record = {
            "command": word,
            "initial": before,
            "final": final,
            "forward_displacement_m": forward,
            "lateral_displacement_m": lateral,
            "yaw_change_rad": yaw_change,
            "until_stop_confirmed_wall_s": time.perf_counter() - action_start,
            "functional_pass": passed,
        }
        records.append(record)
        print(f"{word}: functional_pass={passed}", flush=True)
        if not passed:
            break

    completed = time.perf_counter()
    report = {
        "mode": args.mode,
        "file": item["file"],
        "sha256": item["sha256"],
        "recognition": result,
        "initial": initial,
        "actions": records,
        "http_e2e_wall_s": received - start,
        "execution_until_stop_confirmed_wall_s": completed - execution_start,
        "total_request_to_completion_wall_s": completed - start,
        "functional_pass":
            len(records) == 5 and all(r["functional_pass"] for r in records),
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
    output = Path(__file__).parent / f"task_b_sequence_{args.mode}_{stamp}.json"
    with output.open("x") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    print("Salvato:", output)

try:
    main()
finally:
    for _ in range(10):
        command(0.0)
        time.sleep(0.05)
    node.unsubscribe("/model/robot/odometry")
