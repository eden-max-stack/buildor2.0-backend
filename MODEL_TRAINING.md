# GNN Model Training Documentation

This document details the architecture, methodology, and usage of the Graph Neural Network (GNN) pipeline designed to detect, locate, and fix bugs in Python code.

## 1. Core Architecture & Files

### `core_engine/models/gnn_models.py` (The Brain)

This file defines the neural network architecture. We evolved from a simple classifier to a Hybrid Multi-Task GNN (V3).

- **Encoder**: Uses GATConv (Graph Attention Network) layers to process code graphs. Crucially, it uses Learned Embeddings (vector representations of "IfStatement", "ForLoop", "+", etc.) instead of random noise, allowing the model to learn the semantic relationship between Python tokens.

- **Path A (Classification)**: Uses Sum Pooling and Vector Subtraction (|User - Optimal|) to explicitly detect if a bug exists. This "Difference Vector" makes operator errors (like + vs -) mathematically obvious.

- **Path B (Localization & Patching)**: Uses Cross-Attention to align the User's code with the Optimal code node-by-node. This preserves high-resolution data needed to pinpoint the exact line number of a bug.

### `train.py` (The Teacher)

The main training loop. It employs several advanced techniques to ensure convergence:

- **Weighted Loss**: We apply a 5x Penalty for missing a bug (Class 1-4) compared to correctly identifying correct code (Class 0). This prevents the model from becoming "lazy" and guessing "No Bug" for everything.

- **Multi-Task Loss**: The model minimizes three losses simultaneously:
  - `Loss_Cls`: Did it find the bug type? (CrossEntropy)
  - `Loss_Loc`: Did it find the correct node? (Binary CrossEntropy)
  - `Loss_Patch`: Did it predict the correct fix token? (CrossEntropy)

- **Dynamic Vocabulary**: Automatically builds and saves a `vocab.json` so the training and inference stages speak the same "language."

### `core_engine/mutator.py` (The Saboteur)

Generates training data by actively breaking valid code.

- **Methodology**: It parses Python code into an AST and applies random transformations (e.g., swapping `+` to `-`, `==` to `!=`, or `True` to `False`).

- **Metadata**: Unlike standard fuzzers, it returns a Forensic Report (MutationMetadata) containing the exact line number, column offset, and original token of the bug. This provides the "Ground Truth" labels needed to train the Locator and Patcher heads.

### `app/services/graph_service.py` (The Translator)

Converts raw Python source code into a graph format the GNN can understand.

- **Flattening**: Converts nested ASTs into flat lists of nodes and edges.

- **Enrichment**: Adds strictly 1-indexed `start_line` attributes to every node, ensuring the GNN can map its graph predictions back to the user's actual source code lines.

### `core_engine/inference.py` (The Doctor)

Loads the trained model to diagnose new code.

- **Vision Test**: Includes debug logic to verify if the model can "see" specific tokens (e.g., ensuring `+` isn't just labeled as generic `binary_operator`).

- **Heatmap Generation**: Aggregates the localization scores for all nodes on a single line to produce a "Suspicion Score" for that line of code.

## 2. Methodology & Experiments (What We Tried)

### Phase 1: The "Naive" Classifier (Failed)

- **Approach**: Used random noise for node embeddings and global mean pooling.
- **Result**: ~50% Accuracy.
- **Why it Failed**: The model treated "If" and "While" as random, unrelated vectors. Mean pooling "washed out" the signal of small bugs (like a single wrong operator) in large graphs.

### Phase 2: Learned Embeddings (Success)

- **Approach**: Switched to `nn.Embedding` to learn vector representations for node types.
- **Result**: Accuracy jumped to ~70%.
- **Why it Worked**: The model learned that `+` and `-` are semantically related (both operators) but distinct, similar to how NLP models learn words.

### Phase 3: The "Siamese" Trap (Setback)

- **Approach**: Used pure Cross-Attention for classification.
- **Result**: Diagnosis confidence dropped (40% "None").
- **Why it Failed**: Attention aligns graphs so well that it "hides" the differences. The model aligned the buggy `+` with the correct `-` and thought they were the same.

### Phase 4: Hybrid Architecture & Weighted Loss (Final Success)

- **Approach**:
  - Hybrid Path: Use subtraction (diff = abs(u - o)) for detection and attention for localization.
  - Sum Pooling: Use `sum()` instead of `mean()` so bug signals aren't diluted by graph size.
  - 5x Penalty: Heavily punish the model for missing bugs.

- **Result**: High accuracy, correct "Operator Error" diagnosis, and precise line localization.

## 3. How to Run the Pipeline

### Prerequisites

Ensure you are in the root directory (`buildor2.0-backend`) and your virtual environment is active.

### Step 1: Train the Model

Run the training module. This will generate `gnn_model_v3_ep50.pth` and `vocab.json`.

```powershell
python -m train
```

**Watch for**: `Cls_Acc` increasing and `Loss` decreasing in the logs.

**Output**: The model weights and vocabulary mapping will be saved to the root directory.

### Step 2: Run Inference (Test the Model)

Run the inference module to test the model on a sample buggy function (default is checking `a - b` vs `a + b`).

```powershell
python -m core_engine.inference
```

**Expected Output**:

- **Diagnosis**: Operator Error (High Confidence)
- **Suspicious Lines**: Line 3 (or relevant line) should have the longest bar `||||||`.
