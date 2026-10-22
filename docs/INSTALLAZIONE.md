# Installazione da GitHub e prova

Il componente 0.5.0 è sperimentale: letture e controlli cloud; LAN in sola lettura. Non configura il gateway,
non recupera chiavi locali e non trasforma la password cloud in API key.
Per il cloud servono le credenziali della app DAIKIN Control. Le API LAN sono un percorso separato.

## HACS, repository personalizzato

Repository: https://github.com/MarlonMarketing/daikin-rocon-control

1. In una istanza Home Assistant di prova, aprire HACS e il menu dei repository
   personalizzati. Inserire l'URL indicato, categoria **Integration**.
2. Cercare **RoCon Daikin Control**, scaricare la versione disponibile e seguire la
   richiesta di riavvio di Home Assistant. Questo passaggio è manuale.
3. Aprire Impostazioni → Dispositivi e servizi → Aggiungi integrazione →
   **RoCon Daikin Control**. Scegliere Cloud, inserire username/password, scegliere l’impianto e l’abilitazione dei controlli. Per la modalità LAN servono IPv4 e API key locale esistente.
4. Un errore di connessione o autenticazione lascia il flusso aperto:
   non viene creata una integrazione con valori inventati.
5. Confrontare i sensori con il display del controller. Le letture provengono
   da una cache senza timestamp di misura. La freschezza del bus non è provata: progettare le automazioni soltanto con limiti e fallback verificati.

Questo è un repository personalizzato: non significa inclusione nel catalogo
predefinito HACS o supporto ufficiale Daikin.

## Installazione manuale alternativa

Scaricare il sorgente dalla release o da Code → Download ZIP su GitHub.
Copiare soltanto `custom_components/rocon_g1_local` in
`/config/custom_components/rocon_g1_local`, senza aggiungere un livello di
directory. Riavvio manuale e configurazione come sopra. APK, firmware e strumenti
di reverse engineering non sono necessari sul server Home Assistant.

## Interfaccia Climate Studio

Per il nuovo template unificato con configurazione facile e consumi, seguire
[RoCon Studio: installazione visuale](STUDIO.md). La scheda classica seguente resta disponibile.

L'integrazione serve il proprio file statico con il metodo asincrono HA.
Dopo che è stata caricata, aggiungere nelle risorse della dashboard:

- URL: `/rocon_g1_local/rocon-climate-card.js?v=0.4.0`
- Tipo: **JavaScript module**.

Nell'editor della dashboard aggiungere la scheda **RoCon Climate Studio**.
La configurazione minima, in formato JSON accettato dall'editor, è:

```json
{"type":"custom:rocon-climate-card"}
```

Riconosce automaticamente le entità dell'integrazione mediante attributi.
Se sono presenti più gateway, l'editor richiede di sceglierne uno, evitando di
mescolare i dati. Non contiene entity_id personali o indirizzi di rete.

È possibile usare la sola scheda con sensori già esistenti, selezionati
nell'editor visuale. In questo caso copiare il file
`custom_components/rocon_g1_local/frontend/rocon-climate-card.js` in
`/config/www/rocon-climate-card.js` e registrare la risorsa
`/local/rocon-climate-card.js?v=0.4.0`, tipo JavaScript module.
Le selezioni restano nella propria dashboard: non pubblicarle nel repository.
L'unità viene letta dal sensore scelto, senza conversioni implicite.

Sono disponibili **Panoramica**, **Impostazioni lette**, **Controlli cloud** e
**Diagnostica**. I controlli cloud usano le entità native Home Assistant. Alcune entità avanzate sono disabilitate di default: abilitarle singolarmente nelle impostazioni
dell'entità se servono. Non vengono attivati dalla scheda.

La [demo grafica](interface-preview.html) usa dati sintetici dichiarati e lo
stesso JavaScript. Gli stati simulabili includono assenza dati, indisponibilità,
sensori parziali e più gateway. La demo non è una verifica sull'impianto.

## Prove e rimozione

Verificare prima: configurazione rifiutata senza chiave corretta; letture valide;
assenza di segreti nei log; perdita rete con entità indisponibili; rimozione e
riconfigurazione; leggibilità della scheda su smartphone. L'assenza di un valore
mostra un trattino, mai uno zero sostitutivo.

Le GitHub Actions eseguono test offline, controllo JavaScript, HACS/hassfest e
test del flusso nel runtime HA con gateway simulato. I test runtime non provano
il firmware reale: controllarne l'esito nella scheda Actions del repository.

Per tornare indietro: rimuovere la scheda e la risorsa dalla dashboard,
rimuovere la config entry, poi il componente tramite HACS e riavviare
manualmente. Non viene modificata la configurazione del G1.

Fonti: [requisiti HACS](https://www.hacs.dev/docs/publish/integration/),
[risorse dashboard](https://www.home-assistant.io/dashboards/dashboards/#resources),
[registrazione statica asincrona](https://contributors.home-assistant.io/blog/2024/06/18/async_register_static_paths/).
