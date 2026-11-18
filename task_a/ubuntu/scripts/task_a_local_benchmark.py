import sys
import time
import csv
import os
import threading
from datetime import datetime, timezone

import cv2
import numpy as np
import requests

from gz.transport13 import Node
from gz.msgs10.image_pb2 import Image as GzImage
from gz.msgs10.twist_pb2 import Twist


# ============================================================
# Configurazione benchmark
# ============================================================

IMAGE_TOPIC = "/robot/camera/image"
CMD_TOPIC = "/cmd_vel"

RASPBERRY_URL = "http://192.168.50.20:5000/process"

FORWARD_SPEED = 0.30
TURN_SPEED = 0.50

MIN_REQUEST_INTERVAL = 0.10
MAX_TURN_DURATION = 4.0

WARMUP_SAMPLES = 10
VALID_SAMPLES = 100


# ============================================================
# Numero run
# ============================================================

if len(sys.argv) != 2:
    print(
        "Uso: python3 task_a_local_benchmark.py NUMERO_RUN"
    )
    sys.exit(1)

try:
    RUN_ID = int(sys.argv[1])
except ValueError:
    print("NUMERO_RUN deve essere un intero.")
    sys.exit(1)

if RUN_ID < 1:
    print("NUMERO_RUN deve essere >= 1.")
    sys.exit(1)


# ============================================================
# CSV
# ============================================================

RESULT_DIR = os.path.expanduser(
    "~/tesi_gazebo/results/task_a_lan/local"
)

os.makedirs(
    RESULT_DIR,
    exist_ok=True
)

CSV_FILE = os.path.join(
    RESULT_DIR,
    f"run_{RUN_ID:02d}.csv"
)

if os.path.exists(CSV_FILE):
    print(f"ERRORE: {CSV_FILE} esiste già.")
    print("La run NON verrà sovrascritta.")
    sys.exit(1)


CSV_HEADER = [
    "timestamp",
    "run_id",
    "sample_id",
    "mode",
    "action",
    "red_ratio",
    "processing_time_ms",
    "service_time_ms",
    "e2e_time_ms",
    "simulation_link_overhead_ms"
]


# ============================================================
# Gazebo
# ============================================================

node = Node()

cmd_pub = node.advertise(
    CMD_TOPIC,
    Twist
)


# ============================================================
# Stato
# ============================================================

state = "FORWARD"

turn_start_time = None
last_request_time = 0.0

received_samples = 0
valid_samples = 0

benchmark_complete = False

callback_lock = threading.Lock()


# ============================================================
# Comandi robot
# ============================================================

def send_command(linear_x, angular_z):

    msg = Twist()

    msg.linear.x = linear_x
    msg.angular.z = angular_z

    cmd_pub.publish(msg)


def command_forward():
    send_command(FORWARD_SPEED, 0.0)


def command_turn_left():
    send_command(0.0, TURN_SPEED)


def command_stop():
    send_command(0.0, 0.0)


# ============================================================
# CSV
# ============================================================

def initialize_csv():

    with open(
        CSV_FILE,
        "w",
        newline=""
    ) as csvfile:

        writer = csv.writer(csvfile)
        writer.writerow(CSV_HEADER)


def save_measurement(
    sample_id,
    action,
    red_ratio,
    processing_time_ms,
    service_time_ms,
    e2e_time_ms,
    simulation_link_overhead_ms
):

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    with open(
        CSV_FILE,
        "a",
        newline=""
    ) as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow([
            timestamp,
            RUN_ID,
            sample_id,
            "LOCAL",
            action,
            f"{red_ratio:.6f}",
            f"{processing_time_ms:.6f}",
            f"{service_time_ms:.6f}",
            f"{e2e_time_ms:.6f}",
            f"{simulation_link_overhead_ms:.6f}"
        ])


# ============================================================
# Raspberry
# ============================================================

def send_frame_to_raspberry(frame_rgb):

    frame_bgr = cv2.cvtColor(
        frame_rgb,
        cv2.COLOR_RGB2BGR
    )

    ok, encoded = cv2.imencode(
        ".jpg",
        frame_bgr
    )

    if not ok:
        raise RuntimeError(
            "Errore codifica JPEG"
        )

    files = {
        "image": (
            "frame.jpg",
            encoded.tobytes(),
            "image/jpeg"
        )
    }

    request_start = time.perf_counter()

    response = requests.post(
        RASPBERRY_URL,
        files=files,
        timeout=2
    )

    request_end = time.perf_counter()

    response.raise_for_status()

    result = response.json()

    e2e_time_ms = (
        request_end - request_start
    ) * 1000.0

    return result, e2e_time_ms


# ============================================================
# Callback camera
# ============================================================

def process_frame(msg: GzImage):

    global state
    global turn_start_time
    global last_request_time
    global received_samples
    global valid_samples
    global benchmark_complete

    # Evita callback concorrenti durante il benchmark
    if not callback_lock.acquire(blocking=False):
        return

    try:

        if benchmark_complete:
            return

        now = time.monotonic()

        if (
            now - last_request_time
            <
            MIN_REQUEST_INTERVAL
        ):
            return

        last_request_time = now

        # ----------------------------------------------------
        # Frame Gazebo
        # ----------------------------------------------------

        width = msg.width
        height = msg.height

        data = np.frombuffer(
            msg.data,
            dtype=np.uint8
        )

        expected = width * height * 3

        if data.size != expected:
            print("Frame non valido")
            return

        frame_rgb = data.reshape(
            (height, width, 3)
        )

        # ----------------------------------------------------
        # Elaborazione LOCAL
        # ----------------------------------------------------

        try:

            result, e2e_time_ms = \
                send_frame_to_raspberry(
                    frame_rgb
                )

        except Exception as exc:

            print(
                f"Errore Raspberry: {exc}"
            )

            command_stop()
            return

        received_samples += 1

        action = result.get("action")

        red_ratio = result.get(
            "red_ratio",
            0.0
        )

        processing_time_ms = result.get(
            "processing_time_ms",
            0.0
        )

        service_time_ms = result.get(
            "service_time_ms",
            0.0
        )

        simulation_link_overhead_ms = (
            e2e_time_ms
            -
            service_time_ms
        )

        # ----------------------------------------------------
        # Warm-up
        # ----------------------------------------------------

        if received_samples <= WARMUP_SAMPLES:

            print(
                f"WARM-UP "
                f"{received_samples}/{WARMUP_SAMPLES} | "
                f"processing: "
                f"{processing_time_ms:.3f} ms"
            )

        else:

            valid_samples += 1

            save_measurement(
                valid_samples,
                action,
                red_ratio,
                processing_time_ms,
                service_time_ms,
                e2e_time_ms,
                simulation_link_overhead_ms
            )

            print(
                f"RUN {RUN_ID:02d} | "
                f"{valid_samples}/{VALID_SAMPLES} | "
                f"processing: "
                f"{processing_time_ms:.3f} ms | "
                f"service: "
                f"{service_time_ms:.3f} ms | "
                f"e2e: "
                f"{e2e_time_ms:.3f} ms"
            )

        # ----------------------------------------------------
        # Controllo robot
        # ----------------------------------------------------

        if state == "FORWARD":

            if action == "TURN_LEFT":

                state = "TURNING"
                turn_start_time = now
                command_turn_left()

            else:

                command_forward()

        elif state == "TURNING":

            elapsed = (
                now - turn_start_time
            )

            if action == "FORWARD":

                state = "FORWARD"
                turn_start_time = None
                command_forward()

            elif elapsed >= MAX_TURN_DURATION:

                state = "FORWARD"
                turn_start_time = None
                command_forward()

            else:

                command_turn_left()

        # ----------------------------------------------------
        # Fine benchmark
        # ----------------------------------------------------

        if valid_samples >= VALID_SAMPLES:

            benchmark_complete = True
            command_stop()

    finally:

        callback_lock.release()


# ============================================================
# Avvio
# ============================================================

initialize_csv()

if not node.subscribe(
    GzImage,
    IMAGE_TOPIC,
    process_frame
):

    raise RuntimeError(
        "Errore sottoscrizione camera"
    )


print("")
print("========================================")
print("TASK A - BENCHMARK LOCAL")
print("========================================")
print(f"Run: {RUN_ID:02d}")
print(f"Warm-up: {WARMUP_SAMPLES} campioni")
print(f"Campioni validi: {VALID_SAMPLES}")
print(f"Raspberry: {RASPBERRY_URL}")
print(f"CSV: {CSV_FILE}")
print("========================================")
print("")


# ============================================================
# Main loop
# ============================================================

try:

    while not benchmark_complete:
        time.sleep(0.1)

except KeyboardInterrupt:

    print("\nBenchmark interrotto manualmente.")
    command_stop()

    try:
        node.unsubscribe(IMAGE_TOPIC)
    except Exception:
        pass

    # Una run incompleta non deve sembrare valida.
    print(
        f"Campioni validi raccolti: "
        f"{valid_samples}/{VALID_SAMPLES}"
    )

    print(
        f"File parziale: {CSV_FILE}"
    )

    sys.exit(1)


# ============================================================
# Chiusura normale
# ============================================================

command_stop()

try:
    node.unsubscribe(IMAGE_TOPIC)
except Exception:
    pass

time.sleep(0.5)

print("")
print("========================================")
print("BENCHMARK LOCAL COMPLETATO")
print("========================================")
print(f"Warm-up scartati: {WARMUP_SAMPLES}")
print(f"Campioni salvati: {valid_samples}")
print(f"CSV: {CSV_FILE}")
print("Robot fermato.")
print("========================================")
