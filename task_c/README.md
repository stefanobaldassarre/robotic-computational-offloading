# Task C — pianificazione A* su griglie

[Torna al README generale](../README.md)

Confronto tra A* sul Raspberry Pi (LOCAL) e sul Mac M3 tramite proxy Raspberry (REMOTE). Cinque mappe fisse L1–L5 aumentano il lavoro di ricerca. I benchmark inviano i JSON predisposti: per queste run Gazebo non deve essere avviato o riavviato. La generazione delle mappe e l'esecuzione fisica del percorso non fanno parte della misura.

## Contenuto

- `raspberry/`: servizio LOCAL e proxy REMOTE, Dockerfile e requirements.
- `mac/`: servizio REMOTE, algoritmo A*, Dockerfile e requirements.
- `ubuntu/scripts/`: benchmark LOCAL e REMOTE.
- `ubuntu/task_c/maps/`: mappe JSON usate dai benchmark e anteprime PGM.
- `results/local/`, `results/remote/`: soli dieci CSV definitivi LAN.

## Ambiente e rete

Docker sul Raspberry e sul Mac; Python 3 con `requests` su Ubuntu. I requirements dei servizi e la base Python sono indicati nei Dockerfile. L'ambiente Ubuntu non dispone di un lockfile completo nel pacchetto. Per le build occorre accesso a registry e indice dei pacchetti.

| Nodo | IP Ethernet | Porta host → container |
|---|---|---|
| Ubuntu | 192.168.50.10/24 | Client benchmark |
| Raspberry LOCAL | 192.168.50.20/24 | 5200 → 5200 |
| Raspberry proxy | 192.168.50.20/24 | 5202 → 5202 |
| Mac REMOTE | 192.168.50.30/24 | 5201 → 5200 |

Configurazione comune dello switch nel README generale. Il proxy usa esclusivamente l'IP Ethernet del Mac. Ubuntu → Raspberry usa JSON normale; Raspberry → Mac usa JSON compatto + gzip livello 6. La risposta JSON contiene anche il percorso.

## Installazione dei file

Dalla radice `separazione-computazionale-robotica` sulla rispettiva macchina, copiare nei percorsi attesi dagli script. Salvare prima i file omonimi già presenti.

Raspberry:

```bash
mkdir -p ~/tesi
cp -R task_c/raspberry/. ~/tesi/
```

Mac:

```bash
mkdir -p ~/tesi/task_c
cp -R task_c/mac/. ~/tesi/task_c/
```

Ubuntu:

```bash
mkdir -p ~/tesi_gazebo
cp -R task_c/ubuntu/. ~/tesi_gazebo/
python3 -c 'import requests'
```

I CSV archiviati restano separati dalla directory di output operativa.

## Build

Sul Raspberry:

```bash
cd ~/tesi
docker build -t task-c-local:lan -f Dockerfile.task_c .
docker build -t task-c-proxy:lan -f Dockerfile.task_c_proxy .
```

Sul Mac:

```bash
cd ~/tesi/task_c
docker build -t task-c-remote:lan -f Dockerfile.task_c .
```

Ricostruire da questi sorgenti per includere gli indirizzi LAN; i tag di immagini storiche non ne garantiscono il contenuto. Registrare image ID/digest e versioni dell'ambiente prima della campagna. Non modificare immagini, sorgenti, mappe o rete durante le run.

## Protocollo di esecuzione

Una run comprende L1–L5 in ordine: per ogni livello 10 warm-up scartati e 100 campioni salvati, 500 campioni complessivi. I container della stessa modalità rimangono attivi tra le run. Eseguire prima le cinque LOCAL, poi le cinque REMOTE, come nella campagna archiviata. Fermare gli altri servizi sperimentali prima dei benchmark.

Controllare `docker ps` prima dell'avvio. Se esiste già un container con lo stesso nome, fermarlo; non avviarne un secondo. Sul Raspberry deve essere attivo un solo servizio Task C alla volta.

### LOCAL

Sul Raspberry, fermare `task-c-proxy` se attivo, quindi:

```bash
docker run -d --rm --name task-c-local -p 5200:5200 task-c-local:lan
```

Su Ubuntu, una run alla volta:

```bash
python3 ~/tesi_gazebo/scripts/task_c_local_benchmark.py 611
python3 ~/tesi_gazebo/scripts/task_c_local_benchmark.py 612
python3 ~/tesi_gazebo/scripts/task_c_local_benchmark.py 613
python3 ~/tesi_gazebo/scripts/task_c_local_benchmark.py 614
python3 ~/tesi_gazebo/scripts/task_c_local_benchmark.py 615
```

### REMOTE

Sul Mac:

```bash
docker run -d --rm --name task-c-remote -p 5201:5200 task-c-remote:lan
```

Sul Raspberry:

```bash
docker stop task-c-local
docker run -d --rm --name task-c-proxy -p 5202:5202 task-c-proxy:lan
```

Su Ubuntu, una run alla volta:

```bash
python3 ~/tesi_gazebo/scripts/task_c_remote_benchmark.py 711
python3 ~/tesi_gazebo/scripts/task_c_remote_benchmark.py 712
python3 ~/tesi_gazebo/scripts/task_c_remote_benchmark.py 713
python3 ~/tesi_gazebo/scripts/task_c_remote_benchmark.py 714
python3 ~/tesi_gazebo/scripts/task_c_remote_benchmark.py 715
```

Questi ID identificano il dataset archiviato. Per una ripetizione scegliere ID liberi e registrarli: i benchmark rifiutano di sovrascrivere file esistenti. Le prove tecniche `901` sono escluse. Se una run fallisce, fermarsi e verificare l'errore prima di proseguire.

## Output e controlli

Output operativo: `~/tesi_gazebo/results/task_c_lan/local/` e `remote/`. Ogni CSV ha 501 righe (intestazione + 500 campioni), `sample_id` da 1 a 500 e `level_sample_id` da 1 a 100 per livello.

```bash
wc -l ~/tesi_gazebo/results/task_c_lan/local/run_61{1..5}.csv \
  ~/tesi_gazebo/results/task_c_lan/remote/run_71{1..5}.csv
```

Per gli ID della campagna: 501 righe per file e 5.010 totali. Il benchmark controlla i seguenti risultati per ogni richiesta:

| Livello | path_length | expanded_nodes |
|---|---:|---:|
| L1 | 61 | 450 |
| L2 | 91 | 1440 |
| L3 | 143 | 4259 |
| L4 | 223 | 10383 |
| L5 | 283 | 16148 |

## Confini delle misure

| Colonna | Misura |
|---|---|
| `processing_time_ms` / `remote_processing_time_ms` | Solo chiamata A* sul Raspberry / Mac |
| `service_time_ms` / `remote_service_time_ms` | Lettura del corpo, parsing, eventuale decompressione, A* e costruzione del dizionario; termina prima di `jsonify()` |
| `serialization_time_ms` | Serializzazione JSON nel proxy Raspberry |
| `compression_time_ms` | Compressione gzip nel proxy |
| `offload_e2e_time_ms` | Dall'inizio della serializzazione sul Raspberry al ritorno di `requests.post` e controllo HTTP; esclude parsing iniziale nel proxy e successivo `response.json()` |
| `client_e2e_time_ms` / `total_e2e_time_ms` | Richiesta HTTP vista dal client Ubuntu LOCAL / REMOTE |
| `offload_nonprocessing_time_ms` | Offload meno algoritmo Mac |
| `offload_transport_overhead_ms` | Offload meno serializzazione, compressione e servizio Mac: residuo, non sola latenza di rete |
| `client_overhead_ms` / `ubuntu_raspberry_overhead_ms` | E2E Ubuntu meno servizio LOCAL / offload REMOTE; residui con componenti differenti |
| `raw_payload_bytes`, `compressed_payload_bytes`, `compression_ratio` | Dimensioni del JSON del proxy e del gzip; rapporto compresso/non compresso |

La lettura del corpo può includere attesa di dati; i timer di servizio non isolano completamente la rete. Il confronto servizio LOCAL/offload REMOTE ha confini differenti, perché il proxy ha già effettuato il parsing prima di avviare il timer offload. Il processing è incluso negli altri tempi: non sommarlo di nuovo.

## Risultati della campagna LAN del 18 ottobre 2026

Dieci CSV, 5.000 campioni validi: cinque repliche per modalità e 100 campioni per livello in ogni replica. Medie in millisecondi:

| Livello | A* LOCAL | A* REMOTE | E2E LOCAL | E2E REMOTE |
|---|---:|---:|---:|---:|
| L1 | 9,374 | 1,425 | 68,700 | 106,927 |
| L2 | 30,114 | 4,248 | 89,896 | 109,980 |
| L3 | 93,432 | 11,687 | 153,714 | 117,635 |
| L4 | 233,598 | 24,757 | 294,193 | 131,004 |
| L5 | 371,383 | 33,922 | 432,012 | 138,049 |

REMOTE rallenta L1–L2 e accelera L3–L5 sull'E2E Ubuntu. Il passaggio osservato è tra L2 e L3; non è una stima di un punto di pareggio esatto. L'inferenza statistica deve usare le cinque run per modalità come repliche, non i 500 campioni per livello come repliche indipendenti. L'ordine LOCAL poi REMOTE non è randomizzato.

## Provenienza e verifiche del pacchetto

Sorgenti recuperati dal pacchetto di preparazione condiviso; applicate le sostituzioni IP e directory output documentate e verificate durante la sessione. Corretto anche un commento sui confini del timer di servizio, senza modificare la logica. Non è stata verificata byte per byte l'identità con tutti i file attualmente sui dispositivi.

Il pacchetto è stato verificato per sintassi Python, dipendenze dei Dockerfile, mappe e integrità dei CSV. Le prove sui dispositivi sono quelle riportate nella sessione; build e rete non sono state rieseguite nel presente ambiente. Non sono inclusi vecchi proxy Wi-Fi, backup, prove `901` o script di analisi storici riferiti ad altri ID.

## Verifica funzionale aggiuntiva

Il 29 ottobre è stato aggiunto un controllore Ubuntu per L1, provato in LOCAL e REMOTE con odometria. Sono documentati raggiungimento dei waypoint e arresto; non contatti/collisioni o inseguimento L2–L5. Si veda [verifica L1](functional_checks/README.md). Le precedenti indicazioni sull’assenza di esecuzione robotica si riferiscono ai benchmark, non a questa prova aggiuntiva.

## Campagna aggiuntiva CPU/RAM

Misure risorse del 29–30 ottobre 2026, separate dalle misure temporali precedenti: [protocollo, script e dati definitivi](resources/README.md). Il controller memoria è stato abilitato per questa nuova campagna.
