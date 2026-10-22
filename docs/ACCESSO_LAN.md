# Accesso al G1: risultati e passo necessario

## Quattro accessi distinti

| Accesso | Dove viene verificato | Cosa consente |
| --- | --- | --- |
| Account cloud Daikin | Server cloud | App e API mobile; già verificato in lettura |
| Utente web locale | File locale user.json, hash con salt | Sessione /web sul G1 |
| API key locale | File locale apikey.json | Richieste /api sul G1 |
| Account/chiave SSH | Sistema operativo del G1 | Diagnosi del software installato, se autorizzato |

Il pacchetto applicativo 140 non contiene la configurazione SSH dell'apparato
installato. Non fornisce la chiave privata necessaria all'accesso effettivo.
Il segreto del dispositivo usato verso il cloud è un'altra credenziale ancora,
letto dall'EEPROM dal software G1: non serve all'integrazione API LAN e non viene
richiesto, letto o copiato da questi strumenti.

## Avvio e file locali

app.js inizializza CAN, moduli hardware, repository utenti/chiavi e cache, poi
avvia il server web. La porta predefinita è 80; config/parameters.js può
sovrascrivere impostazioni. Il file non va importato con require per la sola
diagnosi, perché è codice eseguibile.

DataHandler legge user.json e apikey.json dalla directory configurata
(default /home/root/.rocon/); file assente → elenco vuoto. Il cloud non popola
automaticamente questi utenti tramite il login dell'app. Il pacchetto include
una vecchia migrazione di provisioning dell'utente, ma non è prova che sia
stata eseguita sull'apparato reale. Non va lanciata per tentativi: copia un file
utente e modifica il gateway.

Il web login locale crea una sessione quando utente/hash corrispondono. Dalla
pagina autenticata /web/apikey si possono gestire le chiavi. Questa capacità
è nel sorgente; non è una prova che il servizio sia raggiungibile sul G1 reale.
La creazione di un utente o di una chiave è una modifica di configurazione e
non è stata eseguita da questa attività.

## Lettura completa e limitazioni

L'API /api espone solo viste sintetiche. Per la cache completa esiste
POST /web/export.json, autenticato con sessione web. L'analisi di ExportController
e ParameterExporter conferma che il percorso di export restituisce
ValueCache.getAll(): non invia setter CAN. Può aspettare il completamento del
primo ciclo Refresher e non aggiunge timestamp per parametro.

Il percorso /web/import è diverso: applica parametri e orario alla macchina.
Non è usato. Non sostituire import a export e non eseguire script di migrazione
o updater per ottenere un accesso locale.

La cache completa può contenere molti più parametri dei template API e rende
possibile preparare un'integrazione più ampia. La sua lettura richiede comunque
accesso web locale legittimo e verifica di disponibilità/freschezza. Il prototipo
HA attuale non implementa il login web o POST export: usa soltanto GET API.

## Cosa è noto sul dispositivo reale

Nei controlli di rete registrati HTTP 80 e HTTPS 443 non erano raggiungibili,
mentre SSH rispondeva. L'ultima verifica SSH senza login ha ricevuto il banner
OpenSSH_6.0p1, ma non una chiave host confrontabile: non si deve concludere che
la chiave sia cambiata. I precedenti tentativi documentati sull'account debian
offrivano solo autenticazione publickey. Nessun accesso remoto è stato ottenuto.

Quindi non sappiamo se il web sia fermo, spostato, filtrato o diverso nella
versione installata. Non possiamo scegliere una causa dal solo software 140
scaricato o dalla porta chiusa.

## Cosa serve dal proprietario

Prima verifica senza SSH: dal telefono sul Wi-Fi di casa aprire nel browser
`http://IP_DEL_PROPRIO_G1/web/login`, con http esplicito. Comunicare se appare
il login, una pagina bianca o un errore; non usare qui la password cloud.
Il telefono è stato verificato con un percorso Wi-Fi verso l'IP G1, ma non
dispone dei client HTTP da terminale cercati. La prova browser resta manuale.

1. Verificare con installatore/assistenza se esiste un accesso locale supportato
   al proprio G1: account web, API key oppure chiave SSH già autorizzata. Chiedere
   anche versione applicativa installata e porta del servizio web. Non inviare
   password o chiavi in chat o in issue GitHub.
2. Una foto dell'etichetta/modello del G1 e dei connettori esterni, coprendo
   seriale/MAC, più schermata Informazioni del controller. Non aprire la caldaia
   o scollegare cavi per acquisirle. Servono a distinguere revisioni e a valutare
   eventuali percorsi di accesso fisico supportati.
3. Dopo un accesso shell funzionante, eseguire la diagnostica originale
   `tools/g1_readonly_diagnostics.sh`: legge versione, porte e soli metadati/conteggi
   dei file. Non stampa hash password, utenti, API key o EEPROM; non richiede sudo
   e non modifica servizi o file.

Non occorre un altro login cloud per analizzare i file già acquisiti.
Se non è disponibile un accesso locale recuperabile, il percorso alternativo
è un bridge CAN esterno compatibile con il controller e la connessione esistente,
con prima fase di monitoraggio. Richiede verifica hardware prima di scegliere
componenti o predisporre comandi; non è una API LAN del G1.
