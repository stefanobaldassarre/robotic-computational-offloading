# Capitolo 3 - Quali grafici inserire e come costruirli

Il capitolo contiene nove riquadri vuoti, G1-G9, senza dipendenze da immagini mancanti. I grafici non sono inclusi: il programma facoltativo `genera_grafici_tesi.m` li crea quando si decide di inserirli.

## Regole comuni

- LOCAL blu (#1768A5), REMOTE arancione (#CE591E), stessi colori in tutte le figure. Distinguere anche le linee con marcatori/stili quando necessario per la stampa.
- Tempi in ms, movimento in secondi reali, memoria in MiB; CPU in ms CPU/richiesta. CPU non significa tempo reale né energia.
- Per tempi e risorse: cinque repliche per modalità. Mostrare tutti e cinque i punti, media e deviazione standard campionaria (denominatore n-1). Le barre NON sono IC95%, errori standard o range delle singole richieste.
- Valore temporale della replica = media delle richieste della condizione in quella run. Mai calcolare le barre usando 500 richieste come se fossero 500 run indipendenti.
- Per memoria: prima media ponderata nel tempo della finestra attiva; poi media e SD delle cinque repliche. Non utilizzare la sola memoria finale né la differenza fine-inizio.
- Confrontare LOCAL/REMOTE dentro lo stesso task e la stessa condizione; i costi di A e B hanno unità di lavoro diverse. Mostrare pannelli con assi propri quando le scale differiscono molto.
- Assi lineari con origine zero per barre e tempi; nessun asse spezzato. La traiettoria usa assi metrici uguali e limiti adeguati al percorso.
- PDF vettoriale, font incorporati, dimensione leggibile dopo inserimento a larghezza testo. Non usare screenshot di Excel o del terminale. Non usare grafici 3D o due scale y sullo stesso pannello.
- Non sommare processing, servizio e E2E: sono intervalli annidati. Non chiamare rete l'E2E meno processing.
- Nel capitolo le figure devono essere richiamate e discusse. I commenti G1-G9 nel sorgente indicano il punto preciso di sostituzione.

## G1 - Task A: processing ed E2E

**File:** `g3_01_A_tempi.pdf`; label `fig:ch3_a_times`.

Due pannelli affiancati: processing, E2E Ubuntu. Asse x LOCAL/REMOTE, asse y ms (scala propria per ogni pannello, da zero). Barre o punti medi con cinque punti di replica e ±SD. Non sovrapporre servizio e processing come parti additive.

**Dati:** `dati_grafici/tempi_per_replica.csv`, task=a, condition=all; metric=processing_ms o e2e_ms. Sintesi già disponibile in `tempi_sintesi.csv`.

**Costruzione:** raggruppare per mode/metric, media e SD dei cinque value. Deve risultare evidente il divario del processing e la vicinanza dell'E2E. Il grafico non dimostra equivalenza statistica.

## G2 - Task B: tempi per numero di comandi

**File:** `g3_02_B_tempi.pdf`; label `fig:ch3_b_times`.

Due pannelli processing/E2E, x = categorie 1,3,5 comandi, y = ms. Per ogni modalità punti medi collegati, ±SD e punti delle repliche. Nessun fit di regressione: tre categorie non isolano l'effetto delle parole dalla durata audio/silenzi. Il programma usa posizioni equidistanti per le tre categorie.

**Dati:** tempi_per_replica, task=b, condition=1/3/5. I warm-up sono già esclusi; per ogni replica/condizione il valore riassume 15 richieste (5 file ripetuti tre volte). Cinque repliche, non 75 repliche.

**Valori E2E di controllo (ms):** LOCAL 2591,107/5054,016/7522,430; REMOTE 218,943/382,578/541,714. Non moltiplicare la durata del file per il numero di ripetizioni per costruire il tempo di riconoscimento.

## G3 - Task C: tempi L1-L5

**File:** `g3_03_C_tempi.pdf`; label `fig:ch3_c_times`.

Due pannelli processing/E2E; x = L1-L5 categorici; y = ms. Punti medi ±SD e cinque punti di run per condizione. Linee come guida visiva. Non stimare una soglia esatta interpolando l'incrocio delle linee: le cinque mappe sono istanze discrete.

**Dati:** tempi_per_replica, task=c, condition=L1...L5; ogni media di run deriva da 100 richieste del livello. Le griglie sono tutte 200x200: non intitolare l'asse x “dimensione della mappa”.

**Lettura:** sul calcolo REMOTE è sempre più rapido; sull'E2E LOCAL prevale a L1-L2 e REMOTE a L3-L5.

## G4 - Task A e B: lavoro CPU per richiesta

**File:** `g3_04_AB_cpu.pdf`; label `fig:ch3_ab_cpu`.

Due pannelli, uno per task, x LOCAL/REMOTE; y ms CPU/richiesta. Punti delle cinque repliche, media e ±SD. Assi propri da zero; non usare la stessa scala per A e B se rende invisibile A.

**Dati:** resources_per_run, task=a o b, level=all; valore = 1000*cpu_seconds_per_request. La colonna è CPU cumulativa divisa per 300 richieste in A o 15 in B. Non usare cpu_percent_one_core come se fosse tempo.

**Controllo:** A 37,332/17,205; B 5053,448/28,737 ms CPU/richiesta. Sono risorse Raspberry; non includono CPU Mac o energia.

## G5 - Task A e B: memoria totale e anonima

**File:** `g3_05_AB_memoria.pdf`; label `fig:ch3_ab_memory`.

Quattro pannelli: righe A/B, colonne totale cgroup/anonima. x LOCAL/REMOTE; y MiB. Cinque medie di finestra per modalità, media e ±SD. Totale e anonima NON sono categorie da sommare: anonima è una componente del totale.

**Dati:** resources_per_run, colonne memory_mean_mib e memory_anon_mean_mib. La dispersione totale B è importante; mostrare i punti evita che una barra media nasconda la variabilità della cache.

**Nota:** la memoria del container non equivale alla RSS dell'algoritmo. Non usare solo il delta di memoria attiva, dato che il modello Vosk risiede già in memoria dopo il warm-up.

## G6 - Task C: lavoro CPU per livello

**File:** `g3_06_C_cpu.pdf`; label `fig:ch3_c_cpu`.

x L1-L5; y ms CPU/richiesta; due serie, cinque punti di replica per livello, media ±SD. Valori = 1000*cpu_seconds_per_request. Non mescolare i livelli di una replica per aumentare n.

**Dati:** resources_per_run, task=c, level=L1...L5. Ogni finestra contiene 100 richieste. LOCAL cresce con il lavoro A*, REMOTE è quasi costante; a L1-L2 il proxy costa più CPU.

## G7 - Task C: memoria per livello

**File:** `g3_07_C_memoria.pdf`; label `fig:ch3_c_memory`.

Due pannelli totale/anonima; x L1-L5, y MiB, medie ±SD con cinque punti per modalità/livello. Stesso colore e legenda delle altre figure.

**Dati:** resources_per_run, task=c, colonne memory_mean_mib e memory_anon_mean_mib.

**Lettura:** le barre totali LOCAL hanno ampia dispersione da cache; la memoria anonima del proxy non risulta inferiore a LOCAL a L1-L4. Il container e l'ordine crescente sono condivisi tra livelli: niente conclusioni causali sulla sola dimensione del problema.

## G8 - Task B: richiesta, esecuzione e totale nella sequenza

**File:** `g3_08_B_movimento.pdf`; label `fig:ch3_b_motion`.

Tre pannelli HTTP, esecuzione con arresti, totale; x LOCAL/REMOTE, y secondi reali. Una barra o punto per modalità e valori numerici. Nessuna barra di errore: esiste UNA prova della sequenza per modalità. Non trattare i cinque comandi come cinque repliche della sequenza.

**Dati:** movimento_sintesi, task=b; colonne http_s, execution_s, total_s. Non sommare i tre pannelli: il totale comprende gli altri intervalli e piccoli overhead del client.

**Controllo:** HTTP circa 7,518/0,537; esecuzione 8,589/8,587; totale 16,106/9,124. Queste sono le prove S5_01, non la prova stop singola e non la media dei benchmark B.

## G9 - Task C L1: percorso e tracce odometriche

**File:** `g3_09_C_traiettoria.pdf`; label `fig:ch3_c_trajectory`.

Un piano x-y in metri con aspect='equal'. Sfondo: griglia di pianificazione L1, celle libere chiare/occupate scure; percorso A* tratteggiato nero; traccia LOCAL blu continua e REMOTE arancione puntinata. Segnare partenza pianificata e obiettivo. Se le tracce si sovrappongono, conservarle e distinguere gli stili: non traslarle artificialmente.

**Dati:** L1_mappa.json, C_L1_percorso.csv, C_L1_tracce.csv. La mappa è la griglia di pianificazione, che può comprendere margini di ingombro: non è un'immagine ground-truth delle collisioni del simulatore.

**Conversione celle:** x=x0+(col+0.5)*resolution, y=y0+(row+0.5)*resolution. Per imshow: origin='lower', extent=(x0,x0+ncol*s,y0,y0+nrow*s). Non invertire righe/colonne. Assi uguali e zoom intorno al percorso (circa x -0,5...4,55 m; y -0,5...1,55 m).

**Controllo:** start pianificato (0,05;0,05), robot reale odometrico vicino a (0;0), goal (4,05;0,05). Le tracce sono feedback odometrico, non ground-truth o prova di assenza di collisioni. Nessuna fascia di confidenza con una sola traiettoria per modalità.


Per esecuzione e download in MATLAB Online seguire LEGGIMI_MATLAB_ONLINE.md.
