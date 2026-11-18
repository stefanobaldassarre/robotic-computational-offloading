import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests


# ============================================================
# Configurazione
# ============================================================

RASPBERRY_URL = "http://192.168.50.20:5200/process"

MAP_DIR = os.path.expanduser(
    "~/tesi_gazebo/task_c/maps"
)

OUTPUT_DIR = os.path.expanduser(
    "~/tesi_gazebo/results/task_c_lan/local"
)

LEVELS = [
    "L1",
    "L2",
    "L3",
    "L4",
    "L5",
]

WARMUP_SAMPLES = 10
VALID_SAMPLES = 100

REQUEST_TIMEOUT = 10.0


# ============================================================
# Risultati attesi
#
# Servono per verificare che ogni richiesta restituisca
# esattamente lo stesso problema A* validato.
# ============================================================

EXPECTED = {

    "L1": {
        "path_length": 61,
        "expanded_nodes": 450,
    },

    "L2": {
        "path_length": 91,
        "expanded_nodes": 1440,
    },

    "L3": {
        "path_length": 143,
        "expanded_nodes": 4259,
    },

    "L4": {
        "path_length": 223,
        "expanded_nodes": 10383,
    },

    "L5": {
        "path_length": 283,
        "expanded_nodes": 16148,
    },
}


# ============================================================
# Caricamento mappe
# ============================================================

def load_payload(level):

    filename = os.path.join(
        MAP_DIR,
        f"{level}.json"
    )

    if not os.path.isfile(filename):

        raise FileNotFoundError(
            f"Mappa non trovata: {filename}"
        )

    with open(
        filename,
        "r"
    ) as f:

        data = json.load(f)

    return {

        "level":
            level,

        "grid":
            data["grid"],

        "start":
            data["start"],

        "goal":
            data["goal"],
    }


# ============================================================
# Verifica risposta
# ============================================================

def validate_result(
    level,
    result
):

    expected = EXPECTED[
        level
    ]

    if (
        result["path_length"]
        !=
        expected["path_length"]
    ):

        raise RuntimeError(
            f"{level}: path_length errato. "
            f"Atteso "
            f"{expected['path_length']}, "
            f"ricevuto "
            f"{result['path_length']}"
        )

    if (
        result["expanded_nodes"]
        !=
        expected["expanded_nodes"]
    ):

        raise RuntimeError(
            f"{level}: expanded_nodes errato. "
            f"Atteso "
            f"{expected['expanded_nodes']}, "
            f"ricevuto "
            f"{result['expanded_nodes']}"
        )


# ============================================================
# Richiesta LOCAL
# ============================================================

def send_request(
    level,
    payload
):

    client_start = (
        time.perf_counter()
    )

    response = requests.post(
        RASPBERRY_URL,
        json=payload,
        timeout=REQUEST_TIMEOUT
    )

    client_end = (
        time.perf_counter()
    )

    response.raise_for_status()

    result = response.json()

    validate_result(
        level,
        result
    )

    client_e2e_time_ms = (
        client_end
        -
        client_start
    ) * 1000.0

    return (
        result,
        client_e2e_time_ms
    )


# ============================================================
# Main
# ============================================================

def main():

    # --------------------------------------------------------
    # Run ID
    # --------------------------------------------------------

    if len(sys.argv) != 2:

        print(
            "Uso:"
        )

        print(
            "python3 "
            "task_c_local_benchmark.py "
            "<run_id>"
        )

        sys.exit(1)

    run_id = sys.argv[1]


    # --------------------------------------------------------
    # Directory risultati
    # --------------------------------------------------------

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    output_file = os.path.join(
        OUTPUT_DIR,
        f"run_{run_id}.csv"
    )


    # --------------------------------------------------------
    # Protezione da sovrascrittura
    # --------------------------------------------------------

    if os.path.exists(
        output_file
    ):

        print(
            f"ERRORE: "
            f"{output_file} "
            f"esiste già."
        )

        print(
            "La run NON verrà "
            "sovrascritta."
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Caricamento mappe PRIMA delle misure
    # --------------------------------------------------------

    payloads = {}

    for level in LEVELS:

        payloads[level] = (
            load_payload(level)
        )


    # --------------------------------------------------------
    # Informazioni run
    # --------------------------------------------------------

    print()
    print(
        "Task C benchmark LOCAL"
    )
    print(
        "======================"
    )

    print(
        f"Run ID: {run_id}"
    )

    print(
        f"Raspberry: "
        f"{RASPBERRY_URL}"
    )

    print(
        f"Livelli: "
        f"{', '.join(LEVELS)}"
    )

    print(
        f"Warm-up per livello: "
        f"{WARMUP_SAMPLES}"
    )

    print(
        f"Campioni validi "
        f"per livello: "
        f"{VALID_SAMPLES}"
    )

    print(
        f"Campioni totali: "
        f"{VALID_SAMPLES * len(LEVELS)}"
    )

    print(
        f"Output: "
        f"{output_file}"
    )

    print()


    # ========================================================
    # CSV
    # ========================================================

    fieldnames = [

        "timestamp",
        "run_id",
        "sample_id",
        "level",
        "level_sample_id",

        "path_length",
        "expanded_nodes",

        "processing_time_ms",
        "service_time_ms",

        "client_e2e_time_ms",
        "client_overhead_ms",
    ]


    global_sample_id = 0


    with open(
        output_file,
        "w",
        newline=""
    ) as csvfile:

        writer = (
            csv.DictWriter(
                csvfile,
                fieldnames=fieldnames
            )
        )

        writer.writeheader()


        # ====================================================
        # L1 -> L5
        # ====================================================

        for level in LEVELS:

            payload = payloads[
                level
            ]

            print()
            print(
                f"===== {level} ====="
            )


            # =================================================
            # Warm-up
            # =================================================

            print(
                f"Warm-up: "
                f"{WARMUP_SAMPLES} "
                f"richieste..."
            )

            for i in range(
                1,
                WARMUP_SAMPLES + 1
            ):

                try:

                    result, _ = (
                        send_request(
                            level,
                            payload
                        )
                    )

                except Exception as exc:

                    print()
                    print(
                        f"ERRORE warm-up "
                        f"{level} "
                        f"#{i}: {exc}"
                    )

                    sys.exit(1)

            print(
                "Warm-up completato."
            )


            # =================================================
            # Campioni validi
            # =================================================

            print(
                f"Acquisizione "
                f"{VALID_SAMPLES} "
                f"campioni..."
            )

            for level_sample_id in range(
                1,
                VALID_SAMPLES + 1
            ):

                try:

                    (
                        result,
                        client_e2e_ms
                    ) = send_request(
                        level,
                        payload
                    )

                except Exception as exc:

                    print()
                    print(
                        f"ERRORE "
                        f"{level} "
                        f"campione "
                        f"{level_sample_id}: "
                        f"{exc}"
                    )

                    print(
                        "Run interrotta."
                    )

                    sys.exit(1)


                global_sample_id += 1


                # --------------------------------------------
                # Metriche server
                # --------------------------------------------

                processing_ms = float(
                    result[
                        "processing_time_ms"
                    ]
                )

                service_ms = float(
                    result[
                        "service_time_ms"
                    ]
                )


                # --------------------------------------------
                # Overhead client/server
                #
                # E2E Ubuntu -> Raspberry -> Ubuntu
                # meno il service Raspberry.
                # --------------------------------------------

                client_overhead_ms = (
                    client_e2e_ms
                    -
                    service_ms
                )


                # --------------------------------------------
                # Timestamp UTC
                # --------------------------------------------

                timestamp = (
                    datetime.now(
                        timezone.utc
                    )
                    .isoformat()
                )


                # --------------------------------------------
                # CSV
                # --------------------------------------------

                writer.writerow({

                    "timestamp":
                        timestamp,

                    "run_id":
                        run_id,

                    "sample_id":
                        global_sample_id,

                    "level":
                        level,

                    "level_sample_id":
                        level_sample_id,

                    "path_length":
                        result[
                            "path_length"
                        ],

                    "expanded_nodes":
                        result[
                            "expanded_nodes"
                        ],

                    "processing_time_ms":
                        processing_ms,

                    "service_time_ms":
                        service_ms,

                    "client_e2e_time_ms":
                        client_e2e_ms,

                    "client_overhead_ms":
                        client_overhead_ms,
                })


                # Scrittura immediata
                csvfile.flush()


                print(
                    f"{level} "
                    f"["
                    f"{level_sample_id:03d}/"
                    f"{VALID_SAMPLES}"
                    f"] | "
                    f"A*: "
                    f"{processing_ms:8.3f} ms | "
                    f"service: "
                    f"{service_ms:8.3f} ms | "
                    f"E2E: "
                    f"{client_e2e_ms:8.3f} ms"
                )


    # ========================================================
    # Fine
    # ========================================================

    print()
    print(
        "================================"
    )

    print(
        "RUN LOCAL COMPLETATA"
    )

    print(
        "================================"
    )

    print(
        f"Campioni registrati: "
        f"{global_sample_id}"
    )

    print(
        f"File: "
        f"{output_file}"
    )


if __name__ == "__main__":

    main()
