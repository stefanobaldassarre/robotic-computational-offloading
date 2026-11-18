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
item = next(x for x in items if x["file"] == "S1_02.wav")
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

def command(speed):
    msg = Twist()
    msg.linear.x = speed
    msg.angular.z = 0.0
    publisher.publish(msg)

if not node.subscribe(Odometry, "/model/robot/odometry", on_odom):
    raise RuntimeError("Sottoscrizione odometria fallita")

def main():
    deadline = time.perf_counter() + 10
    while snapshot() is None:
        if time.perf_counter() > deadline:
            raise RuntimeError("Nessuna odometria")
        time.sleep(0.05)

    for _ in range(20):
        command(0.0)
        time.sleep(0.05)

    before_request = fresh_state()
    if (
        abs(before_request["linear_x"]) > 0.01
        or abs(before_request["angular_z"]) > 0.01
    ):
        raise RuntimeError("Robot non fermo prima della richiesta")

    request_start = time.perf_counter()
    response = requests.post(
        url,
        data=raw,
        headers={"Content-Type": "audio/wav"},
        timeout=(5, 60),
    )
    response_received = time.perf_counter()
    response.raise_for_status()
    result = response.json()

    if result.get("commands") != ["indietro"]:
        raise RuntimeError(f"Comando inatteso: {result}")

    initial = fresh_state()
    if math.hypot(
        initial["x"] - before_request["x"],
        initial["y"] - before_request["y"],
    ) > 0.01:
        raise RuntimeError("Robot spostato durante il riconoscimento")

    motion_start = time.perf_counter()
    print("Riconosciuto indietro; avvio movimento", flush=True)

    while True:
        current = fresh_state()
        elapsed = current["sim_seconds"] - initial["sim_seconds"]
        if elapsed < 0:
            raise RuntimeError("Tempo simulato resettato")
        if elapsed >= 2.0:
            break
        if time.perf_counter() - motion_start > 15:
            raise RuntimeError("Timeout movimento")
        command(-0.1)
        time.sleep(0.02)

    stop_sent = time.perf_counter()
    stop_reference = fresh_state()
    stable = 0
    last_sequence = stop_reference["sequence"]
    deadline = time.perf_counter() + 5

    while stable < 5:
        command(0.0)
        time.sleep(0.02)
        current = fresh_state()
        if current["sequence"] != last_sequence:
            last_sequence = current["sequence"]
            stopped = (
                abs(current["linear_x"]) < 0.005
                and abs(current["angular_z"]) < 0.005
            )
            stable = stable + 1 if stopped else 0
        if time.perf_counter() > deadline:
            raise RuntimeError("Arresto non confermato")

    completed = time.perf_counter()
    final = fresh_state()
    dx = final["x"] - initial["x"]
    dy = final["y"] - initial["y"]

    report = {
        "mode": args.mode,
        "file": item["file"],
        "sha256": item["sha256"],
        "recognition": result,
        "before_request": before_request,
        "initial_motion": initial,
        "final": final,
        "http_e2e_wall_s": response_received - request_start,
        "response_to_motion_wall_s": motion_start - response_received,
        "command_interval_wall_s": stop_sent - motion_start,
        "command_interval_sim_s":
            stop_reference["sim_seconds"] - initial["sim_seconds"],
        "motion_until_stop_confirmed_wall_s": completed - motion_start,
        "motion_until_stop_confirmed_sim_s":
            final["sim_seconds"] - initial["sim_seconds"],
        "total_until_stop_confirmed_wall_s": completed - request_start,
        "total_until_stop_confirmed_sim_s":
            final["sim_seconds"] - before_request["sim_seconds"],
        "dx_m": dx,
        "dy_m": dy,
        "displacement_m": math.hypot(dx, dy),
        "movement_observed": math.hypot(dx, dy) > 0.05,
        "stop_confirmed": True,
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
    output = Path(__file__).parent / f"task_b_backward_{args.mode}_{stamp}.json"
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
