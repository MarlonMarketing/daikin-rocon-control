# Integrazione Home Assistant da realizzare

È presente il prototipo `custom_components/rocon_g1_local`, non installato né
verificato nel runtime HA. Supporta soltanto letture dell'API LAN tramite key
locale già disponibile. Config flow, coordinator e sensori sono predisposti;
l'adattatore è testato offline. Il client diagnostico resta separato.

Il prototipo usa un coordinatore di lettura, richieste GET su host LAN esplicito
e primo refresh obbligatorio. I/O sincrono è eseguito nell'executor HA.
I sensori di impostazioni e programmi sono disabilitati di default, attivabili
come letture; non ci sono setter, servizi, climate o water_heater. Il polling
iniziale di 60 secondi è documentato, non prova freschezza delle misure.
La modalità LAN sarà presentata come verificata solo dopo una
lettura autenticata verificata sul firmware specifico; nessun fallback cloud
silenzioso per un utente che richiede funzionamento esclusivamente locale.

Sensori: misura reale, richiesta, conferma e stato comunicazione separati.
Acquisizione HA, timestamp misura e ultimo contatto sono grandezze diverse.
Campi mancanti rimangono unknown/unavailable; nessuno zero di comodo.

Possibili piattaforme future: climate, water_heater, number, select e funzioni
di programma. Non sono stati inventati entity_id o servizi HA. Il tipo di entità
dipenderà dalla semantica verificata, non soltanto dall'etichetta nell'app.

I setter saranno allowlist esplicite per circuito e firmware; richiederanno
range, passo, prerequisiti e conferma verificati. Modalità condivise tra ACS e
direct saranno evidenziate. Nessuna modifica a protezioni native, parametri
installatore o bus sconosciuti solo perché compare un campo nel codice.

In caso di dati critici assenti, stato vecchio o comando incerto: fermare nuove
scritture, svuotare le code e notificare. Nessuna ripetizione cieca del boost ACS
o ripristino automatico di programmi vecchi. Controllo nativo sempre disponibile.

Prove e diff precederanno l'applicazione di ogni proposta. Il runtime finale
sarà deterministico, eseguito da HA senza REA, AI o computer di sviluppo.
