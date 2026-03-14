# User Profile API Documentation

## Overview

This document describes the backend API routes for managing user profiles in the Buildor platform. The profile system includes profile cards, portfolio README, contribution graphs, questions solved history, academic information, external links, and professor feedback.

---

## Base URL: `/profile`

---

## Table of Contents

1. [Profile Card Endpoints](#profile-card-endpoints)
2. [Portfolio README Endpoints](#portfolio-readme-endpoints)
3. [Contribution Graph Endpoints](#contribution-graph-endpoints)
4. [Questions Solved History Endpoints](#questions-solved-history-endpoints)
5. [Academic Info Endpoints](#academic-info-endpoints)
6. [External Links Endpoints](#external-links-endpoints)
7. [Professor Feedback Endpoints](#professor-feedback-endpoints)
8. [Database Schema](#database-schema)
9. [Usage Examples](#usage-examples)

---

## Profile Card Endpoints

### 1. **GET /profile/{user_id}**

Get complete profile card information for a user.

**Path Parameters:**

- `user_id` (UUID): The ID of the user

**Response (200 OK):**

```json
{
  "user_id": "uuid",
  "full_name": "John Doe",
  "username": "johndoe",
  "email": "john@example.com",
  "role": "student",
  "profile_description": "Full-stack developer passionate about AI",
  "location": "San Francisco, CA",
  "website": "https://johndoe.dev",
  "github_username": "johndoe",
  "graduation_year": 2025,
  "avatar_url": "https://...",
  "banner_url": "https://...",
  "skill_level": "Advanced",
  "problems_solved": 150,
  "rank": 42,
  "university": "Stanford University",
  "department": "Computer Science"
}
```

---

### 2. **PATCH /profile/{user_id}**

Update profile card information.

**Path Parameters:**

- `user_id` (UUID): The ID of the user

**Request Body:**

```json
{
  "username": "johndoe",
  "profile_description": "Updated bio",
  "location": "New York, NY",
  "website": "https://newsite.com",
  "github_username": "johndoe",
  "graduation_year": 2025,
  "avatar_url": "https://...",
  "banner_url": "https://..."
}
```

**Notes:**

- All fields are optional
- Creates profile if it doesn't exist (username required for new profiles)
- Returns updated profile card

---

## Portfolio README Endpoints

### 3. **GET /profile/{user_id}/readme**

Get portfolio README markdown content.

**Response (200 OK):**

```json
{
  "user_id": "uuid",
  "portfolio_readme": "# My Portfolio\n\nWelcome to my portfolio...",
  "readme_updated_at": "2026-03-14T12:00:00Z"
}
```

---

### 4. **PATCH /profile/{user_id}/readme**

Update portfolio README markdown content.

**Request Body:**

```json
{
  "portfolio_readme": "# Updated Portfolio\n\n## Projects\n- Project 1\n- Project 2"
}
```

**Notes:**

- Markdown content up to 50,000 characters
- Automatically updates `readme_updated_at` timestamp

---

## Contribution Graph Endpoints

### 5. **GET /profile/{user_id}/contributions**

Get contribution activity graph data.

**Query Parameters:**

- `days` (optional, int): Number of days to retrieve (default: 365)

**Response (200 OK):**

```json
{
  "user_id": "uuid",
  "contributions": [
    {
      "date": "2026-03-14",
      "count": 5,
      "level": 3
    },
    {
      "date": "2026-03-13",
      "count": 2,
      "level": 1
    }
  ],
  "total_contributions": 450,
  "current_streak": 7,
  "longest_streak": 21
}
```

**Notes:**

- `level` is 0-4 for visualization intensity (GitHub-style)
- Contributions include submissions, questions solved, and comments
- Streaks calculated based on consecutive days with contributions

---

## Questions Solved History Endpoints

### 6. **GET /profile/{user_id}/questions-solved**

Get detailed history of questions solved by a user.

**Query Parameters:**

- `limit` (optional, int): Number of results (default: 100)
- `offset` (optional, int): Pagination offset (default: 0)
- `difficulty` (optional, string): Filter by difficulty ("Easy", "Medium", "Hard")

**Response (200 OK):**

```json
[
  {
    "question_id": "uuid",
    "question_title": "Two Sum",
    "difficulty": "Easy",
    "tags": ["Arrays", "Hash Table"],
    "solved_at": "2026-03-14T10:30:00Z",
    "best_runtime_ms": 124,
    "best_memory_kb": 18400,
    "runtime_percentile": 95.5,
    "memory_percentile": 92.3,
    "hints_used": 0,
    "language": "python",
    "attempts": 3
  }
]
```

**Notes:**

- Includes runtime/memory percentiles (e.g., 95.5 = top 5%)
- Language is always "python" as per requirements
- Ordered by `solved_at` descending (most recent first)

---

## Academic Info Endpoints

### 7. **GET /profile/{user_id}/academic-info**

Get academic information for a user.

**Response (200 OK):**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "university": "Stanford University",
  "degree": "B.S. Computer Science",
  "major": "Computer Science",
  "minor": "Mathematics",
  "gpa": 3.85,
  "expected_graduation": "May 2025",
  "honors": ["Dean's List", "Cum Laude"],
  "relevant_coursework": ["Data Structures", "Algorithms", "Machine Learning"],
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-03-14T12:00:00Z"
}
```

**Returns:** `null` if no academic info exists

---

### 8. **POST /profile/{user_id}/academic-info**

Create academic information for a user.

**Request Body:**

```json
{
  "university": "Stanford University",
  "degree": "B.S. Computer Science",
  "major": "Computer Science",
  "minor": "Mathematics",
  "gpa": 3.85,
  "expected_graduation": "May 2025",
  "honors": ["Dean's List"],
  "relevant_coursework": ["Data Structures", "Algorithms"]
}
```

**Response (201 Created):**
Returns created academic info object.

**Notes:**

- `university` and `degree` are required
- GPA must be between 0.0 and 4.0
- Returns 400 if academic info already exists

---

### 9. **PATCH /profile/{user_id}/academic-info**

Update academic information.

**Request Body:**

```json
{
  "gpa": 3.9,
  "honors": ["Dean's List", "Summa Cum Laude"],
  "relevant_coursework": ["Data Structures", "Algorithms", "AI"]
}
```

**Notes:**

- All fields are optional
- Returns 404 if academic info doesn't exist

---

## External Links Endpoints

### 10. **GET /profile/{user_id}/external-links**

Get all external links for a user.

**Response (200 OK):**

```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "platform": "GitHub",
    "url": "https://github.com/johndoe",
    "display_name": "My GitHub",
    "order_index": 0
  },
  {
    "id": "uuid",
    "user_id": "uuid",
    "platform": "LinkedIn",
    "url": "https://linkedin.com/in/johndoe",
    "display_name": null,
    "order_index": 1
  }
]
```

**Notes:**

- Ordered by `order_index` ascending, then `created_at`

---

### 11. **POST /profile/{user_id}/external-links**

Create a new external link.

**Request Body:**

```json
{
  "platform": "GitHub",
  "url": "https://github.com/johndoe",
  "display_name": "My GitHub Profile",
  "order_index": 0
}
```

**Response (201 Created):**
Returns created link object.

---

### 12. **PATCH /profile/external-links/{link_id}**

Update an external link.

**Request Body:**

```json
{
  "user_id": "uuid",
  "platform": "GitHub",
  "url": "https://github.com/newusername",
  "display_name": "Updated Name",
  "order_index": 2
}
```

**Notes:**

- `user_id` required in body for ownership verification
- All other fields are optional

---

### 13. **DELETE /profile/external-links/{link_id}**

Delete an external link.

**Request Body:**

```json
{
  "user_id": "uuid"
}
```

**Response (204 No Content)**

**Notes:**

- `user_id` required for ownership verification

---

## Professor Feedback Endpoints

### 14. **GET /profile/{student_id}/professor-feedback**

Get professor feedback for a student's profile.

**Query Parameters:**

- `include_hidden` (optional, bool): Include hidden feedback (default: false)

**Response (200 OK):**

```json
[
  {
    "id": "uuid",
    "student_id": "uuid",
    "professor_id": "uuid",
    "professor_name": "Dr. Jane Smith",
    "course_name": "Data Structures & Algorithms",
    "course_code": "CS201",
    "feedback_text": "Excellent work on the final project. Shows deep understanding of algorithms.",
    "rating": 5,
    "is_visible": true,
    "is_pinned": false,
    "created_at": "2026-03-10T15:00:00Z"
  }
]
```

**Notes:**

- By default, only returns visible feedback
- Ordered by pinned status (pinned first), then creation date descending

---

### 15. **POST /profile/professor-feedback**

Create professor feedback for a student.

**Request Body:**

```json
{
  "professor_id": "uuid",
  "student_id": "uuid",
  "course_name": "Data Structures & Algorithms",
  "course_code": "CS201",
  "feedback_text": "Great performance in class!",
  "rating": 5
}
```

**Response (201 Created):**
Returns created feedback object.

**Notes:**

- `professor_id` required in body
- Only trainers can create feedback (verified via role check)
- Rating is optional (1-5 scale)

---

### 16. **PATCH /profile/professor-feedback/{feedback_id}**

Update professor feedback visibility/pinned status.

**Request Body:**

```json
{
  "student_id": "uuid",
  "is_visible": false,
  "is_pinned": true
}
```

**Notes:**

- `student_id` required for ownership verification
- Only students can update their own feedback visibility
- Students can hide or pin feedback they received

---

## Database Schema

### New Tables Created

#### 1. **user_profiles**

Extended profile information for users.

```sql
CREATE TABLE public.user_profiles (
    user_id UUID PRIMARY KEY REFERENCES public.users(id),
    username TEXT UNIQUE NOT NULL,
    profile_description TEXT,
    location TEXT,
    website TEXT,
    github_username TEXT,
    graduation_year INTEGER,
    portfolio_readme TEXT,
    readme_updated_at TIMESTAMP WITH TIME ZONE,
    avatar_url TEXT,
    banner_url TEXT,
    theme_preference TEXT DEFAULT 'system',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 2. **academic_info**

Detailed academic information for students.

```sql
CREATE TABLE public.academic_info (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    university TEXT NOT NULL,
    degree TEXT NOT NULL,
    major TEXT,
    minor TEXT,
    gpa DECIMAL(3,2),
    expected_graduation TEXT,
    honors TEXT[],
    relevant_coursework TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);
```

#### 3. **external_links**

Social media and external platform links.

```sql
CREATE TABLE public.external_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    platform TEXT NOT NULL,
    url TEXT NOT NULL,
    display_name TEXT,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 4. **contribution_activity**

Daily contribution tracking (GitHub-style graph).

```sql
CREATE TABLE public.contribution_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    activity_date DATE NOT NULL,
    contribution_count INTEGER DEFAULT 0,
    submissions_count INTEGER DEFAULT 0,
    questions_solved_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, activity_date)
);
```

#### 5. **professor_feedback_profile**

Feedback from professors shown on student profiles.

```sql
CREATE TABLE public.professor_feedback_profile (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES public.users(id),
    professor_id UUID NOT NULL REFERENCES public.users(id),
    course_name TEXT NOT NULL,
    course_code TEXT,
    feedback_text TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    is_visible BOOLEAN DEFAULT TRUE,
    is_pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 6. **submission_rankings**

Stores ranking/percentile information for submissions.

```sql
CREATE TABLE public.submission_rankings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES public.submissions(id),
    question_id UUID NOT NULL REFERENCES public.questions(id),
    user_id UUID NOT NULL REFERENCES public.users(id),
    runtime_percentile DECIMAL(5,2),
    memory_percentile DECIMAL(5,2),
    overall_rank INTEGER,
    total_submissions_at_time INTEGER,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(submission_id)
);
```

---

## Usage Examples

### Get User Profile Card

```bash
curl http://127.0.0.1:8000/profile/10000000-0000-0000-0000-000000000001
```

### Update Profile Card

```bash
curl -X PATCH "http://127.0.0.1:8000/profile/10000000-0000-0000-0000-000000000001" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "profile_description": "Full-stack developer",
    "location": "San Francisco, CA",
    "graduation_year": 2025
  }'
```

### Update Portfolio README

```bash
curl -X PATCH "http://127.0.0.1:8000/profile/10000000-0000-0000-0000-000000000001/readme" \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_readme": "# My Portfolio\n\n## About Me\nI am a passionate developer..."
  }'
```

### Get Contribution Graph

```bash
curl "http://127.0.0.1:8000/profile/10000000-0000-0000-0000-000000000001/contributions?days=365"
```

### Get Questions Solved History

```bash
curl "http://127.0.0.1:8000/profile/10000000-0000-0000-0000-000000000001/questions-solved?limit=50&difficulty=Medium"
```

### Create Academic Info

```bash
curl -X POST "http://127.0.0.1:8000/profile/10000000-0000-0000-0000-000000000001/academic-info" \
  -H "Content-Type: application/json" \
  -d '{
    "university": "Stanford University",
    "degree": "B.S. Computer Science",
    "major": "Computer Science",
    "gpa": 3.85,
    "expected_graduation": "May 2025",
    "honors": ["Dean'\''s List"],
    "relevant_coursework": ["Data Structures", "Algorithms"]
  }'
```

### Add External Link

```bash
curl -X POST "http://127.0.0.1:8000/profile/10000000-0000-0000-0000-000000000001/external-links" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "GitHub",
    "url": "https://github.com/johndoe",
    "display_name": "My GitHub",
    "order_index": 0
  }'
```

### Create Professor Feedback

```bash
curl -X POST "http://127.0.0.1:8000/profile/professor-feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "professor_id": "20000000-0000-0000-0000-000000000001",
    "student_id": "10000000-0000-0000-0000-000000000001",
    "course_name": "Data Structures & Algorithms",
    "course_code": "CS201",
    "feedback_text": "Excellent work throughout the semester!",
    "rating": 5
  }'
```

### Update Feedback Visibility (Student)

```bash
curl -X PATCH "http://127.0.0.1:8000/profile/professor-feedback/{feedback_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "10000000-0000-0000-0000-000000000001",
    "is_visible": false,
    "is_pinned": true
  }'
```

---

## Error Responses

### 403 Forbidden

```json
{
  "detail": "Access denied: Not your link"
}
```

### 404 Not Found

```json
{
  "detail": "User not found"
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

## Security Features

1. **SQLite Guard**: All endpoints verify Postgres/Supabase connection
2. **Ownership Verification**: Users can only update their own data
3. **Role-Based Access**: Only trainers can create professor feedback
4. **Input Validation**: Pydantic models validate all input data
5. **UUID Validation**: Path parameters validated as proper UUIDs

---

## Frontend Integration Notes

### Profile Page Sections Supported

1. **Left Profile Card** (`@profile/page.tsx:L69-L122`)
   - GET/PATCH `/profile/{user_id}`
   - Displays: name, username, bio, location, website, GitHub, graduation year

2. **Portfolio README** (`@profile/page.tsx:L420-L430`)
   - GET/PATCH `/profile/{user_id}/readme`
   - Markdown editor for portfolio content

3. **Contribution Graph** (`@profile/page.tsx:L55`)
   - GET `/profile/{user_id}/contributions`
   - GitHub-style contribution heatmap

4. **Questions Solved Tab** (`@profile/page.tsx:L302-L310`)
   - GET `/profile/{user_id}/questions-solved`
   - Displays: runtime, memory, percentiles, hints used, attempts

5. **Professor Feedback** (`@profile/page.tsx:L461-L478`)
   - GET `/profile/{student_id}/professor-feedback`
   - POST `/profile/professor-feedback` (trainers only)
   - PATCH visibility/pinned status (students)

6. **Academic Info** (`@profile/page.tsx:L493-L543`)
   - GET/POST/PATCH `/profile/{user_id}/academic-info`
   - University, degree, GPA, graduation, honors, coursework

7. **External Links** (`@profile/page.tsx:L493-L543`)
   - GET/POST/PATCH/DELETE external links
   - GitHub, LinkedIn, LeetCode, etc.

---

## Future Enhancements

1. **Contribution Activity Auto-Update**: Trigger to automatically update contribution counts on submissions
2. **Ranking Calculation**: Background job to calculate submission rankings/percentiles
3. **Profile Analytics**: Track profile views, link clicks
4. **Custom Themes**: Support for custom profile themes/colors
5. **Profile Badges**: Achievement badges displayed on profiles
6. **Profile Privacy Settings**: Control who can view different sections
7. **Profile Export**: Export profile data as PDF/JSON

---

**Last Updated:** March 14, 2026  
**Version:** 1.0.0  
**Status:** Phase 1 Complete

---

## Setup Instructions

### 1. Run Profile Schema Migration

```bash
# Connect to your Supabase database
psql -h db.wvbbdvwdazwehwlsdvsc.supabase.co -U postgres -d postgres

# Run the profile schema
\i database/profile_schema.sql
```

### 2. Verify Tables Created

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'user_profiles',
    'academic_info',
    'external_links',
    'contribution_activity',
    'professor_feedback_profile',
    'submission_rankings'
  );
```

### 3. Test Endpoints

Start the backend server and test via Swagger UI:

```
http://127.0.0.1:8000/docs
```

Look for the "User Profile" tag with all endpoints listed.

---

## Notes

- **Contribution Graph**: Currently returns data from `contribution_activity` table. You'll need to implement a background job or trigger to populate this table based on user activity (submissions, questions solved, etc.).

- **Submission Rankings**: The `submission_rankings` table needs to be populated when submissions are evaluated. Consider adding a post-processing step after code execution to calculate percentiles.

- **Professor Feedback vs Class Feedback**: The `professor_feedback_profile` table is separate from the general `feedback` table. Profile feedback is meant to be displayed on student profiles as testimonials, while class feedback is for course-specific complaints/questions.

- **Username Uniqueness**: Usernames must be unique across the platform. The first time a user updates their profile, they must provide a username.
