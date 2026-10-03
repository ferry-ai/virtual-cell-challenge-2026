# Tentativo v1: senza GPU

2 ottobre 2026. La versione 1 del kernel `alfredo2003bit/rlead-training-r1` è stata inviata alle 20:17 circa, con
`enable_gpu` e `machine_shape` NvidiaTeslaT4. È finita in ERROR alle 20:23.

**Misurato** (`env.json`):
- il runtime non aveva GPU: `nvidia-smi: not found`, torch `2.10.0+cpu`, `cuda` falso;
- gli shard, il codice e lo stato del prepass sono stati trovati e verificati (`verify.json`).

**Come è fallito.**
1. Il primo run del ciclo di ripresa si è fermato sul primo tensore CUDA, con
   `AssertionError: Torch not compiled with CUDA enabled` (`cycle_ref.log`).
2. Il kernel è poi caduto cercando un checkpoint che non era stato scritto (`rlead-training-r1.log`).

Non è stato addestrato nulla e non è stata usata quota GPU.

**Causa probabile** (ipotesi): l'account non ha ancora accesso alla GPU. Kaggle la concede solo dopo la verifica del
telefono. Kaggle non ha rifiutato il kernel: lo ha eseguito senza acceleratore.

**Correzione al launcher** (`cellnet_rlead_2026-10-01/kaggle_train.py`): se il kernel chiede una GPU e il runtime
non ne ha, si ferma subito, prima di montare i dati, con un messaggio esplicito.

La regola di lettura del [protocollo](../PROTOCOLLO.md) non cambia. Il training si rilancia come nuova versione dello
stesso kernel, quando l'account avrà la GPU.
