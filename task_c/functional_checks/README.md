# Verifiche funzionali di movimento — 29 ottobre 2026

Script e JSON originali recuperati da Ubuntu; nessuna modifica ai programmi eseguiti. Sono prove funzionali separate dalle campagne statistiche: una prova per condizione, non nuove repliche dei benchmark.

I programmi girano su Ubuntu, Gazebo Sim 8.15.0, binding gz.transport13 e gz.msgs10; richiedono requests. Lanciare da SSH aperta dal Mac. Il controllore dei movimenti gira su Ubuntu, mentre Raspberry esegue LOCAL o proxy e Mac esegue REMOTE. Non descrivere quindi l'attuazione come eseguita dal Raspberry.

Prima di ogni prova riavviare il mondo; attendere servizi HTTP pronti. Topic /cmd_vel e /model/robot/odometry. Non eseguire contemporaneamente altri publisher di velocità. Copiare gli script in ~/tesi_gazebo/movement_checks; gli output JSON vengono creati accanto agli script, con nome temporale esclusivo. Arresto finale nei blocchi finally; un arresto forzato del processo o perdita della connessione non garantisce l'esecuzione di finally.

Le posizioni sono stime odometriche. Raggiungimento odometrico non equivale a misura indipendente della posa fisica del simulatore; non sono registrati contatti/collisioni. L'arresto viene confermato su cinque aggiornamenti odometrici con velocità sotto soglia: il relativo tempo include la finestra di conferma, non misura solo frenata. Le verifiche usano tempo reale monotono e timestamp odometrici di simulazione.

## Task C — sola mappa L1

Mondo ~/tesi_gazebo/worlds/thesis_world_L1.sdf, mappa ~/tesi_gazebo/task_c/maps/L1.json, servizi e porte come README C. Il mondo L1 e il generatore sono conservati in questa cartella quando disponibili dal pacchetto di preparazione; verificarne corrispondenza con il mondo effettivamente usato sui dispositivi.

```bash
gz sim -s -r --headless-rendering ~/tesi_gazebo/worlds/thesis_world_L1.sdf
```

In un altro terminale Ubuntu:

```bash
python3 ~/tesi_gazebo/movement_checks/task_c_follow.py local
```

Riavviare il mondo, attivare REMOTE, poi eseguire lo stesso comando con remote. Robot vicino a (0,0), yaw zero. Il client richiede il percorso al servizio, verifica 61 celle, 450 nodi, estremi e adiacenza/celle libere; segue i vertici senza tagliare gli angoli, con velocità massima 0,1 m/s e arresti alle svolte. Celle convertite al centro: origine (-10,-10), passo 0,1 m, obiettivo (4,05;0,05). Tolleranza waypoint 2,5 cm durante avvicinamento, controllo entro 4 cm dopo arresto. Timeout e odometria non aggiornata interrompono la prova.

| Misura | LOCAL | REMOTE |
|---|---:|---:|
| HTTP reale, s | 0,111322 | 0,174064 |
| Attuazione reale, s | 86,127340 | 86,188673 |
| Totale reale, s | 86,238980 | 86,362955 |
| Errore finale odometrico, m | 0,024456 | 0,024464 |

Sei waypoint raggiunti per modalità, 847 campioni di traccia per prova. Risultati limitati a L1 e feedback odometrico; non dimostrano L2–L5, assenza di collisioni o superiorità statistica del tempo completo. Il campo recognition dei JSON contiene la risposta A*, non riconoscimento vocale.
