# Task B — campagna CPU e memoria del Raspberry

[Torna al task](../README.md) · [Metodo comune](../../monitoring/README.md)

Carico: un passaggio fisso sui 15 WAV (1, 3, 5 comandi). Tre warm-up S1_01/S3_01/S5_01, 10 secondi idle, poi 15 richieste attive. Cinque repliche per modalità: 150 richieste misurate complessive. Risorse misurate sul blocco bilanciato completo, non separatamente per durata. Non confondere con la campagna temporale B: 45 misure/run e ordine pseudocasuale.

Dataset in ../dataset/; copiarlo nel percorso operativo ~/tesi_gazebo/task_b_audio/Task_B_sequenze_pilot/. Client scripts/client.py, da copiare in ~/tesi_gazebo/task_b_audio/. Avvio Ubuntu: `python3 ~/tesi_gazebo/task_b_audio/client.py local --dataset ~/tesi_gazebo/task_b_audio/Task_B_sequenze_pilot` (oppure remote). Porte Raspberry 5300/5302, Mac 5301; servizi e modello come README B.

## Selezione definitiva

`runs.json` identifica esplicitamente le repliche e i file originali Ubuntu/Raspberry. I nomi originali contengono resource_pilot ma solo le repliche dichiarate definitive sono incluse qui. Pilot iniziali e log transitori esclusi. CSV/JSON non modificati.

Ordine per coppie: REMOTE1 LOCAL1; LOCAL2 REMOTE2; REMOTE3 LOCAL3; LOCAL4 REMOTE4; REMOTE5 LOCAL5. Container Raspberry ricreato prima di ciascuna replica completa; server Mac riavviato prima di ogni REMOTE. Servizi seriali, nessun altro carico sperimentale sul Raspberry. Tre/dieci warm-up come sopra, fuori dalle finestre risorse.

## Output e analisi

`raw/ubuntu/`: richieste e riepiloghi del client. `raw/raspberry/`: campioni cgroup e metadati del monitor. Cartelle operative indicate nei client; i file originali hanno nomi temporali esclusivi. Non usare il solo nome resource_pilot per distinguere campagne: consultare runs.json.

[Metriche per replica](../../analysis/resources_per_run.csv) e [medie per modalità/livello](../../analysis/resources_summary.csv) generate da `analysis/analyze_resources.py`. Le run sono le repliche, i campioni temporali sono letture ripetute.

## Sintesi della campagna risorse

Medie di cinque repliche; RAM ponderata nel tempo dentro ogni replica. Tempo CPU lordo del blocco attivo, non tempo reale né energia.

| Condizione | Modalità | CPU cumulativa s | RAM media MiB | Memoria anonima MiB |
|---|---|---:|---:|---:|
| all | local | 75.802 | 238.64 | 204.49 |
| all | remote | 0.431 | 30.85 | 27.31 |

La memoria totale dipende anche da file/cache; la componente anonima va valutata separatamente. Le risorse sono quelle del container Raspberry, non del sistema complessivo.
