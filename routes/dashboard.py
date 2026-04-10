from flask import render_template, redirect, url_for, session, g
from helpers import login_required

def register_dashboard(app):


    @app.route('/dashboard')
    @login_required
    def dashboard():
        user_id = session['user_id']
        role = session['role']

        if role == 'student':
            # Get enrolled courses with progress
            enrollments = g.db.execute('''
                SELECT e.*, c.title, c.description, c.category, c.image_url, u.full_name as lecturer_name,
                       (SELECT COUNT(*) FROM lessons WHERE course_id = c.id) as total_lessons
                FROM enrollments e
                JOIN courses c ON e.course_id = c.id
                JOIN users u ON c.lecturer_id = u.id
                WHERE e.student_id = ?
                ORDER BY e.enrolled_at DESC
            ''', (user_id,)).fetchall()

            # Recent announcements
            announcements = g.db.execute('''
                SELECT a.*, u.full_name as author_name
                FROM announcements a JOIN users u ON a.user_id = u.id
                WHERE a.target_role IN ('all', 'student')
                ORDER BY a.created_at DESC LIMIT 5
            ''').fetchall()

            # Upcoming assessments
            assessments = g.db.execute('''
                SELECT a.*, c.title as course_title
                FROM assessments a
                JOIN courses c ON a.course_id = c.id
                JOIN enrollments e ON e.course_id = c.id
                WHERE e.student_id = ?
                AND a.id NOT IN (SELECT assessment_id FROM submissions WHERE student_id = ?)
                ORDER BY a.created_at DESC LIMIT 5
            ''', (user_id, user_id)).fetchall()

            return render_template('dashboard/student.html',
                                 enrollments=enrollments,
                                 announcements=announcements,
                                 assessments=assessments)

        elif role == 'lecturer':
            # Get lecturer's courses
            courses = g.db.execute('''
                SELECT c.*,
                       (SELECT COUNT(*) FROM enrollments WHERE course_id = c.id) as student_count,
                       (SELECT COUNT(*) FROM lessons WHERE course_id = c.id) as lesson_count,
                       (SELECT COUNT(*) FROM discussions WHERE course_id = c.id) as discussion_count
                FROM courses c WHERE c.lecturer_id = ?
                ORDER BY c.created_at DESC
            ''', (user_id,)).fetchall()

            # Recent discussions across all courses
            recent_discussions = g.db.execute('''
                SELECT d.*, c.title as course_title, u.full_name as author_name,
                       (SELECT COUNT(*) FROM replies WHERE discussion_id = d.id) as reply_count
                FROM discussions d
                JOIN courses c ON d.course_id = c.id
                JOIN users u ON d.user_id = u.id
                WHERE c.lecturer_id = ?
                ORDER BY d.created_at DESC LIMIT 5
            ''', (user_id,)).fetchall()

            return render_template('dashboard/lecturer.html',
                                 courses=courses,
                                 recent_discussions=recent_discussions)

        else:  # admin
            stats = {
                'total_users': g.db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
                'total_students': g.db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
                'total_lecturers': g.db.execute("SELECT COUNT(*) FROM users WHERE role='lecturer'").fetchone()[0],
                'total_courses': g.db.execute('SELECT COUNT(*) FROM courses').fetchone()[0],
                'published_courses': g.db.execute('SELECT COUNT(*) FROM courses WHERE is_published=1').fetchone()[0],
                'total_enrollments': g.db.execute('SELECT COUNT(*) FROM enrollments').fetchone()[0],
                'total_discussions': g.db.execute('SELECT COUNT(*) FROM discussions').fetchone()[0],
                'total_submissions': g.db.execute('SELECT COUNT(*) FROM submissions').fetchone()[0],
            }

            recent_users = g.db.execute('''
                SELECT * FROM users ORDER BY created_at DESC LIMIT 10
            ''').fetchall()

            return render_template('dashboard/admin.html',
                                 stats=stats,
                                 recent_users=recent_users)


