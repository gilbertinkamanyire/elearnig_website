from flask import render_template, redirect, url_for, flash, session, g
from helpers import login_required

def register_unique(app):
    @app.route('/cognitive-mirror')
    @login_required
    def cognitive_mirror():
        user_id = session['user_id']
        db = g.db
        
        # 1. Analyze Pace (Lesson progress vs time)
        attendance = db.execute('''
            SELECT COUNT(*) as views, DATE(timestamp) as date 
            FROM attendance 
            WHERE user_id = ? 
            GROUP BY DATE(timestamp)
        ''', (user_id,)).fetchall()
        
        # 2. Analyze Focus Window (When do they study?)
        hours = db.execute('''
            SELECT STRFTIME('%H', timestamp) as hour, COUNT(*) as count 
            FROM attendance 
            WHERE user_id = ? 
            GROUP BY hour 
            ORDER BY count DESC 
            LIMIT 1
        ''', (user_id,)).fetchone()
        
        focus_window = "Not enough data yet"
        if hours:
            h = int(hours['hour'])
            if 5 <= h < 12: focus_window = "Early Bird 🌅"
            elif 12 <= h < 17: focus_window = "Afternoon Achiever ☀️"
            elif 17 <= h < 21: focus_window = "Evening Scholar 🌙"
            else: focus_window = "Night Owl 🦉"

        # 3. Analyze Struggle Points (Failed quiz questions or repeated lesson views)
        struggles = db.execute('''
            SELECT l.title, COUNT(a.id) as views 
            FROM attendance a
            JOIN lessons l ON a.lesson_id = l.id
            WHERE a.user_id = ? AND a.activity_type = 'view'
            GROUP BY a.lesson_id
            HAVING views > 3
            LIMIT 3
        ''', (user_id,)).fetchall()

        # 4. Strengths (Quick completions)
        strengths = db.execute('''
            SELECT l.title 
            FROM lesson_progress lp
            JOIN lessons l ON lp.lesson_id = l.id
            WHERE lp.student_id = ? AND lp.completed = 1
            LIMIT 3
        ''', (user_id,)).fetchall()

        # 5. Competency mirror data
        competencies = db.execute('''
            SELECT c.id as course_id,
                   c.title as skill_name,
                   c.category,
                   e.progress,
                   COUNT(l.id) as total_lessons,
                   SUM(CASE WHEN lp.completed = 1 THEN 1 ELSE 0 END) as completed_lessons
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            LEFT JOIN lessons l ON l.course_id = c.id
            LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id AND lp.student_id = ?
            WHERE e.student_id = ?
            GROUP BY c.id, c.title, c.category, e.progress
            ORDER BY e.progress DESC, c.title
        ''', (user_id, user_id)).fetchall()

        competencies_mastered = []
        competencies_in_progress = []
        competencies_not_started = []
        for row in competencies:
            progress = float(row['progress'] or 0.0)
            skill = {
                'course_id': row['course_id'],
                'title': row['skill_name'],
                'category': row['category'] or 'General',
                'progress': round(progress, 0),
                'completed_lessons': int(row['completed_lessons'] or 0),
                'total_lessons': int(row['total_lessons'] or 0)
            }
            if progress >= 80:
                competencies_mastered.append(skill)
            elif progress > 0:
                competencies_in_progress.append(skill)
            else:
                competencies_not_started.append(skill)

        # Get existing insights from DB
        stored_insights = db.execute('SELECT * FROM learning_insights WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()

        return render_template('unique/cognitive_mirror.html', 
                               focus_window=focus_window, 
                               struggles=struggles, 
                               strengths=strengths,
                               stored_insights=stored_insights,
                               competencies_mastered=competencies_mastered,
                               competencies_in_progress=competencies_in_progress,
                               competencies_not_started=competencies_not_started)

    @app.route('/synergy-connect')
    @login_required
    def synergy_connect():
        user_id = session['user_id']
        db = g.db
        # Get my progress for comparison
        my_enrollments = db.execute('SELECT course_id, progress FROM enrollments WHERE student_id = ?', (user_id,)).fetchall()
        my_progress_map = {e['course_id']: e['progress'] for e in my_enrollments}
        
        course_ids = [c['course_id'] for c in my_enrollments]
        
        peers = []
        if course_ids:
            # Find peers who have completed different lessons than me
            placeholders = ', '.join(['?'] * len(course_ids))
            peers = db.execute(f'''
                SELECT DISTINCT u.id, u.full_name, c.title as course_title, e.progress, e.course_id
                FROM users u
                JOIN enrollments e ON u.id = e.student_id
                JOIN courses c ON e.course_id = c.id
                WHERE e.course_id IN ({placeholders})
                AND u.id != ?
                ORDER BY RANDOM()
                LIMIT 5
            ''', (*course_ids, user_id)).fetchall()

        return render_template('unique/synergy_connect.html', peers=peers, my_progress=my_progress_map)

    @app.route('/synergy/sync/<int:peer_id>')
    @login_required
    def synergy_sync(peer_id):
        db = g.db
        peer = db.execute('SELECT full_name FROM users WHERE id = ?', (peer_id,)).fetchone()
        if peer:
            flash(f"Sync request sent to {peer['full_name']}! They will be notified to join a 15-minute session.", "success")
        else:
            flash("User not found.", "danger")
        return redirect(url_for('synergy_connect'))

