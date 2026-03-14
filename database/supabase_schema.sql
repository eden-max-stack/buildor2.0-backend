-- ============================================
-- BUILDOR DATABASE SCHEMA FOR SUPABASE
-- ============================================
-- This script creates all tables, relationships, and indexes
-- for the Buildor learning platform
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. USERS TABLE
-- ============================================
-- Extends Supabase auth.users with additional profile information
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'trainer')),
    
    -- Student-specific fields (from mockStudents)
    university TEXT,
    department TEXT,
    skill_level TEXT CHECK (skill_level IN ('Beginner', 'Intermediate', 'Advanced', 'Expert')),
    problems_solved INTEGER DEFAULT 0,
    rank INTEGER,
    
    -- Metadata
    avatar_url TEXT,
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 2. CLASSES TABLE
-- ============================================
-- Stores information about classes/courses taught by trainers
CREATE TABLE public.classes (
    id TEXT PRIMARY KEY, -- e.g., "cs201"
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL, -- e.g., "CS201"
    description TEXT,
    trainer_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Schedule information
    next_session TEXT, -- e.g., "Mon, 10:00 AM"
    schedule_details JSONB, -- For more complex scheduling
    
    -- Progress tracking
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_trainer FOREIGN KEY (trainer_id) REFERENCES public.users(id)
);

-- ============================================
-- 3. CLASS ENROLLMENTS TABLE
-- ============================================
-- Many-to-many relationship between students and classes
CREATE TABLE public.class_enrollments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    class_id TEXT NOT NULL REFERENCES public.classes(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Enrollment details
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'dropped')),
    
    -- Student progress in this class
    individual_progress INTEGER DEFAULT 0 CHECK (individual_progress >= 0 AND individual_progress <= 100),
    
    UNIQUE(class_id, student_id)
);

-- ============================================
-- 4. TASKS TABLE
-- ============================================
-- Assignments, quizzes, and other tasks for classes
CREATE TABLE public.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    class_id TEXT NOT NULL REFERENCES public.classes(id) ON DELETE CASCADE,
    
    -- Task details
    type TEXT NOT NULL CHECK (type IN ('assignment', 'quiz', 'review', 'lecture')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'grading', 'overdue', 'completed')),
    
    -- Dates
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Additional metadata
    total_submissions INTEGER DEFAULT 0,
    graded_submissions INTEGER DEFAULT 0
);

-- ============================================
-- 5. FEEDBACK TABLE
-- ============================================
-- Student feedback and complaints
CREATE TABLE public.feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    class_id TEXT NOT NULL REFERENCES public.classes(id) ON DELETE CASCADE,
    
    -- Feedback details
    type TEXT NOT NULL CHECK (type IN ('feedback', 'complaint', 'question')),
    message TEXT NOT NULL,
    
    -- Status tracking
    is_read BOOLEAN DEFAULT FALSE,
    response TEXT,
    responded_at TIMESTAMP WITH TIME ZONE,
    responded_by UUID REFERENCES public.users(id),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 6. QUESTIONS TABLE
-- ============================================
-- Coding problems/questions in the platform
CREATE TABLE public.questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    
    -- Question metadata
    difficulty TEXT NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    tags TEXT[] NOT NULL, -- Array of tags like ["Arrays", "Hash Table"]
    
    -- Statistics
    acceptance_rate DECIMAL(5,2), -- e.g., 47.30
    total_submissions INTEGER DEFAULT 0,
    successful_submissions INTEGER DEFAULT 0,
    
    -- Question content
    constraints TEXT[], -- Array of constraint strings
    optimal_solution TEXT, -- Python code for the optimal solution
    time_complexity TEXT, -- e.g., "O(n)"
    space_complexity TEXT, -- e.g., "O(1)"
    
    -- Author information
    created_by UUID REFERENCES public.users(id),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================
-- 7. TEST CASES TABLE
-- ============================================
-- Test cases for each question
CREATE TABLE public.test_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    
    -- Test case details
    input JSONB NOT NULL, -- Flexible JSON structure for inputs
    expected_output JSONB NOT NULL, -- Expected output
    
    -- Test case metadata
    is_sample BOOLEAN DEFAULT FALSE, -- Whether this is shown to users as example
    is_hidden BOOLEAN DEFAULT TRUE, -- Hidden test cases for validation
    difficulty TEXT CHECK (difficulty IN ('basic', 'edge', 'performance')),
    
    -- Ordering
    order_index INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 8. SUBMISSIONS TABLE
-- ============================================
-- User submissions for questions
CREATE TABLE public.submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Submission content
    code TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'python' CHECK (language IN ('python', 'javascript', 'java', 'cpp', 'go')),
    
    -- Results
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'accepted', 'wrong_answer', 'time_limit_exceeded', 'runtime_error', 'compilation_error')),
    test_cases_passed INTEGER DEFAULT 0,
    total_test_cases INTEGER DEFAULT 0,
    
    -- Performance metrics
    runtime_ms INTEGER, -- Runtime in milliseconds
    memory_kb INTEGER, -- Memory used in kilobytes
    
    -- Hints and assistance
    hints_used INTEGER DEFAULT 0,
    
    -- Metadata
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_at TIMESTAMP WITH TIME ZONE,
    
    -- Error details if any
    error_message TEXT,
    failed_test_case_id UUID REFERENCES public.test_cases(id)
);

-- ============================================
-- 9. USER QUESTION PROGRESS TABLE
-- ============================================
-- Tracks which questions users have solved/attempted
CREATE TABLE public.user_question_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    
    -- Progress details
    status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'attempted', 'solved')),
    attempts INTEGER DEFAULT 0,
    best_runtime_ms INTEGER,
    best_memory_kb INTEGER,
    hints_used_total INTEGER DEFAULT 0,
    
    -- Timestamps
    first_attempted_at TIMESTAMP WITH TIME ZONE,
    solved_at TIMESTAMP WITH TIME ZONE,
    last_attempted_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(user_id, question_id)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Users indexes
CREATE INDEX idx_users_role ON public.users(role);
CREATE INDEX idx_users_skill_level ON public.users(skill_level);
CREATE INDEX idx_users_rank ON public.users(rank);

-- Classes indexes
CREATE INDEX idx_classes_trainer_id ON public.classes(trainer_id);
CREATE INDEX idx_classes_code ON public.classes(code);

-- Class enrollments indexes
CREATE INDEX idx_enrollments_class_id ON public.class_enrollments(class_id);
CREATE INDEX idx_enrollments_student_id ON public.class_enrollments(student_id);
CREATE INDEX idx_enrollments_status ON public.class_enrollments(status);

-- Tasks indexes
CREATE INDEX idx_tasks_class_id ON public.tasks(class_id);
CREATE INDEX idx_tasks_status ON public.tasks(status);
CREATE INDEX idx_tasks_due_date ON public.tasks(due_date);
CREATE INDEX idx_tasks_type ON public.tasks(type);

-- Feedback indexes
CREATE INDEX idx_feedback_student_id ON public.feedback(student_id);
CREATE INDEX idx_feedback_class_id ON public.feedback(class_id);
CREATE INDEX idx_feedback_is_read ON public.feedback(is_read);
CREATE INDEX idx_feedback_type ON public.feedback(type);

-- Questions indexes
CREATE INDEX idx_questions_difficulty ON public.questions(difficulty);
CREATE INDEX idx_questions_tags ON public.questions USING GIN(tags);
CREATE INDEX idx_questions_created_by ON public.questions(created_by);
CREATE INDEX idx_questions_is_active ON public.questions(is_active);

-- Test cases indexes
CREATE INDEX idx_test_cases_question_id ON public.test_cases(question_id);
CREATE INDEX idx_test_cases_is_sample ON public.test_cases(is_sample);

-- Submissions indexes
CREATE INDEX idx_submissions_question_id ON public.submissions(question_id);
CREATE INDEX idx_submissions_user_id ON public.submissions(user_id);
CREATE INDEX idx_submissions_status ON public.submissions(status);
CREATE INDEX idx_submissions_submitted_at ON public.submissions(submitted_at DESC);

-- User question progress indexes
CREATE INDEX idx_user_progress_user_id ON public.user_question_progress(user_id);
CREATE INDEX idx_user_progress_question_id ON public.user_question_progress(question_id);
CREATE INDEX idx_user_progress_status ON public.user_question_progress(status);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.classes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.class_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_question_progress ENABLE ROW LEVEL SECURITY;

-- Users: Users can read all profiles, but only update their own
CREATE POLICY "Users can view all profiles" ON public.users
    FOR SELECT USING (true);

CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

-- Classes: Everyone can view, only trainers can create/update their own classes
CREATE POLICY "Anyone can view classes" ON public.classes
    FOR SELECT USING (true);

CREATE POLICY "Trainers can create classes" ON public.classes
    FOR INSERT WITH CHECK (
        auth.uid() = trainer_id AND
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'trainer')
    );

CREATE POLICY "Trainers can update own classes" ON public.classes
    FOR UPDATE USING (
        auth.uid() = trainer_id AND
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'trainer')
    );

-- Class enrollments: Students can view their enrollments, trainers can view their class enrollments
CREATE POLICY "Users can view relevant enrollments" ON public.class_enrollments
    FOR SELECT USING (
        auth.uid() = student_id OR
        EXISTS (SELECT 1 FROM public.classes WHERE id = class_id AND trainer_id = auth.uid())
    );

CREATE POLICY "Students can enroll in classes" ON public.class_enrollments
    FOR INSERT WITH CHECK (
        auth.uid() = student_id AND
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'student')
    );

-- Tasks: Students in class and trainers can view, trainers can create/update
CREATE POLICY "Users can view relevant tasks" ON public.tasks
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.classes c
            WHERE c.id = class_id AND (
                c.trainer_id = auth.uid() OR
                EXISTS (SELECT 1 FROM public.class_enrollments WHERE class_id = c.id AND student_id = auth.uid())
            )
        )
    );

CREATE POLICY "Trainers can manage tasks" ON public.tasks
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.classes WHERE id = class_id AND trainer_id = auth.uid())
    );

-- Feedback: Students can create, trainers can view feedback for their classes
CREATE POLICY "Students can create feedback" ON public.feedback
    FOR INSERT WITH CHECK (
        auth.uid() = student_id AND
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'student')
    );

CREATE POLICY "Users can view relevant feedback" ON public.feedback
    FOR SELECT USING (
        auth.uid() = student_id OR
        EXISTS (SELECT 1 FROM public.classes WHERE id = class_id AND trainer_id = auth.uid())
    );

CREATE POLICY "Trainers can update feedback" ON public.feedback
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM public.classes WHERE id = class_id AND trainer_id = auth.uid())
    );

-- Questions: Everyone can view active questions, trainers can create
CREATE POLICY "Anyone can view active questions" ON public.questions
    FOR SELECT USING (is_active = true OR created_by = auth.uid());

CREATE POLICY "Trainers can create questions" ON public.questions
    FOR INSERT WITH CHECK (
        auth.uid() = created_by AND
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'trainer')
    );

CREATE POLICY "Creators can update their questions" ON public.questions
    FOR UPDATE USING (auth.uid() = created_by);

-- Test cases: Users can view sample cases, trainers can manage all for their questions
CREATE POLICY "Users can view test cases" ON public.test_cases
    FOR SELECT USING (
        is_sample = true OR
        EXISTS (SELECT 1 FROM public.questions WHERE id = question_id AND created_by = auth.uid())
    );

CREATE POLICY "Question creators can manage test cases" ON public.test_cases
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.questions WHERE id = question_id AND created_by = auth.uid())
    );

-- Submissions: Users can view their own submissions
CREATE POLICY "Users can view own submissions" ON public.submissions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create submissions" ON public.submissions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- User question progress: Users can view and update their own progress
CREATE POLICY "Users can view own progress" ON public.user_question_progress
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own progress" ON public.user_question_progress
    FOR ALL USING (auth.uid() = user_id);

-- ============================================
-- FUNCTIONS AND TRIGGERS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_classes_updated_at BEFORE UPDATE ON public.classes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON public.tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feedback_updated_at BEFORE UPDATE ON public.feedback
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_questions_updated_at BEFORE UPDATE ON public.questions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update acceptance rate when submissions are added
CREATE OR REPLACE FUNCTION update_question_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.questions
    SET 
        total_submissions = (
            SELECT COUNT(*) FROM public.submissions WHERE question_id = NEW.question_id
        ),
        successful_submissions = (
            SELECT COUNT(*) FROM public.submissions WHERE question_id = NEW.question_id AND status = 'accepted'
        ),
        acceptance_rate = (
            SELECT 
                CASE 
                    WHEN COUNT(*) = 0 THEN 0
                    ELSE (COUNT(*) FILTER (WHERE status = 'accepted')::DECIMAL / COUNT(*) * 100)
                END
            FROM public.submissions 
            WHERE question_id = NEW.question_id
        )
    WHERE id = NEW.question_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_question_stats_trigger
AFTER INSERT OR UPDATE ON public.submissions
FOR EACH ROW EXECUTE FUNCTION update_question_stats();

-- Function to update user's problems_solved count
CREATE OR REPLACE FUNCTION update_user_problems_solved()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'solved' AND (OLD IS NULL OR OLD.status != 'solved') THEN
        UPDATE public.users
        SET problems_solved = problems_solved + 1
        WHERE id = NEW.user_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_problems_solved_trigger
AFTER INSERT OR UPDATE ON public.user_question_progress
FOR EACH ROW EXECUTE FUNCTION update_user_problems_solved();

-- Function to calculate leaderboard ranks
CREATE OR REPLACE FUNCTION update_leaderboard_ranks()
RETURNS void AS $$
BEGIN
    WITH ranked_users AS (
        SELECT 
            id,
            ROW_NUMBER() OVER (ORDER BY problems_solved DESC, created_at ASC) as new_rank
        FROM public.users
        WHERE role = 'student'
    )
    UPDATE public.users u
    SET rank = r.new_rank
    FROM ranked_users r
    WHERE u.id = r.id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- View for trainer analytics overview
CREATE OR REPLACE VIEW trainer_analytics_overview AS
SELECT 
    u.id as trainer_id,
    u.full_name as trainer_name,
    COUNT(DISTINCT c.id) as total_classes,
    COUNT(DISTINCT ce.student_id) as total_students,
    COUNT(DISTINCT CASE WHEN t.status IN ('pending', 'grading', 'overdue') THEN t.id END) as pending_tasks,
    COUNT(DISTINCT CASE WHEN f.is_read = false THEN f.id END) as unread_feedback
FROM public.users u
LEFT JOIN public.classes c ON c.trainer_id = u.id
LEFT JOIN public.class_enrollments ce ON ce.class_id = c.id
LEFT JOIN public.tasks t ON t.class_id = c.id
LEFT JOIN public.feedback f ON f.class_id = c.id
WHERE u.role = 'trainer'
GROUP BY u.id, u.full_name;

-- View for class details with student count
CREATE OR REPLACE VIEW class_details AS
SELECT 
    c.*,
    COUNT(DISTINCT ce.student_id) as student_count,
    u.full_name as trainer_name
FROM public.classes c
LEFT JOIN public.class_enrollments ce ON ce.class_id = c.id AND ce.status = 'active'
LEFT JOIN public.users u ON u.id = c.trainer_id
GROUP BY c.id, u.full_name;

-- View for leaderboard
CREATE OR REPLACE VIEW leaderboard AS
SELECT 
    u.id,
    u.full_name as name,
    u.rank,
    u.problems_solved,
    u.skill_level,
    u.university,
    u.department,
    u.avatar_url
FROM public.users u
WHERE u.role = 'student' AND u.rank IS NOT NULL
ORDER BY u.rank ASC;

-- ============================================
-- SAMPLE DATA INSERTION (OPTIONAL)
-- ============================================
-- Uncomment the following section if you want to insert sample data

/*
-- Insert sample trainer
INSERT INTO public.users (id, email, full_name, role, created_at)
VALUES 
    ('00000000-0000-0000-0000-000000000001', 'trainer@example.com', 'Dr. John Smith', 'trainer', NOW());

-- Insert sample students
INSERT INTO public.users (id, email, full_name, role, university, department, skill_level, problems_solved, created_at)
VALUES 
    ('00000000-0000-0000-0000-000000000002', 'alice@example.com', 'Alice Johnson', 'student', 'MIT', 'Computer Science', 'Expert', 250, NOW()),
    ('00000000-0000-0000-0000-000000000003', 'bob@example.com', 'Bob Williams', 'student', 'Stanford', 'Computer Science', 'Advanced', 180, NOW());

-- Update ranks
SELECT update_leaderboard_ranks();
*/

-- ============================================
-- END OF SCHEMA
-- ============================================
