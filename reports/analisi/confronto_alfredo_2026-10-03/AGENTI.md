# Revisioni esterne e verifica

3 ottobre 2026. Il proprietario ha autorizzato prima l'uso di Grok e Antigravity, poi esplicitamente il brief e la lettura delle fonti elencate, dopo il primo rifiuto del controllo automatico. Nessuna modifica ai permessi o alle credenziali.

Run hub `20261003-142026-alfredo-critique`, modalità `read`, stesso [brief](brief_antigravity.md). Rapporti integrali: [Grok](agenti/critica_grok.md), [Antigravity](agenti/critica_antigravity.md). Entrambi exit code 0. Modello non fissato nel lancio (`model: null` nei metadati), quindi non attribuisco un nome di modello non verificato. CLI: Grok 1.0.44, Antigravity 1.2.13. I metadati essenziali sono conservati accanto ai rapporti.

## Verifica del coordinatore

Accolti dopo verifica diretta nel codice, protocollo e JSON del pilot: distinzione π/responsabilità; fallimento del floor e del warmup nei nostri esperimenti; tre training r3 accettati, Q1 e Q3 passati ma Q2 fallito; necessità di distinguere linea e tipo cellulare; insufficienza del bootstrap dei target per stimare generalizzazione fra linee. Confermate sul testo ufficiale le regole relative ai dati sperimentali; il changelog sostiene l'invarianza della regola tra 0.16 e 0.18, che i revisori non avevano verificato online.

**Correzioni ad Antigravity:**

- «Non risolvibile con floor 0,05» e «π=1 unica salvaguardia adeguata» sono assoluti non dimostrati. Il floor non garantisce il recupero; π=1 ha funzionato tecnicamente in questi run. Altri obiettivi o schemi di ottimizzazione restano concepibili, senza essere già provati.
- Senza il codice di Alfredo non si può affermare che Strada C sia già dimostrata confusa o priva di controlli. Il report finale parla di rischi e requisiti da verificare.
- Il rapporto di somme è l'aggregazione corretta della MSE ufficiale, non un difetto in sé. I limiti riguardano incertezza, supporto e denominatore.
- Non adotto la proposta di chiudere l'intero adattamento contestuale sulla base di un confronto di studio o di alcune baseline negative. Non riallineo retroattivamente la soglia KOLF a quella H1.

**Correzioni a Grok:**

- L'apertura «Strada C non identifica un contesto nuovo né un MSE ufficiale» va resa condizionale: Alfredo dichiara lo scorer vero. Il codice del nostro `metrics.py` non dimostra quale metrica calcoli il suo kernel. Una linea interamente esclusa e sorgenti di altre linee possono costituire C; il confronto stessa-linea è una domanda diversa.
- Una macro che dà lo stesso peso alle linee non è automaticamente scorretta; è un estimando da dichiarare, da affiancare alla copertura e a un'incertezza coerente.
- Il report propone una decisione sul ponte Flex/3′ basata su 0,12 dopo averne contestato l'universalità. Non la adotto: soglia da motivare e fissare nel nuovo protocollo, senza convertirla in score VCC.
- Con ampiezza non negativa il coseno negativo non aiuta: il minimo è `1−max(c,0)^2`, non una condizione su `|c|` indiscriminatamente. Il [calcolo](calcoli_analitici.py) lo esplicita.
- Le citazioni di vecchi banchi e del memo MSE non sono state tutte rieseguite. Non le promuovo a nuove misure né riapro automaticamente il ponte Flex già studiato. L'incarico proposto resta prima Strada C, poi transfer/affidabilità e cis con contrasti separati.

## Grok: falso negativo del preflight

L'hub ha detto `missing / not logged in`, anche fuori dal sandbox. La configurazione `agents.toml` usa `grok models` come `auth_check` e cerca la sottostringa `not authenticated`; `hublib/doctor.py` controlla questa stringa prima del codice di uscita. **La richiesta reale a Grok è poi terminata con rapporto completo, exit code 0, in 440,7 s, senza login o modifiche alle credenziali.** Questo dimostra che il preflight non era una diagnosi affidabile dell'accesso al modello in questa sessione. Non ho isolato perché l'endpoint/comando dei modelli risponda diversamente: non attribuisco la causa a token scaduti, account o rete senza prova.

Non modificato l'hub, che vive fuori dalla repo e non appartiene a questo intervento. La lezione operativa è distinguere fallimento di `models` e fallimento della richiesta effettiva, senza chiedere automaticamente un nuovo login.

## Avviso di modifiche concorrenti

L'hub segnala per entrambi `git status changed during read mode`. Durante il run il Claude del training ha committato il protocollo e il codice delle miscele e creato l'analisi per strati; io ho creato questa cartella. L'avviso non dimostra scritture dei revisori. Le dichiarazioni dei due rapporti sono di sola lettura; non certifico l'attribuzione di ogni variazione da un semplice status. Ho preservato i file esterni al mio perimetro e non li includo nel commit.
