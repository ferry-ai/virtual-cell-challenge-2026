# Rapporto integrale — antigravity

Agente: antigravity. Run: 20261005-132632-predittori-web. Modalità: read. Modello: non registrato (campo model null in meta.json). Brief: control/briefs/predittori-blocchi-web-2026-10-05.md nell'agent-hub, fuori da questo repository. Exit 0. Durata 211,1 s. Inizio 2026-10-05T13:26:32+02:00, fine 2026-10-05T13:30:03+02:00. Caratteri: 6467.

Il testo sotto è il rapporto originale. È una pretesa finché il catalogo non lo verifica. La lettura adottata è in ../CATALOGO.md.

---

I successfully cataloged twelve single-cell perturbation prediction models from 2023–2026 via web search, extracted their details, and ranked three for testing against a frozen anchor.

Using `search_web`, I found the following models (all claims about their attributes are **measured** from search snippets unless labeled otherwise):

1. **scELMo**
- GitHub: `https://github.com/HelloWorldLTY/scELMo`
- Module: "not named in the snippet"
- Context: Tested unseen cell context and unseen gene.
- Weights: Public.
- License: MIT License.
- Shared shift: The LLM embeddings for genes could be uniformly shifted, applying a shared contextual bias across all targets (**inferred**).

2. **scDisInFact**
- GitHub: `https://github.com/ZhangLabGT/scDisInFact`
- Module: "not named in the snippet"
- Context: Tested unseen conditions (contexts).
- Weights: "not named in the snippet" (**unverified**).
- License: "not named in the snippet" (**unverified**).
- Shared shift: The unshared biological factors might collapse to a mean shift, applying the same transformation across all conditions (**inferred**).

3. **MultiFlow**
- GitHub: `https://github.com/liuq-lab/MultiFlow`
- Module: "not named in the snippet"
- Context: Tested unseen cellular contexts.
- Weights: "not named in the snippet" (**unverified**).
- License: CC-BY 4.0.
- Shared shift: The flow-matching process could learn a dominant constant vector for perturbation velocity, translating all cells equally (**inferred**).

4. **scDFM**
- GitHub: `https://github.com/AI4Science-WestlakeU/scDFM`
- Module: PAD-Transformer (Perturbation-Aware Differential Transformer)
- Context: Tested unseen perturbation and combinatorial contexts.
- Weights: Public.
- License: MIT License.
- Shared shift: The PAD-Transformer might attend uniformly to the perturbation condition, applying a flat residual shift to all control states (**inferred**).

5. **DynPerturb**
- GitHub: `https://github.com/BGIResearch/DynPerturb`
- Module: "not named in the snippet"
- Context: Tested unseen cell contexts and unseen genes.
- Weights: "not named in the snippet" (**unverified**).
- License: MIT License.
- Shared shift: The temporal encoding or memory module might default to an average perturbation state, applying the same update everywhere (**inferred**).

6. **UNAGI**
- GitHub: `https://github.com/mcgilldinglab/UNAGI`
- Module: VAE-GAN
- Context: Tested unseen complex disease states.
- Weights: "not named in the snippet" (**unverified**).
- License: "not named in the snippet" (**unverified**).
- Shared shift: The GAN generator might suffer from mode collapse, producing a single generic perturbation vector regardless of the input (**inferred**).

7. **SLIM**
- GitHub: `https://github.com/RasmussenLab/SLIM`
- Module: "not named in the snippet"
- Context: Tested unseen perturbations.
- Weights: "not named in the snippet" (**unverified**).
- License: "not named in the snippet" (**unverified**).
- Shared shift: The ridge-regression estimator could learn a large intercept or a single dominant principal component, shifting all predictions equally (**inferred**).

8. **veloAgent**
- GitHub: `https://github.com/mcgilldinglab/veloAgent`
- Module: in silico perturbation module
- Context: Tested unseen cell and unseen gene weights via transfer learning.
- Weights: "not named in the snippet" (**unverified**).
- License: "not named in the snippet" (**unverified**).
- Shared shift: The agent-based model might assign a uniform transition rule to all cells when simulating an intervention (**inferred**).

9. **CoupleVAE**
- GitHub: `https://github.com/LiminLi-XJTU/CoupleVAE`
- Module: VAE class
- Context: Only unseen gene in a seen context (struggles with unseen cell types).
- Weights: "not named in the snippet" (**unverified**).
- License: "not named in the snippet" (**unverified**).
- Shared shift: The coupled decoders could map the latent difference to a constant offset in the ambient gene space (**inferred**).

10. **UniPert**
- GitHub: `https://github.com/lynn-1998/UniPert-G2CP_reproduce`
- Module: G2CP
- Context: Tested unseen gene perturbations and drug treatments.
- Weights: Public.
- License: "not named in the snippet" (**unverified**).
- Shared shift: The multimodal representation model could map all perturbations to a dense cluster, causing the decoder to output a shared mean effect (**inferred**).

11. **CaLMFlow**
- GitHub: `https://github.com/van-dijk-lab/calmflow`
- Module: "not named in the snippet"
- Context: Tested unseen conditions.
- Weights: "not named in the snippet" (**unverified**).
- License: "not named in the snippet" (**unverified**).
- Shared shift: The causal language model could output a uniform flow trajectory for all cells if the conditioning signal is weak (**inferred**).

12. **PertAdapt**
- GitHub: `https://github.com/BaiDing1234/PertAdapt`
- Module: condition-sensitive attention mechanism
- Context: Tested unseen cellular contexts.
- Weights: "not named in the snippet" (**unverified**).
- License: "not named in the snippet" (**unverified**).
- Shared shift: The adapter could overfit to the mean perturbation effect, turning the attention mechanism into a static bias (**inferred**).

**Ranked three to try first against a frozen anchor:** (**inferred**)
1. **scDFM**: Its PAD-Transformer block explicitly learns perturbation-aware differences.
2. **PertAdapt**: Its condition-sensitive attention mechanism acts perfectly as a plug-in residual adapter.
3. **MultiFlow**: Flow matching inherently predicts a vector field, making it easily adaptable as a residual.

**Early measurement that should stop each one:** (**inferred**)
For all three models, measure the variance of the predicted residual shifts across a batch of diverse targets; if the variance approaches zero (or if the pairwise cosine similarity approaches 1), training should be stopped early as this indicates mode collapse to a shared mean.

**What I did not do or could not verify:**
- I did not run commands, read local files, or open URLs to fetch exact source code files (**measured**).
- I could not verify the exact file names, classes, weights availability, or licenses for some models because they were not named in the search snippets (**measured**).

**Open questions for Claude1:**
- What specific baseline variance or cosine similarity threshold should trigger the early stop?
- Which specific cell context and perturbation dataset will be used as the anchor for these trials?
