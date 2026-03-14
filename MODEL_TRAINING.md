# GNN Model Training Documentation

This document details the architecture, methodology, and usage of the 5-layer hint generation pipeline designed to detect, locate, and fix bugs in Python code.

## 1. System Architecture (5 Layers)

| Layer | Name                | File                                                                  | Purpose                                     |
| ----- | ------------------- | --------------------------------------------------------------------- | ------------------------------------------- |
| 1     | Code Property Graph | `graph_service.py`, `ast_models.py`, `cfg_models.py`, `dfg_models.py` | Build AST+CFG+DFG from source               |
| 2     | GNN Encoder         | `gnn_models.py`                                                       | Encode graphs with GAT convolutions         |
| 3     | Multi-Task Heads    | `gnn_models.py`                                                       | Classify, localize, and suggest patches     |
| 4     | Fuzzy Inference     | `fuzzy_inference.py`                                                  | Decide hint aggressiveness based on context |
| 5     | Hint Generator      | `hint_generator.py`                                                   | Produce natural-language hints (MiniLM)     |

## 2. Core Files

### `core_engine/models/gnn_models.py` (Layers 2-3)

Defines the `HintGeneratorGNN` with a Siamese architecture:

- **Encoder**: `CodeEncoder` uses `nn.Embedding` + 2 `GATConv` layers with dropout (0.3 in GAT, 0.5 after each layer). Learned embeddings let the model understand that `+` and `-` are related but distinct.

- **Cross-Attention**: `nn.MultiheadAttention` aligns user (buggy) nodes against optimal (correct) nodes. A `LayerNorm` residual connection stabilizes training.

- **Head 1 — Classifier**: Takes **two inputs** concatenated into `[2*H]`:
  - Global signal: `|mean(user_emb) - mean(opt_emb)|` — detects IF code differs.
  - Local signal: softmax-weighted pooling of cross-attention output using localizer scores — focuses on WHERE the bug is.
  - This attention-weighted classification approach was critical for distinguishing bug types from single-node changes in large graphs.
  - Uses dropout (0.4) for regularization.

- **Head 2 — Localizer**: `Linear→ReLU→Dropout(0.3)→Linear(1)` producing raw logits (no sigmoid). Trained with `BCEWithLogitsLoss(pos_weight=10)` to handle extreme class imbalance (~5 positive nodes out of 100+).

- **Head 3 — Patch Decoder**: `Linear→ReLU→Dropout(0.3)→Linear(39)` predicting from only mutation tokens (IDs 1-38) + UNK. Reducing from 500 to 39 classes improved patch accuracy by 40%.

### `prepare_data.py` (Data Pipeline)

Pre-generates and caches all training data for fast, consistent training:

- Loads HumanEval problems (164 problems)
- Generates 15 mutations per problem using `mutator.py`
- Builds CPG tensors (AST+CFG+DFG merged) for each
- **Seeds mutation tokens** (`True`, `False`, `+`, `-`, integers, etc.) into the vocabulary BEFORE graph construction — without this, the patch head can't learn boolean/integer fixes
- Splits by problem (not by sample) to prevent data leakage
- Saves `training_cache.pkl` (~16 MB, ~2400 samples)

### `train.py` (Training Loop)

Loads cached data and trains the GNN with:

- **Weighted CrossEntropy** for classification (5x penalty for bug classes)
- **BCEWithLogitsLoss** with `pos_weight=10` for localization
- **Multi-node targets**: ALL nodes on the bug line are marked positive (not just the first)
- **Gradient accumulation** (8 steps) to smooth gradients from batch_size=1
- **Learning rate**: 0.0005 with weight_decay=1e-4 (L2 regularization)
- **Gradient clipping** (norm=1.0) and **LR scheduler** (ReduceLROnPlateau)
- **Loss weighting**: 0.5×cls + 1.0×loc + 1.0×patch (prioritizes loc/patch for E2E)
- **E2E accuracy** metric: requires cls + loc + patch all correct per sample

### `core_engine/mutator.py` (Bug Injector)

Generates training data by breaking valid code via AST transformations:

- **Operator Error**: `+` ↔ `-`, `*` ↔ `/`, etc. (40% probability)
- **Logic Error**: `==` ↔ `!=`, `<` ↔ `>`, `True` ↔ `False`, off-by-one integers (40%/25%)
- Returns `MutationMetadata` with exact line number, original token, and buggy token
- Uses targeted string replacement (not `ast.unparse`) to preserve original line numbers

### `core_engine/fuzzy_inference.py` (Layer 4)

Mamdani-style fuzzy inference engine that decides hint aggressiveness:

- **Inputs**: `tests_failed_ratio` [0,1], `model_confidence` [0,1], `skill_level` (low/medium/high)
- **Membership functions**: Trapezoidal/triangular for tests and confidence
- **27 rules** mapping (tests, confidence, skill) → hint style
- **Output**: `hint_style` (aggressive/moderate/gentle) + `hint_detail` [0,1]

### `core_engine/hint_generator.py` (Layer 5)

Template-based hint generation with optional MiniLM semantic matching:

- **Templates**: 3 styles × 3 bug types × 3 variations = 27 templates
- **Semantic selection**: Encodes context with `sentence-transformers/all-MiniLM-L6-v2`, picks best-matching template via cosine similarity
- **Fallback**: Works without transformer (template-only mode)
- **Max 40 words** enforced per hint

### `app/services/graph_service.py` (Graph Builder)

Converts Python source into CPG (Code Property Graph):

- Builds AST via `tree-sitter`, CFG via `CFGBuilder`, DFG via `DFGBuilder`
- Adds 1-indexed `start_line` to every AST node (from tree-sitter's `start_point`)
- Debug prints gated behind `DEBUG` flag (suppressed during training)

## 3. Training Evolution

| Version | Key Change                                       | Best Val E2E | Key Finding                                       |
| ------- | ------------------------------------------------ | ------------ | ------------------------------------------------- |
| V4      | Bug fixes (start_line, class_weights, loc loss)  | 52%          | Baseline after critical fixes                     |
| V5      | Multi-node loc targets + BCEWithLogitsLoss       | ~50%         | Loc jumped 8%→47%, but E2E unstable               |
| V6      | 3-class (removed dead "Missing Return"/"Syntax") | 70.8%        | Fewer classes = easier classification             |
| V7      | Attention-weighted classifier + mean pooling     | 43%          | Architecture change needs more data               |
| V8a     | Pre-cached data (2400 samples) + vocab fix       | 16.4%        | Vocab fix enabled patch learning, but overfitting |
| V8b     | + Gradient accumulation (8) + dropout (0.5)      | 19.5%        | Reduced train-val gap, smoother convergence       |
| V8c     | + Weight decay (1e-4) + LR=0.0005                | 21.0%        | **Best model**: Cls=80.8%, Loc=55.3%, Patch=34.2% |

### Key Bugs Found & Fixed

1. **`start_line` missing from `ASTNode`** — localization matched nothing
2. **`class_weights` defined but not passed** to `CrossEntropyLoss`
3. **`ast.unparse` shifted line numbers** — replaced with targeted string replacement
4. **Dead bug classes** ("Missing Return", "Syntax") never generated by mutator
5. **Mutation tokens missing from vocab** — `True`, `False`, integers mapped to UNK, making patch head unable to learn 60% of corrections
6. **Patch head output dimension** — 500 classes (full vocab) when only 39 are valid mutation tokens. Reducing to 39 improved patch accuracy from ~24% to 34%
7. **Warm-start with mismatched vocab** — Old checkpoints had different vocab ordering, causing embedding misalignment. Always train from scratch after vocab changes.
8. **Overfitting from insufficient regularization** — Train metrics far ahead of val. Fixed with higher dropout (0.5 encoder, 0.4 classifier, 0.3 heads) + weight decay (1e-4)
9. **Noisy gradients from batch_size=1** — Added gradient accumulation (8 steps) to smooth updates

## 4. How to Run

### Prerequisites

```powershell
cd backend
.\venv\Scripts\activate
```

### Step 1: Prepare Training Data (run once)

```powershell
python prepare_data.py
```

Generates `training_cache.pkl` and `vocab.json`.

### Step 2: Train the Model

```powershell
python train.py
```

Logs to `train_output.txt`. Saves `gnn_model_best.pth` when E2E improves.

### Step 3: Run Inference

```powershell
python -m core_engine.inference
```

### Step 4: Test Fuzzy + Hint Pipeline

```powershell
python test_layers.py
```

Verifies Layer 4 (fuzzy) and Layer 5 (hint generator) end-to-end.

## 5. Training on MBPP (`mbpp.jsonl`)

MBPP provides a larger and more diverse set of problems than HumanEval. The training pipeline is the same (mutate correct code, build CPGs, train multi-task heads), but we keep MBPP artifacts separate to avoid overwriting HumanEval caches/checkpoints.

### Step 1: Prepare MBPP Training Data (run once)

```powershell
python prepare_data_mbpp.py
```

Outputs:

- `training_cache_mbpp.pkl`
- `vocab_mbpp.json`

### Step 2: Train on MBPP

```powershell
python train_mbpp.py
```

Outputs:

- `train_output_mbpp.txt`
- `gnn_model_mbpp_best.pth`
- Periodic checkpoints: `gnn_model_mbpp_ep{N}.pth`

### Notes

- **No warm-start across datasets**: vocab ordering and distribution differ; only warm-start from `gnn_model_mbpp_best.pth` for MBPP runs.
- **Same mutation vocabulary seeding**: mutation tokens are pre-registered so the patch head can learn `True`/`False`/integers/operators.
