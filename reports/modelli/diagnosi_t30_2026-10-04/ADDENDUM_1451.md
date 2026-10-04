# Addendum del 4/10, 14:51 CEST: due correzioni di Codex al resoconto, accolte

Ora letta con `date`. Sessione `ba9b8bcb`. Il proprietario ha inoltrato in chat la valutazione di Codex (14:48) sul
[resoconto](README.md). Due suoi rilievi correggono formulazioni troppo forti dei miei §3 e §5; le misure non cambiano.
Il testo del resoconto resta com'è: questo addendum dice come vanno letti quei due punti.

## 1. La parte comune non va azzerata per regola

**Che cosa avevo scritto (§5):** «Correzione a media nulla sui bersagli […] applicata identica in banco ed
esportazione».

**Che cosa è misurato:** all'esportazione la quota comune di R è 0,62–0,69 contro 0,07–0,24 sulle righe del banco; il
vettore comune è quasi lo stesso in A, B, C e sui controlli di HepG2 (R3, R4).

**Che cosa non è misurato:** se quella parte comune sia risposta biologica condivisa, artefatto della rete o diversa
quantità di rumore fra i due modi di calcolare R; e se toglierla migliori o peggiori i sei membri. In più, togliere la
media **sui bersagli del pannello** rende la previsione di un gene dipendente da quali altri geni sono nel pannello: il
pannello di D/E/F sarà un altro.

**Lettura corretta:** la centratura è un **braccio diagnostico** (`all_wRspec`, `all_wRcom`, `all_wRdose` del
[protocollo](PROTOCOLLO_CONFRONTI.md) §3–4), non un vincolo di progetto. Il vincolo che resta è misurare ampiezza,
riproducibilità e contributo specifico della parte comune sul contesto di destinazione, e rifiutare un'esportazione
che esce dal regime in cui la correzione è stata valutata. Se un modello futuro vuole una correzione senza parte
comune, il riferimento per la centratura deve essere indipendente dal pannello (per esempio un insieme fisso di
bersagli di training), scelto prima dei numeri.

## 2. L'assenza dei 300 bersagli dal banco non invalida da sola il banco

**Che cosa avevo scritto (§3, punto 6):** «bersagli del pannello (o del loro stesso regime di supporto e ampiezza) fra
quelli valutati e fra le righe del selettore».

**Lettura corretta:** vale solo la parte fra parentesi. Mettere nel banco proprio i 300 bersagli di A/B/C sarebbe un
adattamento alla validazione; il pannello finale cambia. Il difetto misurato è di **regime**: sui bersagli del pannello
il transfer è più piccolo (RMS mediana 0,107 contro 0,120–0,135), ha meno fonti (5 gruppi contro 6–8) e la correzione è
più grande (R5). Il banco deve coprire quel regime (effetti deboli, poche sorgenti, supporto scarso, bersagli nuovi)
con bersagli scelti per quelle proprietà, non per nome.

## 3. Che cosa ne segue per i confronti già pronti

- Le letture C2 e C3 del protocollo restano diagnostiche e non cambiano; nessuna delle due autorizza una correzione
  centrata come candidato.
- Il riferimento da battere proposto da Codex è la ricetta t28 (effetti t25 ×1,5 e dispersione per gene). Le corsie
  diagnostiche coprono la sola ampiezza (`prod_x15`, `prod_wR_x15`): la dispersione per gene **non** è nel generatore
  delle corsie. Un banco che confronti contro il t28 richiede quel generatore; è lavoro da fare, non già pronto.
- Il primo passo del piano di Codex coincide con il braccio fedele del §8 (`all_wRexp`): è pronto, non eseguito, e
  attende il via del proprietario per Kaggle.
