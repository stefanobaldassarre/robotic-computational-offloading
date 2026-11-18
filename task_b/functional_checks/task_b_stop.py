import argparse
import hashlib
import json
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
item = next(
    x for x in json.loads((dataset / "manifest.json").read_text())
    if x["file"] == "S1_05.wav"
)
raw = (dataset / "wav" / item["file"]).read_bytes()
if hashlib.sha256(raw).hexdigest() != item["sha256"]:
    raise RuntimeError("Checksum audio errato")

port = 5300 if args.mode == "local" else 5302
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

def fresh():
    with lock:
        current = None if state is None else dict(state)
    if current is None or time.perf_counter() - current["received_wall"] > 1:
        raise RuntimeError("Odometria assente o non aggiornata")
    return current

publisher = node.advertise("/cmd_vel", Twist)

def command(angular):
    msg = Twist()
    msg.linear.x = 0.0
    msg.angular.z = angular
    publisher.publish(msg)

if not node.subscribe(Odometry, "/model/robot/odometry", on_odom):
    raise RuntimeError("Sottoscrizione fallita")

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
        command(0.0)
        time.sleep(0.05)

    # Rotazione preliminare: comando mantenuto dal DiffDrive durante HTTP.
    for _ in range(20):
        command(0.2)
        time.sleep(0.02)

    before_request = fresh()
    if before_request["angular_z"] < 0.1:
        raise RuntimeError("Rotazione preliminare non confermata")

    start = time.perf_counter()
    response = requests.post(
        f"http://192.168.50.20:{port}/process",
        data=raw,
        headers={"Content-Type": "audio/wav"},
        timeout=(5, 10),
    )
    received = time.perf_counter()
    response.raise_for_status()
    result = response.json()
    if result.get("commands") != ["stop"]:
        raise RuntimeError(f"Comando inatteso: {result}")

    before_stop = fresh()
    moving_before_stop = before_stop["angular_z"] > 0.1
    stop_sent = time.perf_counter()
    command(0.0)

    stable = 0
    last_sequence = before_stop["sequence"]
    deadline = time.perf_counter() + 5

    while stable < 5:
        command(0.0)
        time.sleep(0.02)
        current = fresh()
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
    final = fresh()
    report = {
        "mode": args.mode,
        "file": item["file"],
        "sha256": item["sha256"],
        "recognition": result,
        "before_request": before_request,
        "before_stop": before_stop,
        "final": final,
        "http_e2e_wall_s": received - start,
        "response_to_stop_command_wall_s": stop_sent - received,
        "stop_command_to_confirmation_wall_s": completed - stop_sent,
        "stop_command_to_confirmation_sim_s":
            final["sim_seconds"] - before_stop["sim_seconds"],
        "total_request_to_stop_confirmed_wall_s": completed - start,
        "moving_before_stop": moving_before_stop,
        "stop_confirmed": True,
        "functional_pass": moving_before_stop,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
    output = Path(__file__).parent / f"task_b_stop_{args.mode}_{stamp}.json"
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
