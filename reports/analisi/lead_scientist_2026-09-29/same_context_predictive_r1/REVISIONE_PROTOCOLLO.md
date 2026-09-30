# Stato dopo la review scientifica

29 settembre 2026, prima di qualsiasi ingestione reale o fit di questa revisione.
Protocollo iniziale SHA256
`56035834a8bed466c002676661e547880cac76a0c355e756297e35e33376d74e`.

Il revisore `audit_scientifico` conferma coerenza del confronto predittivo,
esclusione globale delle guide riservate, partizione per canale, aggregazione
guida→bersaglio→stato e distinzione tra previsione multi-perturbata ed effetto
causale singolo. Parser e test sintetici non stimano alcun effetto.

**Due contratti restano da risolvere prima del fit**, quindi il documento
iniziale è una proposta congelata, non un'autorizzazione ad avviare il modello:

1. Identità e conversione numerica del prior esterno alla scala log1p(CP10K),
   con verifiche sulla maschera e assi.
2. Null operativo: una stessa guida compare in molti strati di cellule.
   Permutare guida→target separatamente in ogni strato produce mapping
   incoerenti; farlo globalmente non garantisce il rispetto degli strati.

Proposta del revisore: mantenere D, co-guide e nuisance fissi e permutare i
vettori di correzione tra bersagli abbinati per esposizione/supporto. Vanno
fissati prima degli outcome abbinamento, trattamento dei mancanti e quali
parametri vengono rifittati. Finché non lo sono, non è implementabile il gate
del 95º percentile indicato nel protocollo. La permutazione è una sensibilità,
non un test esatto senza giustificazione di scambiabilità; 20 permutazioni
offrono risoluzione minima 1/21, non p-value di precisione maggiore.

Stato operativo: quattro test tiny superati sul parser, sulle esclusioni e sul
rischio appaiato. Contratto privato del solo primo canale preparato con 15 input
e 179.180.168 byte raw, senza ingestione o hash completo dei raw rieseguito.
Si attende il completamento del recupero VCC e la verifica dello spazio prima
di qualunque ingestione. Nessun cloud, fit o candidato prodotto.
