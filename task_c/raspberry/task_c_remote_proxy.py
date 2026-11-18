import gzip
import json
import time

import requests

from flask import Flask, request, jsonify


# ============================================================
# Configurazione
# ============================================================

HOST = "0.0.0.0"
PORT = 5202

MAC_URL = (
    "http://192.168.50.30:5201/process"
)

GZIP_LEVEL = 6


# ============================================================
# Flask
# ============================================================

app = Flask(__name__)


# ============================================================
# Endpoint
# ============================================================

@app.route("/process", methods=["POST"])
def process():

    # ========================================================
    # Input da Ubuntu
    #
    # Ubuntu -> Raspberry rimane JSON normale.
    #
    # La compressione riguarda esclusivamente il collegamento
    # di offloading Raspberry -> Mac.
    # ========================================================

    data = request.get_json(
        silent=True
    )

    if data is None:

        return jsonify({
            "error": "invalid JSON"
        }), 400


    # ========================================================
    # Serializzazione JSON
    # ========================================================

    serialization_start = (
        time.perf_counter()
    )

    try:

        raw_json = json.dumps(
            data,
            separators=(",", ":")
        ).encode("utf-8")

    except Exception as exc:

        return jsonify({
            "error": "JSON serialization error",
            "details": str(exc)
        }), 400


    serialization_end = (
        time.perf_counter()
    )


    # ========================================================
    # Compressione gzip
    # ========================================================

    compression_start = (
        time.perf_counter()
    )

    compressed_payload = gzip.compress(
        raw_json,
        compresslevel=GZIP_LEVEL
    )

    compression_end = (
        time.perf_counter()
    )


    # ========================================================
    # Misura offload
    #
    # Definizione:
    #
    # parte PRIMA di serializzazione/compressione.
    #
    # In questo modo offload_e2e_time_ms rappresenta il costo
    # completo necessario al Raspberry per delegare il task:
    #
    # JSON serialization
    # + gzip
    # + HTTP/network
    # + decompressione sul Mac
    # + JSON parsing sul Mac
    # + A*
    # + risposta
    # ========================================================

    offload_start = (
        serialization_start
    )

    try:

        response = requests.post(
            MAC_URL,

            data=compressed_payload,

            headers={
                "Content-Type":
                    "application/json",

                "Content-Encoding":
                    "gzip",
            },

            timeout=10
        )

        response.raise_for_status()

    except Exception as exc:

        return jsonify({
            "error":
                "remote node unavailable",

            "details":
                str(exc)
        }), 502


    offload_end = (
        time.perf_counter()
    )


    # ========================================================
    # Risposta del Mac
    # ========================================================

    try:

        remote_result = (
            response.json()
        )

    except Exception as exc:

        return jsonify({
            "error":
                "invalid remote response",

            "details":
                str(exc)
        }), 502


    # ========================================================
    # Tempi locali del proxy
    # ========================================================

    serialization_time_ms = (
        serialization_end
        -
        serialization_start
    ) * 1000.0


    compression_time_ms = (
        compression_end
        -
        compression_start
    ) * 1000.0


    # ========================================================
    # Tempi restituiti dal Mac
    # ========================================================

    remote_processing_time_ms = float(
        remote_result[
            "processing_time_ms"
        ]
    )

    remote_service_time_ms = float(
        remote_result[
            "service_time_ms"
        ]
    )


    # ========================================================
    # Offload E2E
    # ========================================================

    offload_e2e_time_ms = (
        offload_end
        -
        offload_start
    ) * 1000.0


    # ========================================================
    # Metriche derivate
    # ========================================================

    offload_nonprocessing_time_ms = (
        offload_e2e_time_ms
        -
        remote_processing_time_ms
    )


    offload_transport_overhead_ms = (
        offload_e2e_time_ms
        -
        serialization_time_ms
        -
        compression_time_ms
        -
        remote_service_time_ms
    )


    # ========================================================
    # Dimensioni payload
    # ========================================================

    raw_payload_bytes = len(
        raw_json
    )

    compressed_payload_bytes = len(
        compressed_payload
    )


    # ========================================================
    # Risposta verso Ubuntu
    # ========================================================

    return jsonify({

        "level":
            remote_result.get(
                "level"
            ),

        "path":
            remote_result.get(
                "path"
            ),

        "path_length":
            remote_result.get(
                "path_length"
            ),

        "expanded_nodes":
            remote_result.get(
                "expanded_nodes"
            ),


        # ----------------------------------------------------
        # Mac
        # ----------------------------------------------------

        "remote_processing_time_ms":
            remote_processing_time_ms,

        "remote_service_time_ms":
            remote_service_time_ms,


        # ----------------------------------------------------
        # Raspberry / encoding
        # ----------------------------------------------------

        "serialization_time_ms":
            serialization_time_ms,

        "compression_time_ms":
            compression_time_ms,


        # ----------------------------------------------------
        # Offloading
        # ----------------------------------------------------

        "offload_e2e_time_ms":
            offload_e2e_time_ms,

        "offload_nonprocessing_time_ms":
            offload_nonprocessing_time_ms,

        "offload_transport_overhead_ms":
            offload_transport_overhead_ms,


        # ----------------------------------------------------
        # Payload
        # ----------------------------------------------------

        "raw_payload_bytes":
            raw_payload_bytes,

        "compressed_payload_bytes":
            compressed_payload_bytes,

        "compression_ratio":
            (
                compressed_payload_bytes
                /
                raw_payload_bytes
            )
    })


# ============================================================
# Avvio
# ============================================================

if __name__ == "__main__":

    print()
    print("Task C proxy REMOTE")
    print("-------------------")
    print(f"Host: {HOST}")
    print(f"Porta: {PORT}")
    print(f"Mac: {MAC_URL}")
    print(f"Gzip level: {GZIP_LEVEL}")
    print()
    print(
        "Raspberry -> Mac: JSON + gzip"
    )

    app.run(
        host=HOST,
        port=PORT,
        threaded=False
    )
