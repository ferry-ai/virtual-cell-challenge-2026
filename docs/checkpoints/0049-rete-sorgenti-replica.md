# CP-0049 — La replica conferma il guadagno neurale sotto soglia e il limite del condizionamento

- **Data:** 2026-09-29
- **Tipo:** osservazione
- **Redatto da:** Codex, sessione 01a0ee03-b357-7012-81a9-e8d7de767478
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

La seconda replica della rete che pesa le sorgenti raggiunge l'utilità minima
registrata e dimostra un beneficio del contesto basale rispetto alla rete cieca?

## 2. Cosa è stato fatto

Il kernel privato `davidmaisterx/vcc-lead-neural-seed1-r1` ha completato i cinque
fold C entro le 20:43:45 UTC. È la replica già avviata prima della lettura del
primo seme, con protocollo e split invariati. I risultati sono stati letti con
`read_neural_verified.py` e confrontati con il primo seme tramite
`compare_neural_seeds_r1.py`. Fonti e comandi sono nel
[report completo](../../reports/analisi/lead_scientist_2026-09-29/RISULTATI_NEURALE_SEED1.md).

## 3. Cosa si è osservato

**Misurato, proxy PDS e non VCC:** seme 1, rete meno trasferimento +0,00245854,
CI95 [+0,00068125;+0,00439651]. Rete meno cieca +0,00074226,
CI95 [−0,00004817;+0,00155537]. Entrambi i semi falliscono la soglia primaria
di +0,01: nessuna promozione. Fonti:
[verdetto](../../reports/analisi/lead_scientist_2026-09-29/kaggle_neural_seed1_r1/readout_verified_r1/verdict.json)
e [confronto dei semi](../../reports/analisi/lead_scientist_2026-09-29/neural_two_seeds_r1/comparison.json).

Le 6.144 coppie target–contesto, i 5.049 target distinti e gli assi dei due semi
coincidono. Il contributo pesato di RPE1 nel seme 1 è +0,00261512, superiore
all'intero incremento medio; le altre quattro famiglie insieme danno −0,00015658.
La perdita K562 e il beneficio CD4/iPSC/RPE1 si ripetono nei due semi.
La diagnostica cluster del seme 1, che conserva i target condivisi e ricalcola
i ranghi, lascia il CI contro rete cieca attraverso zero. Tabelle e limiti
sono nel report completo citato sopra.

## 4. Interpretazione e incertezza

**Interpretazione:** si replica un piccolo aggiustamento della miscela di sorgenti,
ma non un beneficio utile e robusto dimostrato del condizionamento implementato.
Non prova che la rete ignori materialmente ogni feature biologica o che nessuna
architettura neurale possa funzionare. Le famiglie hanno peso uguale; non si
sceglie RPE1 dopo il risultato. I CI sono condizionati alle predizioni e ai
contesti osservati, non coprono l'intero training o future famiglie cellulari.
Non si aggregano i due semi come repliche biologiche indipendenti.

## 5. Spiegazione semplice

La rete migliora leggermente la media, ma quasi tutto il vantaggio viene da una
famiglia. Conoscere il contesto non la rende stabilmente migliore della stessa
rete a cui quel contesto è nascosto. Completare il training non basta ad adottarla.

## 6. Conseguenze

Nessun fit di produzione, adattamento ai contesti ufficiali o correzione al t28
con questa rete. La replica prevista è conclusa. Stack resta un esperimento
distinto con protocollo A/B proprio; il generatore t28 conserva la sua regola.
Nuove architetture richiedono un'ipotesi distinta e un test prospettico.

## 7. Cosa corregge

Completa, senza contraddirlo, [CP-0048](0048-rete-sorgenti-primo-seme.md), che
aveva soltanto il primo seme. Precisa il campo `evidence_for_context_use=true`
nel verdetto del seme 1: significa punto positivo contro rete cieca, non CI
positivo né prova replicata. Il JSON originale resta immutato.

## 8. Domanda di comprensione

Perché un piccolo guadagno medio replicato sul trasferimento non dimostra da solo
che la rete sfrutti utilmente il contesto biologico?
