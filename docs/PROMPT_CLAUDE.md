# Prompt per Claude — generalizzazione a contesti nuovi

Incollare il testo sotto nella sessione che lavorerà sulla repo. La specifica completa
è la scheda R-LEAD corrente: questo prompt non è un piano alternativo.

---

Implementa `docs/piani/strategia-scientifica.md` (R-LEAD), con i mandati correnti registrati.
La domanda iniziale è: dai soli controlli di una linea mai vista perturbata sappiamo
imparare una correzione della risposta che migliori il transfer? Il primo obiettivo è
costruire questa prova; la riparazione completa di cellnet non deve precederla.

Leggi prima `CLAUDE.md`, `docs/PROGETTO.md` §0, `docs/PIANI.md` §2–3 e R-LEAD.
Applica il mandato non negoziabile D-053 di `docs/GENERALIZZAZIONE.md` §2.1: tutte le linee
e i contesti idonei, campionamento senza omissioni silenziose, riconciliazione del catalogo
e verifica dell'uso effettivo. Un pilot su poche linee resta intermedio; le esclusioni di
validazione e le riserve protette non si aggirano per ottenere copertura.
Segui le letture per compito e le guide di cartella. Registra sessione, macchina, commit,
file e nuove destinazioni; Claude e teammate erano fermi al rinnovo, verifica eventuali
cambiamenti successivi rilevanti. Su altra macchina usa `docs/CONSEGNA_TEAMMATE.md`.

Esegui P0/P1: inventario verificabile dei collegamenti contesto–bersaglio–studio,
esposizione reale, controlli, split per linee intere e storia delle riserve. Poi implementa
il banco P2, congela la regola prima dei nuovi risultati e realizza il confronto P3:
transfer, generico addestrato, modello del bersaglio senza contesto e correzione semplice
condizionata. Misura C e J separatamente; T resta diagnostico. Verifica il contributo del
contesto all'effetto mantenendo veri basale e generatore nelle ablation previste dal piano.

La prima consegna deve includere codice eseguibile e test, manifest e protocollo;
anche misure se gli input sono disponibili. Non limitarti a un altro documento di proposte.
Se il banco è fattibile, prosegui alle decisioni e alle fasi condizionate secondo R-LEAD.
Se manca un input, completa il lavoro indipendente e indica file minimo e passo impedito.

HepG2 già esaminata resta sviluppo; K562 vista da r2/r3 non è un loro contesto nuovo;
H1 train/val sono nel corpus e H1 test resta chiusa. Applica esclusioni globali anche a
transfer, cache e pretraining. Non confondere uno split di cellule con nuove linee.
Conserva originali e report, usa copie e output nuovi. Il quarto training non riparte
automaticamente e il collasso identity di r3 non spiega da solo il t29 r2 desc.

Confronta la catena sui sei membri con supporti e generatori comuni. Una loss minore o
un guadagno T non promuovono per il 2026. Una rete P4 richiede un'ipotesi verificabile;
non richiede che il bilineare abbia vinto, ma neppure nasce automaticamente se perde.
Conferma secondo P5 e prepara la forma piena P6 anche se resta il transfer.

Download, quota cloud, nuovi agenti, invii e push seguono CLAUDE.md e le autorizzazioni
della chat. Consegna commit locali, test/log, misure e decisione secondo la regola;
aggiorna scheda, indici e registro distinguendo implementato, eseguito, misurato e adottato.
