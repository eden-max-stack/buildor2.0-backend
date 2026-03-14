# Buildor Database Schema Documentation

## Overview
This document describes the PostgreSQL database schema for the Buildor learning platform, designed for deployment on Supabase.

## Database Structure

### 1. Users Table (`public.users`)
Extends Supabase's `auth.users` with additional profile information for both trainers and students.

**Columns:**
- `id` (UUID, PK) - References `auth.users(id)`
- `email` (TEXT, UNIQUE) - User email address
- `full_name` (TEXT) - User's full name
- `role` (TEXT) - Either 'student' or 'trainer'
- `university` (TEXT) - Student's university (nullable)
- `department` (TEXT) - Student's department (nullable)
- `skill_level` (TEXT) - 'Beginner', 'Intermediate', 'Advanced', or 'Expert'
- `problems_solved` (INTEGER) - Count of problems solved (auto-updated)
- `rank` (INTEGER) - Leaderboard rank (auto-calculated)
- `avatar_url` (TEXT) - Profile picture URL
- `bio` (TEXT) - User biography
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

**Purpose:** Stores all user profile information with role-based differentiation between trainers and students.

---

### 2. Classes Table (`public.classes`)
Stores information about courses/classes taught by trainers.

**Columns:**
- `id` (TEXT, PK) - Class identifier (e.g., "cs201")
- `name` (TEXT) - Full class name
- `code` (TEXT, UNIQUE) - Short class code (e.g., "CS201")
- `description` (TEXT) - Class description
- `trainer_id` (UUID, FK) - References `users(id)`
- `next_session` (TEXT) - Next session time (e.g., "Mon, 10:00 AM")
- `schedule_details` (JSONB) - Complex scheduling information
- `progress` (INTEGER) - Overall class progress (0-100)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

**Purpose:** Manages class/course information for the trainer analytics system.

---

### 3. Class Enrollments Table (`public.class_enrollments`)
Many-to-many relationship between students and classes.

**Columns:**
- `id` (UUID, PK)
- `class_id` (TEXT, FK) - References `classes(id)`
- `student_id` (UUID, FK) - References `users(id)`
- `enrolled_at` (TIMESTAMP)
- `status` (TEXT) - 'active', 'completed', or 'dropped'
- `individual_progress` (INTEGER) - Student's progress in this class (0-100)

**Purpose:** Tracks which students are enrolled in which classes and their individual progress.

---

### 4. Tasks Table (`public.tasks`)
Assignments, quizzes, and other tasks assigned to classes.

**Columns:**
- `id` (UUID, PK)
- `title` (TEXT) - Task title
- `description` (TEXT) - Task description
- `class_id` (TEXT, FK) - References `classes(id)`
- `type` (TEXT) - 'assignment', 'quiz', 'review', or 'lecture'
- `status` (TEXT) - 'pending', 'grading', 'overdue', or 'completed'
- `due_date` (TIMESTAMP)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- `total_submissions` (INTEGER)
- `graded_submissions` (INTEGER)

**Purpose:** Manages tasks/assignments for classes, displayed in trainer analytics.

---

### 5. Feedback Table (`public.feedback`)
Student feedback and complaints about classes.

**Columns:**
- `id` (UUID, PK)
- `student_id` (UUID, FK) - References `users(id)`
- `class_id` (TEXT, FK) - References `classes(id)`
- `type` (TEXT) - 'feedback', 'complaint', or 'question'
- `message` (TEXT) - Feedback content
- `is_read` (BOOLEAN) - Whether trainer has read it
- `response` (TEXT) - Trainer's response
- `responded_at` (TIMESTAMP)
- `responded_by` (UUID, FK) - References `users(id)`
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

**Purpose:** Allows students to provide feedback and trainers to respond.

---

### 6. Questions Table (`public.questions`)
Coding problems/questions available on the platform.

**Columns:**
- `id` (UUID, PK)
- `title` (TEXT) - Question title
- `description` (TEXT) - Full problem description
- `difficulty` (TEXT) - 'Easy', 'Medium', or 'Hard'
- `tags` (TEXT[]) - Array of tags (e.g., ["Arrays", "Hash Table"])
- `acceptance_rate` (DECIMAL) - Percentage of successful submissions
- `total_submissions` (INTEGER) - Auto-calculated
- `successful_submissions` (INTEGER) - Auto-calculated
- `constraints` (TEXT[]) - Array of constraint strings
- `optimal_solution` (TEXT) - Python code for optimal solution
- `time_complexity` (TEXT) - e.g., "O(n)"
- `space_complexity` (TEXT) - e.g., "O(1)"
- `created_by` (UUID, FK) - References `users(id)`
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- `is_active` (BOOLEAN) - Whether question is visible

**Purpose:** Stores all coding problems available on the platform.

---

### 7. Test Cases Table (`public.test_cases`)
Test cases for validating question submissions.

**Columns:**
- `id` (UUID, PK)
- `question_id` (UUID, FK) - References `questions(id)`
- `input` (JSONB) - Test case input (flexible JSON structure)
- `expected_output` (JSONB) - Expected output
- `is_sample` (BOOLEAN) - Whether shown to users as example
- `is_hidden` (BOOLEAN) - Hidden test cases for validation
- `difficulty` (TEXT) - 'basic', 'edge', or 'performance'
- `order_index` (INTEGER) - Display order
- `created_at` (TIMESTAMP)

**Purpose:** Stores test cases for each question to validate submissions.

---

### 8. Submissions Table (`public.submissions`)
User code submissions for questions.

**Columns:**
- `id` (UUID, PK)
- `question_id` (UUID, FK) - References `questions(id)`
- `user_id` (UUID, FK) - References `users(id)`
- `code` (TEXT) - Submitted code
- `language` (TEXT) - 'python', 'javascript', 'java', 'cpp', or 'go'
- `status` (TEXT) - 'pending', 'running', 'accepted', 'wrong_answer', 'time_limit_exceeded', 'runtime_error', 'compilation_error'
- `test_cases_passed` (INTEGER)
- `total_test_cases` (INTEGER)
- `runtime_ms` (INTEGER) - Execution time in milliseconds
- `memory_kb` (INTEGER) - Memory used in kilobytes
- `hints_used` (INTEGER) - Number of hints used
- `submitted_at` (TIMESTAMP)
- `executed_at` (TIMESTAMP)
- `error_message` (TEXT)
- `failed_test_case_id` (UUID, FK) - References `test_cases(id)`

**Purpose:** Tracks all user submissions with detailed execution metrics.

---

### 9. User Question Progress Table (`public.user_question_progress`)
Tracks user progress on individual questions.

**Columns:**
- `id` (UUID, PK)
- `user_id` (UUID, FK) - References `users(id)`
- `question_id` (UUID, FK) - References `questions(id)`
- `status` (TEXT) - 'not_started', 'attempted', or 'solved'
- `attempts` (INTEGER) - Number of attempts
- `best_runtime_ms` (INTEGER) - Best runtime achieved
- `best_memory_kb` (INTEGER) - Best memory usage achieved
- `hints_used_total` (INTEGER) - Total hints used
- `first_attempted_at` (TIMESTAMP)
- `solved_at` (TIMESTAMP)
- `last_attempted_at` (TIMESTAMP)

**Purpose:** Maintains a summary of each user's progress on each question.

---

## Database Views

### 1. `trainer_analytics_overview`
Provides aggregated statistics for trainer dashboard:
- Total classes
- Total students across all classes
- Pending tasks count
- Unread feedback count

### 2. `class_details`
Enhanced class information with:
- Student count per class
- Trainer name
- All class metadata

### 3. `leaderboard`
Ordered list of students by rank with:
- Name, rank, problems solved
- Skill level, university, department
- Avatar URL

---

## Indexes

### Performance Indexes Created:
- **Users:** role, skill_level, rank
- **Classes:** trainer_id, code
- **Class Enrollments:** class_id, student_id, status
- **Tasks:** class_id, status, due_date, type
- **Feedback:** student_id, class_id, is_read, type
- **Questions:** difficulty, tags (GIN index), created_by, is_active
- **Test Cases:** question_id, is_sample
- **Submissions:** question_id, user_id, status, submitted_at (DESC)
- **User Question Progress:** user_id, question_id, status

---

## Automated Functions & Triggers

### 1. `update_updated_at_column()`
Automatically updates `updated_at` timestamp on row modification.
- Applied to: users, classes, tasks, feedback, questions

### 2. `update_question_stats()`
Automatically recalculates question statistics when submissions are added:
- `total_submissions`
- `successful_submissions`
- `acceptance_rate`

### 3. `update_user_problems_solved()`
Increments user's `problems_solved` count when they solve a new question.

### 4. `update_leaderboard_ranks()`
Recalculates all student ranks based on problems solved.
- Call manually: `SELECT update_leaderboard_ranks();`

---

## Row Level Security (RLS)

All tables have RLS enabled with the following policies:

### Users
- ✅ Anyone can view all profiles
- ✅ Users can update their own profile only

### Classes
- ✅ Anyone can view classes
- ✅ Only trainers can create classes
- ✅ Trainers can only update their own classes

### Class Enrollments
- ✅ Students can view their enrollments
- ✅ Trainers can view enrollments for their classes
- ✅ Students can enroll themselves in classes

### Tasks
- ✅ Students can view tasks for classes they're enrolled in
- ✅ Trainers can view tasks for their classes
- ✅ Trainers can create/update/delete tasks for their classes

### Feedback
- ✅ Students can create feedback
- ✅ Students can view their own feedback
- ✅ Trainers can view feedback for their classes
- ✅ Trainers can update feedback (mark as read, respond)

### Questions
- ✅ Anyone can view active questions
- ✅ Trainers can create questions
- ✅ Question creators can update their questions

### Test Cases
- ✅ Anyone can view sample test cases
- ✅ Question creators can view all test cases for their questions
- ✅ Question creators can manage test cases

### Submissions
- ✅ Users can view their own submissions
- ✅ Users can create submissions

### User Question Progress
- ✅ Users can view and update their own progress

---

## Relationships Diagram

```
users (trainer/student)
  ├── classes (trainer_id) ──┐
  │   ├── class_enrollments (student_id)
  │   ├── tasks
  │   └── feedback
  ├── questions (created_by)
  │   └── test_cases
  ├── submissions
  └── user_question_progress
```

---

## Key Features

### 1. **Trainer Analytics Support**
- Classes with student counts
- Task management with status tracking
- Feedback system with read/unread status
- Calculated metrics (total students, pending tasks, unread feedback)

### 2. **Question Management**
- Flexible test case structure using JSONB
- Support for multiple programming languages
- Automatic statistics calculation
- Hidden and sample test cases

### 3. **Leaderboard System**
- Automatic rank calculation
- Problems solved tracking
- Skill level progression

### 4. **Performance Optimizations**
- Strategic indexes on frequently queried columns
- GIN index for tag searching
- Materialized views for complex queries

### 5. **Security**
- Row Level Security on all tables
- Role-based access control
- User isolation for sensitive data

---

## Setup Instructions

### 1. **Copy SQL to Supabase**
1. Open your Supabase project
2. Navigate to SQL Editor
3. Copy the entire contents of `supabase_schema.sql`
4. Execute the script

### 2. **Verify Installation**
Run these queries to verify:
```sql
-- Check tables created
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- Check RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';

-- Check views created
SELECT table_name FROM information_schema.views 
WHERE table_schema = 'public';
```

### 3. **Populate Database with Seed Data**
After creating the schema, populate the database with sample data using `seed_data.sql`:
1. Open your Supabase project
2. Navigate to SQL Editor
3. Copy the entire contents of `seed_data.sql`
4. Execute the script

**Seed Data Includes:**
- 5 Trainers
- 20 Students
- 15 Classes (3 per trainer)
- 150 Class Enrollments (10 students per class)
- 25 Tasks (5 per trainer)
- 75 Feedback items (5 per class)
- 45 Questions
- 900 Test Cases (20 per question)
- 135 Submissions (3 per question)
- Auto-generated User Question Progress records
- Auto-calculated Leaderboard ranks

**Verification:**
After running the seed script, you'll see a summary output showing the count of records in each table.

---

## Seed Data Details

### Data Generation Strategy
The seed data is generated dynamically using PostgreSQL functions and doesn't require manual content creation:

**Users:**
- Trainers: `trainer1@buildor.com` through `trainer5@buildor.com`
- Students: `student1@buildor.com` through `student20@buildor.com`
- Avatar URLs use DiceBear API for unique avatars
- Students have varying skill levels (Beginner, Intermediate, Advanced, Expert)

**Classes:**
- Named systematically: "Class 1 by Trainer 1", "Class 2 by Trainer 1", etc.
- Class codes: C1T1, C2T1, C3T1, C1T2, etc.
- Each class has 10 enrolled students
- Progress values range from 30-70%

**Tasks:**
- 5 tasks per trainer distributed across their classes
- Mix of types: assignment, quiz, review, lecture
- Various statuses: pending, grading, overdue, completed
- Due dates spread across past and future

**Feedback:**
- 5 feedback items per class (75 total)
- Types rotate: feedback, complaint, question
- Some marked as read, others unread
- Students cycle through to provide feedback

**Questions:**
- 45 questions with varying difficulty (Easy, Medium, Hard)
- Each has descriptive title, description, constraints
- Tags and complexity analysis included
- Optimal solution code provided

**Test Cases:**
- 20 test cases per question (900 total)
- First 3 are sample cases (visible to users)
- Remaining 17 are hidden validation cases
- Categorized by difficulty: basic, edge, performance
- Uses JSONB for flexible input/output structure

**Submissions:**
- 3 submissions per question (135 total)
- Students cycle through questions
- Mix of statuses: accepted, wrong_answer, time_limit_exceeded
- Includes runtime and memory metrics
- Tracks hints used

**User Question Progress:**
- Auto-generated from submissions
- Tracks solved vs attempted status
- Records best performance metrics
- Updates user's problems_solved count

---

## Migration Notes

### From Mock Data to Database

**Users:**
- Mock data in `mockStudents` maps directly to `users` table
- Add `role = 'student'` for all mock students
- Trainers need to be created separately

**Classes:**
- Mock data in `mockClasses` maps to `classes` table
- Need to create `class_enrollments` records for student associations
- `studentCount` is now calculated from enrollments

**Tasks:**
- Mock data in `mockTasks` maps to `tasks` table
- Each task must be associated with a `class_id`

**Feedback:**
- Mock data in `mockFeedback` maps to `feedback` table
- `is_read` replaces the read/unread logic

**Questions:**
- Mock data in `mockQuestions` maps to `questions` table
- Test cases need to be created separately in `test_cases` table
- Submissions tracked in `submissions` table

---

## Future Enhancements

Potential additions to consider:
1. **Notifications table** - For real-time alerts
2. **Discussion forums** - For class discussions
3. **Badges/Achievements** - Gamification elements
4. **Code review system** - Peer review functionality
5. **Analytics events** - Detailed user activity tracking
6. **File attachments** - For assignments and submissions

---

## Maintenance

### Regular Tasks:
1. **Update leaderboard ranks:** `SELECT update_leaderboard_ranks();`
2. **Monitor table sizes:** Check for growth in `submissions` table
3. **Archive old data:** Consider archiving old submissions periodically
4. **Backup:** Regular database backups via Supabase

### Performance Monitoring:
- Monitor slow queries using Supabase dashboard
- Check index usage with `pg_stat_user_indexes`
- Analyze query plans for complex queries

---

## Support & Contact

For issues or questions about the database schema:
- Review this documentation
- Check Supabase logs for errors
- Verify RLS policies are correctly configured
- Ensure foreign key relationships are maintained

---

**Last Updated:** March 13, 2026  
**Schema Version:** 1.0.0  
**Database:** PostgreSQL (Supabase)
