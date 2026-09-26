# Trasferimento gerarchico con Bayes empirico (candidato t22)

26 settembre 2026, pomeriggio. Filone della scheda [R-V2](../../docs/piani/modello-v2.md), aperto dopo
che il canale di magnitudine appreso non ha passato il banco isolato
([r5](../trasferimento_appreso_2026-09-26/RISULTATI.md)) e dopo la regola D-045 del proprietario.
**Proxy contro sorgenti pubbliche tenute fuori, non punteggi VCC.**

## L'idea

Il t20 fa una media a pesi uguali degli effetti ristretti di K562, CD4 e HCT116, e moltiplica
tutto per un'ampiezza. Qui ogni sorgente è letta con un modello gerarchico:

    y_s = θ + δ_s + e_s

con θ la risposta che le linee condividono, δ_s la deviazione propria della linea, e_s il rumore di
campionamento della sorgente. Le varianze di θ e di δ si stimano per gene, con i momenti, dalle sole
sorgenti d'ingresso (quelle che anche la produzione ha); la previsione per una linea nuova è la media a
posteriori di θ. Ne seguono tre cose che il t20 non fa:
- i geni che rispondono in modo coerente fra le linee pesano, quelli che cambiano da una linea
  all'altra si restringono verso zero (**biologia**: risposte conservate contro specifiche della linea);
- il peso di una sorgente dipende dal suo rumore e dall'eterogeneità fra linee, non solo dalle cellule;
- CD4 riceve la varianza fra donatori che il suo errore standard non vede (braccio k2: varianza ×2,
  dentro l'1,65–2,17 misurato dalla sessione 76a3a45e; [CP-0040](../../docs/checkpoints/0040-biologia-contesti-donatori.md) §5).

Script `eb_bench.py`, stesso impianto isolato dell'r5 (esclusione della famiglia tenuta fuori; nessuna
misura della sorgente di prova entra nelle stime). Bracci: `t20like`; `eb_k1_det` ed `eb_k2_det`
(scala uguale ai geni rilevabili del t20like, come fu scelta l'ampiezza della ricetta); `eb_k2_energy`
(scala uguale all'energia del t20like). La testa cis del t20 resta fuori dalla scala.

## Regola fissata alle 15:20 del 26/09, prima di eseguire il banco

Su ciascuna delle tre sorgenti la cui linea è nuova (CD4, HCT116, HEK293T) si calcola
Δ = 0,36 × ΔPDS_gen − 0,27 × ΔnMAE_gen rispetto a t20like, con intervallo bootstrap appaiato sui
bersagli (0,36 e 0,27 sono le pendenze ufficiali dei due membri sulla media dei sei, per unità di
grezzo). Un braccio EB passa se Δ > 0 con l'intervallo sopra zero su almeno due linee e nessuna
linea ha Δ < −0,002. Fra i bracci che passano, il t22 è quello con il Δ medio più alto sulle tre
linee. Se nessuno passa, il t22 non si fa con EB e si passa al candidato successivo. K562 tenuto fuori
si riporta, ma non entra nella regola (la sua linea non è nuova).

## Risultati di r1

Differenze da t20like, intervalli bootstrap al 95 % sui bersagli ([summary.csv](r1/summary.csv),
componenti della varianza in [components.csv](r1/components.csv)). Δ è la combinazione della regola.

| Sorgente fuori | braccio | PDS proxy | PDS gen | nMAE gen | Δ | energia |
|---|---|---|---|---|---|---|
| CD4 | eb_k1_det | −0,015 | −0,001 (−0,019…+0,015) | −0,009 (−0,014…−0,004) | +0,002 (−0,004…+0,009) | 0,44 |
| HCT116 | eb_k1_det | −0,019 | −0,018 (−0,043…+0,008) | +0,008 | −0,009 (−0,018…+0,002) | 0,43 |
| HEK293T | eb_k1_det | +0,015 | −0,015 (−0,039…+0,009) | −0,009 | −0,003 (−0,013…+0,007) | 0,42 |
| CD4 / HCT116 / HEK293T | eb_k2_det | −0,015 / −0,014 / +0,014 | −0,001 / −0,018 / −0,016 | −0,009 / +0,013 / −0,004 | +0,002 / −0,010 / −0,005 | 0,44–0,45 |
| CD4 / HCT116 / HEK293T | eb_k2_energy | | 0,000 / −0,027 / −0,023 | +0,021 / +0,044 / +0,041 | −0,006 / −0,021 / −0,019 | 1 |
| K562 (linea non nuova) | eb_k1_det / eb_k2_det | −0,004 / −0,008 | −0,002 / −0,003 | +0,010 / +0,010 | −0,003 / −0,004 | 0,39–0,42 |

- **Esito della regola:** nessun braccio ha Δ > 0 con l'intervallo sopra zero su due linee nuove;
  HCT116 e HEK293T scendono sotto −0,002. **Il t22 non si fa con l'EB.**
- **Misurato:** la varianza condivisa fra linee stimata dalle sorgenti d'ingresso è piccola rispetto
  a quella propria della linea (mediane σ² 0,0001–0,0003 contro τ² 0,0002–0,0005 in k1). Con due sole
  sorgenti d'ingresso (le Orion tenute fuori: K562 e CD4) il modello restringe molto e perde PDS
  attraverso il generatore (−0,015…−0,018).
- **Misurato:** a parità di geni rilevabili l'EB ha il 42–45 % dell'energia del t20like: distribuisce
  l'ampiezza su più geni. Su CD4 l'nMAE proxy migliora (−0,009, intervallo sotto zero).
- **Interpretazione:** con tre o quattro linee la parte condivisa della risposta si stima male
  gene per gene. Il modello gerarchico ha bisogno di molte più linee, o di molti più bersagli per
  linea (gli universi genome-wide), per stimare quali risposte si conservano.
