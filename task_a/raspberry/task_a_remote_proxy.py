import time
import requests

from flask import Flask, request, jsonify


# ============================================================
# Configurazione
# ============================================================

HOST = "0.0.0.0"
PORT = 5002

MAC_URL = "http://192.168.50.30:5001/process"


# ============================================================
# Flask
# ============================================================

app = Flask(__name__)


# ============================================================
# Endpoint REMOTE
# ============================================================

@app.route("/process", methods=["POST"])
def process():

    # --------------------------------------------------------
    # Ricezione frame da Ubuntu
    # --------------------------------------------------------

    file = request.files.get("image")

    if file is None:
        return jsonify({
            "error": "image missing"
        }), 400

    raw_data = file.read()

    # --------------------------------------------------------
    # Preparazione richiesta verso Mac M3
    # --------------------------------------------------------

    files = {
        "image": (
            "frame.jpg",
            raw_data,
            "image/jpeg"
        )
    }

    # --------------------------------------------------------
    # Misura del vero E2E dell'offloading
    # Raspberry -> Mac -> Raspberry
    # --------------------------------------------------------

    offload_start = time.perf_counter()

    try:

        response = requests.post(
            MAC_URL,
            files=files,
            timeout=2
        )

        response.raise_for_status()

    except Exception as exc:

        return jsonify({
            "error": "remote node unavailable",
            "details": str(exc)
        }), 502

    offload_end = time.perf_counter()

    # --------------------------------------------------------
    # Risultato restituito dal Mac
    # --------------------------------------------------------

    remote_result = response.json()

    action = remote_result.get(
        "action"
    )

    red_ratio = remote_result.get(
        "red_ratio",
        0.0
    )

    remote_processing_time_ms = remote_result.get(
        "processing_time_ms",
        0.0
    )

    remote_service_time_ms = remote_result.get(
        "service_time_ms",
        0.0
    )

    # --------------------------------------------------------
    # Metriche offloading
    # --------------------------------------------------------

    offload_e2e_time_ms = (
        offload_end - offload_start
    ) * 1000.0

    # Costo esterno al servizio sul Mac:
    # rete + HTTP + gestione richiesta/risposta
    offload_transport_overhead_ms = (
        offload_e2e_time_ms
        -
        remote_service_time_ms
    )

    # Tutto ciò che non è puro process_image()
    offload_nonprocessing_time_ms = (
        offload_e2e_time_ms
        -
        remote_processing_time_ms
    )

    # --------------------------------------------------------
    # Risposta verso Ubuntu
    # --------------------------------------------------------

    result = {
        "action": action,
        "red_ratio": red_ratio,

        "remote_processing_time_ms":
            remote_processing_time_ms,

        "remote_service_time_ms":
            remote_service_time_ms,

        "offload_e2e_time_ms":
            offload_e2e_time_ms,

        "offload_transport_overhead_ms":
            offload_transport_overhead_ms,

        "offload_nonprocessing_time_ms":
            offload_nonprocessing_time_ms
    }

    return jsonify(result)


# ============================================================
# Avvio
# ============================================================

if __name__ == "__main__":

    print("Task A proxy REMOTE")
    print(f"Host: {HOST}")
    print(f"Porta: {PORT}")
    print(f"Nodo remoto: {MAC_URL}")

    print("Metriche attive:")
    print("- remote_processing_time_ms")
    print("- remote_service_time_ms")
    print("- offload_e2e_time_ms")
    print("- offload_transport_overhead_ms")
    print("- offload_nonprocessing_time_ms")

    app.run(
        host=HOST,
        port=PORT,
        threaded=True
    )
