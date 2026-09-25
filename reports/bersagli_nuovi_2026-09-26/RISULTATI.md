# Bersagli nuovi: che cosa predice un bersaglio che nessuna sorgente ha misurato

26 settembre 2026, notte. Il set finale porterà 300 bersagli nuovi. Qui i 300 bersagli del
pannello fanno da bersagli **nuovi**: nessun loro esito entra in un addestramento, in una base o
in un prior. **Proxy nello spazio degli effetti, non punteggi VCC.** Addestramento sulla cache
universo del K562 ([universo](../universo_2026-09-26/RISULTATI.md)): 9.594 bersagli fuori
pannello, 7.681 geni.

## Esecuzioni

- `linear_new_targets.py` → `r1/`: modello lineare di Ahlmann-Eltze et al. (Nature Methods
  2025; embedding dei geni dalla SVD, il bersaglio rappresentato dal proprio gene come lettura),
  modulo cis, associazione STRING (media degli effetti K562 dei partner fisici con punteggio
  ≥ 700 o ≥ 400), riferimento dello stesso bersaglio misurato in K562.
- `checks.py` → `r2/`: il modello lineare in campione; STRING pesato più cis, con la risposta
  comune `b` in ogni braccio.
- `checks_nob.py` → `r3/`: lo stesso confronto **senza** `b` in nessun braccio.

**Attenzione a r1:** il braccio `cis` non contiene `b`, mentre le braccia lineari e STRING sì;
`b` è uguale per tutti i bersagli e abbassa la discriminazione. I confronti fra `cis` e le altre
braccia di r1 sono falsati; quelli puliti sono in r3.

## Risultati

- **Il modello lineare non discrimina nemmeno i propri bersagli di addestramento** (r2): PDS
  proxy in campione 0,504, contro 0,992 della proiezione sulle stesse 50 componenti. Fuori
  campione resta a 0,49–0,51 (r1). È un limite del metodo in questa forma (la risposta del
  bersaglio come funzione lineare del suo embedding), non un errore di codice: la proiezione
  verifica che la base e i dati sono corretti.
- **Modulo cis da solo** (r3): PDS proxy 0,555 in K562, 0,571–0,579 in CD4, HCT116 e HEK293T.
- **STRING pesato poco più cis** (r3), 0,1 × STRING + cis contro cis:

| Sorgente tenuta fuori | cis | 0,1 × STRING + cis | differenza (IC 95%) |
|---|---|---|---|
| K562 (bersagli nuovi, contesto noto) | 0,555 | 0,590 | +0,035 (+0,005…+0,064) |
| CD4 | 0,579 | 0,611 | +0,032 (+0,005…+0,060) |
| HCT116 | 0,571 | 0,591 | +0,020 (−0,010…+0,047) |
| HEK293T | 0,570 | 0,579 | +0,009 (−0,019…+0,035) |

  Con pesi maggiori (0,25–2) il guadagno cala, e per HCT116 e HEK293T diventa una perdita.
- **Riferimento irraggiungibile per un bersaglio nuovo** (r1): l'effetto dello stesso bersaglio
  misurato in K562 dà 0,711–0,755 in CD4, HCT116 e HEK293T.

## Che cosa se ne ricava

- **Interpretazione:** per un bersaglio senza misure i segnali utili sono il meccanismo (cis) e
  la rete (partner fisici, pesati poco); insieme arrivano a circa 0,58–0,61, contro 0,71–0,75 di
  un bersaglio misurato. **La leva più grande per il set finale è la copertura:** estrarre tutti
  i bersagli delle sorgenti genome-scale (CD4, Orion), non solo i 300 di oggi.
- **Proposta:** per i bersagli del set finale che nessuna sorgente ha misurato, usare cis più
  0,1 × STRING; il peso va riconfermato sul banco con lo scorer vero (filone F2 di R-V2).

## Che cosa non si è fatto

Nessuna rete diversa da STRING fisico (GO, complessi, reti TF con segno sono in
`interim/encoder_inputs_2026-09-14/` e restano da provare); nessun peso STRING scelto fuori dai
bench qui usati; nessuna prova nel modello del generatore. I file STRING copiati in
`external/annotation/` sono identici byte per byte (sha256 `1ca87209…`) a quelli registrati in
`interim/encoder_inputs_2026-09-14/`.
