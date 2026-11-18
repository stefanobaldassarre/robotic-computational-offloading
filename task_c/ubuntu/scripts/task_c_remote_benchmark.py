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

PROXY_URL = (
    "http://192.168.50.20:5202/process"
)

MAP_DIR = os.path.expanduser(
    "~/tesi_gazebo/task_c/maps"
)

OUTPUT_DIR = os.path.expanduser(
    "~/tesi_gazebo/results/task_c_lan/remote"
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
# Caricamento mappa
# ============================================================

def load_payload(level):

    filename = os.path.join(
        MAP_DIR,
        f"{level}.json"
    )

    if not os.path.isfile(
        filename
    ):

        raise FileNotFoundError(
            f"Mappa non trovata: "
            f"{filename}"
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
# Validazione
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
            f"{level}: "
            f"path_length errato. "
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
            f"{level}: "
            f"expanded_nodes errato. "
            f"Atteso "
            f"{expected['expanded_nodes']}, "
            f"ricevuto "
            f"{result['expanded_nodes']}"
        )


# ============================================================
# Richiesta REMOTE
# ============================================================

def send_request(
    level,
    payload
):

    # --------------------------------------------------------
    # E2E completo visto da Ubuntu
    #
    # Ubuntu
    #  -> Raspberry proxy
    #  -> gzip
    #  -> Mac
    #  -> A*
    #  -> Raspberry
    #  -> Ubuntu
    # --------------------------------------------------------

    total_start = (
        time.perf_counter()
    )

    response = requests.post(
        PROXY_URL,
        json=payload,
        timeout=REQUEST_TIMEOUT
    )

    total_end = (
        time.perf_counter()
    )

    response.raise_for_status()

    result = response.json()

    validate_result(
        level,
        result
    )


    total_e2e_time_ms = (
        total_end
        -
        total_start
    ) * 1000.0


    return (
        result,
        total_e2e_time_ms
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
            "task_c_remote_benchmark.py "
            "<run_id>"
        )

        sys.exit(1)

    run_id = sys.argv[1]


    # --------------------------------------------------------
    # Output
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
    # Protezione sovrascrittura
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
    # Mappe
    # --------------------------------------------------------

    payloads = {}

    for level in LEVELS:

        payloads[level] = (
            load_payload(
                level
            )
        )


    # --------------------------------------------------------
    # Informazioni
    # --------------------------------------------------------

    print()
    print(
        "Task C benchmark REMOTE"
    )

    print(
        "======================="
    )

    print(
        f"Run ID: {run_id}"
    )

    print(
        f"Proxy Raspberry: "
        f"{PROXY_URL}"
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

        "remote_processing_time_ms",
        "remote_service_time_ms",

        "serialization_time_ms",
        "compression_time_ms",

        "offload_e2e_time_ms",
        "offload_nonprocessing_time_ms",
        "offload_transport_overhead_ms",

        "raw_payload_bytes",
        "compressed_payload_bytes",
        "compression_ratio",

        "total_e2e_time_ms",
        "ubuntu_raspberry_overhead_ms",
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
                        f"#{i}: "
                        f"{exc}"
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
                        total_e2e_ms
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


                # =================================================
                # Estrazione metriche
                # =================================================

                remote_processing_ms = float(
                    result[
                        "remote_processing_time_ms"
                    ]
                )

                remote_service_ms = float(
                    result[
                        "remote_service_time_ms"
                    ]
                )

                serialization_ms = float(
                    result[
                        "serialization_time_ms"
                    ]
                )

                compression_ms = float(
                    result[
                        "compression_time_ms"
                    ]
                )

                offload_e2e_ms = float(
                    result[
                        "offload_e2e_time_ms"
                    ]
                )

                nonprocessing_ms = float(
                    result[
                        "offload_nonprocessing_time_ms"
                    ]
                )

                transport_ms = float(
                    result[
                        "offload_transport_overhead_ms"
                    ]
                )

                raw_payload_bytes = int(
                    result[
                        "raw_payload_bytes"
                    ]
                )

                compressed_payload_bytes = int(
                    result[
                        "compressed_payload_bytes"
                    ]
                )

                compression_ratio = float(
                    result[
                        "compression_ratio"
                    ]
                )


                # =================================================
                # Overhead Ubuntu <-> Raspberry
                #
                # total_e2e comprende tutto.
                #
                # offload_e2e parte dal Raspberry e comprende:
                # serializzazione + gzip + Mac + ritorno.
                #
                # La differenza rappresenta principalmente
                # il tratto Ubuntu <-> Raspberry e la gestione
                # aggiuntiva del proxy.
                # =================================================

                ubuntu_raspberry_overhead_ms = (
                    total_e2e_ms
                    -
                    offload_e2e_ms
                )


                # =================================================
                # Timestamp
                # =================================================

                timestamp = (
                    datetime.now(
                        timezone.utc
                    )
                    .isoformat()
                )


                # =================================================
                # Scrittura CSV
                # =================================================

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

                    "remote_processing_time_ms":
                        remote_processing_ms,

                    "remote_service_time_ms":
                        remote_service_ms,

                    "serialization_time_ms":
                        serialization_ms,

                    "compression_time_ms":
                        compression_ms,

                    "offload_e2e_time_ms":
                        offload_e2e_ms,

                    "offload_nonprocessing_time_ms":
                        nonprocessing_ms,

                    "offload_transport_overhead_ms":
                        transport_ms,

                    "raw_payload_bytes":
                        raw_payload_bytes,

                    "compressed_payload_bytes":
                        compressed_payload_bytes,

                    "compression_ratio":
                        compression_ratio,

                    "total_e2e_time_ms":
                        total_e2e_ms,

                    "ubuntu_raspberry_overhead_ms":
                        ubuntu_raspberry_overhead_ms,
                })


                csvfile.flush()


                # =================================================
                # Console
                # =================================================

                print(
                    f"{level} "
                    f"["
                    f"{level_sample_id:03d}/"
                    f"{VALID_SAMPLES}"
                    f"] | "
                    f"A*: "
                    f"{remote_processing_ms:8.3f} ms | "
                    f"offload: "
                    f"{offload_e2e_ms:8.3f} ms | "
                    f"total: "
                    f"{total_e2e_ms:8.3f} ms"
                )


    # ========================================================
    # Fine
    # ========================================================

    print()
    print(
        "================================"
    )

    print(
        "RUN REMOTE COMPLETATA"
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
