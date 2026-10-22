# Controlli cloud 0.4.0

## Semantica e stato

Il client HA usa solo `https://api.rotex-control.com`, TLS verificato, header API 6,
login JSON e cookie in memoria. Esegue GET degli impianti e dei circuiti
appartenenti all'account; non accetta URL restituiti dal server. Non usa il sito
web legacy con certificato scaduto e non disabilita TLS cloud.

Il client diagnostico `rocon_local` resta in sola lettura. Il componente HA
implementa separatamente PUT allowlistati, su richiesta delle entità di controllo.
Non è ancora una prova di scritture reali riuscite.

Ogni modifica legge dati nuovi dal cloud e costruisce l'oggetto ampio previsto
dall'app, preservando i campi confirmed e modificando soltanto i set selezionati.
Le date non vengono inventate o riscritte. I campi di misura estranei al serializer
non vengono reinviati. La presenza di richieste precedenti non confermate blocca
l'invio, evitando di riprodurre impostazioni pendenti.

La misura critica deve essere numerica e disponibile: ACS per water, temperatura
caldaia per riscaldamento. La sonda ambiente con sentinella -40 non diventa una
misura valida. Un GET recente non certifica la freschezza del bus: il cloud mobile
non fornisce un timestamp della sonda. Questa versione non installa ottimizzazioni
automatiche basate su tali misure.

## Temperature e modalità

I number mostrano il valore confirmed. Gli attributi includono requested,
confirmed, requested_at e confirmed_at. I range sono quelli della UI dell'app,
non una raccomandazione di esercizio per l'impianto.

La modalità si cambia soltanto dal circuito direct/heating. Summer è una modalità
impianto/ACS, non un generico HVAC auto. Non viene esposta una climate che
inventi temperatura ambiente o setpoint attivo. I controlli number/select/switch
sono utilizzabili dalle automazioni native HA dopo una strategia verificata.
Non vengono generati entity_id fittizi o automazioni pronte con soglie arbitrarie.

## Programmi e vacanze

Abilitare le entità text del programma desiderato nelle impostazioni dell'entità
(se disabilitate di default). Ogni giorno si modifica come transazione unica:

`06:00-08:00;16:00-22:00;00:00-00:00`

Sono sempre tre fasce in ordine. `00:00-00:00` è uno slot vuoto; fine `24:00`
è ammessa. Intervalli sovrapposti, invertiti, con minuti fuori passo o slot mancanti
vengono rifiutati. La modifica riguarda quel giorno e quel programma soltanto.

Vacanze: `2027-12-24/2027-12-31`, con fine inclusiva. Il client converte soltanto
la nuova data finale nel giorno successivo del protocollo. Le date già presenti
sono preservate senza incrementi ripetuti. Non invia 201/202 come modalità.
Per annullamenti mediante date speciali non documentate usare l'app ufficiale:
questa versione non inventa valori sentinella di cancellazione.

Party è espresso in minuti (0–360, passo 15), anche se il campo legacy si chiama
hours. Boost è un booleano UI serializzato come stringa true/false come nell'app.

## Conferme e guasti

- `none`: nessun comando inviato durante questa sessione runtime.
- `sent_waiting_confirmation`: richiesta accettata HTTP, conferma ancora assente.
- `uncertain`: trasmissione/risposta incerta; non ritentare automaticamente.
- `confirmed_by_cloud`: valori attesi e date di conferma successive all'invio
  osservati nel cloud; non è una certificazione fisica del funzionamento.

Nessuna coda di comandi, nessun retry del PUT, nessun ripristino automatico di
vecchie impostazioni. Le letture continuano ogni 300 secondi. Una sessione scaduta
può essere rinnovata una volta per una lettura, mai riproducendo una scrittura.
I comandi equivalenti al valore già effettivo non inviano PUT.

## Piano di prova

1. Installare dal repository su HA di prova; leggere tutti i circuiti e confrontare
   con app/display, incluse impostazioni e valori indisponibili.
2. Verificare credenziali errate, rinnovo sessione, perdita rete, unload e reconfigure.
3. Scegliere manualmente un parametro con valore iniziale, valore di prova, limiti e
   ripristino concordati. Il test automatico non sceglie setpoint per il proprietario.
4. Osservare richiesta e conferma, senza usare HTTP 200 come unico criterio.
5. Verificare concorrenza con app, timeout, assenza sonde, mancata conferma e
   permanenza delle protezioni native.
6. Progettare ottimizzazioni solo dopo aver stabilito freschezza, limiti e fallback.

Prove offline iniziali: 55 test passati, nessun comando reale inviato. I job HA
runtime/HACS/hassfest hanno esiti separati consultabili in Actions.
