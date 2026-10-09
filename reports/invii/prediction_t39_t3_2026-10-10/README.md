# t39: T38/T3 con ESM2 soltanto nei vuoti

**Decisione del Lead, 10 ottobre 2026, prima della generazione:** usare come base
il transfer ampliato T3 già inviato come t38. Il proprietario ha autorizzato
l'invio («ok decidi tu, vai e inviamo») e poi richiamato l'età della base t36.
Il Lead ha annunciato il passaggio a T3. La precedente
[preregistrazione T0](../prediction_t39_2026-10-10/prediction.json) resta conservata;
quel candidato non è stato generato, secondo la consegna del Lead.

La [previsione](prediction.json) fissa banda soggettiva **0,125–0,170**, delta
atteso zero e soglia operativa **±0,005 rispetto a t38 (0,14892212354470022)**.
t36 resta confronto secondario. La banda non è un intervallo di confidenza,
e un singolo risultato favorevole non promuove stabilmente il metodo.

Il ridge ESM2 è già addestrato e le predizioni native sono congelate. La regola
nuova copia T3 e applica `float32(1.576 * E2)` soltanto dove T3 non prevede e
il ridge ha supporto. Non usa la vecchia maschera T0. I controlli sugli input,
comunicati al Lead dall'auditor indipendente, indicano **380.820 coppie da
riempire**, 299 bersagli e 4.231 geni di risposta. Le 4.467.808 coppie già
previste da T3 restano invariate; il supporto finale atteso è 4.848.628 coppie.
Questi conteggi non sono una verifica del file finale ancora da produrre.

**Prima di generare:** DATI deve fissare percorso, byte e SHA256 del nuovo
`T3_E2_fallback.npz` in una ricevuta separata e verificarne formula, assi e
parità con T3 sul suo supporto. La previsione lascia esplicitamente questi
campi finali a `null`. L'[audit](technical_audit_r1.json) distingue input
controllati e candidato finale pendente. Il Lead registra e committa i documenti.

Il generatore resta quello di t38: scala 1,5, dispersione genica a scala 1,
seed 20260912 e 400 cellule per bersaglio e contesto. La scala 1,576 del solo
riempimento e quella 1,5 dell'emissione sono passaggi distinti; niente seconda
applicazione del cis o dell'ampiezza della base.

Il banco a sei membri disponibile riguarda **T0+ESM2**, non questo ibrido:
su iPSC il delta medio contro T0 è +0,0074 ±0,0168, non risolto; il confronto
con il riempimento scambiato distingue il bersaglio. È una motivazione per
un invio esplorativo, non validazione trasferibile a T3+ESM2. Restano pertinenti
[S-013 e S-015](../../../docs/STRADE.md), e il risultato
[t38](../../../docs/checkpoints/0074-t38-crispri-piu-ko-punteggio-ufficiale.md)
non prova che T3 sia stabilmente superiore a t36. Copertura D-053 ancora aperta.

DATI-TRANSFER resta unico owner di generazione, packaging e upload. AMMI prosegue.
I [testi nuovi](../trial_2026-10-10/submission_texts_t39_t3_r1.md) sostituiscono
operativamente quelli T0 per questo invio; i vecchi testi non vengono modificati.
