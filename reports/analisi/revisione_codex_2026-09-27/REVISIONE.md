# Revisione di codex del 27 settembre e risposta

27 settembre 2026. Analisi scritta da codex (app Codex del proprietario; il testo porta l'ora 13:31) e girata
dal proprietario nella sessione `f4f38e58`; qui riassunta punto per punto, con la risposta. **È una
revisione, non una misura**: codex dice di aver confrontato la chat con codice, ricette, manifest e tabelle, e di
non aver riaddestrato modelli.

## Il giudizio complessivo di codex

| Aspetto | Giudizio di codex |
|---|---|
| Patrimonio di dati riutilizzabile | Sì: gli universi completi superano il vincolo dei 300 bersagli |
| Ricerca biologica | Sì: osservazioni concrete su contesto, programmi, segno e affidabilità |
| Biologia incorporata nel modello operativo | In parte: modulo cis, trasferimento e pesatura; molte idee restano proposte |
| Modello avanzato con generalizzazione dimostrata | Non ancora: t23 modifica la baseline; t24 ne misura la variabilità |

## I sei punti e la risposta

1. **L'atlante prova il trasferimento dello stesso intervento verso un contesto nuovo** (per ogni bersaglio di
   prova si leggono le sue risposte nelle sorgenti d'ingresso), non la previsione di un gene mai perturbato.
   *Risposta: d'accordo.* L'atlante è il regime C; i regimi T e J restano da provare (banco C/T/J, sotto).
2. **Il t23 mescola selezione dei geni, pesatura e riscalatura** (8.247 pesi a 0, 8.395 a 1, 1.891 intermedi,
   riscalatura dopo la pesatura); un guadagno non confermerebbe il meccanismo; serve un'ablazione con
   calibrazione comparabile. *Risposta: d'accordo, e c'è di più:* l'esclusione toglie anche i geni Y
   dell'[artefatto del pseudoconteggio](../pseudoconteggio_2026-09-27/RISULTATI.md). Ablazione registrata prima
   di eseguirla in [`../ablazione_t23_2026-09-27/`](../ablazione_t23_2026-09-27/RISULTATI.md).
3. **«Abbiamo provato i modelli complessi e hanno perso» è troppo generale**: sono fallite implementazioni
   precise (proiezioni sui programmi, un modello gerarchico, trasferimento appreso, una piccola rete
   condizionata con due contesti di training e addestramento non riproducibile, CP-0026). *Risposta:
   d'accordo; la frase era sbagliata.*
4. **Gli insight biologici non sono ancora tradotti in vantaggio predittivo**, e i coseni fra linee
   confondono biologia, laboratorio, protocollo e rumore: non dimostrano che la componente di contesto sia
   impossibile da apprendere. *Risposta: d'accordo;* la scheda R-V2 porta ora questa cautela.
5. **Il t24 è un controllo utile, ma una sola coppia di semi non basta** a dire che ±0,005 valga due
   deviazioni standard; la regola 3 × differenza è un'euristica molto incerta; servono più repliche, prima sul
   banco locale con lo scorer completo. *Risposta: d'accordo;* la raccomandazione al proprietario è di non
   inviare il t24.
6. **HIPSCI non rappresenta 34 tipi cellulari**: 34 linee iPSC da 26 donatori, diversità genetica entro un tipo.
   *Risposta: d'accordo* (già corretto in chat).

Codex ha anche verificato nella formula l'artefatto del pseudoconteggio, e chiede di ricontrollare sulle cache
corrette i risultati sensibili ai geni con pochi conteggi.

## Le tre consegne chieste, e chi le fa

| Consegna | Stato al 27/09 pomeriggio |
|---|---|
| Dati corretti e confronti ripetuti, con ablazioni che separano filtraggio, pesatura e scala | cache r9 fatta; ablazione del t23 in corso; universi corretti da ricostruire (`../universo_corretto_2026-09-27/rebuild.py`) |
| Banco C/T/J congelato con scorer completo e prova che il modello usa il contesto | affidato a codex tramite la base di lancio (run `20260927-135336-v2-ctj-frozen`, worktree isolato) |
| Modello bersaglio × contesto con informazione biologica, confrontato con un lineare sugli stessi input e con versioni senza quell'informazione | disegno affidato a claude2 (run `20260927-140821-v2-target-context-design`); prima prova misurabile (espressione basale) pronta per codex |

Codex notava infine che sulla copia condivisa, alle 13:31, 180 test davano due fallimenti documentali e un
errore per `cell_eval2.config` mancante. I due fallimenti erano la cartella `pseudoconteggio_2026-09-27/` ancora
senza riga di registro (lavoro in corso, poi committato); su una copia pulita del commit c402837 i 183 test
passano con il venv del progetto. L'errore di `cell_eval2` non si è ripresentato con il venv: interpretazione,
non verificata, è un Python diverso da quello del progetto.
