# Sandbox API Documentation

## Overview

This document describes the backend API routes for the coding sandbox/playground where users solve coding problems. The system includes question retrieval, code submission with execution, and AI-powered hint generation.

---

## Base URLs

- Questions: `/questions`
- Submissions: `/submissions`
- Code Analysis (Hints): `/analysis`

---

## Table of Contents

1. [Question Endpoints](#question-endpoints)
2. [Submission Endpoints](#submission-endpoints)
3. [Code Analysis Endpoints](#code-analysis-endpoints)
4. [Usage Examples](#usage-examples)
5. [Frontend Integration](#frontend-integration)

---

## Question Endpoints

### 1. **GET /questions/{question_id}**

Get complete question details including test cases for the sandbox page.

**Path Parameters:**

- `question_id` (UUID): The ID of the question

**Response (200 OK):**

```json
{
  "id": "uuid",
  "title": "Two Sum",
  "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
  "difficulty": "Easy",
  "tags": ["Arrays", "Hash Table"],
  "constraints": [
    "2 <= nums.length <= 10^4",
    "-10^9 <= nums[i] <= 10^9",
    "Only one valid answer exists"
  ],
  "acceptance_rate": 47.3,
  "total_submissions": 1500,
  "successful_submissions": 710,
  "optimal_solution": "def two_sum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i\n    return []",
  "time_complexity": "O(n)",
  "space_complexity": "O(n)",
  "test_cases": [
    {
      "id": "uuid",
      "input": { "nums": [2, 7, 11, 15], "target": 9 },
      "expected_output": [0, 1],
      "is_sample": true,
      "is_hidden": false,
      "difficulty": "basic",
      "order_index": 0
    },
    {
      "id": "uuid",
      "input": { "nums": [3, 2, 4], "target": 6 },
      "expected_output": [1, 2],
      "is_sample": false,
      "is_hidden": true,
      "difficulty": "edge",
      "order_index": 1
    }
  ]
}
```

**Notes:**

- Returns all test cases (both sample and hidden)
- `optimal_solution` is used for hint generation
- Test cases ordered by `order_index`

---

### 2. **GET /questions/**

List all active questions with optional filtering.

**Query Parameters:**

- `difficulty` (optional, string): Filter by "Easy", "Medium", or "Hard"
- `limit` (optional, int): Number of results (default: 100)
- `offset` (optional, int): Pagination offset (default: 0)

**Response (200 OK):**

```json
[
  {
    "id": "uuid",
    "title": "Two Sum",
    "difficulty": "Easy",
    "tags": ["Arrays", "Hash Table"],
    "acceptance_rate": 47.3
  }
]
```

---

## Submission Endpoints

### 3. **POST /submissions/**

Submit code for a question and execute it against test cases.

**Request Body:**

```json
{
  "question_id": "uuid",
  "user_id": "uuid",
  "code": "def solution(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return []",
  "language": "python"
}
```

**Response (201 Created):**

```json
{
  "id": "submission-uuid",
  "question_id": "uuid",
  "user_id": "uuid",
  "status": "accepted",
  "test_cases_passed": 5,
  "total_test_cases": 5,
  "runtime_ms": 124,
  "memory_kb": 18400,
  "test_results": [
    {
      "test_case_id": "uuid",
      "passed": true,
      "input": { "nums": [2, 7, 11, 15], "target": 9 },
      "expected_output": [0, 1],
      "actual_output": [0, 1],
      "error_message": null,
      "is_sample": true
    },
    {
      "test_case_id": "uuid",
      "passed": true,
      "input": { "nums": [3, 2, 4], "target": 6 },
      "expected_output": [1, 2],
      "actual_output": [1, 2],
      "error_message": null,
      "is_sample": false
    }
  ],
  "error_message": null,
  "submitted_at": "2026-03-14T12:45:00Z"
}
```

**Status Values:**

- `accepted`: All test cases passed
- `wrong_answer`: Some test cases failed
- `runtime_error`: Code threw an exception
- `time_limit_exceeded`: Code took too long
- `compilation_error`: Syntax error

**Notes:**

- Code is executed in a sandboxed environment
- Runtime and memory are measured for each test case
- Execution stops on first error
- Updates `user_question_progress` table automatically
- If status is `accepted`, marks question as solved

---

## Code Analysis Endpoints

### 4. **POST /analysis/hint**

Generate an AI-powered hint for the user's code using the 5-layer hint engine.

**Request Body:**

```json
{
  "question_id": "uuid",
  "user_id": "uuid",
  "user_code": "def solution(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i] + nums[j] = target:\n                return [i, j]\n    return []",
  "skill_level": "medium"
}
```

**Skill Levels:**

- `low`: More detailed, direct hints
- `medium`: Balanced hints
- `high`: Subtle, minimal hints

**Response (200 OK):**

```json
{
  "hint": "Check line 4: You're using assignment (=) instead of comparison (==). This will cause a syntax error.",
  "analysis": {
    "bug_type": "Operator Error",
    "confidence": 0.95,
    "bug_line": 4,
    "bug_line_confidence": 0.92,
    "patch_suggestion": "==",
    "hint_style": "direct",
    "hint_detail": 0.85
  },
  "hints_used": 3
}
```

**Notes:**

- Uses 5-layer hint generation pipeline:
  1. Code Property Graph (AST + CFG + DFG)
  2. GNN Encoder
  3. Multi-Task Heads (Classification, Localization, Patch)
  4. Fuzzy Inference (Hint Aggressiveness)
  5. Natural Language Hint Generation
- Compares user code with optimal solution
- Tracks hints used in `user_question_progress` table
- Increments `hints_used_total` on each call
- Falls back to generic hints if engine unavailable

---

## Usage Examples

### Fetch Question Details

```bash
curl "http://127.0.0.1:8000/questions/86c744f0-ee89-4ff9-8cff-10dd5316ab85"
```

### Submit Code

```bash
curl -X POST "http://127.0.0.1:8000/submissions/" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "86c744f0-ee89-4ff9-8cff-10dd5316ab85",
    "user_id": "10000000-0000-0000-0000-000000000001",
    "code": "def solution(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i\n    return []",
    "language": "python"
  }'
```

### Get Hint

```bash
curl -X POST "http://127.0.0.1:8000/analysis/hint" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "86c744f0-ee89-4ff9-8cff-10dd5316ab85",
    "user_id": "10000000-0000-0000-0000-000000000001",
    "user_code": "def solution(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i] + nums[j] = target:\n                return [i, j]\n    return []",
    "skill_level": "medium"
  }'
```

---

## Frontend Integration

### Sandbox Page Flow

1. **Load Question**

   ```typescript
   const response = await fetch(`/questions/${questionId}`);
   const question = await response.json();
   // Display: title, description, constraints, tags, sample test cases
   ```

2. **Submit Code**

   ```typescript
   const response = await fetch("/submissions/", {
     method: "POST",
     headers: { "Content-Type": "application/json" },
     body: JSON.stringify({
       question_id: questionId,
       user_id: userId,
       code: editorCode,
       language: "python",
     }),
   });
   const result = await response.json();
   // Display: status, test results, runtime, memory
   ```

3. **Get Hint**
   ```typescript
   const response = await fetch("/analysis/hint", {
     method: "POST",
     headers: { "Content-Type": "application/json" },
     body: JSON.stringify({
       question_id: questionId,
       user_id: userId,
       user_code: editorCode,
       skill_level: "medium",
     }),
   });
   const hint = await response.json();
   // Display: hint text, update hints used counter
   ```

### Data Flow

```
┌─────────────────┐
│  Sandbox Page   │
└────────┬────────┘
         │
         ├─── GET /questions/{id} ──────► Question Details + Test Cases
         │
         ├─── POST /submissions/ ───────► Code Execution + Results
         │                                 └─► Updates user_question_progress
         │
         └─── POST /analysis/hint ──────► AI Hint Generation
                                           └─► Increments hints_used_total
```

### State Management

**Question State:**

```typescript
interface Question {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  tags: string[];
  constraints: string[];
  testCases: TestCase[];
}
```

**Submission State:**

```typescript
interface SubmissionResult {
  status: "accepted" | "wrong_answer" | "runtime_error";
  testCasesPassed: number;
  totalTestCases: number;
  runtimeMs: number;
  memoryKb: number;
  testResults: TestCaseResult[];
}
```

**Hint State:**

```typescript
interface HintData {
  hint: string;
  hintsUsed: number;
  analysis?: {
    bugType: string;
    bugLine: number;
    confidence: number;
  };
}
```

---

## Database Updates

### Automatic Updates on Submission

1. **submissions table**: New row inserted with results
2. **user_question_progress table**:
   - If `accepted`: status → 'solved', solved_at timestamp set
   - If failed: status → 'attempted', attempts incremented
   - Updates best_runtime_ms and best_memory_kb

### Automatic Updates on Hint Request

1. **user_question_progress table**:
   - Increments `hints_used_total`
   - Updates `last_attempted_at` timestamp

---

## Error Responses

### 404 Not Found

```json
{
  "detail": "Question not found"
}
```

### 400 Bad Request

```json
{
  "detail": "No test cases found for this question"
}
```

### 500 Internal Server Error (SQLite Guard)

```json
{
  "detail": "Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
}
```

---

## Code Execution Details

### Python Code Execution

- Sandboxed execution using `exec()`
- Captures stdout/stderr
- Measures runtime using `time.perf_counter()`
- Measures memory using `psutil`
- Timeout: 5 seconds per test case
- Automatically finds solution function (first callable in code)

### Test Case Input Format

```json
{
  "input": {
    "nums": [2, 7, 11, 15],
    "target": 9
  }
}
```

Arguments extracted in sorted key order and passed to function:

```python
solution([2, 7, 11, 15], 9)
```

### Output Comparison

- Handles different data types (int, float, list, dict, string)
- Float comparison uses epsilon (1e-6)
- Recursive comparison for nested structures
- Type coercion attempted if types don't match

---

## Hint Engine Architecture

### 5-Layer Pipeline

**Layer 1: Code Property Graph**

- AST (Abstract Syntax Tree)
- CFG (Control Flow Graph)
- DFG (Data Flow Graph)

**Layer 2: GNN Encoder**

- Graph Neural Network processes CPG
- Learns code structure patterns

**Layer 3: Multi-Task Heads**

- Classification: Identifies bug type
- Localization: Finds buggy line
- Patch: Suggests fix

**Layer 4: Fuzzy Inference**

- Determines hint aggressiveness
- Based on: test failure rate, model confidence, skill level

**Layer 5: Natural Language Generation**

- Converts analysis to readable hint
- Adjusts detail level based on fuzzy inference

### Fallback Behavior

If hint engine unavailable or fails:

- Returns generic helpful hints
- Still tracks hints_used
- Graceful degradation

---

## Performance Metrics

### Typical Response Times

- GET /questions/{id}: ~50ms
- POST /submissions/: ~200-500ms (depends on code complexity)
- POST /analysis/hint: ~1-3s (GNN inference + hint generation)

### Resource Usage

- Code execution: Isolated per request
- Memory tracking: Per-process measurement
- Concurrent submissions: Handled independently

---

**Last Updated:** March 14, 2026  
**Version:** 1.0.0  
**Status:** Backend Complete, Frontend Integration Pending

---

## Next Steps

1. ✅ Backend routes implemented
2. ⏳ Frontend sandbox page integration
3. ⏳ Test with real questions from database
4. ⏳ Deploy and monitor performance
