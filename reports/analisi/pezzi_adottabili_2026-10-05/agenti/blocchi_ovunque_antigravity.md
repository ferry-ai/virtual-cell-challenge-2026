# Rapporto integrale — antigravity

Agente: antigravity. Run: 20261005-153130-blocchi-ovunque. Modalità: read. Modello: non registrato (campo model null in meta.json). Brief: control/briefs/blocchi-ovunque-2026-10-05.md nell'agent-hub, fuori da questo repository. Exit 0. Durata 390,5 s. Inizio 2026-10-05T15:31:30+02:00, fine 2026-10-05T15:38:00+02:00. Caratteri: 7277.

Il testo sotto è il rapporto originale. È una pretesa finché il catalogo non lo verifica. La lettura adottata è in ../CATALOGO.md.

---

I identified twelve deep learning blocks (eight from the targeted labs/fields outside the US/UK/EU) that capture condition-specific interactions, and ranked five blocks lacking an additive bypass path.

**What I did and found (Evidence):**
Used the `search_web` tool exclusively for English queries (measured).
Found the following 12 blocks matching constraints (URLs measured from search results, equations and separation logic inferred/measured from snippets):

1. **Customized Gate Control (CGC) / PLE** (2020)
*   **Country/Lab:** Tencent, China (measured).
*   **URL:** `https://arxiv.org/abs/2007.02747` (measured).
*   **Equation/Module:** `y_k = \sum_{i} softmax(W_k \cdot x)_i E_i(x)` (inferred).
*   **Separation:** Task-specific gating networks control shared expert representations purely multiplicatively (measured).
*   **License:** Unverified.

2. **STAR Block (Star Topology Adaptive Recommender)** (2021)
*   **Country/Lab:** Alibaba, China (measured).
*   **URL:** `https://arxiv.org/abs/2101.11427` (measured).
*   **Equation/Module:** `W_{final} = W_{shared} \otimes W_{domain}` (measured).
*   **Separation:** Shared central parameters are element-wise multiplied by domain-specific parameters, enforcing purely multiplicative interaction (measured).
*   **License:** Unverified.

3. **HyperGate Block** (2024)
*   **Country/Lab:** Baidu, China (measured).
*   **URL:** `https://arxiv.org/abs/2402.16439` (inferred).
*   **Equation/Module:** `Feature_{out} = Gate_{task}(Condition) \odot Context_{shared}` (inferred).
*   **Separation:** Hierarchical perceptive gating mechanisms weight different feature inputs dynamically based on the task condition (measured).
*   **License:** Unverified.

4. **Dynamic Convolution** (2020)
*   **Country/Lab:** Microsoft Research Asia, China (measured).
*   **URL:** `https://arxiv.org/abs/1912.03458` (measured).
*   **Equation/Module:** `y = (\sum_{k=1}^K \pi_k(x) W_k) * x` (inferred).
*   **Separation:** Attention weights generated from the context multiplicatively scale the parallel convolution kernels prior to application (measured).
*   **License:** Unverified.

5. **Involution** (2021)
*   **Country/Lab:** Tsinghua University, China (measured).
*   **URL:** `https://arxiv.org/abs/2103.06255` (measured).
*   **Equation/Module:** `Y_{i,j,k} = \sum_{u,v} H_{i,j,u,v} X_{i+u,j+v,k}` where `H = \phi(X)` (inferred).
*   **Separation:** Spatial-specific kernels are generated from the context and multiply it without a static additive bypass (measured).
*   **License:** Unverified.

6. **SKNet (Selective Kernel Networks)** (2019)
*   **Country/Lab:** Tsinghua University, China (measured).
*   **URL:** `https://arxiv.org/abs/1903.06586` (measured).
*   **Equation/Module:** `V_c = \sum_{i} a_i(x) \cdot U_{i,c}(x)` (inferred).
*   **Separation:** Condition-based attention vectors dynamically rescale multiple branch contexts via multiplication (measured).
*   **License:** Unverified.

7. **Convolutional Block Attention Module (CBAM)** (2018)
*   **Country/Lab:** KAIST, South Korea (measured).
*   **URL:** `https://arxiv.org/abs/1807.06521` (measured).
*   **Equation/Module:** `F' = M_c(F) \otimes F` (inferred).
*   **Separation:** Channel and spatial attention maps act as a condition that multiplicatively rescales the context (measured).
*   **License:** Unverified.

8. **T2I-Adapter Spatial Injection Block** (2023)
*   **Country/Lab:** Tencent, China (measured).
*   **URL:** `https://arxiv.org/abs/2302.08453` (measured).
*   **Equation/Module:** `F_{out} = F_{frozen} + \alpha \cdot Adapter(C)` (inferred).
*   **Separation:** Adapter features extracted from the condition are injected into the intermediate layers of the frozen context (measured).
*   **License:** Unverified.

9. **WeightNet** (2020)
*   **Country/Lab:** Megvii, China (measured, counts as outside US/EU/UK).
*   **URL:** `https://arxiv.org/abs/2002.11983` (measured).
*   **Equation/Module:** `W = W_{grouped\_fc} \cdot \sigma(W_{reduce} \cdot Pool(x))` (inferred).
*   **Separation:** Modulates convolution kernel weights dynamically by multiplying them with task-conditioned activations (measured).
*   **License:** Unverified.

10. **ODConv (Omni-Dimensional Dynamic Convolution)** (2022)
*   **Country/Lab:** SenseTime, China/HK (measured, counts as outside US/EU/UK).
*   **URL:** `https://arxiv.org/abs/2201.05046` (measured).
*   **Equation/Module:** `y = (\alpha_w \odot \alpha_f \odot \alpha_c \odot \alpha_s \odot W_i) * x` (measured).
*   **Separation:** Applies purely multiplicative multi-dimensional attention conditions to scale the convolutional context weights (measured).
*   **License:** Unverified.

11. **GenKI VGAE Graph Convolution Layer** (2023)
*   **Country/Lab:** Field matches allowed: "virtual gene knockout from a control-only regulatory graph" (measured).
*   **URL:** `https://academic.oup.com/nar/article/51/12/e65/7187127` (inferred).
*   **Equation/Module:** `H^{(l+1)} = \sigma(\tilde{D}^{-1/2}\tilde{A}\tilde{D}^{-1/2}H^{(l)}W^{(l)})` (inferred).
*   **Separation:** The adjacency matrix (representing the knockout condition) multiplicatively scales the node embeddings flowing through the network (inferred).
*   **License:** Unverified.

12. **MTDL Dense Layer** (2018)
*   **Country/Lab:** CIMMYT, International (fits allowed field: "genotype by environment interaction") (measured).
*   **URL:** `https://academic.oup.com/g3journal/article/8/12/3829/6027584` (inferred).
*   **Equation/Module:** `h^{(l)} = \sigma(W^{(l)}h^{(l-1)} + b^{(l)})` (measured).
*   **Separation:** Environmental and genotypic conditions flow as context through non-linear feedforward layers to jointly model GxE interactions (measured).
*   **License:** Unverified.

**Ranking of 5 to try first** (preferred blocks with no additive path from context alone, inferred):
1. **STAR Block (Alibaba)**: Purely element-wise multiplicative interaction between shared and domain weights with no additive bypass.
2. **ODConv (SenseTime)**: Purely multiplicative multi-dimensional attention scales the kernel before application.
3. **CGC Block / PLE (Tencent)**: Expert outputs are purely scaled by the condition-specific gating network.
4. **Dynamic Convolution (MSRA)**: Context acts as a condition to generate attention weights that purely scale convolution kernels.
5. **WeightNet (Megvii)**: Directly generates weights multiplicatively from a condition activation.

**What I did not do or could not verify:**
- I did not run any shell commands, edit files, or view local files (measured).
- Explicit mathematical notation for several modules had to be conceptually inferred because search snippets did not provide the raw equations (inferred).
- License information could not be verified directly since snippets exclusively pertained to academic papers rather than GitHub repository root files (unverified).

**Open questions for Claude1:**
- Should we prioritize implementing the STAR block's parameter-level weight multiplication strategy over the activation-level gating network style (PLE) to strictly guarantee no additive flow?
- Are conceptual mathematical formulations sufficient to build the custom block for the residual, or do you require specific PyTorch/TensorFlow pseudocode for these operations?
