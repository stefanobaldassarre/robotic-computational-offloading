# Separazione computazionale in sistemi robotici a risorse limitate: analisi sperimentale delle prestazioni locale-remoto

Confronto sperimentale tra elaborazione LOCAL sul Raspberry Pi 3 B+ e REMOTE sul MacBook Air M3, tramite proxy Raspberry. Ubuntu ospita i benchmark e, nel Task A, la simulazione Gazebo. Gli input audio di B sono esterni; C usa mappe predisposte.

## Architettura e rete

LOCAL: Ubuntu → Raspberry/elaborazione → Ubuntu. REMOTE: Ubuntu → Raspberry/proxy → Mac/elaborazione → Raspberry → Ubuntu. Ubuntu non è un'alternativa di calcolo nei confronti.

| Nodo | IP Ethernet / maschera | Ruolo |
|---|---|---|
| Ubuntu | 192.168.50.10/24 | Input, benchmark, CSV; Gazebo per A |
| Raspberry | 192.168.50.20/24 | LOCAL o proxy REMOTE |
| Mac | 192.168.50.30/24 | REMOTE |

Switch D-Link DES-1005D 10/100 Mbps, senza router. Docker su Raspberry e Mac; Python su Ubuntu, Gazebo Harmonic per A. Dettagli di versioni, porte e dipendenze nei README dei task. Non tutte le dipendenze sono bloccate tramite lockfile/digest: nuove build possono differire dalle immagini della campagna.

## Task e istruzioni

| Task | Contenuto | Documentazione |
|---|---|---|
| A | OpenCV su immagini Gazebo | [README A](task_a/README.md) |
| B | Riconoscimento offline Vosk, sequenze sintetiche italiane | [README B](task_b/README.md) |
| C | Pianificazione A* su mappe L1–L5 | [README C](task_c/README.md) |

Ogni cartella contiene i sorgenti necessari, gli input disponibili e i CSV definitivi. Per B il servizio condiviso Raspberry/Mac è in services/, il client in ubuntu/ e i WAV in dataset/. Il modello esterno si scarica seguendo il README e si verifica col checksum. I file storici con IP Wi-Fi, benchmark matriciali, backup e prove tecniche sono esclusi.

## Ambito delle verifiche

Le campagne misurano i servizi e le richieste HTTP su LAN. B dispone di verifiche funzionali dei cinque comandi e di una sequenza in entrambe le modalità. C dispone di una verifica di inseguimento su L1 in entrambe le modalità, basata su odometria. Dettagli e limiti in functional_checks/ dei rispettivi task. I tempi E2E dei client non comprendono l'intero ciclo fisico/simulato. Confini e limiti specifici nei README.

I CSV originali sono conservati, inclusi i warm-up marcati di B, da escludere durante l'analisi. ID uguali in task diversi appartengono a directory distinte. SHA256SUMS elenca i checksum dei file del pacchetto escluso l'elenco stesso.

## Grafici della tesi

Il capitolo dei risultati usa nove figure riproducibili in MATLAB Online. La [guida ai grafici](analysis/grafici/README.md) spiega come ricostruire i dati derivati, eseguire il generatore ed esportare i PDF.

## Verifiche funzionali

Le prove in Gazebo verificano l'utilizzo dei risultati dei servizi per eseguire le azioni previste:

- **Task B:** cinque comandi singoli e una sequenza composta, in LOCAL e REMOTE. [Script, risultati e istruzioni](task_b/functional_checks/README.md).
- **Task C:** inseguimento del percorso L1 nelle due modalità, con controllo dei waypoint e dell'arresto tramite odometria. [Script, risultati e istruzioni](task_c/functional_checks/README.md).

Queste verifiche sono distinte dai benchmark temporali e dalle misure CPU/RAM. Per estensione delle prove, criteri di verifica e limiti consultare i README collegati.

## Campagne consolidate

| Task | Campagna temporale | Campagna risorse Raspberry | Movimento aggiuntivo |
|---|---|---|---|
| A | 5 run/modo, 100 frame/run | 5 repliche/modo, 300 richieste/replica su un JPEG fisso | Integrazione nel benchmark Gazebo; non tutte le scene validate |
| B | 5 run/modo, 45 misure + 3 warm-up/run | 5 repliche/modo, 15 richieste/replica | 5 comandi singoli e una sequenza, una prova/modo |
| C | 5 run/modo, 100 richieste/livello/run | 5 repliche/modo, 100 richieste/livello/replica | Inseguimento L1, una prova/modo, feedback odometrico |

- [Metodo comune CPU/RAM e installazione monitor](monitoring/README.md)
- [Risorse A](task_a/resources/README.md)
- [Risorse B](task_b/resources/README.md)
- [Risorse C](task_c/resources/README.md)
- [Analisi riproducibile delle risorse](analysis/README.md)

Le campagne temporali e risorse sono distinte: non fondere i frame dinamici A con il JPEG fisso, né i protocolli diversi B/C. Le risorse riguardano solo il container Raspberry LOCAL o proxy REMOTE, non consumi energetici o totali del sistema. Il controller memoria è stato abilitato tra le campagne. Non sono inclusi chiavi SSH, modelli Vosk scaricati o dati di altri esperimenti.

## Autore, licenza e citazione

**Autore:** Stefano Baldassarre.

Il software e la documentazione originale sono distribuiti con [licenza MIT](LICENSE): possono essere utilizzati, modificati e redistribuiti, anche commercialmente, mantenendo copyright e licenza nelle copie o porzioni sostanziali. Per i materiali di terzi si applicano le rispettive condizioni: vedere [provenienza](MATERIALI_DI_TERZI.md).

Se utilizzi il progetto in un lavoro accademico, è gradita la citazione:

> Baldassarre, Stefano (2026). *Separazione computazionale in sistemi robotici a risorse limitate: analisi sperimentale delle prestazioni locale-remoto*. Codice e materiali sperimentali della tesi.

I metadati sono disponibili in [CITATION.cff](CITATION.cff). La citazione accademica è richiesta come riconoscimento, non come condizione aggiuntiva alla MIT. Dopo la pubblicazione aggiungere URL e versione effettivamente utilizzata alla citazione.
