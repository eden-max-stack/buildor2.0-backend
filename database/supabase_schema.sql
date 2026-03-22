-- ==============================================================================
-- INITIAL SETUP: Custom Types (Enums)
-- ==============================================================================

CREATE TYPE role_name AS ENUM ('STUDENT', 'TRAINER', 'ADMIN');
CREATE TYPE material_type AS ENUM ('VIDEO', 'ARTICLE', 'QUESTION');
CREATE TYPE question_type AS ENUM ('MCQ', 'DSA');
CREATE TYPE submission_status AS ENUM ('ACCEPTED', 'WRONG_ANSWER', 'RUNTIME_ERROR', 'TIME_LIMIT_EXCEEDED');
CREATE TYPE task_type AS ENUM ('QUIZ', 'CUSTOM');
CREATE TYPE moderation_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED');

-- ==============================================================================
-- 1. IDENTITY & ACCESS (RBAC)
-- ==============================================================================

CREATE TABLE organizations (
    org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL
);

CREATE TABLE roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name role_name NOT NULL UNIQUE
);

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(role_id),
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE student_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    university VARCHAR(255),
    degree VARCHAR(255),
    expected_grad_year INTEGER,
    gpa NUMERIC(3, 2),
    portfolio_md TEXT,
    github_url VARCHAR(255)
);

CREATE TABLE trainer_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL, -- e.g., "Senior Algorithmic Instructor"
    workplace VARCHAR(255)
);

CREATE TABLE trainer_attestations (
    attestation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainer_profiles(user_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    attachment_url TEXT
);

-- ==============================================================================
-- 2. CORE LEARNING & ASSESSMENT ENGINE (Mixed due to dependencies)
-- ==============================================================================

CREATE TABLE classes (
    class_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES trainer_profiles(user_id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE class_enrollments (
    class_id UUID NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (class_id, user_id)
);

CREATE TABLE questions (
    question_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainer_profiles(user_id),
    type question_type NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    difficulty VARCHAR(50) CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    tags TEXT[] DEFAULT '{}',
    optimal_solution TEXT,
    constraints TEXT,
    total_submissions INTEGER DEFAULT 0,
    successful_submissions INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE materials (
    material_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    type material_type NOT NULL,
    title VARCHAR(255) NOT NULL,
    content_url TEXT, -- Nullable, used for VIDEO or ARTICLE
    question_id UUID REFERENCES questions(question_id) ON DELETE SET NULL, -- Used if type is QUESTION
    transcript_url TEXT,
    order_index INTEGER NOT NULL
);

CREATE TABLE test_cases (
    tc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
    input JSONB NOT NULL,
    expected_output JSONB NOT NULL,
    is_sample BOOLEAN DEFAULT FALSE
);

CREATE TABLE mcq_options (
    option_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
    option_text TEXT NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE
);

CREATE TABLE quizzes (
    quiz_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    due_date TIMESTAMP WITH TIME ZONE
);

CREATE TABLE quiz_questions (
    quiz_id UUID NOT NULL REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
    points INTEGER DEFAULT 10,
    PRIMARY KEY (quiz_id, question_id)
);

-- ==============================================================================
-- 4. SUBMISSIONS & TRACKING
-- ==============================================================================

CREATE TABLE submissions (
    submission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
    status submission_status NOT NULL,
    submitted_code TEXT, -- Can hold code payload OR option_id string for MCQs
    runtime_ms INTEGER,
    memory_kb INTEGER,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    assigned_to_user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    task_type task_type NOT NULL,
    reference_id UUID, -- Nullable, can point to a quiz_id or material_id
    due_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'PENDING'
);

CREATE TABLE learning_plan_goals (
    goal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    class_id UUID NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    target_date DATE
);

CREATE TABLE goal_items (
    goal_id UUID NOT NULL REFERENCES learning_plan_goals(goal_id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(material_id) ON DELETE CASCADE,
    is_completed BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (goal_id, material_id)
);

-- ==============================================================================
-- 5. SOCIAL & FEEDBACK
-- ==============================================================================

CREATE TABLE submission_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(submission_id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES trainer_profiles(user_id),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE trainer_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainer_profiles(user_id) ON DELETE CASCADE,
    class_id UUID NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    moderation_status moderation_status DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    -- NOTE: user_id is intentionally omitted to enforce anonymity at the database level
);