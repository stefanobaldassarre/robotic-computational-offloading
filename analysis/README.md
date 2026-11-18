# Analisi riproducibile delle risorse

[README generale](../README.md)

Dalla radice del progetto:

```bash
python3 analysis/analyze_resources.py
```

Solo libreria standard Python; nessun servizio Docker o modello necessario. Legge gli indici runs.json e i dati originali, verifica etichette, richieste, checksum degli input, risultati applicativi, finestre CPU, swap ed eventi memoria. Rigenera risorse per replica, medie e deviazioni standard campionarie tra cinque repliche. Non modifica i dati originali. File derivati sovrascritti intenzionalmente.

- resources_per_run.csv: 70 blocchi definitivi (A 10, B 10, C 50).
- resources_summary.csv: media delle cinque repliche per task/modalità/livello; la RAM è prima ponderata nel tempo dentro ogni replica.
- resource_quality.json: selezione e intervalli di campionamento prolungati.

Totale 8.150 richieste risorse: A 3.000, B 150, C 5.000. Non comprende i dataset temporali delle campagne precedenti, né warm-up. Nessun test di significatività generato automaticamente. Le letture cgroup non sono repliche sperimentali indipendenti.

I massimi sono campionati: la colonna memory_sampled_max_mib_mean riassume i cinque massimi di replica, non è il massimo di tutto il dataset. Per quest'ultimo usare la tabella per-run. Le percentuali CPU sono derivate dai contatori cumulativi di finestra. Memory.current non è RSS: componenti file/cache e attribuzione dei file condivisi possono cambiare tra container.

## Grafici della tesi

[Guida MATLAB, dati derivati e script](grafici/README.md).
