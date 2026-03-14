# Backend API Implementation - Phase 1

## Overview

This document describes the implemented backend routes for **Leaderboard** and **Trainer Analytics** functionality.

---

## 🎯 Leaderboard API

### Base URL: `/leaderboard`

### 1. **GET /leaderboard/**

Get student leaderboard with multiple ranking algorithms.

**Query Parameters:**

- `ranking_type` (optional): `"overall"` | `"skill"` | `"problems"` (default: `"overall"`)
- `search` (optional): Search students by name (case-insensitive)
- `limit` (optional): Max students to return (1-500, default: 100)

**Ranking Algorithms:**

#### Overall Ranking (default)

- Uses pre-calculated `rank` from database
- Rank is auto-updated by `update_leaderboard_ranks()` function
- Based on problems solved (descending), with creation date as tiebreaker

#### Skill Level Ranking

- Ranks by skill level: Expert (4) > Advanced (3) > Intermediate (2) > Beginner (1)
- Tiebreaker: problems solved (descending)
- Second tiebreaker: account creation date (ascending)

#### Problems Solved Ranking

- Pure ranking by number of problems solved (descending)
- Tiebreaker: account creation date (ascending)

**Response:**

```json
{
  "rankingType": "overall",
  "totalStudents": 20,
  "students": [
    {
      "id": "uuid",
      "name": "Student Name",
      "rank": 1,
      "problemsSolved": 250,
      "skillLevel": "Expert",
      "university": "MIT",
      "department": "Computer Science",
      "avatarUrl": "https://..."
    }
  ]
}
```

**Example Requests:**

```bash
# Get overall leaderboard
GET /leaderboard/?ranking_type=overall

# Get leaderboard ranked by skill level
GET /leaderboard/?ranking_type=skill

# Get leaderboard ranked by problems solved
GET /leaderboard/?ranking_type=problems

# Search for specific students
GET /leaderboard/?search=alice&ranking_type=overall

# Limit results
GET /leaderboard/?limit=50
```

---

### 2. **GET /leaderboard/user/{user_id}**

Get a specific user's leaderboard position and detailed stats.

**Path Parameters:**

- `user_id`: UUID of the student

**Response:**

```json
{
  "id": "uuid",
  "name": "Student Name",
  "rank": 12,
  "problemsSolved": 145,
  "skillLevel": "Intermediate",
  "university": "Stanford",
  "department": "Computer Science",
  "avatarUrl": "https://...",
  "totalQuestions": 45,
  "completionRate": 32.22
}
```

**Example Request:**

```bash
GET /leaderboard/user/20000000-0000-0000-0000-000000000001
```

---

## 👨‍🏫 Trainer Analytics API

### Base URL: `/trainer-analytics`

### 1. **GET /trainer-analytics/overview/{trainer_id}**

Get comprehensive trainer dashboard overview.

**Path Parameters:**

- `trainer_id`: UUID of the trainer

**Response Structure:**

```json
{
  "trainer": {
    "id": "uuid",
    "name": "Trainer Name"
  },
  "stats": {
    "totalClasses": 4,
    "totalStudents": 165,
    "pendingTasks": 2,
    "unreadFeedback": 3
  },
  "classes": [
    {
      "id": "class-1-1",
      "name": "Class Name",
      "code": "CS201",
      "studentCount": 45,
      "nextSession": "Mon, 10:00 AM",
      "progress": 68
    }
  ],
  "tasks": [
    {
      "id": "uuid",
      "title": "Grade Assignment 4",
      "classCode": "CS201",
      "type": "assignment",
      "status": "grading",
      "dueDate": "2026-03-15T10:00:00Z"
    }
  ],
  "feedback": [
    {
      "id": "uuid",
      "studentName": "Alice Johnson",
      "classCode": "CS201",
      "type": "complaint",
      "message": "The assignment was too difficult...",
      "read": false,
      "date": "2026-03-13T14:30:00Z"
    }
  ]
}
```

**Features:**

- **Stats Calculation:**
  - `totalClasses`: Count of classes taught by trainer
  - `totalStudents`: Unique students across all classes (active enrollments only)
  - `pendingTasks`: Tasks with status 'grading' or 'overdue'
  - `unreadFeedback`: Feedback items where `is_read = false`

- **Classes List:**
  - All classes taught by the trainer
  - Includes student count per class
  - Ordered by creation date (newest first)

- **Tasks List:**
  - Top 10 tasks ordered by priority:
    1. Overdue tasks (highest priority)
    2. Grading tasks
    3. Pending tasks
    4. Other tasks
  - Within each priority, ordered by due date

- **Feedback List:**
  - Last 20 feedback items
  - Ordered by creation date (newest first)
  - Includes student name and class code

**Example Request:**

```bash
GET /trainer-analytics/overview/10000000-0000-0000-0000-000000000001
```

---

### 2. **GET /trainer-analytics/classes/{class_id}**

Get detailed information about a specific class.

**Path Parameters:**

- `class_id`: ID of the class (e.g., "class-1-1")

**Query Parameters:**

- `trainer_id` (optional): Trainer UUID for access verification

**Response Structure:**

```json
{
  "classInfo": {
    "id": "class-1-1",
    "name": "Data Structures & Algorithms",
    "code": "CS201",
    "studentCount": 45,
    "avgScore": 72,
    "topPerformer": "Alice Johnson",
    "completionRate": 68,
    "trainerName": "Trainer 1"
  },
  "students": [
    {
      "id": "uuid",
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "rank": 1,
      "problemsSolved": 42,
      "totalProblems": 45,
      "skillLevel": "Expert",
      "individualProgress": 85,
      "enrolledAt": "2025-12-15T10:00:00Z"
    }
  ]
}
```

**Features:**

- **Class Metadata:**
  - Student count (active enrollments)
  - Average score (calculated from individual_progress)
  - Top performer (student with most problems solved)
  - Completion rate (class progress)

- **Student List:**
  - All enrolled students (active status)
  - Ranked by problems solved (descending)
  - Includes individual progress in the class
  - Shows total problems solved vs available

**Example Request:**

```bash
GET /trainer-analytics/classes/class-1-1?trainer_id=10000000-0000-0000-0000-000000000001
```

---

### 3. **POST /trainer-analytics/feedback/{feedback_id}/mark-read**

Mark a feedback item as read.

**Path Parameters:**

- `feedback_id`: UUID of the feedback item

**Request Body:**

```json
{
  "trainer_id": "uuid"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Feedback marked as read"
}
```

**Security:**

- Verifies feedback belongs to trainer's class
- Returns 404 if feedback not found or access denied

---

### 4. **POST /trainer-analytics/feedback/{feedback_id}/respond**

Respond to student feedback.

**Path Parameters:**

- `feedback_id`: UUID of the feedback item

**Request Body:**

```json
{
  "trainer_id": "uuid",
  "response": "Thank you for your feedback. I will..."
}
```

**Response:**

```json
{
  "success": true,
  "message": "Response added successfully"
}
```

**Features:**

- Adds trainer's response to feedback
- Automatically marks feedback as read
- Records response timestamp and responder ID

**Security:**

- Verifies feedback belongs to trainer's class
- Returns 404 if feedback not found or access denied

---

## 🗄️ Database Configuration

### Environment Variables

**For Supabase PostgreSQL (Production):**

```bash
DATABASE_URL=postgresql://postgres:[PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres
```

**For Local Development (SQLite):**

```bash
# No environment variable needed - defaults to SQLite
# Or explicitly set:
DATABASE_URL=sqlite:///./sql_app.db
```

### Configuration File

Location: `backend/app/infrastructure/database.py`

The database configuration automatically detects the database type and applies appropriate connection settings.

---

## 📊 Database Schema Usage

### Tables Used:

1. **`public.users`**
   - Student and trainer profiles
   - Rank and problems_solved fields
   - Role-based filtering

2. **`public.classes`**
   - Class information
   - Trainer ownership via `trainer_id`
   - Progress tracking

3. **`public.class_enrollments`**
   - Student-class relationships
   - Individual progress per student
   - Enrollment status tracking

4. **`public.tasks`**
   - Assignments, quizzes, exams
   - Status tracking (pending, grading, overdue, completed)
   - Due date management

5. **`public.feedback`**
   - Student feedback and complaints
   - Read/unread status
   - Trainer responses

6. **`public.user_question_progress`**
   - Tracks solved questions per user
   - Used for calculating problems_solved

7. **`public.questions`**
   - Available coding problems
   - Active/inactive status

---

## 🔐 Security Features

### Access Control:

- **Trainer Analytics:** Verifies trainer ownership of classes
- **Feedback Operations:** Ensures trainer can only access their class feedback
- **Student Data:** RLS policies enforce data isolation

### Error Handling:

- 404: Resource not found
- 403: Access denied (not your class)
- Proper error messages for debugging

---

## 🚀 Testing the APIs

### Using cURL:

```bash
# Test leaderboard
curl http://localhost:8000/leaderboard/?ranking_type=overall

# Test trainer overview
curl http://localhost:8000/trainer-analytics/overview/10000000-0000-0000-0000-000000000001

# Test class details
curl http://localhost:8000/trainer-analytics/classes/class-1-1

# Mark feedback as read
curl -X POST http://localhost:8000/trainer-analytics/feedback/{feedback_id}/mark-read \
  -H "Content-Type: application/json" \
  -d '{"trainer_id": "10000000-0000-0000-0000-000000000001"}'
```

### Using FastAPI Docs:

Navigate to `http://localhost:8000/docs` for interactive API documentation.

---

## 📝 Implementation Notes

### Ranking Algorithm for Skill Level:

The skill level ranking addresses your concern about having few skill levels by:

1. Primary sort: Skill level (Expert > Advanced > Intermediate > Beginner)
2. Secondary sort: Problems solved (descending) - **This is the key differentiator**
3. Tertiary sort: Account creation date (ascending)

This means students with the same skill level are ranked by their problems solved count, providing granular ranking even within the same skill tier.

### Performance Optimizations:

- Efficient SQL queries with proper JOINs
- Indexed columns used in WHERE and ORDER BY clauses
- Limited result sets to prevent large data transfers
- Aggregated queries to minimize database round-trips

### Future Enhancements:

- Pagination for large result sets
- Caching for frequently accessed data
- WebSocket support for real-time updates
- Batch operations for bulk feedback responses

---

## 🔄 Integration with Frontend

### Frontend Files:

- **Leaderboard:** `frontend/app/leaderboard/page.tsx`
- **Trainer Overview:** `frontend/app/trainer-analytics/page.tsx`
- **Class Details:** `frontend/app/trainer-analytics/classes/[classId]/page.tsx`

### API Call Examples:

```typescript
// Fetch leaderboard
const response = await fetch("/leaderboard/?ranking_type=overall");
const data = await response.json();

// Fetch trainer overview
const overview = await fetch(`/trainer-analytics/overview/${trainerId}`);
const trainerData = await overview.json();

// Fetch class details
const classDetails = await fetch(`/trainer-analytics/classes/${classId}`);
const classData = await classDetails.json();
```

---

## ✅ Completed Features

- ✅ Leaderboard with 3 ranking algorithms (overall, skill, problems)
- ✅ Student search functionality
- ✅ User-specific leaderboard position
- ✅ Trainer analytics overview with aggregated stats
- ✅ Class details with student performance
- ✅ Feedback management (mark as read, respond)
- ✅ Proper error handling and access control
- ✅ Database configuration for Supabase PostgreSQL
- ✅ Comprehensive API documentation

---

**Last Updated:** March 13, 2026  
**Version:** 1.0.0  
**Status:** Phase 1 Complete
