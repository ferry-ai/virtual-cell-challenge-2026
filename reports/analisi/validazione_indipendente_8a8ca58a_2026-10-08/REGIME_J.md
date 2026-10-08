# Regime J: la base di confronto del transfer sui bersagli nascosti

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). **Piano scritto prima dei numeri di questa corsa**: vale
l'ora del commit che contiene questo file; la corsa r4 del livello A parte dopo. È una misura **descrittiva**: non
valuta un candidato e non ha una regola di adozione. Serve a due cose: avere, già misurata, la base contro cui si
leggerà un candidato che generalizza sui bersagli (componente esterna, descrittori), e provare che il banco
nasconde davvero i bersagli prima di ogni statistica.

## Che cosa si esegue

Per ognuno dei sei fold C del [manifest v2](manifest_fold_v2.json), il fold J corrispondente: stesso lignaggio
escluso, e in più i **66 bersagli del pannello del gruppo 0** (`sha256(simbolo) mod 5 = 0`) tolti da **ogni**
tabella prima che lo stadio 100 la legga. Il banco scrive copie filtrate delle tabelle (righe dei bersagli nascosti
eliminate), quindi anche la media comune di ogni fonte è calcolata senza di loro. Bracci T0, R1, T1, P4.

Un transfer dello stesso bersaglio non ha voti per un bersaglio nascosto: la sua previsione è la sola testa cis
(coppie di K562, bersagli del pannello già esclusi dalla stima). È il ripiego dichiarato nel contratto.

## Come si legge

- Bersagli valutati: i nascosti che hanno una riga nella verità primaria del fold, **anche se nessun braccio li
  prevede** (previsione mancante = previsione nulla). I geni del rango vengono dalla sola verità, una per tutti i
  bracci.
- Si riportano: quanti bersagli nascosti ricevono una previsione (quelli con un vicino cis), `disc95` e le altre
  misure; attesa scritta ora: `disc95` vicino a 0,5, perché una testa cis non distingue i bersagli se non per i
  pochi geni vicini, e nessuna differenza fra T0, T1, R1 e P4, che in J hanno la stessa testa cis.
- Controllo della ricevuta: per ogni tabella filtrata, righe prima e righe nascoste tolte; lo stadio 100 deve aver
  letto esattamente le copie filtrate.

**Precedenti:** S-001, S-002, S-006 (reti senza discriminazione): in J la base da battere è questa, non il transfer
in C; ERRORI, «chiamare baseline generica un ingresso non addestrato». **Segnale precoce e arresto:** una tabella
filtrata con un bersaglio nascosto, o una differenza fra i bracci in J, invalida la corsa.
