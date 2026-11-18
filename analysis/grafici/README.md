# Grafici del capitolo 3

[Dati e analisi](../README.md) · [Specifiche delle nove figure](SPECIFICHE_GRAFICI.md)

Aprire la cartella che contiene genera_grafici_tesi.m in MATLAB Online, mantenendo accanto la sottocartella dati_grafici. Nel Command Window:

```matlab
genera_grafici_tesi
```

I dati derivati sono già inclusi: non servono Gazebo, Docker o un modello Vosk per generare le figure. Lo script controlla le aggregazioni, quindi esporta nove PDF, i file FIG modificabili e anteprime PNG in una cartella con data e ora. Per la tesi usare i PDF. Nell'esecuzione di riferimento con MATLAB R2026b Update 2, otto PNG erano vuoti; i nove PDF erano validi e sono stati verificati visivamente.

Per ricostruire i dati derivati, dalla radice della repository:

```bash
python3 analysis/analyze_resources.py
python3 analysis/grafici/prepara_dati_grafici.py --data-root .
```

Questi comandi sovrascrivono le tabelle derivate e non modificano le misure originali. Il file dati_grafici/provenienza.json elenca percorsi e checksum degli input dell'esportatore.

G1–G7 mostrano i valori per replica e la media con deviazione standard campionaria (cinque repliche per condizione). G8–G9 riportano singole verifiche per modalità, senza barre statistiche.
