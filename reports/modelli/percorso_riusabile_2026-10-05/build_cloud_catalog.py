"""Index verified archives and derivatives; never ingest or download matrices."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from pipeline_state import REPO, sha
from release_lock import resolve

HERE = Path(__file__).resolve().parent


def checked_artifact(item):
    if item['state'] != 'remote_complete_manifest_checked':
        raise ValueError('artifact not verified')
    receipt = REPO/item['receipt']
    if sha(receipt) != item['receipt_sha256'] or not item['saved_version']['version_ref']:
        raise ValueError('artifact identity changed')
    result = dict(item)
    result['account'] = item['kernel'].split('/')[0]
    result['url'] = 'https://www.kaggle.com/code/'+item['kernel']
    result['mount_selection'] = 'explicit kernel and relative_path; receipt SHA required'
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    inputs={name:HERE/path for name,path in {
        'cd4':'release_cd4_r5.json','other':'snapshot_other_r2/state.json',
        'launches':'other_sample_launches.jsonl','axis':'axis_binding_r1.json',
        'kolf_axis':'kolf_axis_r1.json','inventory':'snapshot_r11/state.json'}.items()}
    cd4=json.loads(inputs['cd4'].read_text());other=json.loads(inputs['other'].read_text())
    units={}
    for unit, entry in cd4['units'].items():
        raw=entry['raw']
        if sha(REPO/raw['receipt'])!=raw['sha256']:raise ValueError('raw archive changed')
        units[unit]={**entry,'bank':checked_artifact(entry['bank']),
                     'samples':checked_artifact(entry['samples'])}
        units[unit]['samples']['relative_path']='samples/'+unit
    for unit, info in other['units'].items():
        raw_ref = HERE/(('kolf' if unit=='kolf_pan_genome' else
                         'hct116' if unit=='orion_hct116' else 'hek293t')+'_bank_stage_r1/prepared.json')
        prepared=json.loads(raw_ref.read_text())
        raw_receipt=REPO/prepared['source_receipt']
        if sha(raw_receipt)!=prepared['source_receipt_sha256']:raise ValueError('raw archive changed')
        raw={'state':'verified','receipt':prepared['source_receipt'],
             'sha256':prepared['source_receipt_sha256'],'spec':prepared['spec'],
             'kernel_sources':json.loads((raw_ref.parent/'kernel-metadata.json').read_text())['kernel_sources'],
             'raw_version_policy':'manifest and shard SHA bind identity; never infer revision from slug alone'}
        bank=checked_artifact(info);bank['relative_path']='bank/'+unit
        units[unit]={'raw':raw,'bank':bank,'samples':{'state':'partitions_pending_verification','parts':[]},
                     'trainer':{'state':'not_integrated','training_used':False}}
    launches=[json.loads(x) for x in inputs['launches'].read_text().splitlines()]
    for stage in sorted((HERE/'other_sample_stages').iterdir()):
        frozen=json.loads((stage/'prepared.json').read_text()); params=frozen['parameters']
        matches=[r for r in launches if r['parameters']==params and r['accepted']]
        if len(matches)>1:raise ValueError('duplicate partition across accounts')
        item={'part':params['part'],'parts':params['parts'],
              'bank_receipt_sha256':params['bank_receipt_sha256'],'code_sha256':frozen['code_sha256'],
              'state':'launched_output_not_verified' if matches else 'not_launched',
              'kernel':matches[0]['slug'] if matches else None,'saved_version':None,
              'receipt_sha256':None,'relative_path':'samples/'+params['unit']}
        units[params['unit']]['samples']['parts'].append(item)
    inventory=json.loads(inputs['inventory'].read_text())
    catalogue={'schema':1,'created_utc':datetime.now(timezone.utc).isoformat(),
       'scope':'Verified current archive branch: CD4, KOLF, HCT116, HEK293T; full scientific catalogue remains open',
       'training_ready':False,'fallback_to_legacy':False,'units':units,
       'catalogue_records':inventory['catalogue'],
       'legacy_classification':{'davideferrante11/rlead-bench-cube-r2':
           'reduced aggregate pilot; never substitute for donor banks or sampled cell matrices'},
       'historical_sources':'Preserved in catalogue_records; explicit role/version/provenance required before training. Age alone never excludes.',
       'storage_policy':'Kaggle saved outputs are the reusable archive. Local matrices optional; repo stores receipts and index.',
       'reuse_policy':'Reuse when raw hashes, nominal axis, QC, code and parameters match. New sources add only their own derivatives; new release preserves old versions.',
       'consumer_policy':'Pin this manifest SHA in run/checkpoint. Verify receipt then consumed-file hashes in runtime. Pending partitions reject training use. Resume must retain pinned identity.',
       'sources':[{'path':str(f.relative_to(REPO)).replace('\\','/'),'sha256':sha(f)} for f in inputs.values()]}
    a.out.mkdir(parents=True,exist_ok=False)
    manifest=a.out/'manifest.json';manifest.write_text(json.dumps(catalogue,indent=1)+'\n',encoding='utf-8',newline='\n')
    # Metadata-only validation of every already verified bank/sample through the existing resolver.
    for unit,entry in units.items():
        for kind in ('bank','samples'):
            item=entry[kind]
            if item['state']=='remote_complete_manifest_checked':
                resolve(manifest,sha(manifest),unit,kind,(REPO/item['receipt']).parent)
    lines=['# Dove sono archivio, banche e campioni','',
           'Indice attuale delle 15 unità verificate. Corpus completo e trainer esteso ancora da integrare.',
           '','Manifest: `manifest.json`; SHA256: `'+sha(manifest)+'`. Nessuna ingestion eseguita per crearlo.',
           '','| Unità | Banca persistente | Campioni |','|---|---|---|']
    for unit,e in units.items():
        s=e['samples'];status='completi, versione '+str(s['saved_version']['version']) if s['state']=='remote_complete_manifest_checked' else 'parti '+str(sum(x['kernel'] is not None for x in s['parts']))+'/'+str(len(s['parts']))+' lanciate; chiusura da verificare'
        lines.append('| '+unit+' | ['+e['bank']['kernel']+']('+e['bank']['url']+') | '+status+' |')
    lines+=['','Grezzi: per ogni unità il manifest conserva notebook sorgente, ricevuta di ingestione e hash.',
            'Ogni banca ha account, versione salvata, percorso interno e hash della ricevuta; questa contiene gli hash dei file.',
            'I campioni CD4 sono matrici autonome; per le nuove sorgenti le parti ancora aperte non sono certificate persistenti.',
            '','`rlead-bench-cube-r2` resta il cubo del pilot. Nessun fallback automatico per nomi uguali o file mancanti.',
            '','Per aggiungere un dataset: aggiungere la sua voce e i suoi derivati, poi creare una nuova revisione del manifest.',
            'Rigenerare solo ciò che dipende da un asse, QC, normalizzazione o split cambiato. Non ripetere i grezzi invariati.',
            '','Il manifest è un indice e un vincolo di identità, non una copia dei dati né un trainer già integrato.']
    (a.out/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'units':len(units),'sha256':sha(manifest),'training_ready':False,
                      'verified_resolutions':27,'path':str(manifest)}))


if __name__=='__main__':main()
