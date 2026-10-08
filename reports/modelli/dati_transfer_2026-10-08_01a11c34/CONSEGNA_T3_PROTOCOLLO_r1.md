# T3: protocollo congelato prima del fit — 9 ottobre, 00:11 CEST

**Stato: implementazione e preparazione, nessun fit T3 ancora lanciato.** Il vecchio
job T1 non verrà lanciato: la guardia di `quick_generation/r1` resta attiva.

Il mandato umano verificato nella chat Lead è il refit su tutte le fonti possibili
(`01a11d81-e023-7063-839d-b29d4a65e570`), in parallelo ai fit ESM2, con invio
entro le 02:00 e controlli essenziali (`01a11d78-c711-7cb1-9f28-fdcf26fbffa2`).
Lead ha assegnato a DATI il percorso fino al singolo invio del NUOVO candidato;
il suo launcher t37 resta bloccato. Non vi sono upload avviati da DATI.

Il contratto macchina è [protocol.json](extended_transfer/r1/protocol.json), SHA256
`ab0bf8946a3ed98d74bf9752af71073cf6c97eca87a9066bfe46ca9a0b780958`.
L'audit di metadata verificati trova 7 unità KO, 12 contesti, 5 gruppi studio/lignaggio,
34 bersagli distinti del pannello e 52 profili contesto-bersaglio. Sono necessari
22 chunk, 265.225.041 byte. Questo numero non conta tutti i bersagli derivati come
nuovi bersagli predetti; i 34 hanno già un riferimento CRISPRi.

## Politica fissata ex ante

Si ricostruisce T1 al byte come controllo. Il suo stimatore, i pesi CRISPRi e la
centratura sul pannello restano invariati. Per ogni KO si usano i contrasti shrunk
contro controlli abbinati, maschere e QC già applicati (almeno 10 cellule bersaglio,
identità singolo gene esatta); il segno dell'RNA del gene perturbato non è un gate KO.

I contesti dello stesso studio/lignaggio si mediano con affidabilità `n/(n+100)`;
l'affidabilità del voto unico è il massimo fra i contesti disponibili, non la somma.
Ogni gruppo KO pesa **0,25** nel numeratore e denominatore del transfer. È un prior
debole fissato per il meccanismo diverso, non una stima di efficacia o un peso
scelto cercando il migliore punteggio. Non si sottrae la media del pannello ai KO:
altrimenti STAT6, unico bersaglio Shifrut nel pannello, verrebbe annullato. Questo
espone al rischio di risposta comune KO, dichiarato e non risolto dal fit.

Ampiezza 1,576 e testa cis originale si applicano una sola volta, dopo la miscela;
emissione t36 invariata, scala 1,5, seed 20260912 e 400 cellule per bersaglio/contesto.
Non si eliminano KOLF o altre fonti CRISPRi sulla base del banco già osservato.

## Precedenti e controllo

S-010: niente voti nuovi per cloni o pseudo-repliche K562; S-011: il singleton KO
non viene centrato a zero; S-012: nessun riciclo della centratura T2; S-006: il
carico comune del KO resta un rischio, limitato da voti deboli fissati ex ante.
La parità T1, gli hash, gli assi, le maschere, SE finiti/non negativi e l'uso di tutti
i contesti KO previsti sono guardie obbligatorie. Il livello A di VALIDAZIONE può
segnalare un fallimento; non verranno ritoccati i pesi dopo i risultati.

## Limiti della copertura

Il ramo è CRISPRi+KO, non chiude D-053. CRISPRa richiede un modello distinto e non
un'inversione automatica; Datlinger ha mapping incompleto; HIPSCI genome-wide
non ha controlli adeguati; Papalexi non raggiunge l'eleggibilità del derivatore.
Tian2019 conserva la precedente esclusione di ammissione e il suo ruolo nelle viste
estese ESM2; le fonti senza overlap non generano voti stessi-bersagli. Gli assi
completi e i contesti restano nella banca e nei rami che possono consumarli.
H1 test resta protetta. Lettura dei file e contributo effettivo saranno distinti
nella ricevuta T3; questa nota non anticipa il successo del runtime o del modello.

Per VALIDAZIONE: fonti, contesti, chunk, pin e formula sono già nel protocollo;
le tabelle aggregate leggibili e la ricevuta arriveranno dal job privato T3.
