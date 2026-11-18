# Task B — riconoscimento di comandi audio con Vosk

[Torna al README generale](../README.md)

Confronto tra riconoscimento offline sul Raspberry (LOCAL) e sul Mac tramite proxy Raspberry (REMOTE). Stesso codice, modello e WAV nei due casi. Il modello viene caricato una volta all'avvio; ogni richiesta crea un riconoscitore nuovo. Il file viene elaborato alla massima velocità, senza riproduzione in tempo reale. Nessun vocabolario ristretto: parole estranee ai cinque comandi vengono restituite come UNKNOWN.

## Contenuto e prerequisiti

- `services/`: unico server condiviso da Raspberry e Mac, proxy, Dockerfile e contesto di build.
- `ubuntu/benchmark.py`: client della campagna definitiva, invariato.
- `dataset/`: 15 WAV e manifest con sequenza attesa, durata e SHA-256.
- `results/local/`, `results/remote/`: dieci CSV definitivi, inclusi i warm-up marcati.

Docker su Raspberry e Mac; Python 3 con requests su Ubuntu. Le immagini usano Python 3.11 slim Bookworm, Vosk 0.3.45 e libatomic1; versioni dirette nei Dockerfile. Base e dipendenze transitive non sono bloccate tramite digest/lockfile: una nuova build non garantisce identità con le immagini originali. Non ricostruire durante una campagna.

Porte host: Raspberry LOCAL 5300, proxy 5302, Mac REMOTE 5301 (server interno 5300). IP LAN e switch nel README generale. Nessun vecchio IP Wi-Fi nei sorgenti. Le copie via Wi-Fi sono trasferimenti di preparazione, non la rete delle misure.

## Modello italiano

Modello esterno non incluso: `vosk-model-small-it-0.22`, stessa copia su entrambi i nodi. Riferimento ufficiale: https://alphacephei.com/vosk/models

Sul Mac, con accesso Internet:

```bash
mkdir -p ~/tesi/task_b_audio/models
cd ~/tesi/task_b_audio/models
curl -fL --retry 3 -o vosk-model-small-it-0.22.zip \
  https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip
shasum -a 256 vosk-model-small-it-0.22.zip
unzip -n vosk-model-small-it-0.22.zip
```

SHA-256 dell'archivio usato nella sessione:

```text
9ec65e75861d1c6c2e457cccd932705340dcdf233f5b239f00733b4de0bf3267
```

Copiare lo stesso archivio sul Raspberry in `~/tesi/task_b_audio/models/`, verificare con `sha256sum`, quindi estrarre con `python3 -m zipfile -e vosk-model-small-it-0.22.zip .`. Fermarsi se il checksum differisce. Il modello estratto deve contenere am, conf, graph, ivector e README. Non applicare automaticamente una licenza del progetto a modelli o audio di terzi.

## Dataset e limiti

Audio sintetici italiani prodotti tramite Google Translate, secondo la provenienza dichiarata dall'autore. Cinque parole sorgente: avanti, indietro, sinistra, destra, stop. Le sequenze sono assemblate mediante concatenazione PCM senza tagli, filtri o silenzi aggiuntivi; mantengono i silenzi originali. WAV mono PCM16 a 16 kHz, conversione eseguita prima delle misure.

Cinque input per lunghezza (1, 3, 5 comandi), con rotazioni cicliche bilanciate. Durate: circa 3,52–4,54 s, 11,67–13,03 s e 20,49 s. Le sequenze non sono parlato continuo naturale né esempi vocali indipendenti: derivano dai medesimi cinque clip. Durata, numero di parole e dimensione payload variano insieme. Accuratezza riferita a questi 15 input fissi; nessuna generalizzazione a parlanti reali o ambienti rumorosi.

## Copia dei file operativi

Dalla radice del progetto sulla rispettiva macchina; salvare prima eventuali file omonimi.

Raspberry e Mac:

```bash
mkdir -p ~/tesi/task_b_audio/services
cp -R task_b/services/. ~/tesi/task_b_audio/services/
```

Ubuntu:

```bash
mkdir -p ~/tesi_gazebo/task_b_audio/benchmark
mkdir -p ~/tesi_gazebo/task_b_audio/dataset
cp -R task_b/ubuntu/. ~/tesi_gazebo/task_b_audio/benchmark/
cp -R task_b/dataset/. ~/tesi_gazebo/task_b_audio/dataset/
python3 -c 'import requests'
```

Questa organizzazione rinomina solo le cartelle di distribuzione; i sorgenti sono quelli ricevuti dai dispositivi. Il dataset viene selezionato tramite --dataset. I CSV archiviati rimangono separati dagli output sotto la home.

## Build e avvio LOCAL

Sul Raspberry:

```bash
cd ~/tesi/task_b_audio/services
docker build -t task-b-audio-server:pilot -f Dockerfile.server .
docker build -t task-b-audio-proxy:pilot -f Dockerfile.proxy .
docker run -d --rm --name task-b-audio-local -p 5300:5300 \
  --mount type=bind,src="$HOME/tesi/task_b_audio/models/vosk-model-small-it-0.22",dst=/model,readonly \
  task-b-audio-server:pilot
```

Il tag `:pilot` è conservato perché è quello impiegato anche nella campagna definitiva; non indica che i CSV inclusi siano prove tecniche. Controllare docker ps: sul Raspberry solo LOCAL o proxy Task B attivo, altri task fermi. Se un nome esiste già, fermarlo prima di creare il container.

Prima di ogni LOCAL successiva riavviare `docker restart task-b-audio-local`. Su Ubuntu verificare la disponibilità:

```bash
curl --max-time 5 -s -o /dev/null -w 'HTTP %{http_code}\n' \
  http://192.168.50.20:5300/process
```

Attendere HTTP 405: GET non è ammesso, ma conferma che Flask risponde dopo il caricamento del modello. Non è una prova del riconoscimento. In caso di 000/connessione rifiutata attendere e ripetere il controllo, senza lanciare il benchmark.

## Avvio REMOTE

Sul Mac:

```bash
cd ~/tesi/task_b_audio/services
docker build -t task-b-audio-server:pilot -f Dockerfile.server .
docker run -d --rm --name task-b-audio-remote -p 5301:5300 \
  --mount type=bind,src="$HOME/tesi/task_b_audio/models/vosk-model-small-it-0.22",dst=/model,readonly \
  task-b-audio-server:pilot
```

Sul Raspberry, dopo avere fermato LOCAL:

```bash
docker stop task-b-audio-local
docker run -d --rm --name task-b-audio-proxy -p 5302:5302 task-b-audio-proxy:pilot
```

Prima di ogni REMOTE successiva riavviare server Mac e proxy Raspberry; attendere 405 da entrambi, da Ubuntu:

```bash
curl --max-time 5 -s -o /dev/null -w 'Mac HTTP %{http_code}\n' http://192.168.50.30:5301/process
curl --max-time 5 -s -o /dev/null -w 'Proxy HTTP %{http_code}\n' http://192.168.50.20:5302/process
```

Quando si torna a LOCAL fermare il proxy e ricreare LOCAL col comando sopra. I container avviati con --rm vengono eliminati quando fermati.

## Protocollo e comandi benchmark

Tre warm-up (S1_01, S3_01, S5_01), poi tre passaggi su 15 file: 45 campioni misurati per run, 15 per lunghezza. Ogni passaggio permuta tutti i file; seed identico nella coppia LOCAL/REMOTE. Cinque coppie eseguite nel seguente ordine:

| Ordine | Modalità | Run | Seed |
|---|---|---:|---:|
| 1 | local | 611 | 1 |
| 2 | remote | 711 | 1 |
| 3 | remote | 712 | 2 |
| 4 | local | 612 | 2 |
| 5 | local | 613 | 3 |
| 6 | remote | 713 | 3 |
| 7 | remote | 714 | 4 |
| 8 | local | 614 | 4 |
| 9 | local | 615 | 5 |
| 10 | remote | 715 | 5 |

Per ogni riga eseguire su Ubuntu il comando seguente con modalità, ID e seed della tabella:

```bash
python3 ~/tesi_gazebo/task_b_audio/benchmark/benchmark.py \
  local 611 --seed 1 \
  --dataset ~/tesi_gazebo/task_b_audio/dataset
```

Riavviare e controllare i servizi prima di ogni run come sopra. Non occorre Gazebo: si misura la risposta su audio già disponibile, non registrazione, streaming o movimento. Ordine modalità alternato, non completamente randomizzato. Mantenere fissi rete, risorse Docker, codice e modello.

Output: `~/tesi_gazebo/results/task_b_audio_lan/{local,remote}/run_ID.csv`. CSV a creazione esclusiva, nessuna sovrascrittura. Nelle ripetizioni scegliere nuovi ID; seed ammessi 1–5. Errori di riconoscimento vengono registrati, errori HTTP interrompono lasciando un file parziale. Conservarlo separatamente e annotare il tentativo. La prima LOCAL 613 fallì per connessione rifiutata prima di elaborare richieste: dopo aver separato il tentativo fallito è stato riutilizzato lo stesso ID. L'archivio contiene solo la 613 completa. Prove 901–902 e tentativi falliti esclusi.

## CSV e metriche

Ogni file: 49 righe (header + 3 warm-up + 45 measured). Filtrare **phase=measured** per l'analisi. I campi inapplicabili alla modalità sono intenzionalmente vuoti. sample_id è progressivo nella fase; repeat_id identifica i tre passaggi misurati. Ogni file audio compare tre volte per run.

| Metrica | Confine |
|---|---|
| processing_time_ms / remote_processing_time_ms | Creazione riconoscitore, riconoscimento PCM, parsing dei risultati e testo; esclude lettura WAV e modello |
| service_time_ms / remote_service_time_ms | Da prima di leggere il corpo HTTP a risultato pronto, prima di jsonify; include lettura WAV e può includere attesa ricezione |
| offload_e2e_time_ms | WAV già ricevuto sul Raspberry: POST al Mac e controllo stato dopo ricezione completa; prima di response.json nel proxy |
| proxy_service_time_ms | Lettura corpo sul Raspberry, offload, parsing remoto e preparazione risposta; prima di jsonify |
| client_e2e_time_ms | POST visto da Ubuntu fino al corpo completo, prima di controllo stato e parsing |

Confrontare servizio LOCAL e servizio proxy REMOTE per confini simili dal Raspberry; offload esclude invece la ricezione iniziale. Il processing è incluso nel servizio: non sommarli. I residui non misurano pura latenza di rete. Non si usano sessioni HTTP persistenti; richieste seriali, timeout connessione 5 s e lettura 60 s.

## Risultati definitivi

450 richieste misurate + 30 warm-up. Corrette tutte le 450 sequenze misurate sui 15 input fissi. Medie, warm-up esclusi:

| Comandi | Processing LOCAL ms | Processing Mac ms | E2E LOCAL ms | E2E REMOTE ms | Speedup E2E |
|---|---:|---:|---:|---:|---:|
| 1 | 2558,397 | 172,647 | 2591,107 | 218,943 | 11,83× |
| 3 | 4992,615 | 290,132 | 5054,016 | 382,578 | 13,21× |
| 5 | 7432,116 | 403,971 | 7522,430 | 541,714 | 13,89× |

REMOTE è più rapido in tutte le condizioni provate. Le cinque run sono le repliche statistiche; non trattare ripetizioni o sequenze assemblate come nuovi esempi indipendenti. Nessun punto di pareggio identificato nel dominio provato.

L'integrazione aggiunta il 29 ottobre è documentata nelle [verifiche funzionali](functional_checks/README.md): cinque comandi e una sequenza, LOCAL e REMOTE, con attuazione Ubuntu e feedback odometrico. Le campagne temporali di questo README rimangono distinte dalle prove di movimento.

## Campagna aggiuntiva CPU/RAM

Misure risorse del 29–30 ottobre 2026, separate dalle misure temporali precedenti: [protocollo, script e dati definitivi](resources/README.md). Il controller memoria è stato abilitato per questa nuova campagna.
