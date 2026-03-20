import os
from config import Config
from db_compat import USE_POSTGRES, get_postgres_db, get_sqlite_db

# Track if DB has been initialized this process
_db_initialized = False

def get_db():
    """Get database connection - auto-detects PostgreSQL vs SQLite."""
    if USE_POSTGRES:
        return get_postgres_db()
    else:
        return get_sqlite_db()

def init_db():
    """Initialize database with schema."""
    global _db_initialized
    db = get_db()
    
    if USE_POSTGRES:
        # PostgreSQL schema
        cursor = db._conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                full_name TEXT NOT NULL,
                phone TEXT,
                bio TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                profile_pic_url TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                is_verified INTEGER DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS departments (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS courses (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                lecturer_id INTEGER NOT NULL REFERENCES users(id),
                department_id INTEGER REFERENCES departments(id),
                category TEXT DEFAULT 'General',
                image_url TEXT DEFAULT '',
                is_published INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS lessons (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                attachment_url TEXT DEFAULT '',
                attachment_type TEXT DEFAULT '',
                order_num INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS enrollments (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES users(id),
                course_id INTEGER NOT NULL REFERENCES courses(id),
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                progress REAL DEFAULT 0.0,
                participation_points INTEGER DEFAULT 0,
                last_lesson_id INTEGER DEFAULT NULL,
                UNIQUE(student_id, course_id)
            );
            
            CREATE TABLE IF NOT EXISTS lesson_progress (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES users(id),
                lesson_id INTEGER NOT NULL REFERENCES lessons(id),
                completed INTEGER DEFAULT 0,
                completed_at TIMESTAMP,
                UNIQUE(student_id, lesson_id)
            );
            
            CREATE TABLE IF NOT EXISTS assessments (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                questions_json TEXT NOT NULL DEFAULT '[]',
                time_limit INTEGER DEFAULT 0,
                privacy_mode INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                course_id INTEGER NOT NULL REFERENCES courses(id),
                lesson_id INTEGER,
                activity_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                link TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS submissions (
                id SERIAL PRIMARY KEY,
                assessment_id INTEGER NOT NULL REFERENCES assessments(id),
                student_id INTEGER NOT NULL REFERENCES users(id),
                answers_json TEXT NOT NULL DEFAULT '{}',
                score REAL DEFAULT 0,
                max_score REAL DEFAULT 0,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS discussions (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS replies (
                id SERIAL PRIMARY KEY,
                discussion_id INTEGER NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS announcements (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                target_role TEXT DEFAULT 'all',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS assignments (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT,
                due_date TIMESTAMP,
                max_marks INTEGER DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS assignment_submissions (
                id SERIAL PRIMARY KEY,
                assignment_id INTEGER NOT NULL REFERENCES assignments(id),
                student_id INTEGER NOT NULL REFERENCES users(id),
                file_url TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                grade TEXT DEFAULT 'Not Graded',
                feedback TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS learning_insights (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                course_id INTEGER REFERENCES courses(id),
                insight_type TEXT NOT NULL,
                content TEXT NOT NULL,
                relevance_score REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS synergy_matches (
                id SERIAL PRIMARY KEY,
                user_a_id INTEGER NOT NULL REFERENCES users(id),
                user_b_id INTEGER NOT NULL REFERENCES users(id),
                course_id INTEGER NOT NULL REFERENCES courses(id),
                match_reason TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_a_id, user_b_id, course_id)
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                bandwidth_mode TEXT DEFAULT 'standard',
                theme TEXT DEFAULT 'light'
            );
        ''')
        
        # Create indexes (ignore if exists)
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_attendance_user ON attendance(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_course ON attendance(course_id)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id)",
            "CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id)",
            "CREATE INDEX IF NOT EXISTS idx_lessons_course ON lessons(course_id)",
            "CREATE INDEX IF NOT EXISTS idx_discussions_course ON discussions(course_id)",
            "CREATE INDEX IF NOT EXISTS idx_submissions_student ON submissions(student_id)",
            "CREATE INDEX IF NOT EXISTS idx_lesson_progress_student ON lesson_progress(student_id)",
        ]
        for idx in indexes:
            try:
                cursor.execute(idx)
            except:
                db._conn.rollback()
        
        db.commit()
        db.close()
    else:
        # SQLite schema (original)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                full_name TEXT NOT NULL,
                phone TEXT,
                bio TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                profile_pic_url TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                is_verified INTEGER DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                lecturer_id INTEGER NOT NULL,
                department_id INTEGER,
                category TEXT DEFAULT 'General',
                image_url TEXT DEFAULT '',
                is_published INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lecturer_id) REFERENCES users(id),
                FOREIGN KEY (department_id) REFERENCES departments(id)
            );
            
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                attachment_url TEXT DEFAULT '',
                attachment_type TEXT DEFAULT '',
                order_num INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                progress REAL DEFAULT 0.0,
                participation_points INTEGER DEFAULT 0,
                last_lesson_id INTEGER DEFAULT NULL,
                FOREIGN KEY (student_id) REFERENCES users(id),
                FOREIGN KEY (course_id) REFERENCES courses(id),
                UNIQUE(student_id, course_id)
            );
            
            CREATE TABLE IF NOT EXISTS lesson_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,
                completed INTEGER DEFAULT 0,
                completed_at TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES users(id),
                FOREIGN KEY (lesson_id) REFERENCES lessons(id),
                UNIQUE(student_id, lesson_id)
            );
            
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                questions_json TEXT NOT NULL DEFAULT '[]',
                time_limit INTEGER DEFAULT 0,
                privacy_mode INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                lesson_id INTEGER,
                activity_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (course_id) REFERENCES courses(id),
                FOREIGN KEY (lesson_id) REFERENCES lessons(id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                link TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_attendance_user ON attendance(user_id);
            CREATE INDEX IF NOT EXISTS idx_attendance_course ON attendance(course_id);
            CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
            
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assessment_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                answers_json TEXT NOT NULL DEFAULT '{}',
                score REAL DEFAULT 0,
                max_score REAL DEFAULT 0,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assessment_id) REFERENCES assessments(id),
                FOREIGN KEY (student_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS discussions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discussion_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (discussion_id) REFERENCES discussions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                target_role TEXT DEFAULT 'all',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date TIMESTAMP,
                max_marks INTEGER DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS assignment_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                file_url TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                grade TEXT DEFAULT 'Not Graded',
                feedback TEXT DEFAULT '',
                FOREIGN KEY (assignment_id) REFERENCES assignments(id),
                FOREIGN KEY (student_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS learning_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER,
                insight_type TEXT NOT NULL,
                content TEXT NOT NULL,
                relevance_score REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (course_id) REFERENCES courses(id)
            );

            CREATE TABLE IF NOT EXISTS synergy_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_a_id INTEGER NOT NULL,
                user_b_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                match_reason TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_a_id) REFERENCES users(id),
                FOREIGN KEY (user_b_id) REFERENCES users(id),
                FOREIGN KEY (course_id) REFERENCES courses(id),
                UNIQUE(user_a_id, user_b_id, course_id)
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                bandwidth_mode TEXT DEFAULT 'standard',
                theme TEXT DEFAULT 'light',
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
            CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id);
            CREATE INDEX IF NOT EXISTS idx_lessons_course ON lessons(course_id);
            CREATE INDEX IF NOT EXISTS idx_discussions_course ON discussions(course_id);
            CREATE INDEX IF NOT EXISTS idx_submissions_student ON submissions(student_id);
            CREATE INDEX IF NOT EXISTS idx_lesson_progress_student ON lesson_progress(student_id);
        ''')
        
        db.commit()
        db.close()
    
    _db_initialized = True

def seed_db():
    """Seed database with sample data for demonstration."""
    from werkzeug.security import generate_password_hash
    import json
    
    db = get_db()
    
    # Check if already seeded
    existing = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if existing > 0:
        db.close()
        return
    
    # Create users
    users = [
        ('admin', 'admin@learnug.edu', generate_password_hash('admin123'), 'admin', 'System Administrator', '+256700000001'),
        ('dr_ninyesiga', 'aninyesiga@learnug.edu', generate_password_hash('lecturer123'), 'lecturer', 'Allan Ninyesiga', '+256789981418'),
        ('dr_mukasa', 'mukasa@learnug.edu', generate_password_hash('lecturer123'), 'lecturer', 'Dr. James Mukasa', '+256700000002'),
        ('wabulejo', 'wabulejo@learnug.edu', generate_password_hash('student123'), 'student', 'Wabulejo Viamaris', '+256700000003'),
        ('okiria', 'okiria@learnug.edu', generate_password_hash('student123'), 'student', 'Okiria Vincent', '+256700000004'),
        ('nakayiza', 'nakayiza@learnug.edu', generate_password_hash('student123'), 'student', 'Sarah Nakayiza', '+256700000005'),
        ('musoke', 'musoke@learnug.edu', generate_password_hash('student123'), 'student', 'David Musoke', '+256700000006'),
    ]
    
    for u in users:
        db.execute('INSERT INTO users (username, email, password_hash, role, full_name, phone) VALUES (?, ?, ?, ?, ?, ?)', u)
    
    # Create departments
    departments = [
        ('Computing', 'Department of Computing and Information Technology'),
        ('Engineering', 'Department of Engineering and Applied Sciences'),
        ('Business', 'Department of Business and Management'),
    ]
    for d in departments:
        db.execute('INSERT INTO departments (name, description) VALUES (?, ?)', d)
    
    # Create courses
    courses = [
        ('Introduction to Computer Science', 'Learn fundamentals.', 2, 1, 1),
        ('Web Development Fundamentals', 'Master HTML, CSS.', 2, 1, 1),
        ('Database Management Systems', 'Understand SQL.', 3, 1, 1),
        ('Python Programming', 'Introduction to Python.', 2, 1, 1),
        ('ICT for Development', 'Leverage ICT for challenges.', 3, 1, 1),
        ('Networking Essentials', 'Network protocols.', 3, 1, 1),
    ]
    
    for c in courses:
        db.execute('INSERT INTO courses (title, description, lecturer_id, department_id, is_published) VALUES (?, ?, ?, ?, ?)', c)
    
    # Create lessons for Course 1
    cs_lessons = [
        (1, 'What is Computer Science?', '<h3>Welcome to Computer Science!</h3><p>Computer Science is the study of computation, automation, and information.</p>', 1),
        (1, 'Number Systems and Binary', '<h3>Understanding Number Systems</h3><p>Computers use the binary number system (base-2) to represent all data.</p>', 2),
        (1, 'Introduction to Algorithms', '<h3>What is an Algorithm?</h3><p>An algorithm is a finite sequence of well-defined instructions.</p>', 3),
    ]
    
    for l in cs_lessons:
        db.execute('INSERT INTO lessons (course_id, title, content, order_num) VALUES (?, ?, ?, ?)', l)
    
    # Create lessons for Course 2
    web_lessons = [
        (2, 'Introduction to HTML', '<h3>HTML - The Foundation of the Web</h3><p>HTML is the standard markup language for creating web pages.</p>', 1),
        (2, 'CSS Styling Basics', '<h3>CSS - Making Web Pages Beautiful</h3><p>CSS is used to style and layout web pages.</p>', 2),
    ]
    
    for l in web_lessons:
        db.execute('INSERT INTO lessons (course_id, title, content, order_num) VALUES (?, ?, ?, ?)', l)
    
    # Python lessons
    python_lessons = [
        (4, 'Getting Started with Python', '<h3>Why Python?</h3><p>Python is one of the most popular programming languages.</p>', 1),
        (4, 'Control Structures', '<h3>Making Decisions in Python</h3><p>Control structures allow your program to make decisions.</p>', 2),
    ]
    
    for l in python_lessons:
        db.execute('INSERT INTO lessons (course_id, title, content, order_num) VALUES (?, ?, ?, ?)', l)
    
    # Create enrollments
    enrollments = [
        (4, 1), (4, 2), (4, 4),
        (5, 1), (5, 3), (5, 4),
        (6, 1), (6, 2), (6, 5),
        (7, 2), (7, 4), (7, 6),
    ]
    
    for e in enrollments:
        db.execute('INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)', e)
    
    # Create assessments
    quiz1_questions = json.dumps([
        {"question": "What number system do computers use?", "options": ["Decimal", "Binary", "Octal", "Hex"], "correct": 1},
        {"question": "How many bits in a byte?", "options": ["4", "8", "16", "32"], "correct": 1},
        {"question": "What is an algorithm?", "options": ["A language", "A computer", "A step-by-step procedure", "A database"], "correct": 2},
        {"question": "NOT a characteristic of a good algorithm?", "options": ["Input", "Infinity", "Output", "Definiteness"], "correct": 1}
    ])
    
    db.execute('INSERT INTO assessments (course_id, title, description, questions_json, time_limit) VALUES (?, ?, ?, ?, ?)',
               (1, 'Quiz 1: CS Fundamentals', 'Test your understanding of basic CS concepts.', quiz1_questions, 15))
    
    quiz2_questions = json.dumps([
        {"question": "What does HTML stand for?", "options": ["Hyper Text Markup Language", "High Tech Machine Language", "Home Tool Markup Language", "Hyperlinks Text Mark Language"], "correct": 0},
        {"question": "Which tag is the largest heading?", "options": ["h6", "heading", "h1", "head"], "correct": 2},
        {"question": "What does CSS stand for?", "options": ["Computer Style Sheets", "Cascading Style Sheets", "Creative Style System", "Colorful Style Sheets"], "correct": 1}
    ])
    
    db.execute('INSERT INTO assessments (course_id, title, description, questions_json, time_limit) VALUES (?, ?, ?, ?, ?)',
               (2, 'Quiz 1: HTML & CSS Basics', 'Test your knowledge of HTML and CSS.', quiz2_questions, 10))
    
    # Discussions
    discussions = [
        (1, 4, 'Best resources for learning algorithms?', 'Can you recommend good resources for understanding algorithms better?'),
        (1, 5, 'Study group for upcoming quiz', 'Anyone interested in forming a study group for the CS fundamentals quiz?'),
        (2, 6, 'Responsive design tips', 'What are some good practices for making websites look good on mobile?'),
        (4, 4, 'Python project ideas', 'Looking for beginner-friendly Python project ideas.'),
    ]
    
    for d in discussions:
        db.execute('INSERT INTO discussions (course_id, user_id, title, content) VALUES (?, ?, ?, ?)', d)
    
    # Replies
    replies_data = [
        (1, 5, 'I recommend "Introduction to Algorithms" by Cormen.'),
        (1, 2, 'Great question! Practice on platforms like HackerRank.'),
        (2, 7, 'I am interested! Let us coordinate.'),
        (4, 5, 'How about a simple expense tracker?'),
        (4, 2, 'You could also build a grade calculator.'),
    ]
    
    for r in replies_data:
        db.execute('INSERT INTO replies (discussion_id, user_id, content) VALUES (?, ?, ?)', r)
    
    # Announcements
    announcements = [
        (1, 'Welcome to the New Semester!', 'Dear students and lecturers, welcome. All materials are now available.', 'all'),
        (1, 'System Maintenance Notice', 'The platform will undergo maintenance this Saturday.', 'all'),
        (1, 'New Course Available', 'We are pleased to announce a new course on ICT for Development.', 'student'),
    ]
    
    for a in announcements:
        db.execute('INSERT INTO announcements (user_id, title, content, target_role) VALUES (?, ?, ?, ?)', a)
    
    # Lesson progress
    lesson_progress = [
        (4, 1, 1),
        (4, 2, 1),
        (5, 1, 1),
    ]
    
    for lp in lesson_progress:
        db.execute('INSERT INTO lesson_progress (student_id, lesson_id, completed, completed_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)', lp)
    
    # Update progress
    db.execute("UPDATE enrollments SET progress = 66.7 WHERE student_id = 4 AND course_id = 1")
    db.execute("UPDATE enrollments SET progress = 33.3 WHERE student_id = 5 AND course_id = 1")
    
    # Learning insights
    insights = [
        (4, None, 'focus_window', 'Peak performance between 8 AM and 10 AM.'),
        (4, 1, 'struggle_point', 'Viewed "Number Systems and Binary" 5 times.'),
        (4, None, 'strength', 'Python Basics progress was 40% faster than average.')
    ]
    for i in insights:
        db.execute('INSERT INTO learning_insights (user_id, course_id, insight_type, content) VALUES (?, ?, ?, ?)', i)

    db.commit()
    db.close()
    print("Database seeded successfully!")

if __name__ == '__main__':
    init_db()
    seed_db()
    print("Database initialized and seeded!")
