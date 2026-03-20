import os, json
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, g, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required, role_required, send_notification_email, send_reset_email, log_attendance
from flask import send_from_directory

def register_lessons(app):


    @app.route('/courses/<int:course_id>/lessons/<int:lesson_id>')
    @login_required
    def view_lesson(course_id, lesson_id):
        lesson = g.db.execute(
            'SELECT * FROM lessons WHERE id = ? AND course_id = ?',
            (lesson_id, course_id)
        ).fetchone()

        if not lesson:
            abort(404)

        # Check visibility for students
        if session.get('role') == 'student' and lesson['is_hidden']:
            flash('This lesson is currently hidden by the lecturer.', 'warning')
            return redirect(url_for('course_detail', course_id=course_id))

        # Log attendance
        if session.get('role') == 'student':
            log_attendance(session['user_id'], course_id, lesson_id, 'view')

        course = g.db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()

        # Get all lessons for navigation
        all_lessons = g.db.execute(
            'SELECT id, title, order_num FROM lessons WHERE course_id = ? ORDER BY order_num',
            (course_id,)
        ).fetchall()

        # Find prev/next
        current_idx = None
        for i, l in enumerate(all_lessons):
            if l['id'] == lesson_id:
                current_idx = i
                break

        prev_lesson = all_lessons[current_idx - 1] if current_idx and current_idx > 0 else None
        next_lesson = all_lessons[current_idx + 1] if current_idx is not None and current_idx < len(all_lessons) - 1 else None

        # Check completion status
        progress = g.db.execute(
            'SELECT * FROM lesson_progress WHERE student_id = ? AND lesson_id = ?',
            (session['user_id'], lesson_id)
        ).fetchone()

        return render_template('courses/lesson.html',
                             lesson=lesson,
                             course=course,
                             all_lessons=all_lessons,
                             prev_lesson=prev_lesson,
                             next_lesson=next_lesson,
                             is_completed=progress and progress['completed'])


    @app.route('/courses/<int:course_id>/lessons/<int:lesson_id>/complete', methods=['POST'])
    @login_required
    def complete_lesson(course_id, lesson_id):
        # Mark lesson complete
        existing = g.db.execute(
            'SELECT * FROM lesson_progress WHERE student_id = ? AND lesson_id = ?',
            (session['user_id'], lesson_id)
        ).fetchone()

        if existing:
            g.db.execute(
                'UPDATE lesson_progress SET completed = 1, completed_at = CURRENT_TIMESTAMP WHERE student_id = ? AND lesson_id = ?',
                (session['user_id'], lesson_id)
            )
        else:
            g.db.execute(
                'INSERT INTO lesson_progress (student_id, lesson_id, completed, completed_at) VALUES (?, ?, 1, CURRENT_TIMESTAMP)',
                (session['user_id'], lesson_id)
            )

        # Update course progress
        total_lessons = g.db.execute(
            'SELECT COUNT(*) FROM lessons WHERE course_id = ?', (course_id,)
        ).fetchone()[0]

        completed_lessons = g.db.execute('''
            SELECT COUNT(*) FROM lesson_progress lp
            JOIN lessons l ON lp.lesson_id = l.id
            WHERE lp.student_id = ? AND l.course_id = ? AND lp.completed = 1
        ''', (session['user_id'], course_id)).fetchone()[0]

        progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

        g.db.execute(
            'UPDATE enrollments SET progress = ?, last_lesson_id = ? WHERE student_id = ? AND course_id = ?',
            (round(progress, 1), lesson_id, session['user_id'], course_id)
        )

        g.db.commit()
        flash('Lesson marked as complete!', 'success')
        return redirect(url_for('view_lesson', course_id=course_id, lesson_id=lesson_id))


    @app.route('/courses/<int:course_id>/lessons/add', methods=['GET', 'POST'])
    @role_required('lecturer', 'admin')
    def add_lesson(course_id):
        course = g.db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            abort(404)

        if session['role'] != 'admin' and course['lecturer_id'] != session['user_id']:
            abort(403)

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            order_num = request.form.get('order_num', 0, type=int)

            attachment = request.files.get('attachment')
            attachment_url = ''
            attachment_type = ''

            if attachment and attachment.filename:
                from werkzeug.utils import secure_filename
                filename = secure_filename(attachment.filename)
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                attachment.save(upload_path)
                attachment_url = f"/static/uploads/{unique_filename}"
                attachment_type = ext

            is_hidden = 1 if request.form.get('is_hidden') else 0

            if title and content:
                g.db.execute(
                    'INSERT INTO lessons (course_id, title, content, attachment_url, attachment_type, order_num, is_hidden) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (course_id, title, content, attachment_url, attachment_type, order_num, is_hidden)
                )
                g.db.commit()
                send_notification_email(
                    subject=f"New Lesson Added in {course['title']}",
                    text_part=f"A new lesson '{title}' has been added to {course['title']}.",
                    html_part=f"<h3>New Lesson Added</h3><p>A new lesson <b>{title}</b> has been added to <b>{course['title']}</b>.</p>",
                    notify_roles=['student']
                )
                flash('Lesson added successfully!', 'success')
                return redirect(url_for('course_detail', course_id=course_id))
            else:
                flash('Title and content are required.', 'danger')

        # Get max order for default
        max_order = g.db.execute(
            'SELECT COALESCE(MAX(order_num), 0) + 1 FROM lessons WHERE course_id = ?',
            (course_id,)
        ).fetchone()[0]

        return render_template('courses/add_lesson.html', course=course, max_order=max_order)


    @app.route('/courses/<int:course_id>/lessons/<int:lesson_id>/edit', methods=['GET', 'POST'])
    @role_required('lecturer', 'admin')
    def edit_lesson(course_id, lesson_id):
        lesson = g.db.execute(
            'SELECT * FROM lessons WHERE id = ? AND course_id = ?',
            (lesson_id, course_id)
        ).fetchone()

        if not lesson:
            abort(404)

        course = g.db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            order_num = request.form.get('order_num', 0, type=int)

            attachment = request.files.get('attachment')
            is_hidden = 1 if request.form.get('is_hidden') else 0
            
            if title and content:
                if attachment and attachment.filename:
                    from werkzeug.utils import secure_filename
                    filename = secure_filename(attachment.filename)
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                    unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    attachment.save(upload_path)
                    attachment_url = f"/static/uploads/{unique_filename}"
                    attachment_type = ext

                    g.db.execute(
                        'UPDATE lessons SET title=?, content=?, attachment_url=?, attachment_type=?, order_num=?, is_hidden=? WHERE id=?',
                        (title, content, attachment_url, attachment_type, order_num, is_hidden, lesson_id)
                    )
                else:
                    g.db.execute(
                        'UPDATE lessons SET title=?, content=?, order_num=?, is_hidden=? WHERE id=?',
                        (title, content, order_num, is_hidden, lesson_id)
                    )
                g.db.commit()
                flash('Lesson updated!', 'success')
                return redirect(url_for('view_lesson', course_id=course_id, lesson_id=lesson_id))

        return render_template('courses/edit_lesson.html', lesson=lesson, course=course)


    @app.route('/courses/<int:course_id>/lessons/<int:lesson_id>/delete', methods=['POST'])
    @role_required('lecturer', 'admin')
    def delete_lesson(course_id, lesson_id):
        g.db.execute('DELETE FROM lessons WHERE id = ? AND course_id = ?', (lesson_id, course_id))
        g.db.commit()
        flash('Lesson deleted.', 'info')
        return redirect(url_for('course_detail', course_id=course_id))


    @app.route('/courses/<int:course_id>/lessons/<int:lesson_id>/download')
    @login_required
    def download_resource(course_id, lesson_id):
        lesson = g.db.execute(
            'SELECT attachment_url FROM lessons WHERE id = ? AND course_id = ?',
            (lesson_id, course_id)
        ).fetchone()

        if not lesson or not lesson['attachment_url']:
            flash('Resource not found.', 'danger')
            return redirect(url_for('view_lesson', course_id=course_id, lesson_id=lesson_id))

        # Log attendance
        if session.get('role') == 'student':
            log_attendance(session['user_id'], course_id, lesson_id, 'download')

        filename = lesson['attachment_url'].split('/')[-1]
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


