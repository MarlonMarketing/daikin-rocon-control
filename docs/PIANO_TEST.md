# Piano di test e stato

## Test offline del pacchetto

Eseguire `py -3 -m unittest discover -s tests -v`.
Coprono appartenenza circuiti, percorsi e credenziali, redirect, dimensione
risposte, JSON non valido, export confinati in _private e assenza di setter.
Non provano compatibilità col cloud o col gateway reale.

## Verifiche reali successive

1. Login e dettagli circuiti: confrontare valori/campi con app e display;
   nessun POST diverso dal login, PUT, PATCH o DELETE.
2. Distinguere set/confirmed, date e contatto gateway; non usare l'orario del
   file esportato come prova di misura fresca.
3. G1: registrare modello/versione senza dati identificativi pubblici; prima
   sola lettura con accesso supportato. HTTP aperto non prova un'API.
4. Futuri setter: prima simulazione offline; poi un solo parametro con valore,
   limiti, durata, criterio di arresto e ripristino documentati e revisionati.
5. Guasti: 401/403/423/429/5xx, perdita cloud/LAN, dati null e sentinelle,
   conferma assente, modifiche manuali concorrenti e riavvio HA.
6. Programmi: fine 24:00, intervalli vuoti/sovrapposti, ora impianto, cambio ora,
   date vacanze a fine mese/anno e anni bisestili.
7. Indipendenza: HA e controllo nativo restano utilizzabili con agente spento;
   per la modalità LAN verificare funzionamento senza cloud.

APK acquisiti e analizzati offline con REA/JADX. Verifica firme eseguita.
Il client ha completato un login reale e le letture installazioni/circuiti;
lo snapshot è stato analizzato offline. Nessuna lettura API LAN autenticata.
Scaricato per il proprio gateway un pacchetto applicativo G1, analizzato come
file inerti senza eseguire script o updater. Dettagli in FIRMWARE_G1.md.
Nessun setter, automazione HA o firmware è stato installato/eseguito.

## Prototipo locale 0.2.0

38 test offline passati: inclusi discovery, route GET fisse, chiavi codificate,
credenziali errate, redirect, valori mancanti/sentinelle e selezione archivio.
Sintassi dei file Python e JSON del componente HA verificata. Runtime HA,
hassfest e API G1 reale autenticata non verificati. Procedura completa in
HA_PROTOTIPO.md; nessuna installazione sull'istanza in uso.
