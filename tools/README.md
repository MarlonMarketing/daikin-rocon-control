# Strumenti di sviluppo

Il client Python non richiede REA, Java, Android SDK o un modello AI.
Questi strumenti servono soltanto per analizzare la propria copia dell'app.

La copia di lavoro può contenere REA 6.7.0 in `_private/tooling/node_modules/`,
JDK portatile in `_private/tooling/jdk21/` e JADX headless 0.7.1 nella stessa
directory. Sono esclusi dal repository e dall'archivio pubblico.

Per predisporre REA in una nuova copia, con una versione Node supportata:

```powershell
npm install --prefix _private/tooling --ignore-scripts --omit=optional --no-audit --no-fund --save-exact rea-agents@6.7.0
```

Per JADX seguire le [istruzioni REA Android](https://github.com/morluto/rea/blob/main/docs/android-analysis.md),
usando un JDK completo. Versione usata: jadx-headless-mcp 0.7.1;
SHA-256 del JAR verificato:
`6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75`.
Non eseguire APK, script o firmware estratti durante la sola analisi statica.

Acquisizione da un telefono proprio, con debug USB autorizzato:

```powershell
./tools/acquire_apk.ps1 -Serial SERIALE_DEL_PROPRIO_TELEFONO -AdbPath PERCORSO_ADB
```

Il seriale e i percorsi compaiono nell'evidenza privata, non nei documenti
pubblici. Non viene letta la directory dati dell'app. Non vengono avviate,
arrestate o reinstallate applicazioni.

`build_public.py` crea lo ZIP da una lista esplicita di directory/file pubblici.
Non sovrascrive un archivio già esistente: conservarlo o spostarlo prima di
generarne una nuova versione. La lista non è uno scanner di segreti: revisionare
sempre i sorgenti ammessi prima della pubblicazione.
