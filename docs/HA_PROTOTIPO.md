# Prototipo Home Assistant locale

Sorgenti: `custom_components/rocon_g1_local/`.
Non installato nell'istanza dell'utente e non verificato nel runtime HA.
Adattatore e normalizzazione sono testati offline con risposte simulate.

## Capacità

- Configurazione da UI con IPv4 privato e API key locale già disponibile.
- Primo controllo connessione obbligatorio, gestione errore credenziali,
  riconfigurazione e rimozione dell'integrazione.
- Solo GET su /api, /api/status e /api/setting; niente cloud o fallback cloud.
- Scoperta direct/water/HC1...HC16, ignorando URL arbitrari restituiti dal server.
- Sensori temperatura e cache impostazioni/programmi; dati assenti restano
  indisponibili e sentinelle room -60/-40/0 non diventano misure reali.
- Impostazioni e codici errore sono disabilitati di default. Zero nel codice
  errore legacy può essere un fallback e non dimostra assenza guasti.
- Polling iniziale 60 secondi, HTTP timeout 8 secondi per chiamata e budget di
  avvio nuove richieste di 30 secondi per snapshot. Nessun retry di scritture.
- La UI evidenzia letture dalla cache; non c'è un timestamp misura fornito
  dall'API. Queste letture non abilitano setpoint automatici.

## Limiti attuali

Nessun controllo climate/water_heater/number/select, setter o servizio.
Non copre tutte le 243 definizioni del registro CAN: le viste API disponibili
sono più ristrette. Per dati completi serve verificare l'export locale o un bridge.
Non supporta hostname, IPv6, porta personalizzata o HTTPS nella prima versione.
La verifica sintassi Python/JSON non equivale a un test end-to-end sul G1.
La versione 0.3.0 aggiunge HACS, una scheda Lovelace e GitHub Actions per
hassfest/HACS e flusso di configurazione nel runtime HA con gateway simulato.
L'esito dei job è consultabile nella scheda Actions: la presenza del workflow
non costituisce un risultato passato. Vedere [installazione](INSTALLAZIONE.md).

## Prova prevista, non eseguita

Prima ottenere una risposta API valida dal proprio G1 e confrontarla con app
e display. Poi, in una istanza HA di test separata, predisporre la cartella
custom_components/rocon_g1_local e verificare flusso configurazione, sensori,
credenziali errate, perdita rete, riconfigurazione e unload. Il progetto corrente
non applica questa installazione o riavvii all'istanza in uso.

Verificare che nessun identificativo o chiave compaia nei registri, che ogni
richiesta sia GET e che i sensori non suggeriscano conferma o freschezza del bus.
Mostrare diff e piano di test prima di passare a una installazione approvata.

Implementazione basata sulle API documentate di Home Assistant per
[coordinator](https://developers.home-assistant.io/docs/integration_fetching_data/),
[config flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
e [runtime_data](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/runtime-data/).
