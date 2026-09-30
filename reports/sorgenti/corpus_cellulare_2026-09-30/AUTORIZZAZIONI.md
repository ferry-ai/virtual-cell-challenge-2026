# Autorizzazioni del proprietario per R-LAB

Trascritte da Claude (sessione `a1ec75f0`) dalle risposte del proprietario in chat, ricevute prima
delle 19:38 del 30/09 (ora letta con `date` subito dopo). Valgono per questa sessione e per i job
qui elencati; un agente nuovo le conferma in chat prima di usarle (`CLAUDE.md`).

| Domanda | Risposta del proprietario |
|---|---|
| Dove salvare in modo persistente gli shard delle cellule | **Google Drive** (prima si misura la quota libera dal runtime) |
| Via ai job J01–J03 di `PIANO_JOB.md` | **Sì, J01–J03**: J01 HepG2 dal Drive; J02 HIPSCI scaricato da Figshare sul runtime (7,93 GB, MIT); J03 Jurkat scaricato dal GEO (circa 3,8 GB); su Colab o Kaggle, con preflight |
| Account Colab e Kaggle | **Più account, confermato**: il proprietario conferma che l'uso degli altri account rispetta i termini dei servizi |
| Riserva | **Sì, H1 2025 come riserva**: prima locatore e byte da mostrare al proprietario, poi download congelato con hash, da leggere una volta sola |

Non autorizzati da queste risposte: i job J04–J12 e i loro download, un invio, un push.

**Conferma alla sessione successiva.** La sessione `a1ec75f0` ha esaurito i token dopo aver scritto
questo file. La sessione di Claude Code che l'ha ripresa (`ec2e5b07`) ha chiesto al proprietario di
confermare le autorizzazioni prima di usarle. Risposta in chat, prima delle 20:00 del 30/09 (ora
letta con `date` alle 20:00:21, subito dopo): «Certo confermo, anche la disponibilità di vari account
colab e kaggle». La conferma copre J01–J03 su Colab con shard su Drive, i download sul runtime di
HIPSCI (Figshare) e di Jurkat (GEO), e H1 2025 prima con locatore e byte mostrati, poi scaricato.
Restano esclusi invii e push.
