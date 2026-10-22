# Protocollo osservato, non API ufficiale

Fonte primaria: analisi statica dell'APK `de.rotex.DAIKINControl` 1.5.13 (47),
acquisito da un dispositivo autorizzato. Base APK SHA-256:
`c49f3b3064f8ce2a3764cf6ac3169123726ffdb7e5f688cc13de387ac0c4acfc`.
Firma APK verificata con Android apksigner, schemi v1/v2/v3. Certificato firmatario
SHA-256 `4099253a0636045ad1905bbc238aa46524e42f282f5c60755e98f91df1d337ba`.
La fingerprint non è stata confrontata con una fingerprint pubblicata dal produttore.

## Cloud

Origine fissa: `https://api.rotex-control.com`; header `X-Api-Version: 6`;
cookie sessione `connect.sid`. Login JSON con username, password e
`deviceInformation` (appVersion, deviceName, systemVersion, language, country).

| Metodo | Percorso | Funzione |
| --- | --- | --- |
| POST | `/login` | Autenticazione, nessun setpoint |
| GET | `/mobile/installation` | Impianti dell'utente |
| GET | `/mobile/heatingcircuit?installationId=...` | Circuiti di un impianto |
| GET | `/mobile/heatingcircuit/{id}` | Dettaglio di un circuito |
| PUT | `/mobile/heatingcircuit/{id}` | Scrittura individuata nel codice; NON implementata nel client diagnostico |

Il formato lista atteso dal client è un array JSON; strutture diverse vengono
rifiutate in attesa di verificarle, non reinterpretate automaticamente.

## Parametri ricostruiti

| Funzione | Campo | Evidenza e limite |
| --- | --- | --- |
| Nome | `name` | Metadato aggiornato solo se cambiato dall'utente |
| Tre temperature profilo | `setTemperature.1`, `.2`, `.3` | UI ACS 10–70 °C; riscaldamento 5–40 °C; picker 0,5 °C |
| Ridotta riscaldamento | `setbackTemperatureHeating` | UI non-water 5–40 °C, passo 0,5 °C |
| Assenza | `setbackTemperatureAbsence` | UI non-water 5–40 °C, passo 0,5 °C |
| Programmi 1 e 2 | `timeProgram.1`, `.2` | Giorni monday...sunday, tre intervalli, start/end, passo UI 15 minuti e fine 24:00 |
| Modalità | `operationMode.type` | Standby 1, heating 3, reduced 4, summer 5, auto1 11, auto2 12, cooling 17 |
| ACS una tantum | `onetimeHeatupActive` | Setter APK produce stringa true/false; non assumere booleano JSON |
| Party | `operationMode.party.hours` | UI 0–6 ore, ma catena codice invia 0–360 minuti; nome campo ingannevole |
| Vacanze | `operationMode.holiday.beginning/ending` | day/month/year a due cifre; fine UI inclusiva → fine trasmessa giorno successivo |
| Rapida temperatura | Modifica profilo attuale/ridotta secondo modalità | ACS minimo slider 35 se heatingGeneratorType=0, altrimenti 10; massimo 70; slider intero |

I range sono quelli dell'app, non limiti di sicurezza approvati per una macchina.
Cooling è mostrato quando softwareNumber > 399 oppure heatingGeneratorType=0.
201/202 sono identificatori UI Party/vacanze: non sono normali valori da inviare
a `operationMode.type.set`.

Il circuito water inoltra modalità/Party/vacanze al circuito direct tramite
`getProxyCircuit`; ACS e riscaldamento non sono quindi indipendenti per tutte
le funzioni. Il boost ACS usa water. I profili 1/2/3 possono influenzare più fasce.

Il serializer invia un oggetto circuito ampio e oggetti `{set, confirmed}`;
supporto di PATCH/PUT parziali non verificato. In lettura anche `setDate` e
`confirmedDate` partecipano alla scelta del valore. Non considerare un HTTP 200
come conferma dell'applicazione fisica.

`setLeadTemperature`, `boilerSetTemperature` e `outsideTemperature` compaiono
nel serializer, ma la presenza nel payload non autorizza a esporli come setter.
Non è stata trovata una UI di modifica per curva climatica, isteresi, parametri
installatore, disinfezione o pompe/valvole nelle classi esaminate. Non è prova
che il firmware non li possieda.

## LAN

Una ricerca indipendente documenta API G1 candidate `/api/status/direct` e
`/api/status/water` con query `apiKey`. Il lettore sperimentale usa solo queste
letture su un IPv4 privato esplicito. Richiede una chiave già disponibile:
non attiva utenti o chiavi, non modifica il gateway, non esegue firmware.
Il percorso LAN non è stato verificato su questo impianto.

## Evidenze riproducibili

Classi APK: ApiConfig, ApiUtil, RestManager, SessionManager,
ControlResponseHelper, AuthenticationHandler, HeatingCircuitHandler,
HeatingCircuitJsonMapper, ConfirmedValueMapper, ConfirmedValueModel,
HeatingCircuitModel, SettingsModelMapper, SettingsNumberPickerDialogFragment,
ControlActivity, ControlFragment, PartyModeDialogFragment, TimePickerDialogFragment.
Risorse: res/values/arrays.xml e strings.xml.

Sono indicazioni per analizzare la propria copia dell'app. Le classi decompilate
e i binari proprietari non sono inclusi nei sorgenti pubblici.

Fonti esterne:

- [REA](https://github.com/morluto/rea)
- [App ufficiale](https://play.google.com/store/apps/details?id=de.rotex.DAIKINControl)
- [Ricerca G1 locale](https://github.com/bikeshedder/thermagate/blob/main/docs/ROTEX_RoCon_G1_Gateway.md)
- [Client cloud di confronto](https://github.com/trama2000/homebridge-rotex-control)
- [Bridge CAN da valutare separatamente](https://github.com/DoctaShizzle/rotex-rocon2mqtt)
