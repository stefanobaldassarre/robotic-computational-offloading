# Verifiche funzionali di movimento — 29 ottobre 2026

Script e JSON originali recuperati da Ubuntu; nessuna modifica ai programmi eseguiti. Sono prove funzionali separate dalle campagne statistiche: una prova per condizione, non nuove repliche dei benchmark.

I programmi girano su Ubuntu, Gazebo Sim 8.15.0, binding gz.transport13 e gz.msgs10; richiedono requests. Lanciare da SSH aperta dal Mac. Il controllore dei movimenti gira su Ubuntu, mentre Raspberry esegue LOCAL o proxy e Mac esegue REMOTE. Non descrivere quindi l'attuazione come eseguita dal Raspberry.

Prima di ogni prova riavviare il mondo; attendere servizi HTTP pronti. Topic /cmd_vel e /model/robot/odometry. Non eseguire contemporaneamente altri publisher di velocità. Copiare gli script in ~/tesi_gazebo/movement_checks; gli output JSON vengono creati accanto agli script, con nome temporale esclusivo. Arresto finale nei blocchi finally; un arresto forzato del processo o perdita della connessione non garantisce l'esecuzione di finally.

Le posizioni sono stime odometriche. Raggiungimento odometrico non equivale a misura indipendente della posa fisica del simulatore; non sono registrati contatti/collisioni. L'arresto viene confermato su cinque aggiornamenti odometrici con velocità sotto soglia: il relativo tempo include la finestra di conferma, non misura solo frenata. Le verifiche usano tempo reale monotono e timestamp odometrici di simulazione.

## Task B

Mondo ~/tesi_gazebo/worlds/thesis_world.sdf. Dataset nel percorso operativo originale ~/tesi_gazebo/task_b_audio/Task_B_sequenze_pilot; copiare lì dataset/ del pacchetto se necessario. Server e porte come README B. Gli script leggono il manifest e verificano SHA-256 prima delle richieste. Modello e servizi identici alla campagna precedente.

Comandi da Ubuntu (scegliere local o remote, dopo aver avviato il servizio corrispondente):

```bash
python3 ~/tesi_gazebo/movement_checks/task_b_forward.py local
python3 ~/tesi_gazebo/movement_checks/task_b_backward.py local
python3 ~/tesi_gazebo/movement_checks/task_b_left.py local
python3 ~/tesi_gazebo/movement_checks/task_b_right.py local
python3 ~/tesi_gazebo/movement_checks/task_b_stop.py local
python3 ~/tesi_gazebo/movement_checks/task_b_sequence.py local
```

Riavviare Gazebo tra i comandi. Ripetere con remote. Avanti/indietro: ±0,1 m/s per 2 s simulati; sinistra/destra: ±0,5 rad/s per 2 s. Stop provato durante rotazione a 0,2 rad/s, mantenuta durante la richiesta audio. La sequenza S5_01 esegue avanti, indietro, sinistra, destra, stop, con arresto dopo ogni azione. Tolleranze sequenza: 3 cm traslazione e 0,1 rad orientamento; stop finale verifica quiete. Non si tratta di streaming o arresto d'emergenza.

Dodici verifiche B completate: cinque singoli e una sequenza, per ciascuna modalità. Singoli: avanzamenti circa ±0,20 m, rotazioni circa ±1 rad. La sequenza ha superato tutte le tolleranze in LOCAL e REMOTE.

| Sequenza S5_01, secondi reali | LOCAL | REMOTE |
|---|---:|---:|
| HTTP | 7,517519 | 0,536605 |
| Attuazione con arresti confermati | 8,588513 | 8,587418 |
| Totale | 16,106124 | 9,124106 |

È documentata anche la prova preliminare check_motion.py. Le prove forward/backward verificano lo spostamento osservato ma non applicano tutte le tolleranze geometriche della sequenza; il loro status completed non va confuso con una validazione generale della navigazione.
