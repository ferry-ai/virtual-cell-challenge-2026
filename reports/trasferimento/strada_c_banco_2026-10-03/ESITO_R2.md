# Strada C, corsa r2: esito secondo la regola registrata

3 ottobre 2026, verso le 22:40, ora del PC. È il passo 4 del kernel `alfredo2003bit/rete-sorgenti-r1`, codice al commit
23d6475.
- **Cosa cambia dalla [r1](ESITO.md):** **solo** la correzione dei gruppi Tian del §2.1. Le chiavi di neuroni sono ora
  in `tian_neuron`, e non più nel gruppo pluripotente.
- **Cosa resta uguale:** bracci, costanti, semi e regola del [protocollo](PROTOCOLLO.md), come stabilisce
  [PROTOCOLLO_R1](../../modelli/rete_sorgenti_2026-10-03/PROTOCOLLO_R1.md) §2.

I file piccoli sono in [esito_r2/](esito_r2/), con gli hash dell'output scaricato. **Sono numeri di un banco locale,
non punteggi VCC.**

## 1. Esito

| Regola | Esito |
|---|---|
| Cancello tecnico | **passa su tutte e quattro le linee:** 6 membri su 6; pannelli di 51 (H1), 134 (KOLF), 150 e 150 bersagli |
| **Strada C** | **non passa.** Su H1 `same − cross` = −0,007 [−0,050; +0,037], n = 51 |
| Bracci B: `alloc` | **non passa.** HepG2 −0,069 [−0,131; −0,005], che peggiora; Jurkat −0,013 [−0,059; +0,039] |
| Bracci B: `normrest` | **non passa.** HepG2 −0,014 [−0,066; +0,040]; Jurkat −0,004 [−0,040; +0,030] |

**Le altre condizioni della strada C:**
- `same − same_shuf` su H1: +0,160 [+0,114; +0,211];
- `same − cross` su KOLF: +0,103 [+0,031; +0,173].

**Previsione registrata** (PROTOCOLLO_R1): `same − cross` su H1 fra −0,05 e +0,05, regola non passata, fiducia 0,7.
**Avverata.**

## 2. Media dei sei membri per braccio

| Braccio | H1 | KOLF | HepG2 | Jurkat |
|---|---|---|---|---|
| `null` | −0,085 | −0,040 | −0,063 | −0,031 |
| `k562` | 0,154 | 0,072 | 0,130 | **0,252** |
| `cross` | 0,162 | 0,134 | **0,236** | 0,214 |
| `same` | 0,155 | 0,237 | — | — |
| `all` | 0,157 | 0,221 | (= `cross`) | (= `cross`) |
| `same_a2` | 0,178 | **0,273** | — | — |
| `cross_a2` | **0,188** | 0,182 | **0,236** | 0,196 |
| `alloc` | 0,148 | 0,247 | 0,167 | 0,201 |
| `normrest` | 0,170 | 0,241 | 0,222 | 0,210 |

Tabelle complete in `esito_r2/scaled_local_<linea>.csv`.

## 3. Lettura, e che cosa cambia rispetto alla r1

- **La correzione Tian sposta poco.** Su H1 `same − cross` passa da −0,023 a −0,007. Su KOLF da +0,090 a +0,103.
  Il segno opposto fra le due linee pluripotenti resta.
- **Ipotesi smentita, e solo questa:** le sorgenti dello stesso tipo non battono quelle di tipo diverso su H1, con
  questa regola d'ampiezza. Ora la conclusione vale per la misura che il protocollo intendeva.
- **Si ripete fra r1 e r2, ma è descrittivo:** l'ampiezza ×2 non peggiora su nessuna linea pluripotente.
  - Su H1: `cross_a2` 0,188 contro `cross` 0,162; `same_a2` 0,178 contro `same` 0,155.
  - Su KOLF: `same_a2` 0,273 contro 0,237.
  - Sulle linee non pluripotenti è pari o peggio: HepG2 0,236 contro 0,236; Jurkat 0,196 contro 0,214.
- **Su questo banco nessuna scelta delle sorgenti fatta a mano vince su tutte le linee.** È il risultato della r1, ora
  senza l'errore.

## 4. Limiti

Restano quelli della r1 (§2 di [ESITO.md](ESITO.md)), tranne l'errore Tian ora corretto. In particolare:
- H1 ha 51 bersagli;
- la regola d'ampiezza è dominata dalle chiavi HipSci;
- gli spazi dei geni sono diversi fra sorgenti;
- il bootstrap è dentro ciascuna linea;
- le linee del banco non sono D, E, F.

## 5. Consegna a Davide (la sua priorità 1)

- **Esito:** la strada C è conclusa sotto il protocollo congelato e **non passa**, né in r1 né in r2.
- **Che cosa non dice:** che il tipo cellulare non conti mai. Su KOLF il segno è opposto, e qui si è misurata una sola
  regola d'ampiezza.
- **Protocollo successivo (proposta):** l'ampiezza della media di più linee contro la ricetta del t22, sul banco della
  strada B. Serve lo slug del dataset r9.
