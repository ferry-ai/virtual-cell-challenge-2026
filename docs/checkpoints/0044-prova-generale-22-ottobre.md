# CP-0044 — La prova generale del 22 ottobre riesce in forma ridotta: .vcc di D/E/F verificato; restano da correggere la cache che sbaglia in silenzio e il riferimento di gamma

- **Data:** 2026-09-29
- **Tipo:** esperimento
- **Redatto da:** Claude (Opus 5.5, sessione f2abd9a6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Dal pacchetto del 22 ottobre (tre contesti nuovi con i soli controlli, 300 bersagli nuovi) la ricetta del t22 arriva a
un `.vcc` verificato? Dove dipende ancora da A/B/C o dal loro pannello? È l'azione 3 della scheda
[R-REV](../piani/revisione-critica.md) e il filone F8 della scheda [R-V2](../piani/modello-v2.md).

## 2. Cosa è stato fatto

- **Registrato prima di girare:** protocollo, sei previsioni e 13 difetti attesi, alle 20:00 del 28/09 (`b8ccdef`).
  Le deviazioni del codice sono dichiarate prima dei passi 2–10
  ([RISULTATI](../../reports/invii/prova_generale_2026-09-28/RISULTATI.md)).
- **Contesti finti:** A, B e C copiati e rinominati D, E, F con una permutazione (D = B, E = A, F = C).
- **Bersagli finti:** 300, estratti con un seme per strati di copertura.
- **Cache:** ricostruite dagli universi `_me1`.
- **Catena:** stadi 85, 99, 100, 45 e 48, in forma ridotta (40 cellule per bersaglio) perché il disco aveva meno dei
  17 GB della forma piena. Ogni passo è misurato da `misura.py`.
- **Correzione D1:** `--contexts` nello stadio 48, con test e con un pilota prima/dopo su dati veri.

## 3. Cosa si è osservato

Tutto in `reports/invii/prova_generale_2026-09-28/` (`tempi.jsonl`, `diagnostica.json`, `pg22*`).

- **`.vcc` di D/E/F:** il validatore ufficiale lo accetta, il contenuto è identico bit per bit all'input, 300 bersagli
  per contesto.
- **Previsioni registrate:** 1, 3, 4, 5 e 6 si avverano. La 2 si avvera ma non è isolata dalla forma ridotta.
  - La 1: lo stadio 48 senza l'opzione rifiuta D/E/F.
  - La 3: le cache dagli universi uguagliano r5 e r9; gli effetti uguagliano t22 e t25 entro 7,5e-9.
  - La 4: 270 bersagli su 300 coperti.
  - La 6: con la cache del pannello sbagliato lo stadio 100 finisce con codice 0 e 30 bersagli coperti.
- **Tempi, per passo:** 36–254 s, con picco di memoria sotto 0,57 GiB. La forma piena degli stadi 45 e 48 è quella
  misurata sul t22.
- **γ = 1:** il vettore tolto con il pannello finto ha coseno 0,59 con quello del pannello di oggi per K562, e 0,88–0,97
  per le altre sorgenti.
- **Pilota prima/dopo dello stadio 48:** stesso sha256 senza `--contexts`.

## 4. Interpretazione e incertezza

- **Misurato:** la pipeline produce un invio valido per contesti con nomi nuovi e un pannello nuovo, partendo dagli
  universi e senza scaricare nulla. Gli stadi 97/102/98 del §7 di LAVORO non servono più per le sorgenti del t22.
- **Interpretazione:** due difetti possono costare il 22/10 senza che nessuno se ne accorga:
  - D4, una cache costruita per il pannello sbagliato dà una previsione quasi vuota senza errore;
  - D9, il riferimento tolto da γ = 1 cambia con il pannello, molto per K562.
- **Limiti:**
  - D, E ed F sono copie di A, B e C: la prova non dice nulla sul punteggio né su contesti davvero nuovi;
  - forma ridotta;
  - il pannello finto non è quello vero.

## 5. Spiegazione semplice

Si è finto che fosse il 22 ottobre: si sono presi i dati di oggi, si è cambiato loro il nome e si è inventato un
elenco di 300 geni, per vedere se la catena di programmi arriva fino al file da consegnare. Ci arriva. Lungo la strada
si sono visti due punti dove un errore passerebbe inosservato, e vanno chiusi prima del giorno vero.

## 6. Conseguenze

- **Da fare prima del 22/10, ciascuno con il suo test:**
  - D4: la cache registra lo sha256 del file dei bersagli e lo stadio 100 rifiuta una discrepanza;
  - D9: una chiave `"common"` nella ricetta, con il riferimento fissato;
  - D2, D3, D5, D8, D10 e D11;
  - LAVORO §7 da riscrivere sul percorso dagli universi (D12, D6, D13).
- **Disco:** la forma piena chiede circa 17 GB liberi. Il 29/09 ce n'erano 3,9, più 25 GB nel Cestino.
- **L'azione 3 di R-REV** non è chiusa finché quei difetti non sono corretti.

## 7. Cosa corregge

LAVORO §7 dice che il giorno del rilascio le sorgenti si ricostruiscono con gli stadi 97, 102 e 98, e che il picco è di
circa 13 GB. Per le sorgenti del t22 bastano gli universi, e le riserve degli stadi 45 e 48 chiedono circa 17 GB. Il
testo di LAVORO va aggiornato (difetti D10 e D12); questo checkpoint non lo riscrive.

## 8. Domanda di comprensione

Perché una prova che finisce con codice 0 a ogni passo non basta a dire che il 22 ottobre andrà bene?
