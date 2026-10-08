# Consegna delle medie T2 a VALIDAZIONE

**Misurato:** `common_release_production_r1.json` congela tutte le 16 medie di
produzione e il numero di target che sostiene ciascun gene. Gli array sono nella
radice dati, ai percorsi e hash del manifest; sono stati scaricati e verificati
indipendentemente. Questa è una consegna di statistiche, non del candidato T2 finale.

Il campo `common` indica un NPZ compatibile con `load_common` dello stadio 100:
asse `genes`, un vettore finito per nome di fonte. `support` contiene i denominatori
per gene. Zero con supporto nullo significa media non stimata: il fit finale
rifiuta una fonte se ciò riguarda un gene effettivamente votato dalla sua tabella T1.

- K562 usa il bulk storico: 9.866 target, parità esatta dei 272 target condivisi con
  T1. La ricomposizione GWPS single-cell resta un input distinto del trainer e non
  sostituisce silenziosamente questa fonte.
- CD4 combina prima, per target e gene, le condizioni con affidabilità `n/(n+100)`;
  poi media con peso uguale i 11.593 target dell'unione. I donatori sono ricomposti
  prima dello shrinkage nei tre produttori di condizione.
- H1 deduplica soltanto i controlli identici di train/val; test protetta.
- HIPSCI mantiene le identità dei 19 cloni nella provenienza e li ricompone nello
  stimatore prima dello shrinkage per il voto della sorgente.

Per C, le medie di una fonte rimasta ammessa non dipendono dalle altre fonti:
occorre escludere integralmente quelle del lignaggio trattenuto secondo il manifest.
Per T/J non usare queste medie di produzione: la consegna distinta con regime `T`
deve contenere tutte le fonti necessarie, con la regola hash su ogni componente
applicata prima di maschere, pooling e medie. Nessun ripiego sulla media del pannello.

Il job finale T2 è preparato in `final_t2/r1/prepared.json`, con input e codice
congelati. Deve prima riprodurre gli hash degli effetti T1, poi cambiare solo la
centratura, mantenendo tabelle target, pesi, ampiezza, cis e copertura delle risposte.
La ricevuta di fit e gli effetti vanno verificati prima di chiamarlo candidato pronto.

Gli esiti comparativi e l'eventuale promozione restano a VALIDAZIONE. D-053 è aperta;
la nuova release del trainer resta a 47 contesti CRISPRi e non dimostra un fit eseguito.
