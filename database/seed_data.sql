-- ============================================
-- BUILDOR DATABASE SEED DATA
-- ============================================
-- This script populates the database with sample data:
-- - 5 Trainers
-- - 20 Students
-- - 3 Classes per Trainer (15 total)
-- - 10 Students per Class
-- - 5 Feedback comments per Class
-- - 5 Tasks per Trainer (25 total)
-- - 45 Questions
-- - 20 Test Cases per Question
-- - 3 Submissions per Question
-- ============================================

-- ============================================
-- 0. INSERT INTO AUTH.USERS (Required for FK constraint)
-- ============================================
-- Note: In production, users would be created via Supabase Auth signup
-- For seed data, we insert directly into auth.users first

-- Insert trainers into auth.users
INSERT INTO auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at, raw_app_meta_data, raw_user_meta_data, is_super_admin, confirmation_token, email_change, email_change_token_new, recovery_token)
VALUES
    ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'trainer1@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '365 days', NOW() - INTERVAL '365 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'trainer2@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '364 days', NOW() - INTERVAL '364 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('10000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'trainer3@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '363 days', NOW() - INTERVAL '363 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('10000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'trainer4@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '362 days', NOW() - INTERVAL '362 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('10000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'trainer5@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '361 days', NOW() - INTERVAL '361 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', '');

-- Insert students into auth.users
INSERT INTO auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at, raw_app_meta_data, raw_user_meta_data, is_super_admin, confirmation_token, email_change, email_change_token_new, recovery_token)
VALUES
    ('20000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student1@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '180 days', NOW() - INTERVAL '180 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student2@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '179 days', NOW() - INTERVAL '179 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student3@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '178 days', NOW() - INTERVAL '178 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student4@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '177 days', NOW() - INTERVAL '177 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student5@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '176 days', NOW() - INTERVAL '176 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student6@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '175 days', NOW() - INTERVAL '175 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student7@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '174 days', NOW() - INTERVAL '174 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student8@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '173 days', NOW() - INTERVAL '173 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student9@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '172 days', NOW() - INTERVAL '172 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student10@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '171 days', NOW() - INTERVAL '171 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student11@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '170 days', NOW() - INTERVAL '170 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student12@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '169 days', NOW() - INTERVAL '169 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000013', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student13@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '168 days', NOW() - INTERVAL '168 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000014', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student14@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '167 days', NOW() - INTERVAL '167 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000015', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student15@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '166 days', NOW() - INTERVAL '166 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000016', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student16@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '165 days', NOW() - INTERVAL '165 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000017', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student17@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '164 days', NOW() - INTERVAL '164 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000018', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student18@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '163 days', NOW() - INTERVAL '163 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000019', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student19@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '162 days', NOW() - INTERVAL '162 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', ''),
    ('20000000-0000-0000-0000-000000000020', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'student20@buildor.com', crypt('password123', gen_salt('bf')), NOW() - INTERVAL '161 days', NOW() - INTERVAL '161 days', NOW(), '{"provider":"email","providers":["email"]}', '{}', FALSE, '', '', '', '');

-- ============================================
-- 1. INSERT TRAINERS (5 users into public.users)
-- ============================================
INSERT INTO public.users (id, email, full_name, role, avatar_url, bio, created_at, updated_at)
VALUES
    ('10000000-0000-0000-0000-000000000001', 'trainer1@buildor.com', 'Trainer 1', 'trainer', 'https://api.dicebear.com/7.x/avataaars/svg?seed=trainer1', 'Bio for Trainer 1', NOW() - INTERVAL '365 days', NOW()),
    ('10000000-0000-0000-0000-000000000002', 'trainer2@buildor.com', 'Trainer 2', 'trainer', 'https://api.dicebear.com/7.x/avataaars/svg?seed=trainer2', 'Bio for Trainer 2', NOW() - INTERVAL '364 days', NOW()),
    ('10000000-0000-0000-0000-000000000003', 'trainer3@buildor.com', 'Trainer 3', 'trainer', 'https://api.dicebear.com/7.x/avataaars/svg?seed=trainer3', 'Bio for Trainer 3', NOW() - INTERVAL '363 days', NOW()),
    ('10000000-0000-0000-0000-000000000004', 'trainer4@buildor.com', 'Trainer 4', 'trainer', 'https://api.dicebear.com/7.x/avataaars/svg?seed=trainer4', 'Bio for Trainer 4', NOW() - INTERVAL '362 days', NOW()),
    ('10000000-0000-0000-0000-000000000005', 'trainer5@buildor.com', 'Trainer 5', 'trainer', 'https://api.dicebear.com/7.x/avataaars/svg?seed=trainer5', 'Bio for Trainer 5', NOW() - INTERVAL '361 days', NOW());

-- ============================================
-- 2. INSERT STUDENTS (20 users)
-- ============================================
INSERT INTO public.users (id, email, full_name, role, university, department, skill_level, problems_solved, avatar_url, bio, created_at, updated_at)
VALUES
    ('20000000-0000-0000-0000-000000000001', 'student1@buildor.com', 'Student 1', 'student', 'University 1', 'Department 1', 'Beginner', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student1', 'Bio for Student 1', NOW() - INTERVAL '180 days', NOW()),
    ('20000000-0000-0000-0000-000000000002', 'student2@buildor.com', 'Student 2', 'student', 'University 2', 'Department 2', 'Intermediate', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student2', 'Bio for Student 2', NOW() - INTERVAL '179 days', NOW()),
    ('20000000-0000-0000-0000-000000000003', 'student3@buildor.com', 'Student 3', 'student', 'University 3', 'Department 3', 'Advanced', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student3', 'Bio for Student 3', NOW() - INTERVAL '178 days', NOW()),
    ('20000000-0000-0000-0000-000000000004', 'student4@buildor.com', 'Student 4', 'student', 'University 4', 'Department 4', 'Expert', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student4', 'Bio for Student 4', NOW() - INTERVAL '177 days', NOW()),
    ('20000000-0000-0000-0000-000000000005', 'student5@buildor.com', 'Student 5', 'student', 'University 5', 'Department 5', 'Beginner', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student5', 'Bio for Student 5', NOW() - INTERVAL '176 days', NOW()),
    ('20000000-0000-0000-0000-000000000006', 'student6@buildor.com', 'Student 6', 'student', 'University 6', 'Department 6', 'Intermediate', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student6', 'Bio for Student 6', NOW() - INTERVAL '175 days', NOW()),
    ('20000000-0000-0000-0000-000000000007', 'student7@buildor.com', 'Student 7', 'student', 'University 7', 'Department 7', 'Advanced', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student7', 'Bio for Student 7', NOW() - INTERVAL '174 days', NOW()),
    ('20000000-0000-0000-0000-000000000008', 'student8@buildor.com', 'Student 8', 'student', 'University 8', 'Department 8', 'Expert', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student8', 'Bio for Student 8', NOW() - INTERVAL '173 days', NOW()),
    ('20000000-0000-0000-0000-000000000009', 'student9@buildor.com', 'Student 9', 'student', 'University 9', 'Department 9', 'Beginner', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student9', 'Bio for Student 9', NOW() - INTERVAL '172 days', NOW()),
    ('20000000-0000-0000-0000-000000000010', 'student10@buildor.com', 'Student 10', 'student', 'University 10', 'Department 10', 'Intermediate', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student10', 'Bio for Student 10', NOW() - INTERVAL '171 days', NOW()),
    ('20000000-0000-0000-0000-000000000011', 'student11@buildor.com', 'Student 11', 'student', 'University 11', 'Department 11', 'Advanced', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student11', 'Bio for Student 11', NOW() - INTERVAL '170 days', NOW()),
    ('20000000-0000-0000-0000-000000000012', 'student12@buildor.com', 'Student 12', 'student', 'University 12', 'Department 12', 'Expert', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student12', 'Bio for Student 12', NOW() - INTERVAL '169 days', NOW()),
    ('20000000-0000-0000-0000-000000000013', 'student13@buildor.com', 'Student 13', 'student', 'University 13', 'Department 13', 'Beginner', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student13', 'Bio for Student 13', NOW() - INTERVAL '168 days', NOW()),
    ('20000000-0000-0000-0000-000000000014', 'student14@buildor.com', 'Student 14', 'student', 'University 14', 'Department 14', 'Intermediate', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student14', 'Bio for Student 14', NOW() - INTERVAL '167 days', NOW()),
    ('20000000-0000-0000-0000-000000000015', 'student15@buildor.com', 'Student 15', 'student', 'University 15', 'Department 15', 'Advanced', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student15', 'Bio for Student 15', NOW() - INTERVAL '166 days', NOW()),
    ('20000000-0000-0000-0000-000000000016', 'student16@buildor.com', 'Student 16', 'student', 'University 16', 'Department 16', 'Expert', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student16', 'Bio for Student 16', NOW() - INTERVAL '165 days', NOW()),
    ('20000000-0000-0000-0000-000000000017', 'student17@buildor.com', 'Student 17', 'student', 'University 17', 'Department 17', 'Beginner', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student17', 'Bio for Student 17', NOW() - INTERVAL '164 days', NOW()),
    ('20000000-0000-0000-0000-000000000018', 'student18@buildor.com', 'Student 18', 'student', 'University 18', 'Department 18', 'Intermediate', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student18', 'Bio for Student 18', NOW() - INTERVAL '163 days', NOW()),
    ('20000000-0000-0000-0000-000000000019', 'student19@buildor.com', 'Student 19', 'student', 'University 19', 'Department 19', 'Advanced', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student19', 'Bio for Student 19', NOW() - INTERVAL '162 days', NOW()),
    ('20000000-0000-0000-0000-000000000020', 'student20@buildor.com', 'Student 20', 'student', 'University 20', 'Department 20', 'Expert', 0, 'https://api.dicebear.com/7.x/avataaars/svg?seed=student20', 'Bio for Student 20', NOW() - INTERVAL '161 days', NOW());

-- ============================================
-- 3. INSERT CLASSES (3 per Trainer = 15 total)
-- ============================================
INSERT INTO public.classes (id, name, code, description, trainer_id, next_session, progress, created_at, updated_at)
VALUES
    -- Trainer 1 Classes
    ('class-1-1', 'Class 1 by Trainer 1', 'C1T1', 'Description for Class 1 by Trainer 1', '10000000-0000-0000-0000-000000000001', 'Mon, 10:00 AM', 45, NOW() - INTERVAL '90 days', NOW()),
    ('class-1-2', 'Class 2 by Trainer 1', 'C2T1', 'Description for Class 2 by Trainer 1', '10000000-0000-0000-0000-000000000001', 'Tue, 2:00 PM', 60, NOW() - INTERVAL '89 days', NOW()),
    ('class-1-3', 'Class 3 by Trainer 1', 'C3T1', 'Description for Class 3 by Trainer 1', '10000000-0000-0000-0000-000000000001', 'Wed, 9:00 AM', 30, NOW() - INTERVAL '88 days', NOW()),
    -- Trainer 2 Classes
    ('class-2-1', 'Class 1 by Trainer 2', 'C1T2', 'Description for Class 1 by Trainer 2', '10000000-0000-0000-0000-000000000002', 'Thu, 11:00 AM', 55, NOW() - INTERVAL '87 days', NOW()),
    ('class-2-2', 'Class 2 by Trainer 2', 'C2T2', 'Description for Class 2 by Trainer 2', '10000000-0000-0000-0000-000000000002', 'Fri, 3:00 PM', 70, NOW() - INTERVAL '86 days', NOW()),
    ('class-2-3', 'Class 3 by Trainer 2', 'C3T2', 'Description for Class 3 by Trainer 2', '10000000-0000-0000-0000-000000000002', 'Mon, 1:00 PM', 40, NOW() - INTERVAL '85 days', NOW()),
    -- Trainer 3 Classes
    ('class-3-1', 'Class 1 by Trainer 3', 'C1T3', 'Description for Class 1 by Trainer 3', '10000000-0000-0000-0000-000000000003', 'Tue, 10:00 AM', 50, NOW() - INTERVAL '84 days', NOW()),
    ('class-3-2', 'Class 2 by Trainer 3', 'C2T3', 'Description for Class 2 by Trainer 3', '10000000-0000-0000-0000-000000000003', 'Wed, 2:00 PM', 65, NOW() - INTERVAL '83 days', NOW()),
    ('class-3-3', 'Class 3 by Trainer 3', 'C3T3', 'Description for Class 3 by Trainer 3', '10000000-0000-0000-0000-000000000003', 'Thu, 9:00 AM', 35, NOW() - INTERVAL '82 days', NOW()),
    -- Trainer 4 Classes
    ('class-4-1', 'Class 1 by Trainer 4', 'C1T4', 'Description for Class 1 by Trainer 4', '10000000-0000-0000-0000-000000000004', 'Fri, 11:00 AM', 48, NOW() - INTERVAL '81 days', NOW()),
    ('class-4-2', 'Class 2 by Trainer 4', 'C2T4', 'Description for Class 2 by Trainer 4', '10000000-0000-0000-0000-000000000004', 'Mon, 3:00 PM', 62, NOW() - INTERVAL '80 days', NOW()),
    ('class-4-3', 'Class 3 by Trainer 4', 'C3T4', 'Description for Class 3 by Trainer 4', '10000000-0000-0000-0000-000000000004', 'Tue, 1:00 PM', 38, NOW() - INTERVAL '79 days', NOW()),
    -- Trainer 5 Classes
    ('class-5-1', 'Class 1 by Trainer 5', 'C1T5', 'Description for Class 1 by Trainer 5', '10000000-0000-0000-0000-000000000005', 'Wed, 10:00 AM', 52, NOW() - INTERVAL '78 days', NOW()),
    ('class-5-2', 'Class 2 by Trainer 5', 'C2T5', 'Description for Class 2 by Trainer 5', '10000000-0000-0000-0000-000000000005', 'Thu, 2:00 PM', 68, NOW() - INTERVAL '77 days', NOW()),
    ('class-5-3', 'Class 3 by Trainer 5', 'C3T5', 'Description for Class 3 by Trainer 5', '10000000-0000-0000-0000-000000000005', 'Fri, 9:00 AM', 42, NOW() - INTERVAL '76 days', NOW());

-- ============================================
-- 4. INSERT CLASS ENROLLMENTS (10 students per class)
-- ============================================
-- Each class gets students 1-10, then 11-20 for the next class, cycling through
INSERT INTO public.class_enrollments (class_id, student_id, enrolled_at, status, individual_progress)
VALUES
    -- Class 1-1: Students 1-10
    ('class-1-1', '20000000-0000-0000-0000-000000000001', NOW() - INTERVAL '85 days', 'active', 40),
    ('class-1-1', '20000000-0000-0000-0000-000000000002', NOW() - INTERVAL '85 days', 'active', 45),
    ('class-1-1', '20000000-0000-0000-0000-000000000003', NOW() - INTERVAL '85 days', 'active', 50),
    ('class-1-1', '20000000-0000-0000-0000-000000000004', NOW() - INTERVAL '85 days', 'active', 55),
    ('class-1-1', '20000000-0000-0000-0000-000000000005', NOW() - INTERVAL '85 days', 'active', 35),
    ('class-1-1', '20000000-0000-0000-0000-000000000006', NOW() - INTERVAL '85 days', 'active', 48),
    ('class-1-1', '20000000-0000-0000-0000-000000000007', NOW() - INTERVAL '85 days', 'active', 42),
    ('class-1-1', '20000000-0000-0000-0000-000000000008', NOW() - INTERVAL '85 days', 'active', 52),
    ('class-1-1', '20000000-0000-0000-0000-000000000009', NOW() - INTERVAL '85 days', 'active', 38),
    ('class-1-1', '20000000-0000-0000-0000-000000000010', NOW() - INTERVAL '85 days', 'active', 46),
    -- Class 1-2: Students 11-20
    ('class-1-2', '20000000-0000-0000-0000-000000000011', NOW() - INTERVAL '84 days', 'active', 60),
    ('class-1-2', '20000000-0000-0000-0000-000000000012', NOW() - INTERVAL '84 days', 'active', 65),
    ('class-1-2', '20000000-0000-0000-0000-000000000013', NOW() - INTERVAL '84 days', 'active', 55),
    ('class-1-2', '20000000-0000-0000-0000-000000000014', NOW() - INTERVAL '84 days', 'active', 58),
    ('class-1-2', '20000000-0000-0000-0000-000000000015', NOW() - INTERVAL '84 days', 'active', 62),
    ('class-1-2', '20000000-0000-0000-0000-000000000016', NOW() - INTERVAL '84 days', 'active', 68),
    ('class-1-2', '20000000-0000-0000-0000-000000000017', NOW() - INTERVAL '84 days', 'active', 52),
    ('class-1-2', '20000000-0000-0000-0000-000000000018', NOW() - INTERVAL '84 days', 'active', 64),
    ('class-1-2', '20000000-0000-0000-0000-000000000019', NOW() - INTERVAL '84 days', 'active', 59),
    ('class-1-2', '20000000-0000-0000-0000-000000000020', NOW() - INTERVAL '84 days', 'active', 61),
    -- Class 1-3: Students 1-10
    ('class-1-3', '20000000-0000-0000-0000-000000000001', NOW() - INTERVAL '83 days', 'active', 28),
    ('class-1-3', '20000000-0000-0000-0000-000000000002', NOW() - INTERVAL '83 days', 'active', 32),
    ('class-1-3', '20000000-0000-0000-0000-000000000003', NOW() - INTERVAL '83 days', 'active', 30),
    ('class-1-3', '20000000-0000-0000-0000-000000000004', NOW() - INTERVAL '83 days', 'active', 35),
    ('class-1-3', '20000000-0000-0000-0000-000000000005', NOW() - INTERVAL '83 days', 'active', 25),
    ('class-1-3', '20000000-0000-0000-0000-000000000006', NOW() - INTERVAL '83 days', 'active', 31),
    ('class-1-3', '20000000-0000-0000-0000-000000000007', NOW() - INTERVAL '83 days', 'active', 29),
    ('class-1-3', '20000000-0000-0000-0000-000000000008', NOW() - INTERVAL '83 days', 'active', 33),
    ('class-1-3', '20000000-0000-0000-0000-000000000009', NOW() - INTERVAL '83 days', 'active', 27),
    ('class-1-3', '20000000-0000-0000-0000-000000000010', NOW() - INTERVAL '83 days', 'active', 30),
    -- Class 2-1: Students 11-20
    ('class-2-1', '20000000-0000-0000-0000-000000000011', NOW() - INTERVAL '82 days', 'active', 52),
    ('class-2-1', '20000000-0000-0000-0000-000000000012', NOW() - INTERVAL '82 days', 'active', 58),
    ('class-2-1', '20000000-0000-0000-0000-000000000013', NOW() - INTERVAL '82 days', 'active', 54),
    ('class-2-1', '20000000-0000-0000-0000-000000000014', NOW() - INTERVAL '82 days', 'active', 56),
    ('class-2-1', '20000000-0000-0000-0000-000000000015', NOW() - INTERVAL '82 days', 'active', 55),
    ('class-2-1', '20000000-0000-0000-0000-000000000016', NOW() - INTERVAL '82 days', 'active', 60),
    ('class-2-1', '20000000-0000-0000-0000-000000000017', NOW() - INTERVAL '82 days', 'active', 50),
    ('class-2-1', '20000000-0000-0000-0000-000000000018', NOW() - INTERVAL '82 days', 'active', 57),
    ('class-2-1', '20000000-0000-0000-0000-000000000019', NOW() - INTERVAL '82 days', 'active', 53),
    ('class-2-1', '20000000-0000-0000-0000-000000000020', NOW() - INTERVAL '82 days', 'active', 55),
    -- Class 2-2: Students 1-10
    ('class-2-2', '20000000-0000-0000-0000-000000000001', NOW() - INTERVAL '81 days', 'active', 68),
    ('class-2-2', '20000000-0000-0000-0000-000000000002', NOW() - INTERVAL '81 days', 'active', 72),
    ('class-2-2', '20000000-0000-0000-0000-000000000003', NOW() - INTERVAL '81 days', 'active', 70),
    ('class-2-2', '20000000-0000-0000-0000-000000000004', NOW() - INTERVAL '81 days', 'active', 75),
    ('class-2-2', '20000000-0000-0000-0000-000000000005', NOW() - INTERVAL '81 days', 'active', 65),
    ('class-2-2', '20000000-0000-0000-0000-000000000006', NOW() - INTERVAL '81 days', 'active', 71),
    ('class-2-2', '20000000-0000-0000-0000-000000000007', NOW() - INTERVAL '81 days', 'active', 69),
    ('class-2-2', '20000000-0000-0000-0000-000000000008', NOW() - INTERVAL '81 days', 'active', 73),
    ('class-2-2', '20000000-0000-0000-0000-000000000009', NOW() - INTERVAL '81 days', 'active', 67),
    ('class-2-2', '20000000-0000-0000-0000-000000000010', NOW() - INTERVAL '81 days', 'active', 70),
    -- Class 2-3: Students 11-20
    ('class-2-3', '20000000-0000-0000-0000-000000000011', NOW() - INTERVAL '80 days', 'active', 38),
    ('class-2-3', '20000000-0000-0000-0000-000000000012', NOW() - INTERVAL '80 days', 'active', 42),
    ('class-2-3', '20000000-0000-0000-0000-000000000013', NOW() - INTERVAL '80 days', 'active', 40),
    ('class-2-3', '20000000-0000-0000-0000-000000000014', NOW() - INTERVAL '80 days', 'active', 41),
    ('class-2-3', '20000000-0000-0000-0000-000000000015', NOW() - INTERVAL '80 days', 'active', 39),
    ('class-2-3', '20000000-0000-0000-0000-000000000016', NOW() - INTERVAL '80 days', 'active', 43),
    ('class-2-3', '20000000-0000-0000-0000-000000000017', NOW() - INTERVAL '80 days', 'active', 37),
    ('class-2-3', '20000000-0000-0000-0000-000000000018', NOW() - INTERVAL '80 days', 'active', 41),
    ('class-2-3', '20000000-0000-0000-0000-000000000019', NOW() - INTERVAL '80 days', 'active', 39),
    ('class-2-3', '20000000-0000-0000-0000-000000000020', NOW() - INTERVAL '80 days', 'active', 40),
    -- Class 3-1: Students 1-10
    ('class-3-1', '20000000-0000-0000-0000-000000000001', NOW() - INTERVAL '79 days', 'active', 48),
    ('class-3-1', '20000000-0000-0000-0000-000000000002', NOW() - INTERVAL '79 days', 'active', 52),
    ('class-3-1', '20000000-0000-0000-0000-000000000003', NOW() - INTERVAL '79 days', 'active', 50),
    ('class-3-1', '20000000-0000-0000-0000-000000000004', NOW() - INTERVAL '79 days', 'active', 53),
    ('class-3-1', '20000000-0000-0000-0000-000000000005', NOW() - INTERVAL '79 days', 'active', 47),
    ('class-3-1', '20000000-0000-0000-0000-000000000006', NOW() - INTERVAL '79 days', 'active', 51),
    ('class-3-1', '20000000-0000-0000-0000-000000000007', NOW() - INTERVAL '79 days', 'active', 49),
    ('class-3-1', '20000000-0000-0000-0000-000000000008', NOW() - INTERVAL '79 days', 'active', 52),
    ('class-3-1', '20000000-0000-0000-0000-000000000009', NOW() - INTERVAL '79 days', 'active', 48),
    ('class-3-1', '20000000-0000-0000-0000-000000000010', NOW() - INTERVAL '79 days', 'active', 50),
    -- Class 3-2: Students 11-20
    ('class-3-2', '20000000-0000-0000-0000-000000000011', NOW() - INTERVAL '78 days', 'active', 63),
    ('class-3-2', '20000000-0000-0000-0000-000000000012', NOW() - INTERVAL '78 days', 'active', 67),
    ('class-3-2', '20000000-0000-0000-0000-000000000013', NOW() - INTERVAL '78 days', 'active', 65),
    ('class-3-2', '20000000-0000-0000-0000-000000000014', NOW() - INTERVAL '78 days', 'active', 66),
    ('class-3-2', '20000000-0000-0000-0000-000000000015', NOW() - INTERVAL '78 days', 'active', 64),
    ('class-3-2', '20000000-0000-0000-0000-000000000016', NOW() - INTERVAL '78 days', 'active', 68),
    ('class-3-2', '20000000-0000-0000-0000-000000000017', NOW() - INTERVAL '78 days', 'active', 62),
    ('class-3-2', '20000000-0000-0000-0000-000000000018', NOW() - INTERVAL '78 days', 'active', 66),
    ('class-3-2', '20000000-0000-0000-0000-000000000019', NOW() - INTERVAL '78 days', 'active', 64),
    ('class-3-2', '20000000-0000-0000-0000-000000000020', NOW() - INTERVAL '78 days', 'active', 65),
    -- Class 3-3: Students 1-10
    ('class-3-3', '20000000-0000-0000-0000-000000000001', NOW() - INTERVAL '77 days', 'active', 33),
    ('class-3-3', '20000000-0000-0000-0000-000000000002', NOW() - INTERVAL '77 days', 'active', 37),
    ('class-3-3', '20000000-0000-0000-0000-000000000003', NOW() - INTERVAL '77 days', 'active', 35),
    ('class-3-3', '20000000-0000-0000-0000-000000000004', NOW() - INTERVAL '77 days', 'active', 36),
    ('class-3-3', '20000000-0000-0000-0000-000000000005', NOW() - INTERVAL '77 days', 'active', 34),
    ('class-3-3', '20000000-0000-0000-0000-000000000006', NOW() - INTERVAL '77 days', 'active', 36),
    ('class-3-3', '20000000-0000-0000-0000-000000000007', NOW() - INTERVAL '77 days', 'active', 34),
    ('class-3-3', '20000000-0000-0000-0000-000000000008', NOW() - INTERVAL '77 days', 'active', 37),
    ('class-3-3', '20000000-0000-0000-0000-000000000009', NOW() - INTERVAL '77 days', 'active', 33),
    ('class-3-3', '20000000-0000-0000-0000-000000000010', NOW() - INTERVAL '77 days', 'active', 35),
    -- Class 4-1: Students 11-20
    ('class-4-1', '20000000-0000-0000-0000-000000000011', NOW() - INTERVAL '76 days', 'active', 46),
    ('class-4-1', '20000000-0000-0000-0000-000000000012', NOW() - INTERVAL '76 days', 'active', 50),
    ('class-4-1', '20000000-0000-0000-0000-000000000013', NOW() - INTERVAL '76 days', 'active', 48),
    ('class-4-1', '20000000-0000-0000-0000-000000000014', NOW() - INTERVAL '76 days', 'active', 49),
    ('class-4-1', '20000000-0000-0000-0000-000000000015', NOW() - INTERVAL '76 days', 'active', 47),
    ('class-4-1', '20000000-0000-0000-0000-000000000016', NOW() - INTERVAL '76 days', 'active', 50),
    ('class-4-1', '20000000-0000-0000-0000-000000000017', NOW() - INTERVAL '76 days', 'active', 45),
    ('class-4-1', '20000000-0000-0000-0000-000000000018', NOW() - INTERVAL '76 days', 'active', 49),
    ('class-4-1', '20000000-0000-0000-0000-000000000019', NOW() - INTERVAL '76 days', 'active', 47),
    ('class-4-1', '20000000-0000-0000-0000-000000000020', NOW() - INTERVAL '76 days', 'active', 48),
    -- Class 4-2: Students 1-10
    ('class-4-2', '20000000-0000-0000-0000-000000000001', NOW() - INTERVAL '75 days', 'active', 60),
    ('class-4-2', '20000000-0000-0000-0000-000000000002', NOW() - INTERVAL '75 days', 'active', 64),
    ('class-4-2', '20000000-0000-0000-0000-000000000003', NOW() - INTERVAL '75 days', 'active', 62),
    ('class-4-2', '20000000-0000-0000-0000-000000000004', NOW() - INTERVAL '75 days', 'active', 63),
    ('class-4-2', '20000000-0000-0000-0000-000000000005', NOW() - INTERVAL '75 days', 'active', 61),
    ('class-4-2', '20000000-0000-0000-0000-000000000006', NOW() - INTERVAL '75 days', 'active', 63),
    ('class-4-2', '20000000-0000-0000-0000-000000000007', NOW() - INTERVAL '75 days', 'active', 61),
    ('class-4-2', '20000000-0000-0000-0000-000000000008', NOW() - INTERVAL '75 days', 'active', 64),
    ('class-4-2', '20000000-0000-0000-0000-000000000009', NOW() - INTERVAL '75 days', 'active', 60),
    ('class-4-2', '20000000-0000-0000-0000-000000000010', NOW() - INTERVAL '75 days', 'active', 62),
    -- Class 4-3: Students 11-20
    ('class-4-3', '20000000-0000-0000-0000-000000000011', NOW() - INTERVAL '74 days', 'active', 36),
    ('class-4-3', '20000000-0000-0000-0000-000000000012', NOW() - INTERVAL '74 days', 'active', 40),
    ('class-4-3', '20000000-0000-0000-0000-000000000013', NOW() - INTERVAL '74 days', 'active', 38),
    ('class-4-3', '20000000-0000-0000-0000-000000000014', NOW() - INTERVAL '74 days', 'active', 39),
    ('class-4-3', '20000000-0000-0000-0000-000000000015', NOW() - INTERVAL '74 days', 'active', 37),
    ('class-4-3', '20000000-0000-0000-0000-000000000016', NOW() - INTERVAL '74 days', 'active', 39),
    ('class-4-3', '20000000-0000-0000-0000-000000000017', NOW() - INTERVAL '74 days', 'active', 36),
    ('class-4-3', '20000000-0000-0000-0000-000000000018', NOW() - INTERVAL '74 days', 'active', 38),
    ('class-4-3', '20000000-0000-0000-0000-000000000019', NOW() - INTERVAL '74 days', 'active', 37),
    ('class-4-3', '20000000-0000-0000-0000-000000000020', NOW() - INTERVAL '74 days', 'active', 38),
    -- Class 5-1: Students 1-10
    ('class-5-1', '20000000-0000-0000-0000-000000000001', NOW() - INTERVAL '73 days', 'active', 50),
    ('class-5-1', '20000000-0000-0000-0000-000000000002', NOW() - INTERVAL '73 days', 'active', 54),
    ('class-5-1', '20000000-0000-0000-0000-000000000003', NOW() - INTERVAL '73 days', 'active', 52),
    ('class-5-1', '20000000-0000-0000-0000-000000000004', NOW() - INTERVAL '73 days', 'active', 53),
    ('class-5-1', '20000000-0000-0000-0000-000000000005', NOW() - INTERVAL '73 days', 'active', 51),
    ('class-5-1', '20000000-0000-0000-0000-000000000006', NOW() - INTERVAL '73 days', 'active', 53),
    ('class-5-1', '20000000-0000-0000-0000-000000000007', NOW() - INTERVAL '73 days', 'active', 51),
    ('class-5-1', '20000000-0000-0000-0000-000000000008', NOW() - INTERVAL '73 days', 'active', 54),
    ('class-5-1', '20000000-0000-0000-0000-000000000009', NOW() - INTERVAL '73 days', 'active', 50),
    ('class-5-1', '20000000-0000-0000-0000-000000000010', NOW() - INTERVAL '73 days', 'active', 52),
    -- Class 5-2: Students 11-20
    ('class-5-2', '20000000-0000-0000-0000-000000000011', NOW() - INTERVAL '72 days', 'active', 66),
    ('class-5-2', '20000000-0000-0000-0000-000000000012', NOW() - INTERVAL '72 days', 'active', 70),
    ('class-5-2', '20000000-0000-0000-0000-000000000013', NOW() - INTERVAL '72 days', 'active', 68),
    ('class-5-2', '20000000-0000-0000-0000-000000000014', NOW() - INTERVAL '72 days', 'active', 69),
    ('class-5-2', '20000000-0000-0000-0000-000000000015', NOW() - INTERVAL '72 days', 'active', 67),
    ('class-5-2', '20000000-0000-0000-0000-000000000016', NOW() - INTERVAL '72 days', 'active', 70),
    ('class-5-2', '20000000-0000-0000-0000-000000000017', NOW() - INTERVAL '72 days', 'active', 65),
    ('class-5-2', '20000000-0000-0000-0000-000000000018', NOW() - INTERVAL '72 days', 'active', 69),
    ('class-5-2', '20000000-0000-0000-0000-000000000019', NOW() - INTERVAL '72 days', 'active', 67),
    ('class-5-2', '20000000-0000-0000-0000-000000000020', NOW() - INTERVAL '72 days', 'active', 68),
    -- Class 5-3: Students 1-10
    ('class-5-3', '20000000-0000-0000-0000-000000000001', NOW() - INTERVAL '71 days', 'active', 40),
    ('class-5-3', '20000000-0000-0000-0000-000000000002', NOW() - INTERVAL '71 days', 'active', 44),
    ('class-5-3', '20000000-0000-0000-0000-000000000003', NOW() - INTERVAL '71 days', 'active', 42),
    ('class-5-3', '20000000-0000-0000-0000-000000000004', NOW() - INTERVAL '71 days', 'active', 43),
    ('class-5-3', '20000000-0000-0000-0000-000000000005', NOW() - INTERVAL '71 days', 'active', 41),
    ('class-5-3', '20000000-0000-0000-0000-000000000006', NOW() - INTERVAL '71 days', 'active', 43),
    ('class-5-3', '20000000-0000-0000-0000-000000000007', NOW() - INTERVAL '71 days', 'active', 41),
    ('class-5-3', '20000000-0000-0000-0000-000000000008', NOW() - INTERVAL '71 days', 'active', 44),
    ('class-5-3', '20000000-0000-0000-0000-000000000009', NOW() - INTERVAL '71 days', 'active', 40),
    ('class-5-3', '20000000-0000-0000-0000-000000000010', NOW() - INTERVAL '71 days', 'active', 42);

-- ============================================
-- 5. INSERT TASKS (5 per Trainer = 25 total)
-- ============================================
INSERT INTO public.tasks (title, description, class_id, type, status, due_date, created_at, updated_at)
VALUES
    -- Trainer 1 Tasks
    ('Task 1 for Trainer 1', 'Description for Task 1 for Trainer 1', 'class-1-1', 'assignment', 'pending', NOW() + INTERVAL '7 days', NOW() - INTERVAL '10 days', NOW()),
    ('Task 2 for Trainer 1', 'Description for Task 2 for Trainer 1', 'class-1-2', 'quiz', 'grading', NOW() + INTERVAL '3 days', NOW() - INTERVAL '9 days', NOW()),
    ('Task 3 for Trainer 1', 'Description for Task 3 for Trainer 1', 'class-1-3', 'review', 'overdue', NOW() - INTERVAL '2 days', NOW() - INTERVAL '8 days', NOW()),
    ('Task 4 for Trainer 1', 'Description for Task 4 for Trainer 1', 'class-1-1', 'lecture', 'completed', NOW() - INTERVAL '5 days', NOW() - INTERVAL '7 days', NOW()),
    ('Task 5 for Trainer 1', 'Description for Task 5 for Trainer 1', 'class-1-2', 'assignment', 'pending', NOW() + INTERVAL '14 days', NOW() - INTERVAL '6 days', NOW()),
    -- Trainer 2 Tasks
    ('Task 1 for Trainer 2', 'Description for Task 1 for Trainer 2', 'class-2-1', 'assignment', 'pending', NOW() + INTERVAL '8 days', NOW() - INTERVAL '10 days', NOW()),
    ('Task 2 for Trainer 2', 'Description for Task 2 for Trainer 2', 'class-2-2', 'quiz', 'grading', NOW() + INTERVAL '4 days', NOW() - INTERVAL '9 days', NOW()),
    ('Task 3 for Trainer 2', 'Description for Task 3 for Trainer 2', 'class-2-3', 'review', 'overdue', NOW() - INTERVAL '1 day', NOW() - INTERVAL '8 days', NOW()),
    ('Task 4 for Trainer 2', 'Description for Task 4 for Trainer 2', 'class-2-1', 'lecture', 'completed', NOW() - INTERVAL '6 days', NOW() - INTERVAL '7 days', NOW()),
    ('Task 5 for Trainer 2', 'Description for Task 5 for Trainer 2', 'class-2-2', 'assignment', 'pending', NOW() + INTERVAL '15 days', NOW() - INTERVAL '6 days', NOW()),
    -- Trainer 3 Tasks
    ('Task 1 for Trainer 3', 'Description for Task 1 for Trainer 3', 'class-3-1', 'assignment', 'pending', NOW() + INTERVAL '9 days', NOW() - INTERVAL '10 days', NOW()),
    ('Task 2 for Trainer 3', 'Description for Task 2 for Trainer 3', 'class-3-2', 'quiz', 'grading', NOW() + INTERVAL '5 days', NOW() - INTERVAL '9 days', NOW()),
    ('Task 3 for Trainer 3', 'Description for Task 3 for Trainer 3', 'class-3-3', 'review', 'overdue', NOW() - INTERVAL '3 days', NOW() - INTERVAL '8 days', NOW()),
    ('Task 4 for Trainer 3', 'Description for Task 4 for Trainer 3', 'class-3-1', 'lecture', 'completed', NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days', NOW()),
    ('Task 5 for Trainer 3', 'Description for Task 5 for Trainer 3', 'class-3-2', 'assignment', 'pending', NOW() + INTERVAL '16 days', NOW() - INTERVAL '6 days', NOW()),
    -- Trainer 4 Tasks
    ('Task 1 for Trainer 4', 'Description for Task 1 for Trainer 4', 'class-4-1', 'assignment', 'pending', NOW() + INTERVAL '10 days', NOW() - INTERVAL '10 days', NOW()),
    ('Task 2 for Trainer 4', 'Description for Task 2 for Trainer 4', 'class-4-2', 'quiz', 'grading', NOW() + INTERVAL '6 days', NOW() - INTERVAL '9 days', NOW()),
    ('Task 3 for Trainer 4', 'Description for Task 3 for Trainer 4', 'class-4-3', 'review', 'overdue', NOW() - INTERVAL '4 days', NOW() - INTERVAL '8 days', NOW()),
    ('Task 4 for Trainer 4', 'Description for Task 4 for Trainer 4', 'class-4-1', 'lecture', 'completed', NOW() - INTERVAL '8 days', NOW() - INTERVAL '7 days', NOW()),
    ('Task 5 for Trainer 4', 'Description for Task 5 for Trainer 4', 'class-4-2', 'assignment', 'pending', NOW() + INTERVAL '17 days', NOW() - INTERVAL '6 days', NOW()),
    -- Trainer 5 Tasks
    ('Task 1 for Trainer 5', 'Description for Task 1 for Trainer 5', 'class-5-1', 'assignment', 'pending', NOW() + INTERVAL '11 days', NOW() - INTERVAL '10 days', NOW()),
    ('Task 2 for Trainer 5', 'Description for Task 2 for Trainer 5', 'class-5-2', 'quiz', 'grading', NOW() + INTERVAL '7 days', NOW() - INTERVAL '9 days', NOW()),
    ('Task 3 for Trainer 5', 'Description for Task 3 for Trainer 5', 'class-5-3', 'review', 'overdue', NOW() - INTERVAL '5 days', NOW() - INTERVAL '8 days', NOW()),
    ('Task 4 for Trainer 5', 'Description for Task 4 for Trainer 5', 'class-5-1', 'lecture', 'completed', NOW() - INTERVAL '9 days', NOW() - INTERVAL '7 days', NOW()),
    ('Task 5 for Trainer 5', 'Description for Task 5 for Trainer 5', 'class-5-2', 'assignment', 'pending', NOW() + INTERVAL '18 days', NOW() - INTERVAL '6 days', NOW());

-- ============================================
-- 6. INSERT FEEDBACK (5 per class = 75 total)
-- ============================================
-- Generate 5 feedback items per class (15 classes * 5 = 75 feedback items)
INSERT INTO public.feedback (student_id, class_id, type, message, is_read, created_at, updated_at)
SELECT
    ('20000000-0000-0000-0000-0000000000' || LPAD((((row_number() OVER ()) % 20) + 1)::text, 2, '0'))::uuid as student_id,
    class_id,
    CASE (row_number() OVER ()) % 3
        WHEN 0 THEN 'feedback'
        WHEN 1 THEN 'complaint'
        ELSE 'question'
    END as type,
    'Feedback message ' || row_number() OVER () || ' for ' || class_id as message,
    (row_number() OVER ()) % 3 = 0 as is_read,
    NOW() - INTERVAL '1 day' * ((row_number() OVER ()) % 30) as created_at,
    NOW() as updated_at
FROM (
    SELECT id as class_id FROM public.classes
) classes
CROSS JOIN generate_series(1, 5) feedback_num;

-- ============================================
-- 7. INSERT QUESTIONS (45 total)
-- ============================================
INSERT INTO public.questions (title, description, difficulty, tags, constraints, optimal_solution, time_complexity, space_complexity, created_by, created_at, updated_at, is_active)
SELECT
    'Question ' || n as title,
    'Description for Question ' || n || '. This is a coding problem that tests your understanding of algorithms and data structures.' as description,
    CASE (n % 3)
        WHEN 0 THEN 'Easy'
        WHEN 1 THEN 'Medium'
        ELSE 'Hard'
    END as difficulty,
    ARRAY['Tag' || ((n % 5) + 1), 'Tag' || ((n % 3) + 1)] as tags,
    ARRAY['Constraint ' || n || '-1', 'Constraint ' || n || '-2', 'Constraint ' || n || '-3'] as constraints,
    'def solution_' || n || '():\n    # Optimal solution for Question ' || n || '\n    pass' as optimal_solution,
    CASE (n % 4)
        WHEN 0 THEN 'O(n)'
        WHEN 1 THEN 'O(log n)'
        WHEN 2 THEN 'O(n^2)'
        ELSE 'O(1)'
    END as time_complexity,
    CASE (n % 3)
        WHEN 0 THEN 'O(1)'
        WHEN 1 THEN 'O(n)'
        ELSE 'O(log n)'
    END as space_complexity,
    ('10000000-0000-0000-0000-0000000000' || LPAD((((n % 5) + 1))::text, 2, '0'))::uuid as created_by,
    NOW() - INTERVAL '1 day' * (45 - n) as created_at,
    NOW() as updated_at,
    true as is_active
FROM generate_series(1, 45) as n;

-- ============================================
-- 8. INSERT TEST CASES (20 per question = 900 total)
-- ============================================
INSERT INTO public.test_cases (question_id, input, expected_output, is_sample, is_hidden, difficulty, order_index, created_at)
SELECT
    q.id as question_id,
    jsonb_build_object(
        'input' || tc_num, 'Input value ' || tc_num || ' for question ' || q.title,
        'param1', tc_num,
        'param2', tc_num * 2
    ) as input,
    jsonb_build_object(
        'output', 'Expected output ' || tc_num || ' for question ' || q.title,
        'result', tc_num * 3
    ) as expected_output,
    tc_num <= 3 as is_sample,
    tc_num > 3 as is_hidden,
    CASE
        WHEN tc_num <= 5 THEN 'basic'
        WHEN tc_num <= 15 THEN 'edge'
        ELSE 'performance'
    END as difficulty,
    tc_num as order_index,
    NOW() - INTERVAL '1 day' * (20 - tc_num) as created_at
FROM public.questions q
CROSS JOIN generate_series(1, 20) as tc_num;

-- ============================================
-- 9. INSERT SUBMISSIONS (3 per question = 135 total)
-- ============================================
-- Insert submissions for each question (cycling through students)
INSERT INTO public.submissions (question_id, user_id, code, language, status, test_cases_passed, total_test_cases, runtime_ms, memory_kb, hints_used, submitted_at, executed_at)
SELECT
    q.id as question_id,
    ('20000000-0000-0000-0000-0000000000' || LPAD((((row_number() OVER (PARTITION BY q.id)) % 20) + 1)::text, 2, '0'))::uuid as user_id,
    'def solution():\n    # Submission ' || (row_number() OVER (PARTITION BY q.id)) || ' for ' || q.title || '\n    pass' as code,
    'python' as language,
    CASE (row_number() OVER (PARTITION BY q.id)) % 4
        WHEN 0 THEN 'accepted'
        WHEN 1 THEN 'wrong_answer'
        WHEN 2 THEN 'time_limit_exceeded'
        ELSE 'accepted'
    END as status,
    CASE (row_number() OVER (PARTITION BY q.id)) % 4
        WHEN 0 THEN 20
        WHEN 1 THEN 15
        WHEN 2 THEN 10
        ELSE 20
    END as test_cases_passed,
    20 as total_test_cases,
    100 + ((row_number() OVER (PARTITION BY q.id)) * 50) as runtime_ms,
    1024 + ((row_number() OVER (PARTITION BY q.id)) * 256) as memory_kb,
    (row_number() OVER (PARTITION BY q.id)) % 3 as hints_used,
    NOW() - INTERVAL '1 day' * ((row_number() OVER (PARTITION BY q.id)) * 2) as submitted_at,
    NOW() - INTERVAL '1 day' * ((row_number() OVER (PARTITION BY q.id)) * 2) + INTERVAL '5 seconds' as executed_at
FROM public.questions q
CROSS JOIN generate_series(1, 3) as sub_num;

-- ============================================
-- 10. UPDATE USER QUESTION PROGRESS
-- ============================================
-- Create progress records for users who have submitted solutions
INSERT INTO public.user_question_progress (user_id, question_id, status, attempts, best_runtime_ms, best_memory_kb, hints_used_total, first_attempted_at, solved_at, last_attempted_at)
SELECT
    s.user_id,
    s.question_id,
    CASE
        WHEN MAX(CASE WHEN s.status = 'accepted' THEN 1 ELSE 0 END) = 1 THEN 'solved'
        ELSE 'attempted'
    END as status,
    COUNT(*) as attempts,
    MIN(s.runtime_ms) as best_runtime_ms,
    MIN(s.memory_kb) as best_memory_kb,
    SUM(s.hints_used) as hints_used_total,
    MIN(s.submitted_at) as first_attempted_at,
    MAX(CASE WHEN s.status = 'accepted' THEN s.submitted_at ELSE NULL END) as solved_at,
    MAX(s.submitted_at) as last_attempted_at
FROM public.submissions s
GROUP BY s.user_id, s.question_id;

-- ============================================
-- 11. UPDATE LEADERBOARD RANKS
-- ============================================
-- Calculate and update leaderboard ranks based on problems solved
SELECT update_leaderboard_ranks();

-- ============================================
-- VERIFICATION QUERIES
-- ============================================
-- Run these queries to verify the data was inserted correctly

-- Count records in each table
DO $$
BEGIN
    RAISE NOTICE 'Users: %', (SELECT COUNT(*) FROM public.users);
    RAISE NOTICE 'Trainers: %', (SELECT COUNT(*) FROM public.users WHERE role = 'trainer');
    RAISE NOTICE 'Students: %', (SELECT COUNT(*) FROM public.users WHERE role = 'student');
    RAISE NOTICE 'Classes: %', (SELECT COUNT(*) FROM public.classes);
    RAISE NOTICE 'Class Enrollments: %', (SELECT COUNT(*) FROM public.class_enrollments);
    RAISE NOTICE 'Tasks: %', (SELECT COUNT(*) FROM public.tasks);
    RAISE NOTICE 'Feedback: %', (SELECT COUNT(*) FROM public.feedback);
    RAISE NOTICE 'Questions: %', (SELECT COUNT(*) FROM public.questions);
    RAISE NOTICE 'Test Cases: %', (SELECT COUNT(*) FROM public.test_cases);
    RAISE NOTICE 'Submissions: %', (SELECT COUNT(*) FROM public.submissions);
    RAISE NOTICE 'User Question Progress: %', (SELECT COUNT(*) FROM public.user_question_progress);
END $$;

-- ============================================
-- END OF SEED DATA
-- ============================================
