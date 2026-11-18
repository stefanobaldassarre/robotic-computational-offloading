import gzip
import json
import time

from flask import Flask, request, jsonify

from task_c_astar import astar


# ============================================================
# Configurazione
# ============================================================

HOST = "0.0.0.0"
PORT = 5200


# ============================================================
# Flask
# ============================================================

app = Flask(__name__)


# ============================================================
# Endpoint Task C
# ============================================================

@app.route("/process", methods=["POST"])
def process():

    # --------------------------------------------------------
    # Inizio servizio
    #
    # Comprende:
    # - ricezione/decodifica payload
    # - eventuale decompressione gzip
    # - deserializzazione JSON
    # - A*
    # - preparazione risultato
    #
    # Esclude jsonify e invio della risposta. La lettura del corpo
    # puo includere attesa dei dati della richiesta.
    # --------------------------------------------------------

    service_start = time.perf_counter()


    # ========================================================
    # Lettura e decodifica input
    # ========================================================

    content_encoding = (
        request.headers
        .get("Content-Encoding", "")
        .lower()
        .strip()
    )

    try:

        if content_encoding == "gzip":

            # ------------------------------------------------
            # REMOTE:
            # il proxy invia bytes contenenti JSON gzip
            # ------------------------------------------------

            compressed_data = request.get_data()

            raw_json = gzip.decompress(
                compressed_data
            )

            data = json.loads(
                raw_json.decode("utf-8")
            )

        else:

            # ------------------------------------------------
            # LOCAL:
            # normale richiesta application/json
            # ------------------------------------------------

            data = request.get_json(
                silent=True
            )

    except Exception as exc:

        return jsonify({
            "error": "invalid request payload",
            "details": str(exc)
        }), 400


    if data is None:

        return jsonify({
            "error": "invalid JSON"
        }), 400


    # ========================================================
    # Input
    # ========================================================

    grid = data.get("grid")
    start = data.get("start")
    goal = data.get("goal")
    level = data.get("level")


    if (
        grid is None
        or start is None
        or goal is None
    ):

        return jsonify({
            "error":
                "grid, start and goal are required"
        }), 400


    # ========================================================
    # Processing
    #
    # ATTENZIONE:
    # processing_time_ms misura ESCLUSIVAMENTE A*
    # ========================================================

    processing_start = time.perf_counter()

    try:

        result = astar(
            grid,
            start,
            goal
        )

    except Exception as exc:

        return jsonify({
            "error": "A* error",
            "details": str(exc)
        }), 400


    processing_end = time.perf_counter()

    processing_time_ms = (
        processing_end
        -
        processing_start
    ) * 1000.0


    # ========================================================
    # Preparazione risposta
    # ========================================================

    response_data = {

        "level":
            level,

        "path":
            result["path"],

        "path_length":
            result["path_length"],

        "expanded_nodes":
            result["expanded_nodes"],

        "processing_time_ms":
            processing_time_ms,
    }


    # ========================================================
    # Fine servizio
    # ========================================================

    service_end = time.perf_counter()

    service_time_ms = (
        service_end
        -
        service_start
    ) * 1000.0

    response_data[
        "service_time_ms"
    ] = service_time_ms


    return jsonify(
        response_data
    )


# ============================================================
# Avvio
# ============================================================

if __name__ == "__main__":

    print()
    print("Task C server")
    print("-------------------")
    print(f"Host: {HOST}")
    print(f"Porta: {PORT}")
    print()
    print("Input supportati:")
    print("- application/json")
    print("- application/json + gzip")
    print()
    print(
        "processing_time_ms = solo A*"
    )
    print(
        "service_time_ms = "
        "decode + eventuale gzip + A* + risultato"
    )

    app.run(
        host=HOST,
        port=PORT,
        threaded=False
    )
