# Schema + API Decisions

## Workflow of system in detail

NOTE: the words class/course are used synonymously

-- Users exist within educational organizations
-- each organization has an org admin
-- Users are either trainers, students, or org_admins (3 roles in total) within organizations
-- within each organization, there are multiple classes that users can enroll themselves in through invitations
-- trainers can create as many courses as they want tos
-- each class/course has a single trainer, who is the creator of the class/course
-- each class has multiple materials within it, each uploaded by the course creator while creating the course.
-- each material belongs to a single class only
-- materials can be of 3 types: questions (MCQ/DSA), article, video
-- if the material is a video: a transcript can be attached.
-- if the material is a question: the right answer must be added (as questions are only MCQ/DSA type)
-- materials cannot be added after course creation
-- each course has test questions assigned by the trainer as well.
-- test questions within a course are either MCQ questions or DSA questions within a "quiz" (a "quiz" is a set of test questions)
-- a trainer can assign tasks to multiple/individual student(s) enrolled in their class
-- users can set a "learning plan" for each course by setting goals with deadlines.
-- a "goal" within a "learning plan" is a set of materials/quizzes to finish within a set deadline
-- a trainer can give feedback to stuents enrolled in their class
-- a student can visit trainer profiles and view their attestations, skills, other classes they have created, and anonymous feedback posted
-- students can post anonymous feedback on trainer's pages - but it needs to be validated against some rules including no abusive language/derogatory terms
-- each DSA question has a hint generation system attached to it
-- each question is posted by a trainer and the solution is submitted by a student
-- a solution can be submitted multiple times by a student and each submission for a question by a user is recorded in the db
-- students can see their grades against each quiz
-- a student's profile contains their portfolio.md file, their academic info (university, degree, gpa, expected grad), their username, full name, location, links, github
-- upon completion of a course, it appears in your profile under "completed courses"

## Schema required for system

1. Identity & Access (RBAC)

   organizations: org_id (PK), name

   roles: role_id (PK), name (STUDENT, TRAINER, ADMIN)

   users: user_id (PK), org_id (FK), role_id (FK), full_name, email, is_active

   student_profiles: user_id (PK/FK), university, degree, expected_grad_year, gpa, portfolio_md, github_url

   trainer_profiles: user_id (PK/FK), title/delegation, workplace

   trainer_attestations: attestation_id (PK), trainer_id (FK), title, description, attachment_url

2. Core Learning (Courses & Materials)

   classes: class_id (PK), org_id (FK), trainer_id (FK), title, description, created_at

   class_enrollments: class_id (FK), user_id (FK), enrolled_at. (PK is class_id + user_id)

   materials: material_id (PK), class_id (FK), type (VIDEO, ARTICLE, QUESTION), title, content_url (nullable), question_id (nullable FK), transcript_url (nullable), order_index. (Your app logic will enforce the "cannot add after creation" rule).

3. Assessment Engine (Questions & Quizzes)

   questions: question_id (PK), trainer_id (FK), type (MCQ, DSA), title, description, difficulty, tags (array), optimal_solution, constraints, total_submissions, successful_submissions

   test_cases: tc_id (PK), question_id (FK), input, expected_output, is_sample (boolean)

   mcq_options: option_id (PK), question_id (FK), option_text, is_correct (boolean)

   quizzes: quiz_id (PK), class_id (FK), title, due_date

   quiz_questions: quiz_id (FK), question_id (FK), points. (Mapping table)

4. Submissions & Tracking

   submissions: submission_id (PK), user_id (FK), question_id (FK), status (ACCEPTED, WRONG_ANSWER, etc.), submitted_code (or selected_option_id for MCQ), runtime_ms, memory_kb, submitted_at

   tasks: task_id (PK), class_id (FK), assigned_to_user_id (FK), task_type (QUIZ, CUSTOM), reference_id (nullable FK to quiz_id), due_date, status

   learning_plan_goals: goal_id (PK), user_id (FK), class_id (FK), title, target_date

   goal_items: goal_id (FK), material_id (FK), is_completed (boolean)

5. Social & Feedback

   submission_feedback: feedback_id (PK), submission_id (FK), trainer_id (FK), content, created_at (Trainer -> Student)

   trainer_reviews: review_id (PK), trainer_id (FK), class_id (FK), content, moderation_status (PENDING, APPROVED, REJECTED), created_at. (Student -> Trainer. Note: user_id is intentionally omitted to enforce anonymity at the database level).
