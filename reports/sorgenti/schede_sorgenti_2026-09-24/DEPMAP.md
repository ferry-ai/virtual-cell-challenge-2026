# File pubblici DepMap (claude2, run `20260924-222758-depmap-files`), testo dell'agente senza modifiche

The latest DepMap release I could confirm is **DepMap Public 26Q1 (1 April 2026)**, but I could not get its file list: the DepMap portal only showed an access-check page. The newest release on Figshare is **24Q4**, and I have verified file names, sizes, URLs and licence for that one.

I ran no shell commands, downloaded no data files and changed nothing on disk. Sources were web searches and page fetches. Each page was read through a small summarising model, which made at least two extraction errors (item 4), so every value below should be re-checked.

**1. Release**
- 26Q1 was released on 1 April 2026: https://forum.depmap.org/t/announcing-the-26q1-release/4606 — **measured**
- A DepMap staff reply says the schedule is 26Q1 and 26Q3, with no 26Q2 release: https://forum.depmap.org/t/depmap-26q2-release/4569 — **measured**
- I found no 26Q3 announcement as of 24 September 2026. The forum category I read was Q&A, not Announcements, so I am not sure 26Q3 is unreleased — **measured / inferred**
- Releases from 25Q2 onward are not put on Figshare. DepMap's recommended listing is `https://depmap.org/portal/api/download/files`, a CSV of all files with signed URLs that expire (https://forum.depmap.org/t/bulk-download-of-25q2-files/4443) — **measured**
- That endpoint returned only the access-check page to me.

**2. Files: DepMap 24Q4 Public on Figshare+**
- Published 10 Dec 2024, DOI 10.25452/figshare.plus.27993248.v1, page https://plus.figshare.com/articles/dataset/DepMap_24Q4_Public/27993248 — **measured**, from `api.figshare.com/v2/articles/27993248`

| File | Bytes | URL |
|---|---|---|
| OmicsExpressionProteinCodingGenesTPMLogp1.csv | 506,628,654 | https://ndownloader.figshare.com/files/51065489 |
| OmicsCNGene.csv | 1,394,554,236 | https://ndownloader.figshare.com/files/51065324 |
| Model.csv | 645,696 | https://ndownloader.figshare.com/files/51065297 |
| OmicsProfiles.csv | 254,733 | https://ndownloader.figshare.com/files/51065723 |
| OmicsDefaultModelProfiles.csv | 90,080 | https://ndownloader.figshare.com/files/51065339 |

- **Format and orientation:** all are CSV. From memory, in the expression and copy-number files rows are models (ACH-IDs) and columns are genes named "SYMBOL (EntrezID)". I did not check this — **unverified**
- **26Q1 names:** the 26Q1 announcement names `Models.csv`. A forum topic title names `OmicsCNGeneWGS.csv`, which suggests the copy-number file was renamed — **measured names, inferred meaning**

**3. Licence**
- The 24Q4 Figshare record says "CC BY 4.0", https://creativecommons.org/licenses/by/4.0/ — **measured**
- I could not read the portal's own terms for 26Q1. The forum has a thread "CCLE/Depmap License Clarification" dated 16 Sep 2026 that I did not open — **unverified**

**4. Model IDs**
These come from Cellosaurus DepMap cross-references (api.cellosaurus.org), not from the release's Model.csv — **measured from Cellosaurus only**
- K-562 ACH-000551
- HCT 116 ACH-000971
- DLD-1 ACH-001061
- A-549 ACH-000681
- MCF-7 ACH-000019
- HT-29 ACH-000552
- BxPC-3 ACH-000535
- Jurkat ACH-000995
- THP-1 ACH-000146
- MOLT-4 ACH-001127
- HeLa ACH-001086
- SiHa ACH-000556
- Ca Ski ACH-001336
- FaDu ACH-000846
- CAL-27 ACH-000832
- SCC-25 ACH-000188 (seen only in the first, summarised read; a later verbatim read left it out)
- **NCI-H520: conflicting.** One read gave ACH-000395, another gave ACH-001336, which is Ca Ski's ID. Treat it as unverified.
- **No DepMap cross-reference:** HAP-1 and HEK293T. Their status in Model.csv is unknown.
- **Not checked:** the KYSE lines.

**Not done / open questions**
- 26Q1 file sizes, URLs and orientation. They need a browser session on the portal, or someone reading the `/api/download/files` CSV.
- Confirming every ID against Model.csv (645 KB, small enough to download).
- **Memory risk:** OmicsCNGene.csv (1.39 GB) is large for 8.4 GB of RAM. It should be read in chunks, or only the needed columns loaded — **inferred**
