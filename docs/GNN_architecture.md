# Theoretical Framework: Cross-Attention GNN for Code Analysis

## 1. Introduction

This document outlines the theoretical foundation of the **Hint Generation Engine**. Unlike traditional static analysis tools that rely on rigid rule sets (linters), this system uses **Deep Learning on Graphs** to understand the _semantic_ intent of code.

The core philosophy is **Comparative Analysis**: instead of asking "Is this code correct in a vacuum?", the model asks "How does this code deviate from a known optimal solution?"

## 2. Data Representation: The Code Property Graph (CPG)

Source code is not just text; it is a complex structure defined by syntax, execution flow, and data movement. We represent code as a **Heterogeneous Graph** containing three distinct sub-graphs:

1.  **Abstract Syntax Tree (AST):** Represents the hierarchical structure of the code (e.g., `IfStatement` contains `Block`).
2.  **Control Flow Graph (CFG):** Represents the order of execution (e.g., `Entry` → `Condition` → `Branch`).
3.  **Data Flow Graph (DFG):** Represents the lifecycle of variables (e.g., `x_def` → `x_use`).

These graphs are interlinked via "Foreign Key" edges (e.g., a CFG node `maps_to` an AST node), creating a unified structure passed to the neural network.

---

## 3. Model Architecture: Pseudo-Siamese GNN

The model follows a **Pseudo-Siamese** architecture. It processes two inputs (User Code and Optimal Code) in parallel using shared weights to learn a comparable latent representation.

### 3.1. The Backbone (Shared Encoders)

We use a **Heterogeneous Graph Neural Network (HGNN)** as the feature extractor.

- **Input:** Raw features of nodes (e.g., node type, identifier name).
- **Message Passing:** Information flows along specific edge types.
  - _Intra-graph flow:_ AST children inform parents; DFG definitions inform usages.
  - _Inter-graph flow:_ Execution context (CFG) flows into Syntax nodes (AST).
- **Output:** A high-dimensional embedding vector $\mathbf{h}_i$ for every node $i$, capturing its local structure and semantic role.

### 3.2. Cross-Graph Attention (Soft Alignment)

This is the core innovation of the engine. Since User Code and Optimal Code may use different variable names or structures, we cannot perform a rigid 1-to-1 comparison. Instead, we use **Cross-Attention** to learn a "Soft Mapping."

For every node $u$ in the User Graph, the model asks: _"Which parts of the Optimal Graph are most relevant to me?"_

Mathematically, this is a standard Attention mechanism:

- **Query ($Q$):** User Node Embeddings.
- **Key ($K$) & Value ($V$):** Optimal Node Embeddings.

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

The result is an **Aligned Context Vector** ($C_u$) for every user node $u$. This vector represents "What the User Node _should_ look like" based on the logic found in the optimal solution.

---

## 4. Prediction Heads (The Output Layers)

The model concatenates the **User Reality** ($\mathbf{h}_u$) with the **Aligned Expectation** ($C_u$) to form a Context-Aware Embedding:
$$\mathbf{z}_u = [\mathbf{h}_u \mathbin{\|} C_u]$$

This combined vector is fed into three specialized classifiers (Multitask Learning):

### A. Bug Type Classifier (Graph Level)

- **Goal:** Determine the category of the error (e.g., "Logic Error", "Syntax Error").
- **Mechanism:** Pools all node vectors $\mathbf{z}_u$ into a single graph vector and passes it through a Multi-Layer Perceptron (MLP).

### B. Error Localization (Node Level)

- **Goal:** Identify exactly _where_ the bug is.
- **Mechanism:** A binary classifier runs on every node vector $\mathbf{z}_u$.
- **Output:** A probability score $P(\text{bug} | u)$. The node with the highest score is flagged as the root cause.

### C. Patch Proposal (Node Level)

- **Goal:** Suggest a fix.
- **Mechanism:** A multi-class classifier runs on the node vectors.
- **Classes:** Actions like `Replace_Operator`, `Initialize_Variable`, `Move_Statement`.

---

## 5. Handling Algorithmic Divergence (The Reference Bank)

A major challenge in comparative analysis is that a single problem may have multiple valid solutions (e.g., _Iterative_ vs. _Recursive_). If the User Code uses a different algorithm than the Optimal Code, the Cross-Attention mechanism will fail to find meaningful alignment.

**Solution: The Reference Bank Strategy**

1.  **Storage:** We store embeddings for $K$ different valid variations of the optimal solution.
2.  **Selection:** Before running the expensive GNN heads, we calculate the **Cosine Similarity** between the User Graph Embedding and all $K$ Reference Embeddings.
3.  **Inference:** We select the Reference with the highest similarity score to serve as the context for the Cross-Attention layer.

This ensures the model compares "Apples to Apples," critiquing the user's code based on the algorithmic strategy they _intended_ to use.
