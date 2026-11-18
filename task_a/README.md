# Task A — elaborazione immagini con OpenCV

[Torna al README generale](../README.md)

Il task rileva il rosso mediante maschera HSV, regione di interesse (ROI) e isteresi, producendo un comando per il robot simulato. Il confronto cambia la collocazione del servizio OpenCV.

## Percorso delle richieste

- LOCAL: Ubuntu/Gazebo → Raspberry/elaborazione → Ubuntu.
- REMOTE: Ubuntu/Gazebo → Raspberry/proxy → Mac/elaborazione → Raspberry → Ubuntu.

Ubuntu acquisisce e codifica i frame, invia le richieste, registra i CSV e applica i comandi al robot. Il servizio di analisi dell'immagine gira sul Raspberry in LOCAL e sul Mac in REMOTE.

## Prerequisiti


- Ubuntu con Gazebo Harmonic (binding Python `gz.transport13`, `gz.msgs10`), Python 3, OpenCV, NumPy e requests nell'interprete che avvia i benchmark.
- Docker Engine sul Raspberry e Docker Desktop attivo sul Mac, immagini ARM64.
- I requirements dei servizi sono inclusi; i Dockerfile fissano Python 3.13.15. L'ambiente Python Ubuntu non ha un lockfile completo nell'archivio: va verificato sulla macchina originale.
- Per ricostruire immagini occorrono accesso al registry e all'indice dei pacchetti. Nella rete isolata usare le immagini già disponibili.

Verifica su Ubuntu:

```bash
python3 -c 'import cv2, numpy, requests; from gz.transport13 import Node; from gz.msgs10.image_pb2 import Image'
gz sim --versions
```

## Configurazione LAN


| Nodo | IP / maschera |
|---|---|
| Ubuntu | 192.168.50.10/24 |
| Raspberry | 192.168.50.20/24 |
| Mac | 192.168.50.30/24 |

Switch D-Link DES-1005D, porte 10/100 Mbps, senza router. Nessun gateway/DNS necessario sulla rete di test. Collegare tutti i nodi allo switch e verificare ping prima dei test. Le richieste applicative devono usare questi IP Ethernet. Eventuale Wi-Fi serve solo per accesso esterno e non deve sostituire il percorso di test.

## File e installazione operativa

Le cartelle `raspberry/` e `mac/` conservano i contesti Docker originali. `ubuntu/scripts/` contiene i due benchmark; `ubuntu/worlds/` contiene il mondo della campagna. `results/local/` e `results/remote/` conservano i dieci CSV definitivi.

Su ciascuna macchina, dalla radice `separazione-computazionale-robotica` estratta, copiare i file nei percorsi attesi dagli script. Su ambienti già usati salvare prima una copia dei file omonimi.

Raspberry:

```bash
mkdir -p ~/tesi
cp -R task_a/raspberry/. ~/tesi/
```

Mac:

```bash
mkdir -p ~/tesi
cp -R task_a/mac/. ~/tesi/
```

Ubuntu:

```bash
mkdir -p ~/tesi_gazebo
cp -R task_a/ubuntu/. ~/tesi_gazebo/
```

I CSV archiviati non vengono copiati nella directory di output dei benchmark.

## Esecuzione


### Build opzionale

Raspberry, da `~/tesi`:

```bash
docker build -t task-a-local:1.0 -f Dockerfile .
docker build -t task-a-proxy:1.0 -f Dockerfile.proxy .
```

Mac, da `~/tesi`:

```bash
docker build -t task-a-remote:1.0 -f Dockerfile .
```

Per riprodurre la campagna con immagini già presenti, non ricostruire o aggiornare dipendenze durante le run. I sorgenti del repository non provano da soli l'identità delle vecchie immagini: registrare anche image ID/digest sull'ambiente originale.

### Fase LOCAL

Sul Raspberry, assicurarsi che il proxy A sia fermo; avviare:

```bash
docker run -d --rm --name task-a-local -p 5000:5000 task-a-local:1.0
```

Su Ubuntu, terminale 1:

```bash
gz sim -s -r --headless-rendering ~/tesi_gazebo/worlds/thesis_world.sdf
```

Su Ubuntu, terminale 2:

```bash
python3 ~/tesi_gazebo/scripts/task_a_local_benchmark.py 611
```

Ripetere per 612, 613, 614, 615. Prima di OGNI run fermare Gazebo con Ctrl+C, attendere la chiusura e rilanciarlo. Il container resta attivo.

### Fase REMOTE

Sul Raspberry:

```bash
docker stop task-a-local
docker run -d --rm --name task-a-proxy -p 5002:5002 \
  task-a-proxy:1.0
```

Il proxy `task_a_remote_proxy.py` punta al Mac Ethernet `192.168.50.30`. Ricostruire l’immagine proxy da questi sorgenti prima di usare questo comando: un’immagine precedente può contenere ancora il vecchio indirizzo.

Sul Mac:

```bash
docker run -d --rm --name task-a-remote -p 5001:5001 task-a-remote:1.0
```

Su Ubuntu, riavviare Gazebo prima di ciascuna run e lanciare nel secondo terminale:

```bash
python3 ~/tesi_gazebo/scripts/task_a_remote_benchmark.py 711
```

Ripetere per 712, 713, 714, 715. Non rilanciare docker run se il container con lo stesso nome è già attivo: controllare con `docker ps`.

### Output e validazione

10 warm-up scartati, 100 campioni salvati per run. Output:

- `~/tesi_gazebo/results/task_a_lan/local/run_611.csv` … `run_615.csv`
- `~/tesi_gazebo/results/task_a_lan/remote/run_711.csv` … `run_715.csv`

Ogni CSV deve avere 101 righe, sample_id 1–100 e run_id coerente. Gli script rifiutano di sovrascrivere file esistenti: per una nuova campagna scegliere nuovi ID e registrarli. Il dataset in `results/` contiene 500 campioni per modalità; 601, 701 e 901 sono esclusi. Tutti i campioni definitivi hanno azione TURN_LEFT: non generalizzare a tutte le condizioni di navigazione. Le run sono le repliche statistiche, non i singoli frame.

| Risultato medio campagna inclusa | LOCAL ms | REMOTE ms |
|---|---:|---:|
| Processing | 12.558 | 1.350 |
| Servizio locale / offload Raspberry | 21.604 | 20.510 |
| E2E completo Ubuntu | 39.674 | 40.111 |

## Significato delle misure

| Metrica Task A | Confine |
|---|---|
| processing_time_ms | Solo process_image sul Raspberry |
| service_time_ms | Decodifica JPEG, conversione, algoritmo e aggiornamento stato sul Raspberry |
| remote_processing_time_ms | Solo algoritmo sul Mac |
| remote_service_time_ms | Servizio di elaborazione sul Mac |
| offload_e2e_time_ms | Chiamata HTTP dal Raspberry al Mac e ritorno |
| e2e_time_ms / total_e2e_time_ms | Intera richiesta osservata dal benchmark Ubuntu |

`offload_transport_overhead_ms` è un residuo HTTP/trasporto, non pura latenza di rete. Il processing è incluso nel service: non sommarli. Il confronto service LOCAL/offload REMOTE valuta due alternative dal Raspberry con immagine già ricevuta, con operazioni diverse dovute all'offloading.


Le etichette E2E completo indicano il tempo della richiesta HTTP osservata dal benchmark Ubuntu: non l'intero ciclo di acquisizione, codifica e attuazione del robot.

## Riproducibilità e verifiche

I CSV e i sorgenti applicativi sono invariati. Per eliminare la copia storica, il contenuto del proxy LAN della campagna è ora conservato con il solo nome `task_a_remote_proxy.py`, già atteso dal Dockerfile. Il suffisso `_lan` e il montaggio del file non servono più. La build genera quindi un’immagine con la configurazione Ethernet corretta. Le immagini già presenti sui dispositivi non vengono modificate da questo pacchetto.

Gli ID 611–615 e 711–715 identificano i dati archiviati: nelle ripetizioni usare ID liberi, senza sovrascriverli. Mantenere invariati codice, immagini, dipendenze e rete durante la campagna. I container restano attivi tra le run della stessa modalità; Gazebo viene riavviato prima di ciascuna run. Lo stato del servizio persiste tra le richieste; ogni run scarta i primi dieci campioni.

Il pacchetto è stato verificato staticamente; build Docker e prove Gazebo devono essere eseguite sui dispositivi originali. Non è incluso un lockfile dell'ambiente Ubuntu né un export delle immagini Docker.

## Campagna aggiuntiva CPU/RAM

Misure risorse del 29–30 ottobre 2026, separate dalle misure temporali precedenti: [protocollo, script e dati definitivi](resources/README.md). Il controller memoria è stato abilitato per questa nuova campagna.
