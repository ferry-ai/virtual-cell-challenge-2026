# R-REV — verifiche residue della revisione critica

- **Stato:** aperto; alcune azioni concluse, residui distinti sotto.
- **Aggiornato:** rinnovo del 1 ottobre 2026, dopo t29.
- **Assegnazione:** precedenti sessioni Claude `f4f38e58` e `f2abd9a6`; ripresa non avviata.
  Il proprietario conferma gli agenti fermi. Registrare la nuova sottoattività prima di eseguirla.
- **Prossimo passo:** preflight della prova a forma piena (3), indipendente dalla rete;
  raccordare 4/5 a R-LEAD senza ripetere le azioni concluse.
- **Dipendenze:** [PROCEDURE §7](../PROCEDURE.md#7-il-set-finale-22-ottobre), dati e risorse
  effettivi; [R-LEAD](strategia-scientifica.md) per ogni nuovo confronto neurale.
- **Evidenza iniziale:** [revisione del 28/09](../../reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md).

## Azioni: esito, residuo, condizione di avanzamento

| Azione | Stato verificabile | Prossimo passo o chiusura |
|---|---|---|
| 0. Portare la revisione in main | Eseguito il 28/09, cronologia nello storico | Non ripetere merge/stash del vecchio incarico. La divergenza remota si misura oggi, non si copia da una nota |
| 1. Recuperare evidenza mancante | Quattro voci recuperate; resta la preregistrazione t21 citata ma assente, [R-020](../REGISTRO.md#r-020--evidenza-citata-ma-assente-dal-repository) | Documentare l'assenza se non si trova; non inventare una previsione retroattiva |
| 2. Proxy contro ufficiale | Conclusa, [CP-0041](../checkpoints/0041-proxy-contro-ufficiale.md) | Il proxy non promuove candidati da solo |
| 3. Prova generale finale | Forma ridotta valida, [CP-0044](../checkpoints/0044-prova-generale-22-ottobre.md); difetti e correzioni nel [report](../../reports/invii/prova_generale_2026-09-28/RISULTATI.md) | Verificare difetti residui e risorse attuali, poi forma piena in output nuovo; niente invio implicito |
| 4. Banco K562 a sei membri | [Protocollo e bracci](../../reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/RISULTATI.md), nessun esito del job registrato | Preflight e confronto transfer/emissione con le esclusioni dichiarate. `g0:` è già disponibile nello stadio 73; verificare codice e test, non reimplementarlo dalla vecchia consegna |
| 5. Basali sull'asse comune | [Protocollo](../../reports/sorgenti/basali_asse_2026-09-29/), nessun esito registrato | Misurare denominatori e impatto sui lettori che li usano; riscalare non recupera geni non misurati |
| 6. Rete relazionale | Misura conclusa, [CP-0043](../checkpoints/0043-misura-decisiva-relazioni.md); candidato non avviato per la regola | Non riaperta dal fallimento di un'altra rete |
| 7. Stessa linea e Orion | Uso Orion autorizzato dal proprietario; identità private e verifica esterna distinte | Chiarire la decisione pertinente prima di nuovi usi; nessun contatto con organizzatori implicito |
| 8. Portare ricerca in libreria | Proposta subordinata a un componente adottato | Parità e test prima del trasferimento; non migrare in blocco codice sperimentale |

Il banco K562 dichiara anche un prior cis proveniente da target K562 fuori pannello:
conservare questa limitazione. R2/r3 hanno visto K562 in training; il banco non prova
generalizzazione di quelle reti a un contesto mai visto. Un nuovo protocollo richiede
esclusioni coerenti di tutti i componenti (R-LEAD P1).

## Criterio di chiusura e alternative

Ogni azione termina con evidenza, esito e limite; gli esiti negativi sono chiusure valide.
La prova a forma piena richiede un pacchetto verificato. Un input mancante si registra con
il passo impedito, aggiornando i residui senza ripetere il lavoro concluso.

[Mandato, assegnazioni e cronologia completa](../storico/rinnovo_2026-10-01/docs/piani/revisione-critica.md).
