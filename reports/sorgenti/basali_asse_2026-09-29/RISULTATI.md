# Profili basali sull'asse comune (azione 5 di R-REV)

29 settembre 2026. Scrive Claude (app desktop, sessione `f4f38e58`); orari letti da `date`. Scheda:
[R-REV](../../../docs/piani/revisione-critica.md), azione 5; revisione, §2.6.

Etichette: **misurato**, **verificato nel codice**, **interpretazione**, **proposta**. Nessun numero qui è un
punteggio VCC.

## La domanda

I profili basali delle sorgenti sono CPM calcolati su tutti i geni di ciascun file e poi ristretti all'asse ufficiale
(18.533 geni). Quelli di A/B/C sono già sull'asse Flex.
- Di quanto cambiano se il denominatore è l'asse?
- Chi li legge, e che cosa cambia per ciascun lettore?

## Che cosa c'era già

- I manifest di `processed/basal_sources_2026-09-27.json` e `processed/basal_sources_2026-09-28.json`, nella radice
  dati, riportano la quota della libreria sull'asse per KOLF2.1J, A549, VIPerturb-seq e le due raccolte HIPSCI.
- Codex ha misurato il fattore e i geni sopra 5 CPM per tutte le 17 colonne, nel suo `AUDIT_DATI.md` (§4) e in
  `dati_r1/basal_scale.csv` della cartella `reports/analisi/lead_scientist_2026-09-29/`, non committata alle 19:17
  del 29/09.

Qui: una ricostruzione indipendente, il file nuovo, il controllo dal grezzo, dove sta la massa fuori dall'asse e i
lettori.

## Protocollo, fissato alle 19:17 del 29/09, prima di girare

**1. Il file nuovo.** `processed/basal_sources_axis_2026-09-29.csv`, con il suo `.json`, accanto ai vecchi, che
restano come sono.
- Contiene le 17 colonne di `basal_sources_2026-09-28.csv`. Ciascuna è divisa per la sua somma sui geni dell'asse che
  misura e moltiplicata per 10⁶.
- CD4 mix resta la media delle tre condizioni, come nel file vecchio, calcolata sulle tre colonne nuove.
- Prima si controlla che le colonne comuni ai quattro file basali siano identiche: ogni file è costruito sul
  precedente.
- A, B e C devono restare uguali entro la precisione del CSV.

**2. Il controllo dal grezzo.** Per le quattro sorgenti di `basal_profiles.py` (K562, CD4 nelle tre condizioni,
HCT116, HEK293T), i CPM si ricalcolano dai conteggi dei controlli ristretti all'asse, con la stessa scelta delle righe.
Devono coincidere con la riscalatura entro 10⁻⁹ in relazione, sui geni con CPM > 0. Se non coincidono, il file si
costruisce dal grezzo e la differenza si riporta.

**3. Fattore e massa fuori dall'asse.**
- **Per ogni colonna:** il fattore, cioè 10⁶ diviso la somma sull'asse, e la quota della libreria sull'asse, che ne è
  l'inverso.
- **Per le quattro sorgenti con la tabella completa dei geni:** la massa fuori dall'asse divisa per famiglie
  (proteine ribosomiali RPL/RPS, geni mitocondriali MT-, altri) e i dieci geni fuori dall'asse con più conteggi.
- **I file di somme** (KOLF2.1J, A549, VIPerturb-seq, HIPSCI) tengono solo il totale della libreria: per loro, il solo
  fattore.

**4. Le soglie.**
- I geni ≥ 5 CPM per colonna, prima e dopo.
- `detectable_threshold` (4 / √(400 μ), `src/vcc2026/transfer_model.py`) scende di 1/√fattore: si riporta il valore
  per colonna, senza altro calcolo.
- **Colonne a supporto parziale.** K562, K562 essenziale e RPE1 misurano meno di 8.300 geni dell'asse, perché i file
  bulk tengono solo i geni espressi. La riscalatura dà massa zero ai geni mancanti. Si stima quanta massa quei geni
  hanno nelle sorgenti 3′ a supporto pieno (HCT116, HEK293T, KOLF2.1J): è una stima da altre linee, dichiarata come
  tale.

**5. I lettori.**
- **t22 e t25:** non leggono file basali. Verificato nel codice: le ricette non hanno blocchi `pooling`, `gene_share` o
  `expression_gate`. Nessun calcolo.
- **t26:** il cancello legge le colonne A, B e C. Resta invariato se il punto 1 le trova uguali.
- **t23 e t27:**
  - le quote del t23 (`reports/trasferimento/quota_condivisa_2026-09-27/t23_share.py`) usano le colonne di K562,
    CD4 mix e HCT116 per i gruppi di espressione (`blend`, 50 quantili);
  - l'elenco del t27 è l'insieme delle quote nulle;
  - le quote si ricalcolano con lo stesso codice, gli stessi universi e lo stesso seme. Prima con il file vecchio,
    che deve ridare `share.csv` alle sei cifre scritte (riproduzione); poi con il file nuovo;
  - si riportano i geni la cui quota cambia, il cambio massimo e se l'insieme delle quote nulle cambia.
- **Gli altri lettori** si elencano con quello che leggono, senza rigirarli: gli stadi 104 e 105, i banchi con una
  verità pubblica, la rete a contesti, il corpus dell'encoder.

### Regole, scritte prima

- **R1 (t27).** Se l'insieme delle quote nulle cambia anche di un solo gene, l'elenco del t27 dipende dal difetto.
  - Lo si dice alla sessione che tiene il t27 e al proprietario, prima di un eventuale invio.
  - L'elenco del t27 non si cambia: è registrato, e un elenco nuovo sarebbe un invio nuovo, da registrare a parte.
  - Se l'insieme non cambia, il t27 non è toccato dal difetto.
- **R2 (grezzo).** La tolleranza del punto 2.
- **R3 (t23).** Solo descrittivo: il t23 ha già il suo punteggio e non è un candidato.

**Non si fa.** Non cambia nessuna ricetta, nessun valore predefinito di uno stadio e nessuna cache: gli stadi
continuano a leggere il file vecchio. Se i lettori debbano passare al file nuovo lo decide il proprietario (scheda,
azione 5).

**Chiusura:** questo report. Un checkpoint se R1 scatta o se il controllo dal grezzo fallisce.
