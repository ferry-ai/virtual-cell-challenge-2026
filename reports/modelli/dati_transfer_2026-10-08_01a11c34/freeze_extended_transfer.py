"""Freeze the CRISPRi plus KO transfer contrast from verified metadata only."""
import csv
from pathlib import Path
from percorso import DATA, HERE, read, pin, sha, write_new, now

UNITS = ['a549_ko','frangieh2021','sunshine2023','dixit2016_d7',
         'dixit2016_d13','dixit2016_high_moi','shifrut2018']


def main():
    with (DATA/'raw/controls/pert_counts.csv').open() as f:
        panel=[r['target_gene'] for r in csv.DictReader(f)]
    sources=[]; targets=set(); profiles=0; chunks={}
    for unit in UNITS:
        folder=HERE/'alltargets/01a11c34-r3'/unit
        found=list(folder.glob('completion_*/verification.json'))
        if len(found)!=1: raise ValueError('one verified production completion required: '+unit)
        verification=read(found[0]); receipt_path=found[0].with_name('effect_release.json')
        if sha(receipt_path)!=verification['receipt']['sha256']: raise ValueError('changed receipt')
        receipt=read(receipt_path); prepared=read(folder/'prepared.json')
        if receipt['split']['regime']!='production': raise ValueError('wrong split')
        producer=prepared['slug']; contexts=[]
        for i,c in enumerate(receipt['contexts']):
            if c['identity']['modality']!='KO': raise ValueError('non-KO source in KO arm')
            overlap=sorted(set(c['targets_derived']) & set(panel))
            if c['status']!='derived' or not c['controls_cells']: raise ValueError('unusable KO context')
            targets.update(overlap); profiles+=len(overlap)
            offsets=0; relevant=[]
            for chunk in c['chunks']:
                chunk_targets=c['targets_derived'][offsets:offsets+chunk['targets']]
                offsets+=chunk['targets']
                if set(chunk_targets)&set(panel):
                    filename='effects/'+chunk['file']; spec=receipt['outputs'][filename]
                    key=producer+'/'+filename
                    chunks[key]=dict(producer=producer,file=filename,bytes=spec['bytes'],sha256=spec['sha256'],
                        unit=unit,context=i,targets=chunk_targets,identity=c['identity'])
                    relevant.append(key)
            if offsets!=len(c['targets_derived']): raise ValueError('chunk target inventory mismatch')
            contexts.append(dict(context_index=i,identity=c['identity'],donors=c['donors'],
                controls_cells=c['controls_cells'],panel_targets=overlap,relevant_chunks=relevant,
                derived_targets=len(c['targets_derived']),status=c['status']))
        sources.append(dict(unit=unit,producer=producer,receipt=pin(receipt_path),
            verification=pin(found[0]),bank=receipt['bank'],contexts=contexts))
    plan=dict(utc=now(),candidate='T3-CRISPRi-KO',version='r1',
        status='frozen_before_effect_array_read_or_fit',baseline=pin(HERE/'candidate_t1_r1.json'),
        t1_release=pin(HERE/'release_t1_r1.json'),
        official_panel=pin(DATA/'raw/controls/pert_counts.csv'),
        genes=pin(DATA/'raw/controls/gene_names.csv'),
        policy=dict(core='exact T1 source tables, centering, weights and reliability; reproduce byte hashes first',
            ko_centering='none: matched-control contrasts; no panel mean that would erase singleton STAT6',
            ko_estimates='use existing per-context shrunk effects and measured masks; no new shrinkage after pooling',
            ko_qc='exact singleton labels, matched controls, existing min_cells=10, finite nonnegative SE; no own-RNA-sign gate',
            pooling='within each study and lineage, reliability-weighted average over contexts using n/(n+100); keep identities and consumption receipts',
            ko_study_vote_weight=0.25, ko_study_reliability='maximum contributing context reliability per target and gene; never summed over replicates',
            rationale='fixed quarter-weight prior for an unvalidated distinct loss-of-function mechanism; not optimized against scores or new effects',
            combination='add KO numerator and denominator to pre-amplitude CRISPRi mixture; then original amplitude and cis once',
            amplitude=1.576,cis='unchanged t36 max_distance=5000 scale=2',emitter_scale=1.5,
            crispr_a='excluded from this loss-of-function estimator; no automatic sign reversal',
            protected_units=['h1_test'],claims_complete_D053=False,
            off_panel='retained in derived bank and ESM2 views; no false same-target prediction contribution'),
        sources=sources,chunks=chunks,counts=dict(ko_bank_units=len(sources),
            ko_contexts=sum(len(s['contexts']) for s in sources),
            ko_study_lineage_votes=len({(c['identity']['study'],c['identity']['line_group']) for s in sources for c in s['contexts']}),
            new_panel_targets=len(targets),panel_context_profiles=profiles,
            required_chunks=len(chunks),required_bytes=sum(c['bytes'] for c in chunks.values())),
        panel_targets=sorted(targets),
        precedents=['S-010: no new pseudo-replicate votes; T1 control preserved',
            'S-011: singleton KO is not centered to zero',
            'S-012: CRISPRi panel centering unchanged; no all-target common substitution',
            'S-006: uncentered KO common burden remains a risk, bounded by fixed weak study votes'],
        technical_abort=['T1 null parity failure','missing required KO context or chunk','axis/hash/mask mismatch',
                         'nonfinite values or negative SE on measured pairs','no actual KO contribution'],
        scientific_status='exploratory, no promotion; independent validation may flag failure but no weight tuning',
        authorization=dict(thread='01a11c05-970e-7af2-a07e-3860bd74acbd',
            human_all_sources='01a11d81-e023-7063-839d-b29d4a65e570',
            human_fast_submission='01a11d78-c711-7cb1-9f28-fdcf26fbffa2',
            no_T1_launch=True,no_ESM2_interruption=True))
    write_new(HERE/'extended_transfer/r1/protocol.json',plan)
    print(__import__('json').dumps(dict(counts=plan['counts'],panel_targets=plan['panel_targets'],
                                      protocol=pin(HERE/'extended_transfer/r1/protocol.json'))))


if __name__=='__main__': main()
