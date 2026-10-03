# Strada C (con due bracci della B): banco per tipo cellulare con lo scorer vero, su Kaggle

3 ottobre 2026, 12:14 ora del PC (commit 9a5e20d), Claude Code per Alfredo (sessione `42343bb9`), che ha chiesto in chat un'idea con più
sfaccettature e un voto entro oggi. **Registrato prima di ogni numero.** Le soglie e la regola non si spostano dopo i
risultati (CP-0030).

## Da dove viene

- **La proposta:** [STRADA_C.md](../../analisi/letteratura_strade_2026-10-02/STRADA_C.md). D/E/F comprendono
  probabilmente un tipo staminale. Il trasferimento fra linee di tipo diverso porta poca direzione (coseno 0,02–0,07);
  fra stati delle stesse cellule arriva a 0,20–0,25.
- **Perché qui e non con il protocollo della [strada B](../strada_b_2026-10-02/PROTOCOLLO.md):** le quattro sorgenti
  del t22 stanno sul PC di Davide. I dataset rlab su Kaggle oggi leggibili dall'account di Alfredo sono:
  - K562 genome-scale e K562 essential;
  - RPE1, HepG2, Jurkat;
  - H1 della gara 2025 (train e validation, mai il test);
  - HipSci (19 linee), KOLF2.1J (small e strong), Tian/Norman.

  Restano a 403 `rlab-scp-tcells` e `rlab-scp-k562-hek`. Questo banco è quindi **una registrazione nuova, non la
  misura del protocollo B**, che resta in attesa dei suoi dati.

## Che cosa si misura

Per ogni **linea tenuta fuori** L:
- **la verità** sono le cellule reali di L: metà A come verità e metà B come replica, con controlli NTC di L;
- **lo zero** è la baseline ufficiale di `cell_eval2` 0.16.0;
- **le previsioni** si generano con `ControlModel` (stato kde) sui controlli di L, come lo stadio 75, a partire da
  effetti stimati **soltanto su altre linee**.

Sei membri, scala locale (u − b)/(r − b) con la MSE tosata come nello scorer.

### Le sorgenti e i gruppi (regola fissata ora)

**Una chiave** è studio|contesto. Entrano solo le chiavi CRISPRi con almeno 30 controlli NTC; restano fuori KO,
CRISPRa, farmaci e HipSci genome-wide, che ha troppi pochi NTC. Ogni chiave va in un **gruppo di linea**; i gruppi
hanno peso uguale, e dentro un gruppo le chiavi si mediano.

| Gruppo | Chiavi | Tipo |
|---|---|---|
| `k562` | K562 genome-scale, K562 essential | mieloide |
| `rpe1` | RPE1 | epiteliale |
| `hepg2` | HepG2 Nadig | epatico |
| `jurkat` | Jurkat Nadig | linfoide T |
| `h1` | H1 2025 | pluripotente |
| `hipsci` | le 19 linee HipSci targeted | pluripotente |
| `kolf` | KOLF2.1J small e strong | pluripotente |
| `tian_ipsc` | Tian, contesti iPSC CRISPRi | pluripotente |
| `tian_neuron` | Tian, contesti neuronali CRISPRi | neuronale |

Il kernel registra in `sorgenti.json` le chiavi trovate e il gruppo assegnato a ciascuna. Una chiave che la regola non
assegna resta fuori ed è elencata.

**Esclusioni per L:**
- tutto lo studio di L;
- ogni chiave della stessa linea cellulare: per KOLF2.1J tenuta fuori, anche le linee HipSci `kolf_2` e `kolf_3`, da
  cui deriva.

### Effetti per sorgente

Si usa lo stesso stimatore del repository, `predictor_sc.effects_from_bulk`, sullo pseudobulk di somme:
- frazione aggregata del bersaglio contro quella dei controlli della stessa chiave;
- errore quasi-Poisson con φ = 0,2;
- restringimento locale `multisource.z_shrink` con k = 4, fisso;
- forma t22: γ = 1, cioè a ogni chiave si toglie la sua risposta media sui bersagli;
- i geni non misurati o sotto 1e-6 di frazione nei controlli restano NaN.

L'effetto mediato di un braccio è la media pesata per gruppo sui valori finiti.

**Ampiezza (regola unica per tutti i bracci):** l'effetto mediato si riscala di una costante per linea L e braccio.
La norma mediana per bersaglio diventa uguale alla mediana delle norme delle singole chiavi usate, sugli stessi geni.
Così la media di più sorgenti non perde energia solo perché media. Poi si moltiplica per a = 1 (bracci principali) o
a = 2 (bracci `_a2`).

### Le linee tenute fuori

| L | Ruolo |
|---|---|
| `h1` (H1 2025) | **primaria per la strada C**: pluripotente, laboratorio di Arc, nessuna sorgente dello stesso laboratorio fra quelle pluripotenti |
| `kolf` (la chiave KOLF con più bersagli ammessi) | **replica per la strada C** |
| `hepg2` | **primaria per i bracci B** |
| `jurkat` | **replica per i bracci B** |

**Pannello di L:**
- bersagli con almeno 40 cellule in L, coperti da almeno un gruppo di ciascuno dei bracci confrontati;
- al massimo 150, estratti con seme 2026;
- al massimo 300 cellule per bersaglio, divise a metà;
- un pool di al massimo 5.000 controlli di L.

### I bracci

| Braccio | Sorgenti | Per che cosa |
|---|---|---|
| `null` | nessun effetto | controllo del generatore |
| `k562` | solo il gruppo `k562` | il nucleo della ricetta di oggi |
| `cross` | tutti i gruppi **di tipo diverso** da L | la ricetta di oggi resa con le sorgenti di Kaggle |
| `same` | solo i gruppi **dello stesso tipo** di L (solo per H1 e KOLF) | **strada C** |
| `all` | tutti i gruppi | la variante «più sorgenti» |
| `same_shuf` | `same` con i bersagli scambiati (derangement, seme 2027) | controllo d'identità per `same` |
| `cross_shuf` | `cross` con i bersagli scambiati (solo per HepG2 e Jurkat) | controllo d'identità per i bracci B |
| `alloc` | `all` × fattori `arms.alloc_factors`, con i gruppi come sorgenti | strada B, codice e costanti della B |
| `normrest` | `all` × fattori `arms.normrest_factors` | strada B |
| `cross_a2`, `same_a2` | come `cross` e `same`, con a = 2 | sfaccettatura ampiezza (descrittiva) |

Su HepG2 e Jurkat non esiste un gruppo dello stesso tipo: lì `cross` coincide con `all`, e restano `null`, `k562`,
`cross`, `cross_shuf`, `alloc`, `normrest` e `cross_a2`.

## Statistica

Differenza appaiata braccio − riferimento della media dei sei membri in scala locale, con la MSE tosata.
- **Bootstrap** sui bersagli del pannello: 10.000 ricampionamenti, seme 0.
- **A ogni ricampionamento** si ricalcolano anche le ancore: si ricampionano i membri per bersaglio di replica e
  baseline e poi si aggrega con la media, come fa `cell_eval2`.
- **Intervallo al 95%.**

## Regola

1. **La strada C passa** se valgono tutte e tre:
   - `same − cross` ha il limite basso dell'intervallo sopra 0 su H1;
   - la differenza media è ≥ 0 su KOLF;
   - `same − same_shuf` ha il limite basso sopra 0 su H1.

   Se passa, la regola di scelta per D/E/F diventa: un contesto riconosciuto pluripotente dalle impronte usa le fonti
   del suo tipo. È una **regola nuova**, da registrare a parte prima del 22 ottobre.
2. **`alloc` o `normrest` passano** se il limite basso di braccio − `all` è sopra 0 su HepG2 e la media è ≥ 0 su
   Jurkat. Se passano entrambi, vale quello con la differenza media più alta su HepG2.
3. **`all` contro `cross`** su H1 e KOLF, e `cross` contro `k562` su tutte e quattro le linee: sono **descrittivi**.
   Dicono se aggiungere linee aiuta, non decidono.
4. **I bracci `_a2`** sono descrittivi.
5. **Se nessuna regola passa,** la ricetta del t22 resta il riferimento e questi bracci non si rigirano con altre
   costanti.
6. **Una regola che passa** non dice nulla di garantito su D, E, F. Un invio ufficiale che ne derivi ha bisogno di una
   previsione registrata e dell'ok esplicito di Alfredo.

**Cancello tecnico:**
- `replicate` deve superare `baseline` in almeno 4 membri su 6 su ogni L;
- un pannello sotto 20 bersagli rende quella L «non leggibile».

Una L non leggibile toglie la sua parte di regola: se è H1, la strada C non si decide oggi.

## Previsioni (prima dei numeri)

| Previsione | Valore atteso | Fiducia |
|---|---|---|
| `same − cross` su H1, media dei sei | da +0,02 a +0,15 | 0,6 che sia > 0 con l'intervallo sopra 0 |
| `same − same_shuf` su H1 | > 0, intervallo sopra 0 | 0,8 |
| `alloc − all` e `normrest − all` su HepG2 | dentro ±0,01, nessuno passa | 0,7 |
| `cross − k562` | piccolo, segno incerto | 0,5 |
| `null` | vicino a 0 su tutti i membri tranne la MSE | 0,8 |

## Che cosa si conserva

- `bench_<L>/`: `bench.json`, `scaled_local.csv`, `per_pert_*.csv`, `components_*.csv`;
- `sorgenti.json`: chiavi, gruppi, bersagli, controlli;
- `effetti_<gruppo>.npz`: effetti per bersaglio sull'asse ufficiale, per riuso in M4;
- `lettura.json`: la regola applicata.

I file con l'asse ufficiale **non** si committano: si scaricano nella cartella dati, fuori dal repository.
