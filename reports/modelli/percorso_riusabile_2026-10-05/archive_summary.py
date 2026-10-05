"""Summarize byte receipts without confusing rows, biological contexts and training use."""
import json
from pathlib import Path
from pipeline_state import HERE

def main():
 state=json.loads((HERE/'archive_followup_r3/state.json').read_text())
 archives=state['archives'];unique={}
 for entry in archives:
  for f in json.loads((HERE.parents[2]/entry['files_receipt']).read_text()):unique.setdefault(f['sha256'],f['bytes'])
 lines=['# Archivi persistenti: dati e dataset, 5 ottobre 2026','',
  '**Percorso principale: archivio verificato → banca e campioni → training esteso.**',
  'Indice dei dati conservati; non è una dichiarazione di training completo.',
  '', '## Nuova ingestione conservata su Kaggle','',
  'CD4: 12 unità (4 donatori × Rest/Stim8hr/Stim48hr), 21.980.517 cellule, 206,00 GB grezzi.',
  'KOLF2.1J: 2.659.209 cellule, 18,39 GB. HCT116: 3.409.169 cellule, 38,66 GB.',
  'HEK293T: 4.534.299 cellule, 63,12 GB. Totale: **326,17 GB**, 32.583.194 righe cellulari, 15 unità biologiche.',
  'Notebook, versioni, percorsi e hash: [manifest corrente](cloud_catalog_r4/README.md).',
  '', '## Archivi precedenti da riusare, non da reingerire','',
  'Versioni osservate via API e manifest recuperati in `archive_followup_r2/state.json`; subset realmente pubblicati riconciliati con `files.json` in `archive_followup_r3/state.json`.',
  'Tutti i dataset della tabella appartengono a `davidmaisterx`; le unità non coincidono con i contesti biologici.',
  '', '| Dataset | Versione | GB grezzi | Righe cellulari | Unità di sorgente |',
  '|---|---:|---:|---:|---|']
 for entry in archives:
  ref=entry['dataset'];lines.append('| ['+ref.split('/')[1]+'](https://www.kaggle.com/datasets/'+ref+'/versions/'+str(entry['version'])+') | '+str(entry['version'])+' | '+f"{entry['bytes']/1e9:.3f}"+' | '+f"{entry['cells']:,}".replace(',','.')+' | '+', '.join(entry['units'])+' |')
 total=326166252483+sum(unique.values())
 lines+=['',f"**17 archivi precedenti: {sum(unique.values())/1e9:.2f} GB di shard distinti per SHA256.**",
  f"Con il nuovo ramo: **{total/1e9:.2f} GB di grezzi perturbazionali conservati**.",
  'Le 41.765.207 righe sommate fra i rilasci non sono una stima di cellule biologiche uniche: deduplicazione e sovrapposizioni di schermi restano da riconciliare.',
  '', '## Diversità e limiti di copertura','',
  'Sono rappresentati K562, RPE1, HepG2, Jurkat, H1, iPSC/KOLF/HIPSCI, neuroni, A549, CD4/T primarie, melanoma, Calu-3, THP-1, HCT116, HEK293T e HEK293.',
  'HIPSCI comprende 19 linee nel rilascio mirato. CD4 comprende 4 donatori × 3 stati; Frangieh 3 stati; Shifrut 4 combinazioni donatore/stimolo; Dixit 3 esperimenti; Datlinger stimolato/non stimolato. CRISPRi, CRISPRa e KO restano metadati distinti.',
  'Il numero totale delle chiavi biologiche `(studio, contesto, donatore/clone, condizione, modalità, chimica)` va letto dai nuovi `rows.csv`: non sostituirlo con il numero di dataset o delle unità.',
  'Tian 2019 richiede ancora la decisione QC sui droplet; Jurkat GSE249595 non ha chiamate delle guide; HIPSCI genome-wide ha controlli scarsi; gli UNASSIGNED non diventano etichette perturbazionali. Archiviazione completa non implica ammissibilità al fit.',
  'Il catalogo completo mantiene anche sorgenti non ancora convertite/ingerite: queste non entrano nei GB dichiarati e non sono escluse per comodità.',
  '', '## Basali, aggregati e ingestione parziale','',
  'L’audit Kaggle del 2 ottobre conserva anche `vcc-corpus-basale-r1`, `vcc-corpus-tahoe-r1`, aggregati e pacchetti dei modelli: 85,67 GB complessivi di file storici riletti, **comprensivi** dei 69,58 GB sopra. Non sommare i due valori.',
  'Fonte: `reports/sorgenti/archivio_cloud_2026-10-02/kaggle_verify/esito_r2.json`. Basali e Tahoe richiedono un ruolo e un adapter espliciti; non sono pseudobulk perturbazionali.',
  'Southard: output parziali persistenti in `Drive/vcc2026/data/processed/corpus_cellulare_2026-09-30/j09_southard_r3`; job 132 senza battito recente. Preservare shard e ricevute; un eventuale resume deve usare `--reuse`, senza ripartire da zero.',
  '', '## Riutilizzo e trainer','',
  'Non usare nomi simili o “latest” come fallback: selezionare dataset/versione, manifest e hash. Montare i dati cloud; il passaggio sul portatile è facoltativo.',
  'Un nuovo dataset aggiunge solo adattatore e derivati propri, poi una nuova versione dell’indice. Riutilizzare i derivati se input, asse, QC, codice e parametri coincidono.',
  'Per un teammate: l’indice Git non conferisce accesso ai dataset privati. Concedere accesso ai riferimenti nominati e fornire il manifest; non condividere token.',
  'Il trainer esteso deve integrare lettori, split D-053, hash nel runtime e ricevute di esposizione/loss anche dopo resume. I 18 fit precedenti restano un pilot aggregato. **Training esteso non ancora avviato.**']
 (HERE/'DATI_DISPONIBILI_r2.md').open('x',encoding='utf-8').write('\n'.join(lines)+'\n')
 summary={'raw_existing_unique_bytes':sum(unique.values()),'raw_new_bytes':326166252483,
  'raw_total_bytes':total,'raw_cell_rows':41765207,'datasets_existing':17,
  'extended_training_ready':False,'biological_context_total':'not yet reconciled'}
 (HERE/'data_totals_r2.json').open('x').write(json.dumps(summary,indent=1));print(json.dumps(summary))

if __name__=='__main__':main()
