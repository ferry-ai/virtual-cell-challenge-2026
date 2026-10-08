# Risultati del livello A: transfer a lignaggio escluso, spazio degli effetti

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). Tutto **misurato** oggi, su Kaggle CPU, con il banco di
[banco/](banco/); letto con il [contratto v2](PROTOCOLLO_v2.md). Le tabelle sono scritte dal lettore, non
ricopiate: [livello A, v2](TABELLE_LIVELLO_A_r1_v2.md) ([lettura v1](TABELLE_LIVELLO_A_r1.md)),
[scomposizione di K0](TABELLE_SCOMPOSIZIONE_K0_r2.md).

**Che cosa sono questi numeri.** Proxy nello spazio degli effetti: la previsione dello stadio 100, ottenuta senza
nessuna tabella del lignaggio escluso, contro la tabella di effetti di quel lignaggio. **Non sono punteggi VCC** e
non vedono il generatore. I sei lignaggi sono fonti di ogni ricetta: è un banco di **sviluppo**. Gli intervalli
ricampionano i bersagli dentro i contesti osservati; non coprono l'incertezza su contesti nuovi.

## 1. Esecuzioni

| Corsa | Kernel | Che cosa | Verifica |
|---|---|---|---|
| r1, 18:25–18:34 | `davideferrante11/vcc-validazione-logo-8a8ca58a-r1` | bracci T0, R1, T1, P4 e controlli; 42 esecuzioni dello stadio 100 | codice salvato = pacchetto; parità di T0, R1, T1; [consumo](banco/r1/completion/consumption.json) |
| r2, 19:04–19:10 | `davideferrante11/vcc-validazione-logo-8a8ca58a-r2` | gli stessi più P4k e P4kh, [piano scritto prima](SCOMPOSIZIONE_K0.md) | parità; K0 e K1 identici a r1 numero per numero; Q1 + Q2 + Q3 = K0 |

## 2. La baseline e il banco sono riproducibili (misurato)

- Rieseguendo lo stadio 100 dalle fonti trovate **per contenuto**, gli effetti di produzione hanno lo sha256
  registrato di t36 (`08fdfd28…`), di r1 (`d7a8cb14…`) e di T1 (`28f15de7…`); la ricetta ricostruita ha lo sha256
  della ricetta inviata (`3109a6d9…`). Il fit di T1 di DATI-TRANSFER è quindi riprodotto in modo indipendente.
- In 42 esecuzioni su 42 i file letti dallo stadio 100 sono esattamente le fonti ammesse; nessuna tabella del
  lignaggio escluso.
- La suite della repo con l'interprete del progetto dà 289 test superati su 290 e i tre test dello scorer passano
  (`cell-eval2` 0.16.0): il blocco segnalato nel piano lead riguarda l'interprete di quella sessione, non il
  runtime. L'unico fallimento è il controllo dei documenti, che conta come «non coperti» i file che un'altra
  sessione crea mentre gira ([verifiche](verifiche/tests_r1.txt)).

## 3. Il banco vede la specificità? (controlli)

| Controllo | Esito |
|---|---|
| Bersagli permutati | `disc95` di T0 fra 0,56 e 0,97 secondo il fold; permutato 0,47–0,54; differenza risolta su sei fold su sei. Con `disc` (v1) fallisce su C-K562: un solo gene comune ai 272 bersagli |
| Previsione nulla, sola media | `disc` = 0,500; la sola media ha quota comune 1 e nessuna correlazione specifica |
| Senza sottrazione comune (gamma 0) | togliere la risposta comune dà `disc95` +0,008 (risolto) ma **toglie** accordo di segno nei primi 50 geni (−0,018, risolto) e peggiora l'errore sui geni confidenti; l'errore quadratico migliora. La centratura è un compromesso, non un guadagno netto |
| Senza testa cis | la testa cis dà `disc95` +0,003 (risolto), anche sui fold che non l'hanno stimata |
| Ampiezza | l'errore quadratico della previsione supera quello della previsione nulla in tutti i fold (rapporto 1,14–2,29) e l'ampiezza che lo minimizza è 0,01–0,17 contro 1 della previsione. Coerente con il membro MSE ufficiale fermo a zero; non è un contrasto fra bracci |

## 4. K1: T1 contro t36, la banca ampliata a modello invariato

Cambiano 10–16 bersagli per fold (2 su 17 in C-H1). Sulle misure primarie:

- `disc95`: nessun fold risolto, macro **+0,0004 [−0,0005; +0,0013]**;
- `r_spec`: macro −0,0003 [−0,0007; +0,0000]; risolto negativo solo in C-H1 (−0,0019, due bersagli);
- secondarie: l'errore quadratico scende ovunque (macro −0,0045, risolto) perché i voti aggiunti contraggono
  l'ampiezza; `nmae_conf` migliora in C-CD4T e peggiora in C-K562.

**Lettura del §8:** nessun arresto dal livello A, e il livello A non promuove. R1 (la release r1 intera) si legge
allo stesso modo: differisce da T1 solo per RFK.

**Interpretazione.** T1 è indistinguibile da t36 nello spazio degli effetti. Tre dei suoi quattro tipi di voto
nuovo arrivano da tabelle di 5–6 bersagli, che la centratura sul pannello distorce
([audit](AUDIT_DATI_E_LEAKAGE.md), §2), e 10 dei 16 voti raddoppiano un lignaggio che votava già.

## 5. K0: t36 contro le quattro linee, e la sua scomposizione

K0 = T0 − P4 sulle stesse tabelle: macro `disc95` −0,008 [−0,018; +0,003], `r_spec` +0,001 [−0,003; +0,006],
`reach` −0,008 (risolto), errore quadratico −0,077 (risolto). Per fold, la correlazione specifica **scende**,
risolta, in C-CD4T, C-HCT116, C-HEK293 e C-K562 e **sale** in C-iPSC e C-H1; `disc95` è risolto negativo in
C-HEK293 e positivo in C-iPSC.

La scomposizione dice quale pezzo fa che cosa (macro su sei fold; i pezzi sommano a K0):

| Pezzo | Bersagli toccati | `disc95` | `r_spec` | `reach` | errore quadratico |
|---|---|---|---|---|---|
| Q1, iPSC entra con un voto (`kolf_pan_genome`) | 261–281 (17 in C-H1, 0 in C-iPSC) | **−0,011** [−0,021; −0,001] | −0,000 [−0,004; +0,004] | **−0,009** | **−0,060** |
| Q2, entra H1 | 17 (0 in C-H1) | **+0,005** [+0,003; +0,008] | **+0,0012** [+0,0008; +0,0016] | **+0,0014** | **−0,003** |
| Q3, KOLF vota di nuovo con tre tabelle | 62–63 (8 in C-H1, 0 in C-iPSC) | **−0,002** [−0,004; −0,001] | +0,001 [−0,001; +0,002] | **−0,001** | −0,015 [−0,040; +0,001] |

(In grassetto i valori il cui intervallo esclude zero.) Nei quattro fold non staminali Q1 abbassa la correlazione
specifica in modo risolto in tutti e quattro; Q2 la alza in tutti i fold dove agisce.

**Misurato:** H1 migliora le due misure primarie, in modo risolto, in ogni fold in cui è fonte, e le secondarie
quasi ovunque. L'ingresso di KOLF2.1J
riduce la discriminazione e la profondità di segno sui lignaggi non staminali e riduce l'errore d'ampiezza; i suoi
voti ripetuti aggiungono una piccola perdita.

**Interpretazione.** Con pesi uguali, una fonte aiuta i lignaggi che le somigliano e diluisce lo specifico degli
altri: «più fonti» non è monotono. Il guadagno d'ampiezza è in buona parte una contrazione verso zero, che si
otterrebbe anche abbassando l'ampiezza. **Ipotesi, non misurata qui:** pesare le fonti per vicinanza al contesto,
o far votare ogni lignaggio una volta, conserverebbe H1 senza il costo di KOLF sui contesti lontani. Sul sito t36
ha dato +0,0024 su t28, con PDS in salita: quel confronto contiene anche il cambio delle tabelle Orion e tre
contesti di cui non conosciamo la vicinanza alle staminali, quindi non contraddice né conferma questa lettura.

## 6. Esplorativo: t36 senza KOLF2.1J (livello A; il banco a sei membri è a parte)

[Piano scritto prima](ESPLORATIVO_SENZA_KOLF.md), [tabelle](TABELLE_ESPLORATIVO_r3.md), corsa r3 (19:19–19:30,
kernel `davideferrante11/vcc-validazione-logo-8a8ca58a-r3`; parità sì; il contrasto «KOLF vota una volta» coincide
con −Q3 della corsa r2).

| Contrasto | `disc95`, macro | Fold non staminali | C-H1 | errore quadratico, macro |
|---|---|---|---|---|
| P4h − T0: t36 senza le quattro tabelle KOLF | **+0,012** [+0,002; +0,022] | positivo in tutti e quattro, risolto in C-HEK293 (+0,034) e C-K562 (+0,020); `r_spec` risolto positivo in tutti e quattro | `disc95` −0,007 non risolto; `r_spec` −0,027 risolto | **+0,073** (peggiora: meno fonti, ampiezza più alta) |
| P4kh − T0: KOLF vota una volta | **+0,002** [+0,001; +0,004] | `r_spec` risolto positivo in tutti e quattro, di poco | `r_spec` −0,006 risolto | +0,015 [−0,001; +0,040] |
| P4h − P4: H1 aggiunta alle quattro linee | **+0,004** [+0,002; +0,006] | positivo in tutti i fold in cui agisce | — (H1 esclusa) | **−0,004** |

**Misurato:** sui quattro lignaggi non staminali togliere KOLF alza discriminazione, correlazione specifica e
profondità di segno; sul fold H1, che è staminale, la abbassa; l'errore d'ampiezza peggiora ovunque.
**Limiti:** l'ipotesi è nata dalla scomposizione di K0 sugli stessi lignaggi (non è una conferma); nei fold
C-HCT116 e C-HEK293 una fonte è dello stesso studio della verità (Orion), quindi parte dell'accordo può essere
tecnica, ma l'effetto compare anche in C-K562 e C-CD4T, che non hanno fonti dello stesso studio; l'ampiezza non è
ricalibrata fra i bracci.

## 7. Regime J: quanto vale il ripiego del transfer sui bersagli nascosti

[Piano scritto prima](REGIME_J.md), [tabelle](TABELLE_REGIME_J_r4.md), corsa r4 (19:45–19:56): per ogni fold i 66
bersagli del pannello del gruppo 0 tolti da ogni tabella prima dello stadio 100 (24 esecuzioni su copie filtrate,
279–339 righe nascoste tolte per esecuzione, nessuna tabella del lignaggio escluso letta).

- Come atteso, T0, R1, T1 e P4 **sono identici** sui bersagli nascosti: resta la sola testa cis.
- Dei 59–66 bersagli nascosti con verità per fold (6 in H1), 15–20 hanno un vicino cis e ricevono una previsione.
- `disc95` vale 0,54–0,58 contro 0,50 della previsione nulla: differenza risolta in cinque fold su sei, macro
  **+0,065 [+0,036; +0,099]**. Le altre misure non sono definite: troppo pochi geni previsti per bersaglio.

**Lettura:** in J il transfer non prevede quasi nulla, e quel poco viene dalla testa cis. È la base, misurata, contro
cui si leggerà una componente che generalizza sui bersagli: in C la stessa misura vale 0,56–0,97. Nessun candidato
di questo tipo è arrivato alla valutazione stanotte.
