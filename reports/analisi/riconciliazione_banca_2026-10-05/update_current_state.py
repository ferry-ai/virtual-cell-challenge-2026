"""Keep operational state in R-LEAD; dated receipts and protocols remain unchanged."""
from pathlib import Path
R=Path(__file__).resolve().parents[3]
def edit(p,fn):
    p=R/p;p.write_text(fn(p.read_text(encoding='utf-8')),encoding='utf-8')
def main():
    p=R/'docs/piani/strategia-scientifica.md';lines=p.read_text(encoding='utf-8').splitlines();out=[]
    for l in lines:
        if l.startswith('- **Assegnazione:**'):l='- **Assegnazione:** Codex, chat `01a107a9-9c9c-76c2-9161-258f22bd57b1`, workspace `vcc2026`. Unico worker Grok r10 PID21672, stessa sessione `613a1b58-0807-4abe-8dff-be9b67204552`; r1–r9 preservate. Parent verifica e pusha pacchetti; worker non lancia job.'
        if l.startswith('- **Autorizzazione:**'):l='- **Autorizzazione:** [invio diretto](../../reports/modelli/percorso_riusabile_2026-10-05/INVIO_DIRETTO_r1.md) senza banco predittivo. Dopo i rifiuti auto-review, consenso SPECIFICO ricevuto per cache K562+Gencode e tre controlli nei due dataset privati df11: entrambi caricati, [prove](../../reports/modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r13.md). Nessun nuovo push Git implicito o servizio a pagamento.'
        if l.startswith('- **Misurato:**'):l='- **Misurato:** [mix parziale precedente](../../reports/modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r12.md): 12 fonti/8 con target. Nuovo consumer si ferma su SE KOLF; difetto di maschera r4 riprodotto contro AxisTable originale. COMPLETE provider non certifica parità scientifica. K562 storico esatto è disponibile, caricato privato, ancora non consumato in un fit riuscito: [stato/prove r13](../../reports/modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r13.md).'
        if l.startswith('- **Prossimo passo:**'):l='- **Prossimo passo:** Grok prepara immediatamente successor production-only con maschera originale per HCT/HEK/4KOLF, banche già pronte; parent verifica/pusha con preflight e dedup. In parallelo cerca altre statistiche vecchie/nuove compatibili. Non rilanciare `vcc-refit-t28-bank-k562-reuse-r1`, fix1 o fix2 ERROR. Non indebolire guardie SE né inventare valori. Nuova ingestion GWPS attiva separatamente: non duplicare/fermare senza prova.'
        out.append(l)
    index=next(i for i,l in enumerate(out) if l.startswith('- **Percorso completo'))
    out.insert(index,'- **Orario concordato:** 5 ottobre, freeze fonti entro **23:30 Europe/Rome**, poi rifit finale/generazione senza attendere altre ingestion; obiettivo upload entro **02:00 del 6 ottobre**, non promessa. Pacchetti pronti partono subito; ultima release ammette solo fonti verificate, altre restano blocchi nominati. Nessuna aggiunta silenziosa durante generazione.')
    p.write_text('\n'.join(out)+'\n',encoding='utf-8')
    edit('docs/PROGETTO.md',lambda t:t.replace('generazione non ancora avviata', 'generazione non ancora avviata').replace('controlli bloccato dall’auto-review','controlli autorizzato specificamente e completato').replace('controlli bloccato dall\'auto-review','controlli autorizzato specificamente e completato'))
    edit('reports/modelli/percorso_riusabile_2026-10-05/README.md',lambda t:t.replace('[mix concluso e generazione](ESECUZIONE_r12.md)','[cache K562, guardia maschere e freeze](ESECUZIONE_r13.md)').replace('non ancora caricato','caricato privato; guardia maschere da correggere prima del fit finale'))
    edit('docs/REGISTRO.md',lambda t:t.replace('Grok r8 terminato. Cache originale K562 recuperato byte-identico e riuso pronto, upload privati K562/controlli in attesa dopo auto-review.','Grok r10 unico worker. Cache K562 byte-identico e controlli caricati con consenso specifico; guardia SE blocca consumer, adapter originale da ripristinare prima del freeze23:30.'))
if __name__=='__main__':main()
