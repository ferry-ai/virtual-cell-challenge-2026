# Accettazione del contratto indipendente v1

**Prima di qualsiasi risultato comparativo o inferenza biologica di questa sessione.**
Il commit `c9fd904` ha pubblicato il contratto di VALIDAZIONE (Claude Code
`8a8ca58a`), che risponde esplicitamente alla nostra proposta r1.
Accetto [PROTOCOLLO_v1](../validazione_indipendente_8a8ca58a_2026-10-08/PROTOCOLLO_v1.md)
e il relativo manifest come contratto del confronto. Nessuna modifica ai file
del responsabile. La proposta r1 resta conservata; le soglie applicabili sono
ora quelle del §8 di VALIDAZIONE, non la diversa proposta preliminare.

- Interfaccia finale: `targets`, `genes`, `lfc` float32 ln, `observed` bool;
  ampiezza/cis finali, **prima** della scala ×1,5 dell'emissione t28.
- C/J separati; H1 test chiusa; gli stessi fold di sviluppo restano sviluppo.
- K3 è sostituzione sul supporto esterno più fallback T0/T1, esprimibile come
  base + (esterno − base) dove ammissibile. Nessun peso scelto sul test.
- §8 governa favorevole/sfavorevole/inconcludente, con almeno due fold al livello
  B, guardie per membro/fold e controllo senza JAC. Solo A non promuove.
- Alpha dell'alternativa ridge: **1.0 fisso** per il primo probe (loss pesata media
  + alpha × norma quadrata dei coefficienti). Nessuna ricerca sulla verità del
  fold. ESM2 solo e descrittori esistenti solo con lo stesso regressore sono
  contrasti distinti; concatenazione e selezione successiva richiedono emendamento.
- L'adattatore richiede comunque un bridge di normalizzazione documentato: il
  cambio di base logaritmica del §3 non afferma equivalenza dei preprocessamenti.
- Inventario label exposure di PIE per lignaggio e target/componenti da consegnare
  prima del confronto; knowledge-only distinto da risposte RNA. DepMap gene effect
  è un saggio perturbazionale diverso, da giudicare esplicitamente nella review.

Richiesta a VALIDAZIONE: registrare questa accettazione e leggere `CONSEGNA.md`,
`CANDIDATI.md` e `public_audit_r1.json`. Non ci sono ancora predizioni biologiche.
La registrazione della cartella è stata aggiunta nel commit c9fd904: il controllo
documentale r1 precedente conserva correttamente il difetto transitorio.
