import time

import cv2
import numpy as np

from flask import Flask, request, jsonify

from image_processing import process_image


# ============================================================
# Configurazione
# ============================================================

HOST = "0.0.0.0"
PORT = 5000


# ============================================================
# Flask
# ============================================================

app = Flask(__name__)

last_action = None


# ============================================================
# Endpoint Task A
# ============================================================

@app.route("/process", methods=["POST"])
def process():
    global last_action

    # --------------------------------------------------------
    # Ricezione immagine
    # --------------------------------------------------------

    file = request.files.get("image")

    if file is None:
        return jsonify({
            "error": "image missing"
        }), 400

    raw_data = file.read()

    # --------------------------------------------------------
    # Inizio misura servizio lato Raspberry
    # --------------------------------------------------------

    service_start = time.perf_counter()

    data = np.frombuffer(
        raw_data,
        dtype=np.uint8
    )

    # --------------------------------------------------------
    # Decodifica JPEG
    # --------------------------------------------------------

    frame_bgr = cv2.imdecode(
        data,
        cv2.IMREAD_COLOR
    )

    if frame_bgr is None:
        return jsonify({
            "error": "invalid image"
        }), 400

    frame_rgb = cv2.cvtColor(
        frame_bgr,
        cv2.COLOR_BGR2RGB
    )

    # --------------------------------------------------------
    # Misura del solo algoritmo OpenCV
    # --------------------------------------------------------

    processing_start = time.perf_counter()

    result = process_image(
        frame_rgb,
        last_action
    )

    processing_end = time.perf_counter()

    processing_time_ms = (
        processing_end - processing_start
    ) * 1000.0

    # --------------------------------------------------------
    # Aggiornamento stato
    # --------------------------------------------------------

    last_action = result["action"]

    # --------------------------------------------------------
    # Fine misura servizio lato Raspberry
    # --------------------------------------------------------

    service_end = time.perf_counter()

    service_time_ms = (
        service_end - service_start
    ) * 1000.0

    # --------------------------------------------------------
    # Risposta JSON
    # --------------------------------------------------------

    response = {
        "action": result["action"],
        "red_ratio": result["red_ratio"],
        "processing_time_ms": processing_time_ms,
        "service_time_ms": service_time_ms
    }

    return jsonify(response)


# ============================================================
# Avvio server
# ============================================================

if __name__ == "__main__":

    print("Task A server LOCAL")
    print(f"Host: {HOST}")
    print(f"Porta: {PORT}")
    print("Nodo di elaborazione: Raspberry Pi")
    print("Misure attive:")
    print("- processing_time_ms: solo process_image()")
    print("- service_time_ms: decodifica + elaborazione lato Raspberry")

    app.run(
        host=HOST,
        port=PORT,
        threaded=True
    )
