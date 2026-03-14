-- ============================================
-- PROFILE EXTENSIONS FOR BUILDOR DATABASE
-- ============================================
-- This script adds profile-specific tables for enhanced user profiles
-- Run this AFTER supabase_schema.sql
-- ============================================

-- ============================================
-- 1. USER PROFILES EXTENDED TABLE
-- ============================================
-- Extended profile information for users (complements public.users)
CREATE TABLE public.user_profiles (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Profile card information
    username TEXT UNIQUE NOT NULL,
    profile_description TEXT, -- Bio/description shown on profile
    location TEXT,
    website TEXT,
    github_username TEXT,
    graduation_year INTEGER,
    
    -- Portfolio README (markdown content)
    portfolio_readme TEXT, -- Markdown content for portfolio section
    readme_updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Profile customization
    avatar_url TEXT,
    banner_url TEXT,
    theme_preference TEXT DEFAULT 'system' CHECK (theme_preference IN ('light', 'dark', 'system')),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 2. ACADEMIC INFO TABLE
-- ============================================
-- Detailed academic information for students
CREATE TABLE public.academic_info (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Academic details
    university TEXT NOT NULL,
    degree TEXT NOT NULL, -- e.g., "B.S. Computer Science"
    major TEXT,
    minor TEXT,
    gpa DECIMAL(3,2), -- e.g., 3.85
    expected_graduation TEXT, -- e.g., "May 2025"
    
    -- Additional info
    honors TEXT[], -- Array of honors/awards
    relevant_coursework TEXT[], -- Array of course names
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- ============================================
-- 3. EXTERNAL LINKS TABLE
-- ============================================
-- Social media and external platform links
CREATE TABLE public.external_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Link details
    platform TEXT NOT NULL, -- e.g., "GitHub", "LinkedIn", "LeetCode", "Portfolio"
    url TEXT NOT NULL,
    display_name TEXT, -- Optional custom display name
    
    -- Ordering
    order_index INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 4. CONTRIBUTION ACTIVITY TABLE
-- ============================================
-- Daily contribution tracking (like GitHub contribution graph)
CREATE TABLE public.contribution_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Activity details
    activity_date DATE NOT NULL,
    contribution_count INTEGER DEFAULT 0, -- Number of contributions that day
    
    -- Activity breakdown (optional)
    submissions_count INTEGER DEFAULT 0,
    questions_solved_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, activity_date)
);

-- ============================================
-- 5. PROFESSOR FEEDBACK (PROFILE) TABLE
-- ============================================
-- Feedback from professors/trainers shown on student profiles
-- This is DIFFERENT from the general feedback table (which is for class-specific feedback/complaints)
CREATE TABLE public.professor_feedback_profile (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    professor_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Feedback details
    course_name TEXT NOT NULL, -- e.g., "Data Structures & Algorithms"
    course_code TEXT, -- e.g., "CS201"
    feedback_text TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5), -- Optional 1-5 rating
    
    -- Visibility control
    is_visible BOOLEAN DEFAULT TRUE, -- Student can hide feedback
    is_pinned BOOLEAN DEFAULT FALSE, -- Student can pin important feedback
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 6. SUBMISSION RANKINGS TABLE
-- ============================================
-- Stores ranking/percentile information for submissions
-- This helps display "Top 5%" badges on solved questions
CREATE TABLE public.submission_rankings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Ranking metrics
    runtime_percentile DECIMAL(5,2), -- e.g., 95.50 means top 5%
    memory_percentile DECIMAL(5,2),
    overall_rank INTEGER, -- Absolute rank among all submissions for this question
    total_submissions_at_time INTEGER, -- Total submissions when this was ranked
    
    -- Metadata
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(submission_id)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- User profiles indexes
CREATE INDEX idx_user_profiles_username ON public.user_profiles(username);
CREATE INDEX idx_user_profiles_user_id ON public.user_profiles(user_id);

-- Academic info indexes
CREATE INDEX idx_academic_info_user_id ON public.academic_info(user_id);

-- External links indexes
CREATE INDEX idx_external_links_user_id ON public.external_links(user_id);
CREATE INDEX idx_external_links_platform ON public.external_links(platform);

-- Contribution activity indexes
CREATE INDEX idx_contribution_activity_user_id ON public.contribution_activity(user_id);
CREATE INDEX idx_contribution_activity_date ON public.contribution_activity(activity_date DESC);
CREATE INDEX idx_contribution_activity_user_date ON public.contribution_activity(user_id, activity_date DESC);

-- Professor feedback profile indexes
CREATE INDEX idx_prof_feedback_profile_student_id ON public.professor_feedback_profile(student_id);
CREATE INDEX idx_prof_feedback_profile_professor_id ON public.professor_feedback_profile(professor_id);
CREATE INDEX idx_prof_feedback_profile_visible ON public.professor_feedback_profile(is_visible);

-- Submission rankings indexes
CREATE INDEX idx_submission_rankings_submission_id ON public.submission_rankings(submission_id);
CREATE INDEX idx_submission_rankings_question_id ON public.submission_rankings(question_id);
CREATE INDEX idx_submission_rankings_user_id ON public.submission_rankings(user_id);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on all new tables
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.academic_info ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.external_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contribution_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.professor_feedback_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submission_rankings ENABLE ROW LEVEL SECURITY;

-- User profiles policies
CREATE POLICY "Users can view all profiles" ON public.user_profiles
    FOR SELECT USING (true);

CREATE POLICY "Users can update own profile" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile" ON public.user_profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Academic info policies
CREATE POLICY "Users can view all academic info" ON public.academic_info
    FOR SELECT USING (true);

CREATE POLICY "Users can manage own academic info" ON public.academic_info
    FOR ALL USING (auth.uid() = user_id);

-- External links policies
CREATE POLICY "Users can view all external links" ON public.external_links
    FOR SELECT USING (true);

CREATE POLICY "Users can manage own external links" ON public.external_links
    FOR ALL USING (auth.uid() = user_id);

-- Contribution activity policies
CREATE POLICY "Users can view all contribution activity" ON public.contribution_activity
    FOR SELECT USING (true);

CREATE POLICY "System can manage contribution activity" ON public.contribution_activity
    FOR ALL USING (true); -- Managed by backend

-- Professor feedback profile policies
CREATE POLICY "Users can view visible feedback" ON public.professor_feedback_profile
    FOR SELECT USING (is_visible = true);

CREATE POLICY "Students can manage visibility of their feedback" ON public.professor_feedback_profile
    FOR UPDATE USING (auth.uid() = student_id);

CREATE POLICY "Professors can create feedback" ON public.professor_feedback_profile
    FOR INSERT WITH CHECK (auth.uid() = professor_id);

-- Submission rankings policies
CREATE POLICY "Users can view all submission rankings" ON public.submission_rankings
    FOR SELECT USING (true);

CREATE POLICY "System can manage submission rankings" ON public.submission_rankings
    FOR ALL USING (true); -- Managed by backend

-- ============================================
-- AUTOMATED FUNCTIONS AND TRIGGERS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_academic_info_updated_at
    BEFORE UPDATE ON public.academic_info
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_external_links_updated_at
    BEFORE UPDATE ON public.external_links
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prof_feedback_profile_updated_at
    BEFORE UPDATE ON public.professor_feedback_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- HELPER VIEWS
-- ============================================

-- Complete user profile view (joins users + user_profiles)
CREATE OR REPLACE VIEW public.complete_user_profiles AS
SELECT 
    u.id,
    u.email,
    u.full_name,
    u.role,
    u.university,
    u.department,
    u.skill_level,
    u.problems_solved,
    u.rank,
    u.bio,
    u.created_at AS user_created_at,
    up.username,
    up.profile_description,
    up.location,
    up.website,
    up.github_username,
    up.graduation_year,
    up.portfolio_readme,
    up.readme_updated_at,
    up.avatar_url,
    up.banner_url,
    up.theme_preference,
    up.updated_at AS profile_updated_at
FROM public.users u
LEFT JOIN public.user_profiles up ON u.id = up.user_id;

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON TABLE public.user_profiles IS 'Extended profile information for users including username, bio, and portfolio README';
COMMENT ON TABLE public.academic_info IS 'Detailed academic information for students (university, degree, GPA, etc.)';
COMMENT ON TABLE public.external_links IS 'Social media and external platform links for user profiles';
COMMENT ON TABLE public.contribution_activity IS 'Daily contribution tracking for GitHub-style contribution graph';
COMMENT ON TABLE public.professor_feedback_profile IS 'Feedback from professors shown on student profiles (different from class feedback)';
COMMENT ON TABLE public.submission_rankings IS 'Ranking and percentile information for question submissions';

COMMENT ON COLUMN public.user_profiles.portfolio_readme IS 'Markdown content for the portfolio README section';
COMMENT ON COLUMN public.contribution_activity.contribution_count IS 'Total contributions for the day (submissions + questions solved + comments)';
COMMENT ON COLUMN public.submission_rankings.runtime_percentile IS 'Percentile ranking for runtime (95.50 = top 5%)';
COMMENT ON COLUMN public.professor_feedback_profile.is_visible IS 'Students can hide feedback they do not want displayed';
