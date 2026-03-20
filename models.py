import sqlite3
import os
from config import Config

def get_db():
    """Get database connection with row factory and error handling."""
    try:
        db = sqlite3.connect(Config.DATABASE, timeout=10)
        db.row_factory = sqlite3.Row
        # Enable some modern SQLite features
        db.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=NORMAL") # Faster writes
        return db
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        # On Vercel, try to re-initialize if it fails
        if os.environ.get('VERCEL'):
            try:
                # Remove if exists and try again
                if os.path.exists(Config.DATABASE):
                    os.remove(Config.DATABASE)
                init_db()
                seed_db()
                return sqlite3.connect(Config.DATABASE)
            except:
                pass
        raise e


def init_db():
    """Initialize database with schema."""
    db = get_db()
    
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
            is_verified INTEGER DEFAULT 1 -- Default 1, but will be set to 0 for lecturers
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
            activity_type TEXT NOT NULL, -- 'view', 'download'
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
            insight_type TEXT NOT NULL, -- 'focus_window', 'struggle_point', 'strength', 'pace'
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
            bandwidth_mode TEXT DEFAULT 'standard', -- 'standard', 'low', 'ultra'
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
    
    # Create lessons for Course 1 - Intro to CS
    cs_lessons = [
        (1, 'What is Computer Science?', '''<h3>Welcome to Computer Science!</h3>
<p>Computer Science is the study of computation, automation, and information. It spans a range of topics from theoretical studies of algorithms, computation, and information to practical issues of implementing computational systems.</p>

<h4>Key Areas:</h4>
<ul>
<li><strong>Algorithms</strong> - Step-by-step procedures for solving problems</li>
<li><strong>Data Structures</strong> - Ways to organize and store data efficiently</li>
<li><strong>Programming</strong> - Writing instructions for computers</li>
<li><strong>Software Engineering</strong> - Building reliable software systems</li>
</ul>

<h4>Why Study Computer Science?</h4>
<p>In today's digital world, computing skills are essential. From mobile applications to web services, computer science drives innovation across all industries. In Uganda, the growing tech ecosystem offers tremendous opportunities for skilled computing professionals.</p>

<p><strong>Activity:</strong> List three ways computers are used in your daily life and identify the computer science concepts behind each.</p>''', 1),
        (1, 'Number Systems and Binary', '''<h3>Understanding Number Systems</h3>
<p>Computers use the binary number system (base-2) to represent all data. Understanding number systems is fundamental to computing.</p>

<h4>Decimal (Base-10)</h4>
<p>The system we use daily: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9</p>

<h4>Binary (Base-2)</h4>
<p>The system computers use: 0 and 1</p>
<p>Each binary digit is called a <strong>bit</strong>. Eight bits make a <strong>byte</strong>.</p>

<h4>Converting Decimal to Binary</h4>
<p>To convert 13 to binary:</p>
<pre>
13 ÷ 2 = 6 remainder 1
 6 ÷ 2 = 3 remainder 0
 3 ÷ 2 = 1 remainder 1
 1 ÷ 2 = 0 remainder 1
</pre>
<p>Reading remainders bottom-up: <strong>1101</strong></p>

<p><strong>Practice:</strong> Convert the following to binary: 5, 10, 25, 100</p>''', 2),
        (1, 'Introduction to Algorithms', '''<h3>What is an Algorithm?</h3>
<p>An algorithm is a finite sequence of well-defined instructions used to solve a class of specific problems or to perform a computation.</p>

<h4>Characteristics of a Good Algorithm:</h4>
<ol>
<li><strong>Input</strong> - Has zero or more inputs</li>
<li><strong>Output</strong> - Produces at least one output</li>
<li><strong>Definiteness</strong> - Each step is clearly defined</li>
<li><strong>Finiteness</strong> - Terminates after a finite number of steps</li>
<li><strong>Effectiveness</strong> - Each step is basic enough to be carried out</li>
</ol>

<h4>Example: Making Tea Algorithm</h4>
<ol>
<li>Boil water</li>
<li>Place tea bag in cup</li>
<li>Pour hot water into cup</li>
<li>Wait 3-5 minutes</li>
<li>Remove tea bag</li>
<li>Add sugar/milk if desired</li>
</ol>

<p><strong>Exercise:</strong> Write an algorithm for finding the largest number in a list of numbers.</p>''', 3),
    ]
    
    for l in cs_lessons:
        db.execute('INSERT INTO lessons (course_id, title, content, order_num) VALUES (?, ?, ?, ?)', l)
    
    # Lessons for Course 2 - Web Development
    web_lessons = [
        (2, 'Introduction to HTML', '''<h3>HTML - The Foundation of the Web</h3>
<p>HTML (HyperText Markup Language) is the standard markup language for creating web pages. It describes the structure of a web page using elements and tags.</p>

<h4>Basic HTML Structure:</h4>
<pre>
&lt;!DOCTYPE html&gt;
&lt;html&gt;
&lt;head&gt;
    &lt;title&gt;My Page&lt;/title&gt;
&lt;/head&gt;
&lt;body&gt;
    &lt;h1&gt;Hello World!&lt;/h1&gt;
    &lt;p&gt;My first web page.&lt;/p&gt;
&lt;/body&gt;
&lt;/html&gt;
</pre>

<h4>Common HTML Elements:</h4>
<ul>
<li><code>&lt;h1&gt;</code> to <code>&lt;h6&gt;</code> - Headings</li>
<li><code>&lt;p&gt;</code> - Paragraphs</li>
<li><code>&lt;a&gt;</code> - Links</li>
<li><code>&lt;img&gt;</code> - Images</li>
<li><code>&lt;ul&gt;</code>, <code>&lt;ol&gt;</code> - Lists</li>
</ul>

<p><strong>Task:</strong> Create a simple HTML page about yourself with a heading, paragraph, and an unordered list of your hobbies.</p>''', 1),
        (2, 'CSS Styling Basics', '''<h3>CSS - Making Web Pages Beautiful</h3>
<p>CSS (Cascading Style Sheets) is used to style and layout web pages. It controls colors, fonts, spacing, and positioning.</p>

<h4>Three Ways to Add CSS:</h4>
<ol>
<li><strong>Inline</strong> - Using the style attribute</li>
<li><strong>Internal</strong> - Using &lt;style&gt; tags in head</li>
<li><strong>External</strong> - Linking a .css file (recommended)</li>
</ol>

<h4>CSS Syntax:</h4>
<pre>
selector {
    property: value;
}

/* Example */
h1 {
    color: blue;
    font-size: 24px;
}
</pre>

<h4>Common CSS Properties:</h4>
<ul>
<li><code>color</code> - Text color</li>
<li><code>background-color</code> - Background color</li>
<li><code>font-size</code> - Text size</li>
<li><code>margin</code> - Space outside element</li>
<li><code>padding</code> - Space inside element</li>
</ul>

<p><strong>Task:</strong> Style your HTML page from the previous lesson with colors, fonts, and spacing.</p>''', 2),
    ]
    
    for l in web_lessons:
        db.execute('INSERT INTO lessons (course_id, title, content, order_num) VALUES (?, ?, ?, ?)', l)
    
    # Lessons for Course 4 - Python Programming
    python_lessons = [
        (4, 'Getting Started with Python', '''<h3>Why Python?</h3>
<p>Python is one of the most popular programming languages in the world. It is known for its simplicity, readability, and versatility.</p>

<h4>Your First Python Program:</h4>
<pre>
print("Hello, Uganda!")
print("Welcome to Python Programming")
</pre>

<h4>Variables and Data Types:</h4>
<pre>
# Variables
name = "Wabulejo"
age = 22
gpa = 3.8
is_student = True

# Print variables
print(f"Name: {name}")
print(f"Age: {age}")
print(f"GPA: {gpa}")
</pre>

<h4>Python Data Types:</h4>
<ul>
<li><code>str</code> - Text strings ("hello")</li>
<li><code>int</code> - Integers (42)</li>
<li><code>float</code> - Decimal numbers (3.14)</li>
<li><code>bool</code> - True or False</li>
<li><code>list</code> - Ordered collections [1, 2, 3]</li>
</ul>

<p><strong>Exercise:</strong> Create variables to store your personal information and print them.</p>''', 1),
        (4, 'Control Structures', '''<h3>Making Decisions in Python</h3>
<p>Control structures allow your program to make decisions and repeat actions.</p>

<h4>If-Else Statements:</h4>
<pre>
age = 20

if age >= 18:
    print("You are an adult")
elif age >= 13:
    print("You are a teenager")
else:
    print("You are a child")
</pre>

<h4>For Loops:</h4>
<pre>
# Count from 1 to 5
for i in range(1, 6):
    print(i)

# Loop through a list
fruits = ["mango", "banana", "pineapple"]
for fruit in fruits:
    print(f"I love {fruit}")
</pre>

<h4>While Loops:</h4>
<pre>
count = 0
while count < 5:
    print(f"Count: {count}")
    count += 1
</pre>

<p><strong>Exercise:</strong> Write a program that prints all even numbers from 1 to 20.</p>''', 2),
    ]
    
    for l in python_lessons:
        db.execute('INSERT INTO lessons (course_id, title, content, order_num) VALUES (?, ?, ?, ?)', l)
    
    # Create enrollments
    enrollments = [
        (4, 1), (4, 2), (4, 4),  # Wabulejo enrolled in CS, Web Dev, Python
        (5, 1), (5, 3), (5, 4),  # Okiria enrolled in CS, DB, Python
        (6, 1), (6, 2), (6, 5),  # Nakayiza enrolled in CS, Web Dev, ICT4D
        (7, 2), (7, 4), (7, 6),  # Musoke enrolled in Web Dev, Python, Networking
    ]
    
    for e in enrollments:
        db.execute('INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)', e)
    
    # Create assessments
    quiz1_questions = json.dumps([
        {
            "question": "What number system do computers use?",
            "options": ["Decimal (Base-10)", "Binary (Base-2)", "Octal (Base-8)", "Hexadecimal (Base-16)"],
            "correct": 1
        },
        {
            "question": "How many bits are in a byte?",
            "options": ["4", "8", "16", "32"],
            "correct": 1
        },
        {
            "question": "What is an algorithm?",
            "options": [
                "A programming language",
                "A type of computer",
                "A step-by-step procedure for solving problems",
                "A database system"
            ],
            "correct": 2
        },
        {
            "question": "Which of the following is NOT a characteristic of a good algorithm?",
            "options": ["Input", "Infinity", "Output", "Definiteness"],
            "correct": 1
        }
    ])
    
    db.execute('INSERT INTO assessments (course_id, title, description, questions_json, time_limit) VALUES (?, ?, ?, ?, ?)',
               (1, 'Quiz 1: CS Fundamentals', 'Test your understanding of basic computer science concepts.', quiz1_questions, 15))
    
    quiz2_questions = json.dumps([
        {
            "question": "What does HTML stand for?",
            "options": ["Hyper Text Markup Language", "High Tech Machine Language", "Home Tool Markup Language", "Hyperlinks Text Mark Language"],
            "correct": 0
        },
        {
            "question": "Which tag is used for the largest heading?",
            "options": ["<h6>", "<heading>", "<h1>", "<head>"],
            "correct": 2
        },
        {
            "question": "What does CSS stand for?",
            "options": ["Computer Style Sheets", "Cascading Style Sheets", "Creative Style System", "Colorful Style Sheets"],
            "correct": 1
        }
    ])
    
    db.execute('INSERT INTO assessments (course_id, title, description, questions_json, time_limit) VALUES (?, ?, ?, ?, ?)',
               (2, 'Quiz 1: HTML & CSS Basics', 'Test your knowledge of HTML and CSS fundamentals.', quiz2_questions, 10))
    
    # Create discussions
    discussions = [
        (1, 4, 'Best resources for learning algorithms?', 'Hello everyone! Can you recommend good resources for understanding algorithms better? I find the topic challenging but interesting.'),
        (1, 5, 'Study group for upcoming quiz', 'Anyone interested in forming a study group for the CS fundamentals quiz? We could meet online or on campus.'),
        (2, 6, 'Responsive design tips', 'What are some good practices for making websites look good on mobile phones? I want my projects to work well on small screens.'),
        (4, 4, 'Python project ideas', 'Looking for beginner-friendly Python project ideas. Something practical that could help in our daily lives here in Uganda.'),
    ]
    
    for d in discussions:
        db.execute('INSERT INTO discussions (course_id, user_id, title, content) VALUES (?, ?, ?, ?)', d)
    
    # Create replies
    replies_data = [
        (1, 5, 'I recommend starting with "Introduction to Algorithms" by Cormen. Also, there are great free resources on YouTube.'),
        (1, 2, 'Great question! I would also suggest practicing on platforms like HackerRank. Start with easy problems.'),
        (2, 7, 'I am interested! Let us coordinate on WhatsApp. My number is in my profile.'),
        (4, 5, 'How about a simple expense tracker? Or a program to convert currencies? Those would be useful!'),
        (4, 2, 'Excellent ideas! You could also build a simple grade calculator or a to-do list application.'),
    ]
    
    for r in replies_data:
        db.execute('INSERT INTO replies (discussion_id, user_id, content) VALUES (?, ?, ?)', r)
    
    # Create announcements
    announcements = [
        (1, 'Welcome to the New Semester!', 'Dear students and lecturers, welcome to the new semester. All course materials are now available on the platform. Please ensure you enroll in your courses.', 'all'),
        (1, 'System Maintenance Notice', 'The platform will undergo maintenance this Saturday from 2:00 AM to 6:00 AM EAT. Please save your work beforehand.', 'all'),
        (1, 'New Course Available: ICT for Development', 'We are pleased to announce a new course on ICT for Development. This course explores how technology can address challenges in Uganda and East Africa.', 'student'),
    ]
    
    for a in announcements:
        db.execute('INSERT INTO announcements (user_id, title, content, target_role) VALUES (?, ?, ?, ?)', a)
    
    # Add some lesson progress
    lesson_progress = [
        (4, 1, 1),  # Wabulejo completed lesson 1 of CS
        (4, 2, 1),  # Wabulejo completed lesson 2 of CS
        (5, 1, 1),  # Okiria completed lesson 1 of CS
    ]
    
    for lp in lesson_progress:
        db.execute('INSERT INTO lesson_progress (student_id, lesson_id, completed, completed_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)', lp)
    
    # Update progress for enrollments
    db.execute("UPDATE enrollments SET progress = 66.7 WHERE student_id = 4 AND course_id = 1")
    db.execute("UPDATE enrollments SET progress = 33.3 WHERE student_id = 5 AND course_id = 1")
    
    # Add some learning insights for user 4 (Wabulejo)
    insights = [
        (4, None, 'focus_window', 'Your peak performance is usually between 8 AM and 10 AM. Most of your quiz successes happen in the morning!'),
        (4, 1, 'struggle_point', 'You viewed "Number Systems and Binary" 5 times. This seems like a tough one! Try checking the Synergy Connect for a mentor.'),
        (4, None, 'strength', 'Your "Python Basics" progress was 40% faster than the department average. You have a natural flair for logic!')
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
