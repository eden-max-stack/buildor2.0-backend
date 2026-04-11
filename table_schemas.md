# class_enrollments

create table public.class_enrollments (
class_id uuid not null,
user_id uuid not null,
enrolled_at timestamp with time zone null default now(),
constraint class_enrollments_pkey primary key (class_id, user_id),
constraint class_enrollments_class_id_fkey foreign KEY (class_id) references classes (class_id) on delete CASCADE,
constraint class_enrollments_user_id_fkey foreign KEY (user_id) references users (user_id) on delete CASCADE
) TABLESPACE pg_default;

# class_phases

create table public.class_phases (
phase_id uuid not null default gen_random_uuid (),
class_id uuid not null,
title character varying(255) not null,
description text null,
order_index integer not null,
constraint class_phases_pkey primary key (phase_id),
constraint class_phases_class_id_fkey foreign KEY (class_id) references classes (class_id) on delete CASCADE
) TABLESPACE pg_default;

# classes

create table public.classes (
class_id uuid not null default gen_random_uuid (),
org_id uuid not null,
trainer_id uuid not null,
title character varying(255) not null,
description text null,
created_at timestamp with time zone null default now(),
constraint classes_pkey primary key (class_id),
constraint classes_org_id_fkey foreign KEY (org_id) references organizations (org_id) on delete CASCADE,
constraint classes_trainer_id_fkey foreign KEY (trainer_id) references trainer_profiles (user_id)
) TABLESPACE pg_default;

# goal_items

create table public.goal_items (
goal_id uuid not null,
material_id uuid not null,
is_completed boolean null default false,
constraint goal_items_pkey primary key (goal_id, material_id),
constraint goal_items_goal_id_fkey foreign KEY (goal_id) references learning_plan_goals (goal_id) on delete CASCADE,
constraint goal_items_material_id_fkey foreign KEY (material_id) references materials (material_id) on delete CASCADE
) TABLESPACE pg_default;

# learning_plan_goals

create table public.learning_plan_goals (
goal_id uuid not null default gen_random_uuid (),
user_id uuid not null,
class_id uuid not null,
title character varying(255) not null,
target_date date null,
constraint learning_plan_goals_pkey primary key (goal_id),
constraint learning_plan_goals_class_id_fkey foreign KEY (class_id) references classes (class_id) on delete CASCADE,
constraint learning_plan_goals_user_id_fkey foreign KEY (user_id) references users (user_id) on delete CASCADE
) TABLESPACE pg_default;

# materials

create table public.materials (
material_id uuid not null default gen_random_uuid (),
type public.material_type not null,
title character varying(255) not null,
content_url text null,
question_id uuid null,
transcript_url text null,
order_index integer not null,
phase_id uuid not null,
constraint materials_pkey primary key (material_id),
constraint materials_phase_id_fkey foreign KEY (phase_id) references class_phases (phase_id) on delete CASCADE,
constraint materials_question_id_fkey foreign KEY (question_id) references questions (question_id) on delete set null
) TABLESPACE pg_default;

# mcq_options

create table public.mcq_options (
option_id uuid not null default gen_random_uuid (),
question_id uuid not null,
option_text text not null,
is_correct boolean null default false,
constraint mcq_options_pkey primary key (option_id),
constraint mcq_options_question_id_fkey foreign KEY (question_id) references questions (question_id) on delete CASCADE
) TABLESPACE pg_default;

# organizations

create table public.organizations (
org_id uuid not null default gen_random_uuid (),
name character varying(255) not null,
constraint organizations_pkey primary key (org_id)
) TABLESPACE pg_default;

# questions

create table public.questions (
question_id uuid not null default gen_random_uuid (),
trainer_id uuid not null,
type public.question_type not null,
title character varying(255) not null,
description text not null,
difficulty character varying(50) null,
tags text[] null default '{}'::text[],
optimal_solution text null,
constraints text null,
total_submissions integer null default 0,
successful_submissions integer null default 0,
created_at timestamp with time zone null default now(),
constraint questions_pkey primary key (question_id),
constraint questions_trainer_id_fkey foreign KEY (trainer_id) references trainer_profiles (user_id),
constraint questions_difficulty_check check (
(
(difficulty)::text = any (
(
array[
'Easy'::character varying,
'Medium'::character varying,
'Hard'::character varying
]
)::text[]
)
)
)
) TABLESPACE pg_default;

# quiz_questions

create table public.quiz_questions (
quiz_id uuid not null,
question_id uuid not null,
points integer null default 10,
constraint quiz_questions_pkey primary key (quiz_id, question_id),
constraint quiz_questions_question_id_fkey foreign KEY (question_id) references questions (question_id) on delete CASCADE,
constraint quiz_questions_quiz_id_fkey foreign KEY (quiz_id) references quizzes (quiz_id) on delete CASCADE
) TABLESPACE pg_default;

# quizzes

create table public.quizzes (
quiz_id uuid not null default gen_random_uuid (),
class_id uuid not null,
title character varying(255) not null,
constraint quizzes_pkey primary key (quiz_id),
constraint quizzes_class_id_fkey foreign KEY (class_id) references classes (class_id) on delete CASCADE
) TABLESPACE pg_default;

# roles

create table public.roles (
role_id uuid not null default gen_random_uuid (),
name public.role_name not null,
constraint roles_pkey primary key (role_id),
constraint roles_name_key unique (name)
) TABLESPACE pg_default;

# student_profiles

create table public.student_profiles (
user_id uuid not null,
university character varying(255) null,
degree character varying(255) null,
expected_grad_year integer null,
gpa numeric(3, 2) null,
portfolio_md text null,
github_url character varying(255) null,
bio character varying(255) null,
location character varying(255) null,
skills character varying(255) [] null,
constraint student_profiles_pkey primary key (user_id),
constraint student_profiles_user_id_fkey foreign KEY (user_id) references users (user_id) on delete CASCADE
) TABLESPACE pg_default;

# submission_feedback

create table public.submission_feedback (
feedback_id uuid not null default gen_random_uuid (),
submission_id uuid not null,
trainer_id uuid not null,
content text not null,
created_at timestamp with time zone null default now(),
constraint submission_feedback_pkey primary key (feedback_id),
constraint submission_feedback_submission_id_fkey foreign KEY (submission_id) references submissions (submission_id) on delete CASCADE,
constraint submission_feedback_trainer_id_fkey foreign KEY (trainer_id) references trainer_profiles (user_id)
) TABLESPACE pg_default;

# submission

create table public.submissions (
submission_id uuid not null default gen_random_uuid (),
user_id uuid not null,
question_id uuid not null,
status public.submission_status not null,
submitted_code text null,
runtime_ms integer null,
memory_kb integer null,
submitted_at timestamp with time zone null default now(),
constraint submissions_pkey primary key (submission_id),
constraint submissions_question_id_fkey foreign KEY (question_id) references questions (question_id) on delete CASCADE,
constraint submissions_user_id_fkey foreign KEY (user_id) references users (user_id) on delete CASCADE
) TABLESPACE pg_default;

# tasks

create table public.tasks (
task_id uuid not null default gen_random_uuid (),
class_id uuid not null,
assigned_to_user_id uuid not null,
task_type public.task_type not null,
reference_id uuid null,
due_date timestamp with time zone null,
status character varying(50) null default 'PENDING'::character varying,
constraint tasks_pkey primary key (task_id),
constraint tasks_assigned_to_user_id_fkey foreign KEY (assigned_to_user_id) references users (user_id) on delete CASCADE,
constraint tasks_class_id_fkey foreign KEY (class_id) references classes (class_id) on delete CASCADE
) TABLESPACE pg_default;

# test_cases

create table public.test_cases (
tc_id uuid not null default gen_random_uuid (),
question_id uuid not null,
input jsonb not null,
expected_output jsonb not null,
is_sample boolean null default false,
constraint test_cases_pkey primary key (tc_id),
constraint test_cases_question_id_fkey foreign KEY (question_id) references questions (question_id) on delete CASCADE
) TABLESPACE pg_default;

# trainer_attestations

create table public.trainer_attestations (
attestation_id uuid not null default gen_random_uuid (),
trainer_id uuid not null,
title character varying(255) not null,
description text null,
attachment_url text null,
constraint trainer_attestations_pkey primary key (attestation_id),
constraint trainer_attestations_trainer_id_fkey foreign KEY (trainer_id) references trainer_profiles (user_id) on delete CASCADE
) TABLESPACE pg_default;

# trainer_profiles

create table public.trainer_profiles (
user_id uuid not null,
title character varying(255) not null,
workplace character varying(255) null,
constraint trainer_profiles_pkey primary key (user_id),
constraint trainer_profiles_user_id_fkey foreign KEY (user_id) references users (user_id) on delete CASCADE
) TABLESPACE pg_default;

# trainer_reviews

create table public.trainer_reviews (
review_id uuid not null default gen_random_uuid (),
trainer_id uuid not null,
class_id uuid not null,
content text not null,
moderation_status public.moderation_status null default 'PENDING'::moderation_status,
created_at timestamp with time zone null default now(),
constraint trainer_reviews_pkey primary key (review_id),
constraint trainer_reviews_class_id_fkey foreign KEY (class_id) references classes (class_id) on delete CASCADE,
constraint trainer_reviews_trainer_id_fkey foreign KEY (trainer_id) references trainer_profiles (user_id) on delete CASCADE
) TABLESPACE pg_default;

# users

create table public.users (
user_id uuid not null default gen_random_uuid (),
org_id uuid not null,
role_id uuid not null,
full_name character varying(255) not null,
email character varying(255) not null,
is_active boolean null default true,
created_at timestamp with time zone null default now(),
email_id character varying(255) null,
avatar_url character varying(255) null,
constraint users_pkey primary key (user_id),
constraint users_email_key unique (email),
constraint users_org_id_fkey foreign KEY (org_id) references organizations (org_id) on delete CASCADE,
constraint users_role_id_fkey foreign KEY (role_id) references roles (role_id)
) TABLESPACE pg_default;
