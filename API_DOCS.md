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
