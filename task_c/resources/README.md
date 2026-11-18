# Task C — campagna CPU e memoria del Raspberry

[Torna al task](../README.md) · [Metodo comune](../../monitoring/README.md)

Ogni replica comprende L1–L5 in ordine crescente, stesso container tra livelli. Per ciascun livello: tre warm-up, 10 secondi idle, 100 richieste attive; una finestra distinta per livello. Cinque repliche per modalità, 50 blocchi, 5.000 richieste misurate. Ordine dei livelli fisso: possibile effetto di storia dell'allocatore/cache, non un esperimento randomizzato sui livelli.

Mappe in ../ubuntu/task_c/maps/; percorso operativo ~/tesi_gazebo/task_c/maps/. Client scripts/client_c.py, da copiare in ~/tesi_gazebo/scripts/. Avvio Ubuntu: `python3 ~/tesi_gazebo/scripts/client_c.py local` (oppure remote). Porte Raspberry 5200/5202, Mac 5201:5200; servizi come README C. Gazebo non serve durante le misure risorse. La campagna è distribuita tra 29 e 30 ottobre; conservati kernel e immagine nei metadati.

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
| L1 | local | 4.475 | 29.94 | 23.96 |
| L2 | local | 6.537 | 29.94 | 23.97 |
| L3 | local | 12.925 | 30.09 | 24.13 |
| L4 | local | 27.100 | 30.83 | 24.86 |
| L5 | local | 40.909 | 32.31 | 26.34 |
| L1 | remote | 7.119 | 29.19 | 26.26 |
| L2 | remote | 7.151 | 29.23 | 26.28 |
| L3 | remote | 7.203 | 29.28 | 26.31 |
| L4 | remote | 7.299 | 29.33 | 26.34 |
| L5 | remote | 7.383 | 29.31 | 26.34 |

La memoria totale dipende anche da file/cache; la componente anonima va valutata separatamente. Le risorse sono quelle del container Raspberry, non del sistema complessivo.
