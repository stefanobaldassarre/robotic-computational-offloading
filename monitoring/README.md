# Monitoraggio CPU e memoria — Raspberry cgroup v2

[README generale](../README.md)

Monitor comune identico nelle tre campagne. Raspberry: cgroup v2, systemd, quattro CPU logiche, kernel registrato nei metadati. Controller memoria abilitato aggiungendo cgroup_enable=memory a /boot/firmware/cmdline.txt e riavviando. I precedenti benchmark temporali sono conservati come campagne distinte. Nessuna misura energetica o del consumo totale Raspberry+Mac.

## Installazione e autenticazione

Copiare agent.py in ~/tesi/resource_monitor/agent.py sul Raspberry. I client girano su Ubuntu, richiedono requests e avviano l'agente tramite SSH verso raspberry@192.168.50.20. Usano la chiave privata Ubuntu ~/.ssh/tesi_monitor_ed25519 (non inclusa, non caricarla su GitHub).

Da Ubuntu, se la chiave dedicata non esiste:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -f ~/.ssh/tesi_monitor_ed25519 -N '' -C tesi-resource-monitor
ssh-copy-id -i ~/.ssh/tesi_monitor_ed25519.pub raspberry@192.168.50.20
```

Non sovrascrivere una chiave già presente. Verificare:

```bash
ssh -i ~/.ssh/tesi_monitor_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes raspberry@192.168.50.20 'echo OK'
```

Avviare il servizio LOCAL o il proxy REMOTE secondo il README del task. Verificare GET /process: HTTP 405 conferma disponibilità Flask, non correttezza dell'algoritmo. In REMOTE controllare anche il servizio Mac. Non lanciare il client con HTTP 000. Il client avvia e termina il monitor automaticamente; non eseguire agent.py manualmente senza il protocollo di controllo stdin.

## Cosa viene misurato

Il monitor è un processo host esterno al cgroup del container: il suo costo non è incluso nel contatore CPU del container, ma può interferire con l'host. Non è stato quantificato con una campagna separata. Legge i file cgroup circa ogni 200 ms e ai confini delle fasi. Non installa componenti nel servizio.

- CPU cumulativa: differenza usage_usec tra begin/end, in secondi CPU.
- CPU media di finestra: 100 × secondi CPU / secondi reali. 100% = un core; dividere per quattro per riferimento alla capacità nominale dell'host. Valori oltre 100% sono possibili con più thread.
- memory.current: memoria addebitata al cgroup, comprese componenti anonime, file/cache e kernel. Non RSS del solo algoritmo, né tutta la RAM dell'host.
- memory.stat: anon, file, kernel e inactive_file, riportati separatamente. File condivisi/cache possono essere addebitati a cgroup diversi a seconda della storia dell'host: ricreare il container non svuota la cache globale. Non chiamare memory.current una misura indipendente da questo effetto.
- Memoria media: integrazione trapezoidale dei campioni tra begin/end divisa per durata. Massimo: massimo campionato, non picco assoluto garantito.
- Swap ed eventi memory.events confrontati prima/dopo. Le letture dei vari file sono successive, non atomiche.

BEGIN/END ricevuti via SSH sul Raspberry delimitano idle e active con lo stesso orologio monotono. La finestra attiva include scambio di controllo, client/HTTP e intervalli tra richieste. Non coincide con la somma dei processing_time_ms. Nessuna sincronizzazione degli orologi Ubuntu/Raspberry necessaria per queste differenze; timestamp assoluti e nomi dei file possono avere piccoli scarti tra host.

Si riportano consumi lordi della finestra attiva e baseline idle separata. Non è sottratto automaticamente il riposo. Le finestre hanno durata diversa tra LOCAL/REMOTE: confrontare tempo CPU per stesso numero di richieste oltre alle percentuali medie.

## Limitazioni e qualità

Gli agenti usano phase waiting/idle/active; per le risorse sotto carico filtrare active e usare begin/end come confini. La percentuale sulla riga begin può includere l'intervallo precedente: l'analisi usa differenze cumulative di finestra, non la media di queste percentuali. L'analisi mantiene gli intervalli effettivi per la memoria.

Intervalli lunghi osservati nei dati definitivi: B LOCAL replica 2 circa 0,870 s; C LOCAL L2 replica 5 circa 0,658 s. Rilevati nell’analisi riproducibile. Possono nascondere picchi RAM brevi; non invalidano da soli le differenze CPU cumulative. Non eliminare repliche senza motivo documentato.

I file originali agent/client sono mantenuti senza modifiche. Le etichette pilot sono storiche; gli indici runs.json definiscono la selezione definitiva. Per ripetere le campagne usare nomi temporali nuovi e registrare l'associazione tra livelli, replica e modalità. I timeout conservano file parziali: non includerli come repliche complete.
