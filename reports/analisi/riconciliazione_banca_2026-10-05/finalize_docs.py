"""Route current documentation to immutable inventory and preserve historical claims."""
from pathlib import Path
R=Path(__file__).resolve().parents[3]
S='reports/modelli/percorso_riusabile_2026-10-05/'
A='reports/analisi/riconciliazione_banca_2026-10-05/'
def edit(name,fn):
    p=R/name;t=p.read_text(encoding='utf-8');p.write_text(fn(t),encoding='utf-8')
def main():
    edit('README.md',lambda t:t.replace(S+'cloud_catalog_r10/README.md',S+'cloud_catalog_r10/manifest.json').replace('[available data, contexts and GB]('+S+'DATI_DISPONIBILI_r2.md)', '[verified selection, data and remaining gaps]('+A+'README.md)').replace(S+'training_coverage_r1/expected.json',A+'frozen/expected_r2.json'))
    edit(S+'README.md',lambda t:t.replace('RIUSO_r1.md','RIUSO_r2.md').replace('[expected congelato](training_coverage_r1/expected.json)','[expected r2 congelato](../../analisi/riconciliazione_banca_2026-10-05/frozen/expected_r2.json)').replace('## Quali dati usare','[Identità riconciliate e lacune](../../analisi/riconciliazione_banca_2026-10-05/README.md).\nK562 storico disponibile con SHA verificato: [riuso preparato](k562_reuse_r1/ready_r3.json), non ancora caricato.\n\n## Quali dati usare').replace('[dati r2](DATI_DISPONIBILI_r2.md) | 395,75 GB grezzi; storage e contesti distinti','[dati r2, fotografia datata](DATI_DISPONIBILI_r2.md) | 395,75 GB grezzi; non stato corrente né uso nel fit'))
    for name in ['docs/piani/strategia-scientifica.md','docs/piani/piano-giorno-2026-09-30.md','docs/piani/dati-affidabilita.md']:
        edit(name,lambda t:t.replace('RIUSO_r1.md','RIUSO_r2.md'))
    edit('docs/piani/strategia-scientifica.md',lambda t:t.replace('Upload privato dei tre controlli ufficiali resta bloccato', 'Upload privato del cache K562 storico e dei tre controlli ufficiali resta bloccato').replace('**Prossimo passo:** completare/riusare K562 senza duplicare', '**Prossimo passo:** riusare il cache originale K562 (28 MB, SHA storico verificato), pacchetto `k562_reuse_r1/ready_r3.json` pronto; upload privato specifico in attesa di risposta umana dopo rifiuto auto-review. La banca completa K562 prosegue senza duplicare'))
    row='| 05/10 | [riconciliazione_banca_2026-10-05/](riconciliazione_banca_2026-10-05/) | Identità e copertura storage/fit, ledger storico congelato e byte Git corretti; K562 originale verificato e riuso preparato | verifiche tecniche; corpus e upload ancora aperti | ★★★ |\n'
    edit('reports/analisi/README.md',lambda t:t.replace('|---|---|---|---|---|\n','|---|---|---|---|---|\n'+row,1))
    edit('docs/storico/README.md',lambda t:t.replace('|---|---|---|---|\n','|---|---|---|---|\n| 05/10 | [consolidamento_banca_2026-10-05/INDICE.md](consolidamento_banca_2026-10-05/INDICE.md) | Quattro guide complete prima della riconciliazione; copie byte-identiche con manifest | storico; stato corrente R-LEAD |\n',1))
    registry=R/'docs/REGISTRO.md';lines=registry.read_text(encoding='utf-8').splitlines()
    updated=[]
    for line in lines:
        if line.startswith('| `'+S+'` |'):
            line='| `'+S+'` | attuale | — | Storage r10 e producer persistenti; mix parziale concluso 12 fonti/8 sul pannello. Grok r8 terminato. Cache originale K562 recuperato byte-identico e riuso pronto, upload privati K562/controlli in attesa dopo auto-review. Corpus completo/consumer/hash/QC restano aperti | [R-LEAD](piani/strategia-scientifica.md) |'
        if line.startswith('| `docs/piani/strategia-scientifica.md` |'):
            line='| `docs/piani/strategia-scientifica.md` | attuale | — | Coda unica del 5/10: banca persistente, rifit lineare t28 e invio diretto autorizzato; stati/PID precedenti conservati nello storico, nessun nuovo worker dichiarato | — |'
        updated.append(line)
    review='[Riconciliazione](../'+A+'README.md#lettura-dei-report-precedenti)'
    rows=[
      '| `'+A+'` | attuale | — | Verifica metadata, versioni/hash/mount, ledger storico recuperato, byte Git e limiti del consumo; nessuna certificazione di corpus completo | [R-LEAD](piani/strategia-scientifica.md) |',
      '| `docs/storico/consolidamento_banca_2026-10-05/` | storico | `docs/piani/strategia-scientifica.md` | Quattro guide complete e byte-identiche prima del consolidamento; manifest dei file originali | — |',
      '| `'+S+'DATI_DISPONIBILI_r2.md` | da-verificare | — | Dimensioni datate utili; note su training non avviato superate, GB storage non uso del fit | '+review+' |',
      '| `'+S+'TRAINER_r1.md` | storico | `'+S+'RIUSO_r2.md` | Reader neurali e fixture, non launcher lineare corrente; divieti e stato datati non operativi | — |',
      '| `'+S+'TRANSFER_IDENTICO_r1.md` | da-verificare | — | Identità t25/t28 valida; no-VCC superato dal mandato umano INVIO_DIRETTO, senza cambiare ricetta | '+review+' |',
      '| `'+S+'RIUSO_r1.md` | superato | `'+S+'RIUSO_r2.md` | Procedura utile, vecchio inventario vincola un ledger operativo mutato; r2 usa la copia storica byte-identica | '+review+' |',
      '| `'+S+'training_coverage_r1/expected.json` | superato | `'+A+'frozen/expected_r2.json` | Inventario originale preservato; r2 conserva copertura e corregge soltanto il riferimento al ledger congelato | '+review+' |',
    ]
    idx=next(i for i,l in enumerate(updated) if l.startswith('| Percorso | Stato |'))+2
    updated[idx:idx]=rows;registry.write_text('\n'.join(updated)+'\n',encoding='utf-8')
    edit('docs/PIANI.md',lambda t:t.replace('Dal 3 ottobre sera R-LEAD procede su due binari (D-054):\nil **modello**, la rete ancorata al transfer nel pilot v4 e poi sul corpus ampliato; i **dati**,', 'Il mandato corrente di R-LEAD è il rifit del transfer lineare con banca ampliata; il design neurale resta separato. I **dati**,').replace('[R-LEAD — P0–P6]', '[R-LEAD]').replace('Binario del modello (pilot v4, corpus ampliato, conferma P5, finale P6) e binario dei dati (D-053); stato, prossimo passo e job attivi stanno nella sua intestazione','Banca riusabile, rifit lineare t28 e invio autorizzato; copertura D-053 aperta. Stato, prossimo passo e job attivi soltanto nella scheda'))
if __name__=='__main__':main()
