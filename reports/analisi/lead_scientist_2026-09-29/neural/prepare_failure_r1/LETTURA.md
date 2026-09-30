# Preparazione Stack r1: mancata verifica dei fine-riga

Misurato il 29 settembre 2026: il job 063 si è fermato dopo `plan`, prima di
leggere le cellule. `job063.log` conserva il log originale. Il piano remoto ha
1.069 byte LF; il piano locale congelato ha 1.110 byte CRLF. I JSON sono uguali in
ogni campo; sostituire CRLF con LF rende identici anche i byte. Bersagli, hash degli
input, adapter e protocollo sono invariati. Non è un cambiamento del disegno.

Il retry `../colab_stack_prepare_r2.sh` usa lo stesso archivio congelato, nuove
cartelle e confronto semantico di tutti i campi. Il bundle continua a registrare
anche l'hash dei byte del piano realmente letto.
