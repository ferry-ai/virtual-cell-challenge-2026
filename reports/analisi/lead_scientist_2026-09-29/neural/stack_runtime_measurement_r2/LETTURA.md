# Stack072: modello caricato, esito ancora da misurare

29 settembre 2026. **Misurato dai manifest prodotti dal job072:** l'import di
Stack/scvi è riuscito dopo la sola aggiunta di `pooch==1.8.2`. I freeze confrontati
non mostrano rimozioni o altre aggiunte (`runtime_repair_diff.json`). I due file
ufficiali del modello corrispondono ai byte e agli SHA congelati
(`verified_model_files.json`).

`inference_manifest.json` è scritto dopo il caricamento CPU, il trasferimento
GPU e `eval()`: il percorso ha dunque caricato il modello sulla Tesla T4.
Parametri effettivi: **217.806.513**. Memoria GPU dichiarata da PyTorch:
15.637.086.208 byte. Supporto realmente condiviso fra K562, HepG2 e Stack:
**5.179 geni su 15.012** geni del modello. Questi numeri non misurano la qualità
delle predizioni né la copertura dell'intero asse dello scorer; fuori dal supporto
comune l'adapter mantiene la baseline congelata.

Immediatamente prima del loader, alle 19:33:43 UTC, erano disponibili
11.487.318.016 byte di RAM CPU e 50.478.850.048 byte di disco locale
(`resources_before_checkpoint_load.json`). La guardia richiedeva 6 GiB RAM.
Questa è una misura precedente al caricamento, **non il picco RAM o VRAM**.
I componenti tensoriali elencati nel manifest sono calcolati dalle dimensioni e
non sostituiscono una misura di picco.

Al momento di questa acquisizione l'inferenza era iniziata. Non si dichiara un
pilot completato, un miglioramento o l'assenza di HepG2 dal pretraining. I file
copiati qui sono piccoli manifest e log; nessun peso o matrice cellulare è incluso.
