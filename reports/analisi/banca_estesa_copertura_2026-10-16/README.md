# Che cosa aggiunge la banca estesa di Davide per i bersagli del pannello (verifica prima del punto 2)

16 ottobre 2026. Claude Code per Alfredo, che ha approvato il «punto 2»: riaddestrare la rete ponte sulla banca estesa
di Davide. **Prima di investire** si è misurato quanto quella banca aggiunge per i 300 bersagli del pannello, per
stimare il tetto (criterio d'impatto minimo).

## Dati letti (dataset pubblici di Davide, scaricati il 16/10)

- **`davideferrante11/vcc-banca-canonica-derivati-r1`:** 13 studi, già ristretti ai bersagli del pannello; campi
  `raw`, `shrunk`, `se`, `n_cells` sui 18.533 geni ufficiali.
- **`davideferrante11/vcc-rs-bank-extra-70dc-r1`:** 82 file, 1,16 GB; tabelle a pezzi di HipSci targeted 19, Tian 2019
  iPSC/neurone, Tian 2021 CRISPRi, Xu 2023. Sono soltanto elencati, non scaricati.

## Misurato

**Bersagli del pannello coperti da ciascuno studio** (da `ammissione_r1.json` e dai file):

| Studio | Modalità | Bersagli del pannello |
|---|---|---|
| Replogle K562 GWPS (già nel cubo) | CRISPRi | 272 |
| A549 (Liu-Hillsley 2026) | KO | 21 |
| Sunshine 2023 (Calu-3) | KO | 6 |
| Tian 2021 | CRISPRi | 6 |
| Frangieh 2021 (melanoma) | KO | 5 |
| Xu 2023 (HEK293) | CRISPRi | 5 |
| HipSci targeted 19 | CRISPRi | 5 |
| Tian 2021 | CRISPRa | 4 |
| Norman 2019 | CRISPRa | 3 |
| Dixit 2016 | KO | 2 |
| Shifrut 2018, Tian 2019 iPSC, Tian 2019 neurone | KO / CRISPRi | 1 ciascuno |

**Correlazione delle direzioni sui fold a lignaggio escluso** (da
[rete_su_t3](../../modelli/rete_su_t3_2026-10-15/result_banco.json)):

| Coppia | Coseno mediano |
|---|---|
| T3 e transfer `all` del cubo | 0,64–0,71 |
| T3 e rete centrata | 0,48–0,56 |

## Che cosa se ne ricava (interpretazione)

1. **La banca estesa non porta linee nuove per il pannello.** Le linee principali (K562, CD4, H1, HCT116, HEK293T,
   HepG2, Jurkat, RPE1, iPSC/KOLF/HipSci, neurone) sono già nel cubo r2. Gli studi in più toccano circa 50 bersagli su
   300, ciascuno con una fonte piccola e spesso di un'altra modalità (KO, CRISPRa).
2. **Il tetto del punto 2, come era stato pensato, è piccolo.** Sul banco una linea sorgente in più vale circa +0,01 di
   coseno. Qui si applicherebbe a circa il 17% dei bersagli e con fonti parziali: circa +0,002 di coseno complessivo.
   Questa è una **stima**.
3. **Riaddestrare la rete sugli stessi ingressi di T3 potrebbe peggiorare la miscela.** La rete aiuta `ta 42` perché è
   meno correlata con T3 di quanto lo sia un transfer: 0,48–0,56 contro 0,64–0,71. Darle gli ingressi di T3 la
   avvicinerebbe a T3. Questa è un'**ipotesi**.
4. **Il vantaggio di T3 sul transfer del cubo** (indice PDS 0,355 contro 0,325 sui fold) viene dalla ricetta di stima
   di Davide, non da linee nuove. Fra gli ingredienti della ricetta: CD4 per donatore, varianti KOLF, termine cis, più
   geni coperti.

**Proposta:** non investire 2–3 giorni nel punto 2 così come era definito.
