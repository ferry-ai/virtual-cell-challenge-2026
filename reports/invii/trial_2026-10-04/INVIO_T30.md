# t30 — registro dell'invio

Ibrido selettivo D-056: effetti t25 + w · R (protocollo `reports/modelli/ibrido_selettivo_2026-10-04/PROTOCOLLO.md`,
§13–§14). Previsione e regola in `reports/invii/prediction_t30_2026-10-04/prediction.json`, testi in
`submission_texts.md`, entrambi scritti prima della generazione.

## Cronologia (4/10, ora italiana, letta dal sistema o dai log)

- 10:06: effetti t25 rigenerati con lo stadio 100 (ricetta t25, cache r9) in `processed/effects_t25_regen_2026-10-04`.
  Lo sha256 `1d3e1dac…` è uguale a quello del manifest del t25, per A, B e C (`t25_regen_effects_manifest.json`).
- 10:07: emendamento §14 committato (`732a32b`), prima di ogni R su A/B/C.
- 10:11: prima esportazione (`export_abc_r1`). Si è fermata alla lettura dei controlli: l'indice dei geni del file
  ufficiale è un `nullable-string-array`. Non ha scritto uscite e la cartella è vuota.
- 10:14: seconda esportazione (`export_abc_r2`), con la lettura corretta tramite `cellnet.h5_column`; finita alle 10:30.
  Manifest in `t30_effects_manifest.json` e in `reports/modelli/ibrido_selettivo_2026-10-04/esito/export_abc_r2/`:
  - 230 bersagli corretti su 300: gli altri 70 sono senza righe CRISPRi di training, e 48 di loro anche nascosti;
  - w medio sui bersagli corretti 0,276 (A), 0,278 (B), 0,278 (C);
  - parità con w = 0 vera in ogni contesto;
  - RMS della correzione aggiunta sulle coppie osservate 0,019–0,026, contro 0,144 degli effetti t25.
- 10:30: generazione e pacchetto (`gen_t30.ps1`, processo Windows separato), con gli argomenti del t25 e i soli file
  degli effetti cambiati.

## Nota sulla provenienza dell'esportatore

La previsione registrata alle 08:14 UTC indica per `export_abc.py` lo sha256 `f91f27d5…`, la versione di quel momento.
Lo script usato, committato in `18407dc`, ha sha256 `269ea632b1980a195f9d3a78ceca77c3a2026252b10946d47e6cd9c63a0a2d13`.
L'unica differenza è la lettura dell'indice dei geni del file dei controlli, corretta dopo il fallimento di r1 e prima
di qualunque uscita. La previsione non è stata modificata.

## Diagnostica, misurata prima della generazione, senza effetto sulle regole

Su A la correzione è relativamente più grande che sulle linee valutate:
- RMS(R)/RMS(T) mediano e^−0,35 ≈ 0,70 contro e^−0,88…e^−1,43 ≈ 0,24–0,42 delle righe delle cinque linee;
- supporto mediano 5 gruppi contro 6–8;
- i pesi restano simili (mediana 0,27).
È un indizio di dominio diverso (controlli Flex dei contesti di gara), già fra i rischi della previsione.
