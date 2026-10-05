# Rapporto integrale — antigravity

Agente: antigravity. Run: 20261005-141332-blocchi-reti. Modalità: read. Modello: non registrato (campo model null in meta.json). Brief: control/briefs/blocchi-qualsiasi-rete-2026-10-05.md nell'agent-hub, fuori da questo repository. Exit 0. Durata 171,2 s. Inizio 2026-10-05T14:13:32+02:00, fine 2026-10-05T14:16:23+02:00. Caratteri: 8977.

Il testo sotto è il rapporto originale. È una pretesa finché il catalogo non lo verifica. La lettura adottata è in ../CATALOGO.md.

---

Outcome: I identified fourteen distinct architectural blocks for conditioning, extracted their mechanisms via web search, and ranked five that minimize additive paths to prevent residual collapse.

**What I did and found:**
I ran `search_web` for 14 different queries covering the requested domains. Since I was constrained from executing commands, opening URLs, or reading files, I relied entirely on the search snippets. Licenses and specific file paths were not present in the snippets (**unverified**).

**1. FiLM (Feature-wise Linear Modulation)**
- **Name/Year**: FiLM, 2018 (**measured**)
- **URL**: https://github.com/ethanjperez/film (**unverified**)
- **Module/Equation**: $\gamma \cdot F + \beta$ (**measured**)
- **Sit on anchor**: Modulates the frozen anchor's features using affine transformations based on the condition (**inferred**).
- **Shared shift**: Emits a shared shift if the conditioning network always outputs $\gamma=1$ and constant $\beta$ (**inferred**).
- **License**: **unverified**

**2. Adaptive Instance Normalization (AdaIN)**
- **Name/Year**: AdaIN, 2017 (**measured**)
- **URL**: https://github.com/xunhuang1995/AdaIN-style (**measured**)
- **Module/Equation**: not named in the snippet (**measured**)
- **Sit on anchor**: Scales and shifts the frozen anchor's normalized features to match the condition's statistics (**inferred**).
- **Shared shift**: Emits a shared shift if all conditions map to identical mean and variance (**inferred**).
- **License**: **unverified**

**3. HyperNetworks**
- **Name/Year**: HyperNetworks, 2017 (**measured**)
- **URL**: https://github.com/g1910/HyperNetworks (**measured**)
- **Module/Equation**: not named in the snippet (**measured**)
- **Sit on anchor**: Uses a secondary network to dynamically generate weights for a residual layer on the frozen anchor (**inferred**).
- **Shared shift**: Emits a shared shift if the generated weights are identical regardless of the condition (**inferred**).
- **License**: **unverified**

**4. ControlNet**
- **Name/Year**: ControlNet, 2023 (**measured**)
- **URL**: https://github.com/lllyasviel/ControlNet (**measured**)
- **Module/Equation**: zero-convolutions (**measured**)
- **Sit on anchor**: Injects conditional features into the frozen anchor via a trainable copy connected by zero-initialized convolutions (**inferred**).
- **Shared shift**: Emits a shared shift if the trainable copy learns a constant output and ignores the condition (**inferred**).
- **License**: **unverified**

**5. IP-Adapter**
- **Name/Year**: IP-Adapter, 2023 (**measured**)
- **URL**: https://github.com/tencent-ailab/IP-Adapter (**measured**)
- **Module/Equation**: gated cross-attention (**measured**)
- **Sit on anchor**: Attends to condition features using a decoupled cross-attention layer added to the frozen anchor (**inferred**).
- **Shared shift**: Emits a shared shift if the cross-attention constantly weights a learned bias and ignores condition tokens (**inferred**).
- **License**: **unverified**

**6. Classifier-free guidance**
- **Name/Year**: Classifier-free guidance, 2021 (**unverified**)
- **URL**: https://github.com/lucidrains/classifier-free-guidance-pytorch (**unverified**)
- **Module/Equation**: conditional minus unconditional / guidance scale (**measured**)
- **Sit on anchor**: Extrapolates between the frozen anchor's unconditional and conditional outputs (**inferred**).
- **Shared shift**: Emits a shared shift if the conditional and unconditional paths always produce a constant difference (**inferred**).
- **License**: **unverified**

**7. Slot Attention**
- **Name/Year**: Slot Attention, 2020 (**measured**)
- **URL**: https://github.com/google-research/google-research/tree/master/slot_attention (**measured**)
- **Module/Equation**: not named in the snippet (**measured**)
- **Sit on anchor**: Iteratively binds the frozen anchor's representations to condition-specific slots (**inferred**).
- **Shared shift**: Emits a shared shift if the iterative attention collapses to identical slots for all conditions (**inferred**).
- **License**: **unverified**

**8. Low-rank Bilinear Pooling**
- **Name/Year**: Low-rank Bilinear Pooling, 2017 (**measured**)
- **URL**: https://github.com/jnhwkim/MulLowBiVQA (**measured**)
- **Module/Equation**: Hadamard Product for Low-rank Bilinear Pooling (**measured**)
- **Sit on anchor**: Element-wise multiplies low-rank projections of the frozen anchor and the condition (**inferred**).
- **Shared shift**: Emits a shared shift if the condition's projection collapses to a constant scaling vector (**inferred**).
- **License**: **unverified**

**9. Sparse Autoencoders**
- **Name/Year**: Sparse Autoencoders, 2023 (**unverified**)
- **URL**: https://github.com/openai/sparse_autoencoder (**measured**)
- **Module/Equation**: Top-K sparsity mechanism (**measured**)
- **Sit on anchor**: Reconstructs the frozen anchor's residuals using a sparse combination of dictionary features (**inferred**).
- **Shared shift**: Emits a shared shift if the identical subset of sparse features activates across all conditions (**inferred**).
- **License**: **unverified**

**10. Prototypical Networks**
- **Name/Year**: Prototypical Networks, 2017 (**measured**)
- **URL**: https://github.com/jakesnell/prototypical-networks (**measured**)
- **Module/Equation**: class prototypes (mean vector) (**measured**)
- **Sit on anchor**: Classifies the frozen anchor's output by its distance to condition-specific prototypes (**inferred**).
- **Shared shift**: Emits a shared shift if the prototypes for all conditions collapse to a single mean vector (**inferred**).
- **License**: **unverified**

**11. Retrieval-Enhanced Transformer (RETRO)**
- **Name/Year**: RETRO, 2022 (**measured**)
- **URL**: https://github.com/lucidrains/RETRO-pytorch (**measured**)
- **Module/Equation**: chunked cross-attention (**measured**)
- **Sit on anchor**: Allows the frozen anchor to cross-attend to retrieved condition chunks (**inferred**).
- **Shared shift**: Emits a shared shift if the attention ignores retrieved chunks and outputs a constant bias (**inferred**).
- **License**: **unverified**

**12. Mixture-of-Experts (MoE)**
- **Name/Year**: Sparsely-Gated MoE, 2017 (**measured**)
- **URL**: https://github.com/google-research/t5x (**measured**)
- **Module/Equation**: trainable gating network (**measured**)
- **Sit on anchor**: Routes the frozen anchor's features to specific expert modules based on the condition (**inferred**).
- **Shared shift**: Emits a shared shift if the gate always routes to the same experts regardless of condition (**inferred**).
- **License**: **unverified**

**13. Invariant Risk Minimization**
- **Name/Year**: Invariant Risk Minimization, 2019 (**measured**)
- **URL**: https://github.com/facebookresearch/InvariantRiskMinimization (**measured**)
- **Module/Equation**: not named in the snippet (**measured**)
- **Sit on anchor**: Adds an invariant representation layer atop the frozen anchor across different conditions (**inferred**).
- **Shared shift**: Emits a shared shift if the learned representation completely ignores the condition to achieve invariance (**inferred**).
- **License**: **unverified**

**14. Reduced-rank regression**
- **Name/Year**: Reduced-rank regression, 2022 (**unverified**)
- **URL**: https://github.com/bichanw/RRR (**measured**)
- **Module/Equation**: not named in the snippet (**measured**)
- **Sit on anchor**: Projects the condition through a low-rank bottleneck before adding it to the frozen anchor (**inferred**).
- **Shared shift**: Emits a shared shift if the low-rank projection matrix becomes zero, leaving a constant bias (**inferred**).
- **License**: **unverified**

**Ranked five to try first (preferring no additive path from context alone):**
1. HyperNetworks (**inferred** - context generates weights multiplicatively)
2. Low-rank Bilinear Pooling (**inferred** - relies on Hadamard product, no independent additive path)
3. Mixture-of-Experts routing (**inferred** - context drives discrete/sparse routing decisions)
4. Adaptive Instance Normalization (**inferred** - context defines multiplicative variance)
5. Feature-wise Linear Modulation (**inferred** - context defines multiplicative scaling factor)

**Early measurement to stop a candidate:**
The residual vectors of different conditions have pairwise cosine near 1, or their variance across conditions is near 0 (**inferred**).

**What I did not do or could not verify, and open questions:**
- I did not run any shell commands, read local files, or open URLs directly to respect environment constraints (**measured**).
- I could not verify licenses, specific code files, or exact class names because the web search snippets did not include them (**unverified**).
- **Open question for Claude1**: Should we implement a contrastive regularization loss during the adapter's training to explicitly push apart the representations of different conditions and actively penalize this collapse?
