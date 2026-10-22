# Analisi del pacchetto applicativo RoCon G1 versione 140

## Acquisizione

22 ottobre 2026: il cloud autenticato ha restituito un installation ID che è
stato confrontato con il MAC del G1 nell'inventario locale. Solo dopo la
corrispondenza è stato usato il percorso ufficiale relativo al proprio gateway,
`GET /installation/update/{hardware-address}/0`, descritto nella ricerca G1 e
confermato dal codice dell'updater. Nessun identificativo altrui è stato usato.

Ricevuto HTTP 200 con TLS verificato, tipo application/zip, 5.468.559 byte.
SHA-256 del file ricevuto:
`8ae7412460ae1348d57036b8932fa5f8df15e3c952578f147f0d1db048cb77c5`.
Il file `version` dell'archivio contiene 140. Questa è la versione scaricata,
non una verifica della versione installata sul gateway né del sistema operativo.

L'archivio contiene 3.374 elementi, circa 14,6 MB estratti: applicazione Node.js,
web, connettore cloud/CAN, moduli, migrazioni e updater. È stato estratto in
`_private/firmware/` con rifiuto di percorsi esterni e symlink. Non sono stati
avviati app.js, dipendenze, migrazioni, updater o comandi hardware.

Analisi statica REA 6.7.0 completata su app.js, StatusController.js,
SettingController.js e ApiKeyMiddleware.js. L'analisi copre questi quattro
sorgenti; non costituisce verifica runtime dell'intera applicazione.
Pacchetto e sorgenti proprietari restano privati, esclusi dallo ZIP pubblico.

## Interfacce locali confermate nel sorgente

La configurazione predefinita usa porta HTTP 80 e dati applicazione in
`/home/root/.rocon/`. Un file parameters.js locale può sovrascrivere i default;
non sappiamo se sia presente nell'installazione reale.

| Metodo | Percorso | Comportamento nel pacchetto |
| --- | --- | --- |
| GET | `/api` | Elenco dispositivi |
| GET | `/api/status/:device` | Dati sintetici di stato |
| GET | `/api/setting/:device` | Impostazioni del template |
| PUT | `/api/setting/:device` | Tentativo di invio parametri CAN dopo validazione; non usato dal progetto |

Le API sono protette da middleware che richiede `apiKey` nella query e la cerca
nel repository locale. Il login cloud dell'app non fornisce questa chiave.
Le route `/web` usano un'altra sessione autenticata. Nessun utente o chiave
locale è stato creato o modificato durante l'analisi.

Risposte di stato individuate:

- water: `dhwTemperature`, ricavata da HG1/cSPEICHERISTTEMP;
- direct: `outsideTemperature` e `boilerTemperature`, ricavate da HG1;
- HC: `roomTemperature` per il nome circuito richiesto;
- `error` con fallback a zero nel codice originale: non trattarlo come prova
  di assenza guasti se la comunicazione è incompleta.

## Limiti concreti dell'API

- Il template `setting.direct.js` è **vuoto** in questa versione.
- Il template heating ha 53 campi, water 48, inclusi programmi settimanali.
- GET setting di water e direct risolve i dati sul dispositivo interno HG1;
  il PUT cerca invece usando direttamente il nome route ricevuto. Per water
  e direct questa differenza può impedire il corretto abbinamento del parametro.
- Il PUT risponde 200 dopo aver avviato le validazioni asincrone, senza attendere
  una conferma dalla macchina. HTTP 200 non dimostra applicazione del comando.
- I campi data vengono ricostruiti in lettura da parametri TAG/MONAT/JAHR;
  non si può assumere che un campo data aggregato sia direttamente scrivibile.

Queste evidenze spiegano perché non basta copiare le route in un componente HA
e dichiarare il controllo locale funzionante. Nessun PUT è stato provato.

## Registro CAN

`rotex-control-module/data/data.json` contiene 243 definizioni di parametro,
con indirizzi e metadati di tipo/fattore. 218 sono marcate `writeable=true`
nel file: **non sono 218 impostazioni già validate sul singolo impianto**.
Il repository genera combinazioni di parametri/dispositivi e non prova che
ogni combinazione sia implementata dalla macchina.

Sono presenti anche candidati non esposti dall'app mobile, tra cui curva
climatica (`eHZKKURVE`), limiti riscaldamento e isteresi ACS. Alcuni non hanno
minimo/massimo nel registro. Non vengono esposti come setter e non si deducono
limiti di sicurezza dal solo flag writeable o dal validatore legacy.

Questa fonte rende più concreta sia l'analisi LAN sia un eventuale bridge CAN
esterno. Un bridge richiede comunque hardware, pinout, compatibilità del modello
e letture passive verificate prima di abilitare qualsiasi comando.

## Ostacolo attuale

Il test del gateway reale ha trovato raggiungibile SSH, ma non HTTP 80 o HTTPS
443 da questo PC. Non è stato ottenuto un accesso SSH autorizzato né una API key
locale. Il software scaricato non dimostra che il servizio web reale sia
avviato o accessibile. Per proseguire sul dispositivo servono un accesso locale
già autorizzato/supportato o una diagnosi locale del servizio, senza reset o
installazione automatica del pacchetto scaricato.
