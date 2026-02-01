# Theoretical Framework: Graph Analysis Layer Implementation

## 1. Introduction

This document details the theoretical underpinnings of the static analysis engine used to generate the **Abstract Syntax Tree (AST)**, **Control Flow Graph (CFG)**, and **Data Flow Graph (DFG)**.

The engine transforms raw source code into structured graph representations, which serve as the input features for the Hint Generation GNN.

---

## 2. Abstract Syntax Tree (AST) Logic

**File:** `core_engine/models/ast_models.py`

### 2.1. Theory: The Tree Structure

The AST represents the syntactic structure of the code. Unlike a Concrete Syntax Tree (Parse Tree) which contains every grammatical token (parentheses, whitespace), an AST focuses on the _structure_ required for execution.

- **Nodes:** Represents constructs like `FunctionDefinition`, `IfStatement`, `BinaryOperator`.
- **Edges:** Represents hierarchical containment (e.g., a Function _contains_ a Block).

### 2.2. Implementation Specifics

- **Tree-Sitter Integration:** We utilize `tree-sitter` for robust, error-tolerant parsing. This allows us to handle incomplete or syntactically incorrect code often written by students.
- **Semantic Role Labeling:** A raw AST only gives types (e.g., `block`). Our `ASTBuilder` enriches this by assigning **Roles** based on context:
  - _Example:_ A `block` node inside an `if_statement` is tagged as `then_branch` or `else_branch`.
  - _Why this matters:_ The GNN relies on these roles to distinguish between code that _always_ executes vs. code that _conditionally_ executes.

---

## 3. Control Flow Graph (CFG) Logic

**File:** `core_engine/models/cfg_models.py`

### 3.1. Theory: Modeling Execution Paths

The CFG models the possible paths that program execution can take. It transforms the hierarchical AST into a directed graph where:

- **Nodes:** Execution units (statements or conditions).
- **Edges:** Transitions between units (control transfer).

### 3.2. Granularity Strategy

Your implementation uses a **Statement-Level CFG** (Fine-Grained) rather than a Basic-Block CFG.

- _Standard Compiler Theory:_ Groups sequential instructions into "Basic Blocks" to reduce graph size.
- _Your Implementation:_ Every statement (`y = x + 1`) is its own node.
- _Benefit:_ This maximizes the resolution for the GNN, allowing it to pinpoint errors to a specific line/statement rather than a general block.

### 3.3. Structural Logic

The `CFGBuilder` recursively constructs sub-graphs for control structures:

- **Sequential Logic (`build_block`):**
  - Connects Statement $N$ $\rightarrow$ Statement $N+1$ linearly.
- **Branching Logic (`build_if`):** implements a **Diamond Topology**.
  1.  **Split:** The `if_cond` node branches to `then_entry` and `else_entry`.
  2.  **Merge:** Crucially, both branches converge at a **Synthetic Merge Node**. This ensures the graph captures the _post-dominator_ relationship (the point where flow must return regardless of the path taken).
- **Loop Logic (`build_while`):**
  - Creates a **Back-Edge** from the end of the loop body to the `while_cond` node, representing the cycle.

---

## 4. Data Flow Graph (DFG) Logic

**File:** `core_engine/models/dfg_models.py`

### 4.1. Theory: Def-Use Chains

The DFG models the lifecycle of variables. It answers the question: _"Where did the value in this variable come from?"_

- **Definition (Def):** A statement that assigns a value to a variable (e.g., `x = 5`).
- **Use:** A statement that reads the value (e.g., `y = x + 1`).

### 4.2. Algorithm: Reaching Definitions Analysis

Your `DFGBuilder` implements the standard iterative data-flow analysis algorithm:

$$\text{OUT}[n] = \text{GEN}[n] \cup (\text{IN}[n] - \text{KILL}[n])$$

1.  **Initialization:** Assume no definitions reach any node initially.
2.  **Iteration (Fixed-Point Algorithm):**
    - **IN Set:** For a node $n$, the input definitions are the union of the **OUT** sets of all its CFG predecessors ($p \in \text{pred}(n)$).
      $$\text{IN}[n] = \bigcup_{p} \text{OUT}[p]$$
    - **GEN Set:** The definitions created _within_ node $n$ (e.g., `x = ...` generates a def for `x`).
    - **KILL Set:** If node $n$ defines `x`, it "kills" all previous definitions of `x`.
    - **Convergence:** Repeat until the sets stop changing (Fixed Point).

### 4.3. Graph Construction Steps

1.  **Parameter Injection:** Synthetic definitions are created at the `ENTRY` node for function parameters (e.g., `def func(x):`) so that arguments are treated as initialized variables.
2.  **Variable Extraction:** The AST is traversed to find all Identifiers.
    - _Sinks:_ Logic handles special cases like `print(z)`, marking them as sinks/uses rather than simple variables.
3.  **Edge Creation:** Finally, edges are drawn from every Definition in the `IN` set of a node to the corresponding Use in that node.

### 4.4. Path Sensitivity

Because the DFG is built on top of the CFG (via the `_get_predecessors` logic), it is **Path-Sensitive**.

- _Example:_ If variable `z` is defined in an `if` branch and an `else` branch, the usage of `z` after the merge point will correctly have **two incoming edges** (one from each branch's definition).

---

## 5. Summary of Graph Interactions

| Graph   | Role                                              | Inter-Graph Connection                                 |
| :------ | :------------------------------------------------ | :----------------------------------------------------- |
| **AST** | Provides the "Skeleton" (Tokens & Hierarchy)      | Anchors everything. CFG/DFG nodes map back to AST IDs. |
| **CFG** | Provides the "Circulatory System" (Flow)          | Constructed by traversing AST statements.              |
| **DFG** | Provides the "Nervous System" (Data Dependencies) | Uses CFG topology to calculate Reaching Definitions.   |

This triad allows the GNN to learn:

1.  **What** the code is (AST).
2.  **When** it executes (CFG).
3.  **How** data moves through it (DFG).

# TODO:

1. Add a traversal for class_definition in find_functions.
2. CFGBuilder does not have build_try or build_with.
3. List Comprehensions in DFG and CFG.
4. DFG does not seem to handle global variables defined outside the function scope.
