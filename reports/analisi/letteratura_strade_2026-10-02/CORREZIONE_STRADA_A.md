# Correzione alla strada 1 (A): il doppio momento onesto non porta la MSE sopra zero

2 ottobre 2026, 23:40 CEST, stessa sessione. Il [README](README.md) di questa cartella non si riscrive: questa pagina
lo corregge.

## Che cosa diceva il README

Nella tabella del §5, la strada 1 stimava da +0,02 a +0,05 sulla media: la MSE scalata passava da 0 a 0,1–0,3
abbassando l'ampiezza del solo momento aggregato.

## Perché è sbagliato (evidenza già nel repository, non letta prima di scrivere)

[La risposta comune, r2](../../trasferimento/risposta_comune_2026-09-26/RISULTATI.md) ha misurato due cose.
- **Le nostre previsioni sono quasi ortogonali agli effetti veri** nello spazio della MSE. La MSE grezza ufficiale di
  sei invii segue 1 + E/4786, con E l'energia prevista e scarto massimo 0,048: il termine incrociato fra
  previsione e verità è trascurabile.
- **Lo zero ufficiale della MSE scalata** cade a un grezzo di 0,986–0,992.

Abbassare l'ampiezza del momento aggregato porta quindi la MSE grezza verso 1, cioè «come il controllo». Resta sopra
lo zero ufficiale: lo scalato resta 0. Per scendere sotto serve un coseno aggregato con la verità di almeno 0,12
circa (stima di claude2 citata in quel report); il nostro è vicino a 0.

## Da dove vengono allora le MSE dei primi (interpretazione)

Il codice dello scorer descrive un «layout exploit» sulla correzione del rumore di campionamento del pseudobulk. È
misurato dagli organizzatori:
- fino a 0,9121 dell'intervallo del membro sul pannello val A;
- una sottomissione sulla classifica di sviluppo ne ha preso +0,1389 su 0,2295 di media, prima della correzione
  #348.

Si veda il [confronto 0.16–0.18](../../gara/scorer_0_18_2026-10-02/README.md). Le descrizioni pubbliche con «carriers»
e «sampling-refund ratio portato a 0,95» puntano lì. È plausibile che buona parte delle MSE positive in classifica
venga da questa leva e non da previsioni migliori. Non è verificato entrata per entrata.

## Che cosa cambia

- **La strada 1 come leva sulla MSE cade.**
  - La forma onesta vale circa 0 finché la direzione resta quasi ortogonale.
  - La forma che sfrutta la correzione resta esclusa (README, §6), ed è quella che la regola 4 degli organizzatori
    chiuderà.
- **La MSE si sblocca solo migliorando la direzione** del profilo aggregato, cioè con la strada B (accordo fra
  sorgenti, modo comune, legge cis) o con dati più vicini al contesto. Il predittore locale 1 + E/4786, con il termine
  incrociato, misura ogni candidato.
- **L'emissione resta una leva sui quattro membri DE,** come ha mostrato il t28 (fedeltà e reach su, nMAE e Jaccard
  giù), non sulla MSE.
- **La priorità diventa:** strada B prima; l'emissione solo come rifinitura dei membri DE.
