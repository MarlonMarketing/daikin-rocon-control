# Segnalazioni e dati privati

Non aprire issue pubbliche con password, cookie, API key, seriali, indirizzi,
installation ID, catture HAR/PCAP o risposte cloud integrali. Lo strumento salva
le risposte soltanto in `_private/`, esclusa da Git. Questo non rende sicuro
pubblicarne manualmente il contenuto.

La CLI diagnostica esegue soltanto login e letture. Il componente HA cloud 0.4.0
include setter espliciti: non esegue retry di scritture e non invia comandi
durante l’installazione. Leggere docs/CLOUD_CONTROL.md. I redirect HTTP sono rifiutati e TLS
cloud resta verificato. La CLI non salva sessioni o credenziali su disco.
Se configurata in HA, la password cloud (o API key per la LAN)
viene conservata nella config entry di Home Assistant: non esportare
pubblicamente la relativa storage o i backup.
Le risposte private possono comunque contenere informazioni personali.

Le API LAN candidate del G1 sono HTTP: l'API key transita in chiaro nella LAN.
Usarle soltanto con un gateway proprio e già configurato, su rete fidata.
Non esporre il gateway o la diagnostica a Internet. La password cloud non è
un'API key locale; questo progetto non crea utenti sul gateway.

Il futuro componente HA dovrà sospendere nuove scritture se mancano stato,
conferma o freschezza; nessun reset, aggiornamento firmware o bypass di accesso
è compreso nella diagnostica. Mantenere le protezioni native dell'impianto.
