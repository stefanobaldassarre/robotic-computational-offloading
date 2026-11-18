import json
import math
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from gz.transport13 import Node
from gz.msgs10.twist_pb2 import Twist
from gz.msgs10.odometry_pb2 import Odometry

node = Node()
lock = threading.Lock()
state = None
sequence = 0

def on_odom(msg):
    global state, sequence
    stamp = msg.header.stamp
    with lock:
        sequence += 1
        state = {
            "sequence": sequence,
            "received_wall": time.perf_counter(),
            "sim_seconds": stamp.sec + stamp.nsec * 1e-9,
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
            raise RuntimeError("Nessuna odometria entro 10 secondi")
        time.sleep(0.05)

    # Stabilizzazione con comando nullo e attesa della discovery.
    for _ in range(20):
        command(0.0)
        time.sleep(0.05)

    initial = fresh_state()
    if abs(initial["linear_x"]) > 0.01 or abs(initial["angular_z"]) > 0.01:
        raise RuntimeError("Il robot non risulta fermo all'inizio")

    wall_start = time.perf_counter()
    print("Avanzamento: 0.1 m/s per 2 s simulati", flush=True)

    while True:
        current = fresh_state()
        elapsed_sim = current["sim_seconds"] - initial["sim_seconds"]
        if elapsed_sim < 0:
            raise RuntimeError("Tempo simulato resettato durante la prova")
        if elapsed_sim >= 2.0:
            break
        if time.perf_counter() - wall_start > 15:
            raise RuntimeError("Timeout movimento: simulazione lenta o ferma")
        command(0.1)
        time.sleep(0.02)

    wall_stop_command = time.perf_counter()
    stop_reference = fresh_state()
    stable_samples = 0
    last_sequence = stop_reference["sequence"]
    deadline = time.perf_counter() + 5

    while stable_samples < 5:
        command(0.0)
        time.sleep(0.02)
        current = fresh_state()
        if current["sequence"] != last_sequence:
            last_sequence = current["sequence"]
            stopped = (
                abs(current["linear_x"]) < 0.005
                and abs(current["angular_z"]) < 0.005
            )
            stable_samples = stable_samples + 1 if stopped else 0
        if time.perf_counter() > deadline:
            raise RuntimeError("Arresto non confermato entro 5 secondi")

    wall_end = time.perf_counter()
    final = fresh_state()
    displacement = math.hypot(final["x"] - initial["x"],
                              final["y"] - initial["y"])
    result = {
        "status": "completed",
        "initial": initial,
        "final": final,
        "commanded_speed_m_s": 0.1,
        "requested_sim_duration_s": 2.0,
        "command_interval_wall_s": wall_stop_command - wall_start,
        "command_interval_sim_s":
            stop_reference["sim_seconds"] - initial["sim_seconds"],
        "until_stop_confirmed_wall_s": wall_end - wall_start,
        "until_stop_confirmed_sim_s":
            final["sim_seconds"] - initial["sim_seconds"],
        "displacement_m": displacement,
        "movement_observed": displacement > 0.05,
        "stop_confirmed": True,
    }
    filename = datetime.now(timezone.utc).strftime("motion_%Y%m%dT%H%M%S_%f.json")
    output = Path(__file__).parent / filename
    with output.open("x") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
    print("Salvato:", output)

try:
    main()
finally:
    for _ in range(10):
        command(0.0)
        time.sleep(0.05)
    node.unsubscribe("/model/robot/odometry")
