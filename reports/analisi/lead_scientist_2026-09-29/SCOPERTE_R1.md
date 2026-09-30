# Scoperte della sessione e conseguenze concrete

29 settembre 2026, prima dell'invio ufficiale t28. Fotografia delle scoperte
materiali, con collegamenti alle prove; non sostituisce i report originali.
Lo stato vivo resta in [PROGETTO](../../../docs/PROGETTO.md).
Un risultato locale non viene promosso qui a punteggio VCC.

| Scoperta e tipo di affermazione | Conseguenza pratica | Prova e limiti |
|---|---|---|
| **Verificato:** CD4 usa già GEMX Flex v1. La premessa che la ricetta avesse soltanto sorgenti 3′ era falsa. | Riformulare il ponte di piattaforma come problema di studio, stato e qualità delle stime; non aumentare automaticamente il peso CD4. | [Audit dati §1](AUDIT_DATI.md#1-correzione-decisiva-cd4-è-già-flex), tabella degli autori con SHA verificato. |
| **Misurato:** l'accordo CD4 fra stati degli stessi donatori supera molto quello fra metà disgiunte dei donatori nello stesso stato. Il mix modifica anche energia e peso di affidabilità. | Tenere fuori lo stesso donatore in tutti gli stati; distinguere stato biologico, numerosità, energia e dipendenza fra campioni. | [Audit dati §2](AUDIT_DATI.md#2-che-cosa-cambia-tra-gli-stati-cd4). Il basso accordo non prova da solo quale componente sia biologica o tecnica. |
| **Misurato:** basali su supporti genici diversi hanno scale e maschere diverse; rinormalizzare non ricrea geni non misurati. | Preservare maschere e denominatori espliciti. Non trattare gene assente come espressione zero. | [Audit dati §4](AUDIT_DATI.md#4-normalizzazione-difetto-misurato-senza-promessa-di-guadagno). Non implica un guadagno automatico della ricetta. |
| **Ricostruito:** medie ufficiali quasi ferme nascondono compensazioni fra membri; una coppia di semi non stima con precisione il rumore. | Leggere tutti i membri. Non dedurre saturazione dell'ampiezza o attribuzione causale da interventi che cambiano più fattori. | [Audit scientifico](AUDIT_SCIENTIFICO.md), 17 invii e otto contrasti, con fonti per campo. |
| **Misurato:** ampiezza e dispersione interagiscono. Una prova della dispersione soltanto all'ampiezza iniziale avrebbe perso il miglior braccio osservato. | Banco fattoriale, selezione su sviluppo, conferma su bersagli disgiunti; combinazione t28 registrata prima della generazione. | [Sviluppo](RISULTATI_GENERATORE_SVILUPPO.md), [conferma](RISULTATI_GENERATORE_CONFERMA.md). Non attribuire il risultato a un singolo fattore. |
| **Misurato sul banco:** t28 migliora la proiezione locale di +0,028918 su 96 bersagli e tre semi. Guadagna soprattutto fedeltà/reach; peggiora NMAE, Jaccard e MSE grezza. | Preparare il candidato e misurarlo nel servizio ufficiale; non presentarlo come miglioramento uniforme o +0,028918 atteso in gara. | [Conferma](RISULTATI_GENERATORE_CONFERMA.md), [registrazione t28](../../invii/prediction_t28_2026-09-29/prediction.json). Un contesto pubblico, sorgente K562 e controlli condivisi; la produzione usa quattro sorgenti. |
| **Misurato:** la rete che pesa le sorgenti guadagna +0,002222/+0,002459 nel proxy nei due semi, sotto +0,01. Il vantaggio rispetto alla rete cieca non è robusto. | Non adottare questa rete secondo il test registrato; conservare tutti i fold e i semi. | [Replica completa](RISULTATI_NEURALE_SEED1.md), [CP-0049](../../../docs/checkpoints/0049-rete-sorgenti-replica.md). Proxy di rango su effetti, non sei metriche su cellule. |
| **Revisione metodologica:** quel prescreen PDS non è una condizione necessaria dimostrata per migliorare il punteggio completo. | Proporre un esperimento distinto sul vero scorer con rete, rete cieca e baseline; non dichiarare superato retroattivamente il vecchio test. | [Audit del prescreen](neural/NN_PRESCREEN_AUDIT.md). Nuovo banco ancora da collegare e verificare; nessun nuovo beneficio misurato. |
| **Misurato:** il pilot Stack A perde; nelle cellule generate la componente specifica dei bersagli cala del 32,6%, mentre quella comune resta quasi invariata. | Non adottare A; indagare perdita di specificità e rappresentazione degli input. Evitare l'etichetta causale non dimostrata «stress universale». | [Risultato A](neural/RISULTATI_STACK_A.md), [diagnostica post hoc](neural/STACK_A_POSTHOC.md). Misura su predizioni finali, senza nuove verità perturbate. |
| **Misurato:** B recupera input presenti nei propri contesti, ma il suo confronto locale resta negativo (−0,128512; PDS −0,234848). | Nessuna evidenza per inserire B nel candidato. Completare la verifica formale A/B conservando il protocollo. | [Confronto B](neural/stack_b_scoring_r1/pilot_comparison.json), [protocollo](neural/PROTOCOLLO_STACK_AB.md). L'attestazione congiunta è ferma su una differenza di 11 ULP in un valore della baseline; [tentativo conservato](neural/stack_ab_selector_attempt1.json). |
| **Inventario misurato, test proposto:** una sorgente mirata già locale misura 358 geni dell'asse ufficiale, con molte guide per cellula. La vecchia soglia di correlazione fra metà non è un test di utilità predittiva. | Parser a blocchi e test implementati; protocollo con cellule, guide e canali separati. Nessuna adozione o nuovo fit ancora. | [Protocollo e inventario](same_context_predictive_r1/PROTOCOLLO.md). Copertura ridotta, confondimento fra guide, necessità di un prior esplicito e di una verifica indipendente. |
| **Verificato tecnicamente:** le cellule t28 rigenerate sono identiche byte per byte al primo tentativo perso; packaging e payload hanno passato la convalida remota. | Persistenza su Drive prima del packaging; invio dal file verificato senza seconda copia sul disco locale. | [Recupero](candidate_generation_remote/recovery_r2/RISULTATO_STAGE45_R2.md), [packaging](candidate_generation_remote/recovery_r2/pack_receipt/packaging.json), [percorso di invio](candidate_generation_remote/recovery_r2/INVIO_DIRETTO_G.md). Non prova accuratezza biologica o score ufficiale. |
| **Implementato e applicato:** gli errori operativi diventano incidenti con causa, fix, test e prova locale/remota. | Preflight obbligatorio sui nuovi job; 084 lo ha superato sul portatile e su Colab prima dello scoring. | [Guida](../../../docs/ERRORI.md), [registro](learning/README.md), [ricevuta remota](neural/stack_b_scoring_runtime_r1/preflight_runtime_receipt.json). Il controllo copre gli input dichiarati; serve comunque revisione del manifest. |

## Quanto credere ai numeri

I risultati pubblicati dal servizio VCC sono punteggi ufficiali dei singoli invii.
Le proiezioni dei banchi e il proxy neurale rispondono a domande diverse: non
devono essere messi nella stessa graduatoria numerica. Le direzioni degli effetti,
le maschere, i denominatori e le condizioni di confronto sono parte della misura.

La previsione registrata **0,155** per t28, con banda **0,135–0,180**, è
esplicitamente soggettiva e non calibrata; non è un intervallo di confidenza né
una prova di competitività. L'intervallo sul banco di 96 bersagli riguarda quel
banco e non copre il passaggio ai contesti ufficiali. L'invio ufficiale è la
verifica ancora necessaria.

Alla domanda del proprietario sulla credibilità è stato avviato un ulteriore
audit indipendente della catena di score e dei bias di selezione dei dati.
Le sue conclusioni non sono anticipate in questa fotografia. Nuove prove e
correzioni lasceranno un nuovo report, senza riscrivere i risultati precedenti.
