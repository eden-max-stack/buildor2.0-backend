# Questions Management API Documentation

## Overview

This document describes the backend API routes for managing coding questions within classes. Trainers can create, view, and update questions for their classes.

---

## Base URL: `/classes`

---

## Endpoints

### 1. **POST /classes/{class_id}/questions**

Create a new coding question for a specific class.

**Path Parameters:**

- `class_id` (string): The ID of the class

**Request Body:**

```json
{
  "trainer_id": "uuid",
  "title": "Two Sum Problem",
  "description": "Given an array of integers nums and an integer target...",
  "difficulty": "Easy",
  "tags": ["Arrays", "Hash Table"],
  "constraints": ["1 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9"],
  "optimal_solution": "def twoSum(nums, target):\n    # solution code",
  "time_complexity": "O(n)",
  "space_complexity": "O(n)",
  "test_cases": [
    {
      "input": { "nums": [2, 7, 11, 15], "target": 9 },
      "expected_output": [0, 1],
      "is_sample": true,
      "is_hidden": false,
      "difficulty": "basic",
      "order_index": 0
    }
  ]
}
```

**Response (201 Created):**

```json
{
  "id": "uuid",
  "title": "Two Sum Problem",
  "description": "Given an array of integers...",
  "difficulty": "Easy",
  "tags": ["Arrays", "Hash Table"],
  "constraints": ["1 <= nums.length <= 10^4"],
  "optimal_solution": "def twoSum(nums, target):\n    # solution",
  "time_complexity": "O(n)",
  "space_complexity": "O(n)",
  "acceptance_rate": null,
  "total_submissions": 0,
  "successful_submissions": 0,
  "created_by": "uuid",
  "created_at": "2026-03-14T00:00:00Z",
  "updated_at": "2026-03-14T00:00:00Z",
  "is_active": true,
  "test_cases": [
    {
      "id": "uuid",
      "input": { "nums": [2, 7, 11, 15], "target": 9 },
      "expected_output": [0, 1],
      "is_sample": true,
      "is_hidden": false,
      "difficulty": "basic",
      "order_index": 0
    }
  ]
}
```

**Validation:**

- Trainer must own the class (403 if not)
- Title, description, difficulty, tags, optimal_solution, and at least one test case are required
- Difficulty must be one of: "Easy", "Medium", "Hard"

---

### 2. **GET /classes/{class_id}/questions**

Get all questions for a specific class.

**Path Parameters:**

- `class_id` (string): The ID of the class

**Query Parameters:**

- `trainer_id` (optional, UUID): Verify trainer access
- `include_inactive` (optional, boolean): Include inactive questions (default: false)

**Response (200 OK):**

```json
[
  {
    "id": "uuid",
    "title": "Two Sum Problem",
    "description": "Given an array of integers...",
    "difficulty": "Easy",
    "tags": ["Arrays", "Hash Table"],
    "constraints": ["1 <= nums.length <= 10^4"],
    "optimal_solution": "def twoSum(nums, target):\n    # solution",
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
    "acceptance_rate": 47.3,
    "total_submissions": 150,
    "successful_submissions": 71,
    "created_by": "uuid",
    "created_at": "2026-03-14T00:00:00Z",
    "updated_at": "2026-03-14T00:00:00Z",
    "is_active": true,
    "test_cases": [...]
  }
]
```

**Notes:**

- Returns questions created by the class trainer
- Ordered by creation date (newest first)
- Includes all test cases for each question

---

### 3. **PATCH /questions/{question_id}**

Update an existing question.

**Path Parameters:**

- `question_id` (UUID): The ID of the question to update

**Request Body:**

```json
{
  "trainer_id": "uuid",
  "title": "Updated Title",
  "description": "Updated description",
  "difficulty": "Medium",
  "tags": ["Arrays", "Two Pointers"],
  "constraints": ["Updated constraints"],
  "optimal_solution": "Updated solution code",
  "time_complexity": "O(n log n)",
  "space_complexity": "O(1)",
  "is_active": false
}
```

**Notes:**

- All fields are optional (only provided fields will be updated)
- Trainer must be the creator of the question (403 if not)
- At least one field must be provided for update

**Response (200 OK):**

```json
{
  "id": "uuid",
  "title": "Updated Title",
  "description": "Updated description",
  ...
  "updated_at": "2026-03-14T01:00:00Z"
}
```

---

## Error Responses

### 403 Forbidden

```json
{
  "detail": "Access denied: Not your class"
}
```

or

```json
{
  "detail": "Access denied: Not your question"
}
```

### 404 Not Found

```json
{
  "detail": "Class not found"
}
```

or

```json
{
  "detail": "Question not found"
}
```

### 400 Bad Request

```json
{
  "detail": "No fields to update"
}
```

### 500 Internal Server Error (SQLite Guard)

```json
{
  "detail": "Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
}
```

---

## Database Schema

### Questions Table

```sql
CREATE TABLE public.questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    tags TEXT[] NOT NULL,
    acceptance_rate DECIMAL(5,2),
    total_submissions INTEGER DEFAULT 0,
    successful_submissions INTEGER DEFAULT 0,
    constraints TEXT[],
    optimal_solution TEXT,
    time_complexity TEXT,
    space_complexity TEXT,
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

### Test Cases Table

```sql
CREATE TABLE public.test_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    input JSONB NOT NULL,
    expected_output JSONB NOT NULL,
    is_sample BOOLEAN DEFAULT FALSE,
    is_hidden BOOLEAN DEFAULT TRUE,
    difficulty TEXT CHECK (difficulty IN ('basic', 'edge', 'performance')),
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Frontend Integration

### Class Details Page with Tabs

The frontend now includes two tabs in the class details page:

1. **Students Tab** - Shows all enrolled students with their performance
2. **Course Materials Tab** - Shows:
   - Questions (with create/edit functionality)
   - Articles (mock data)
   - Videos (mock data)

### Question Form Features

- Create new questions with all required fields
- Edit existing questions
- Form validation
- Modal-based UI
- Support for:
  - Title and description
  - Difficulty selection (Easy/Medium/Hard)
  - Tags (comma-separated)
  - Constraints (one per line)
  - Optimal solution in Python
  - Time and space complexity
  - Test cases (note displayed for future implementation)

### Question Display

- List view with difficulty badges
- Tag display (first 3 tags + count)
- Edit button for trainers
- Creation date
- Hover effects and transitions

---

## Usage Examples

### Create a Question

```bash
curl -X POST "http://localhost:8000/classes/class-1-1/questions" \
  -H "Content-Type: application/json" \
  -d '{
    "trainer_id": "10000000-0000-0000-0000-000000000001",
    "title": "Reverse Linked List",
    "description": "Given the head of a singly linked list, reverse the list...",
    "difficulty": "Easy",
    "tags": ["Linked List", "Recursion"],
    "constraints": ["The number of nodes in the list is in the range [0, 5000]"],
    "optimal_solution": "def reverseList(head):\n    prev = None\n    curr = head\n    while curr:\n        next_temp = curr.next\n        curr.next = prev\n        prev = curr\n        curr = next_temp\n    return prev",
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
    "test_cases": [
      {
        "input": {"head": [1,2,3,4,5]},
        "expected_output": [5,4,3,2,1],
        "is_sample": true,
        "is_hidden": false,
        "difficulty": "basic",
        "order_index": 0
      }
    ]
  }'
```

### Get All Questions for a Class

```bash
curl "http://localhost:8000/classes/class-1-1/questions?trainer_id=10000000-0000-0000-0000-000000000001"
```

### Update a Question

```bash
curl -X PATCH "http://localhost:8000/questions/{question_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "trainer_id": "10000000-0000-0000-0000-000000000001",
    "difficulty": "Medium",
    "time_complexity": "O(n log n)"
  }'
```

---

## Security Features

1. **Trainer Verification**: All endpoints verify that the trainer owns the class or question
2. **SQLite Guard**: Prevents accidental use with SQLite (requires Postgres/Supabase)
3. **Input Validation**: Pydantic models validate all input data
4. **UUID Validation**: Path parameters are validated as proper UUIDs

---

## Future Enhancements

1. **Test Case Management**: Separate endpoints for adding/updating/deleting test cases
2. **Question Assignment**: Link questions to specific assignments or tasks
3. **Student Visibility**: Control which questions are visible to students
4. **Question Analytics**: Track submission rates, average solve time, etc.
5. **Question Categories**: Group questions by topic or difficulty
6. **Bulk Operations**: Create multiple questions at once
7. **Question Templates**: Pre-defined question structures

---

**Last Updated:** March 14, 2026  
**Version:** 1.0.0  
**Status:** Phase 1 Complete
