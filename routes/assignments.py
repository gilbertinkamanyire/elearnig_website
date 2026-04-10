import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, g, abort
from config import Config
from helpers import login_required, role_required, send_notification_email, create_notification

def register_assignments(app):

    @app.route('/courses/<int:course_id>/assignments/create', methods=['GET', 'POST'])
    @role_required('lecturer', 'admin')
    def create_assignment(course_id):
        course = g.db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            abort(404)
        
        # Check permissions
        if session['role'] != 'admin' and course['lecturer_id'] != session['user_id']:
            abort(403)

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            due_date = request.form.get('due_date', '')
            max_marks = request.form.get('max_marks', 100, type=int)
            
            file_url = ''
            file = request.files.get('file')
            if file and file.filename != '':
                from werkzeug.utils import secure_filename
                filename = secure_filename(file.filename)
                unique_filename = f"asm_file_{course_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(upload_path)
                file_url = f"/uploads/{unique_filename}"

            if title:
                g.db.execute(
                    'INSERT INTO assignments (course_id, title, description, due_date, max_marks, file_url) VALUES (?, ?, ?, ?, ?, ?)',
                    (course_id, title, description, due_date, max_marks, file_url)
                )
                g.db.commit()
                
                send_notification_email(
                    subject=f"New Assignment: {title}",
                    text_part=f"A new assignment has been added to {course['title']}. Due: {due_date}",
                    html_part=f"<h3>New Assignment</h3><p><b>{title}</b> has been added to <b>{course['title']}</b>.</p><p>Due Date: {due_date}</p>",
                    notify_roles=['student']
                )
                
                flash('Assignment created!', 'success')
                return redirect(url_for('course_detail', course_id=course_id))
            
        return render_template('assignments/create.html', course=course)

    @app.route('/courses/<int:course_id>/assignments/<int:assignment_id>')
    @login_required
    def view_assignment(course_id, assignment_id):
        assignment = g.db.execute('SELECT * FROM assignments WHERE id = ? AND course_id = ?', (assignment_id, course_id)).fetchone()
        if not assignment:
            abort(404)
        
        course = g.db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        
        submission = None
        if session['role'] == 'student':
            submission = g.db.execute(
                'SELECT * FROM assignment_submissions WHERE assignment_id = ? AND student_id = ?',
                (assignment_id, session['user_id'])
            ).fetchone()
            
        submissions = []
        if session['role'] in ('lecturer', 'admin'):
            submissions = g.db.execute('''
                SELECT s.*, u.full_name, u.email 
                FROM assignment_submissions s 
                JOIN users u ON s.student_id = u.id 
                WHERE s.assignment_id = ?
            ''', (assignment_id,)).fetchall()

        return render_template('assignments/view.html', course=course, assignment=assignment, submission=submission, submissions=submissions)

    @app.route('/courses/<int:course_id>/assignments/<int:assignment_id>/edit', methods=['GET', 'POST'])
    @role_required('lecturer', 'admin')
    def edit_assignment(course_id, assignment_id):
        assignment = g.db.execute('SELECT * FROM assignments WHERE id = ? AND course_id = ?', (assignment_id, course_id)).fetchone()
        if not assignment:
            abort(404)
        
        course = g.db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        
        if session['role'] != 'admin' and course['lecturer_id'] != session['user_id']:
            abort(403)

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            due_date = request.form.get('due_date', '')
            max_marks = request.form.get('max_marks', 100, type=int)

            if title:
                file_url = assignment['file_url']
                file = request.files.get('file')
                if file and file.filename != '':
                    from werkzeug.utils import secure_filename
                    filename = secure_filename(file.filename)
                    unique_filename = f"asm_file_{course_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(upload_path)
                    file_url = f"/uploads/{unique_filename}"

                g.db.execute(
                    'UPDATE assignments SET title=?, description=?, due_date=?, max_marks=?, file_url=? WHERE id=?',
                    (title, description, due_date, max_marks, file_url, assignment_id)
                )
                g.db.commit()
                flash('Assignment updated!', 'success')
                return redirect(url_for('course_detail', course_id=course_id))

        return render_template('assignments/edit.html', course=course, assignment=assignment)

    @app.route('/courses/<int:course_id>/assignments/<int:assignment_id>/delete', methods=['POST'])
    @role_required('lecturer', 'admin')
    def delete_assignment(course_id, assignment_id):
        course = g.db.execute('SELECT lecturer_id FROM courses WHERE id = ?', (course_id,)).fetchone()
        if session['role'] != 'admin' and course['lecturer_id'] != session['user_id']:
            abort(403)
            
        g.db.execute('DELETE FROM assignments WHERE id = ? AND course_id = ?', (assignment_id, course_id))
        g.db.commit()
        flash('Assignment deleted.', 'info')
        return redirect(url_for('course_detail', course_id=course_id))

    @app.route('/courses/<int:course_id>/assignments/<int:assignment_id>/submit', methods=['POST'])
    @role_required('student')
    def submit_assignment(course_id, assignment_id):
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('view_assignment', course_id=course_id, assignment_id=assignment_id))

        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        unique_filename = f"asm_{session['user_id']}_{assignment_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(upload_path)
        file_url = f"/uploads/{unique_filename}"

        # Check for existing submission
        existing = g.db.execute(
            'SELECT id FROM assignment_submissions WHERE assignment_id = ? AND student_id = ?',
            (assignment_id, session['user_id'])
        ).fetchone()

        if existing:
            g.db.execute(
                'UPDATE assignment_submissions SET file_url = ?, submitted_at = CURRENT_TIMESTAMP WHERE id = ?',
                (file_url, existing['id'])
            )
        else:
            g.db.execute(
                'INSERT INTO assignment_submissions (assignment_id, student_id, file_url) VALUES (?, ?, ?)',
                (assignment_id, session['user_id'], file_url)
            )
        
        g.db.commit()

        assignment = g.db.execute('SELECT title FROM assignments WHERE id = ?', (assignment_id,)).fetchone()

        # Notify lecturer and admin
        lecturer = g.db.execute('''
            SELECT u.email, u.full_name 
            FROM courses c JOIN users u ON c.lecturer_id = u.id 
            WHERE c.id = ?
        ''', (course_id,)).fetchone()

        if lecturer:
            send_notification_email(
                subject=f"Submission: {assignment['title']}",
                text_part=f"{session.get('full_name')} has submitted work for {assignment['title']}.",
                html_part=f"<h3>New Assignment Submission</h3><p>Student: <b>{session.get('full_name')}</b></p><p>Assignment: <b>{assignment['title']}</b></p>",
                specific_emails=[{"Email": lecturer['email'], "Name": lecturer['full_name']}]
            )

        flash('Assignment submitted successfully!', 'success')
        return redirect(url_for('view_assignment', course_id=course_id, assignment_id=assignment_id))

    @app.route('/assignments/grade/<int:submission_id>')
    @role_required('lecturer', 'admin')
    def grade_submission(submission_id):
        submission = g.db.execute('''
            SELECT s.*, u.full_name, u.email, a.title as assignment_title, a.max_marks, a.course_id, a.id as assignment_id
            FROM assignment_submissions s 
            JOIN users u ON s.student_id = u.id 
            JOIN assignments a ON s.assignment_id = a.id
            WHERE s.id = ?
        ''', (submission_id,)).fetchone()
        
        if not submission:
            abort(404)
            
        return render_template('assignments/grade.html', submission=submission)

    @app.route('/assignments/grade/<int:submission_id>', methods=['POST'])
    @role_required('lecturer', 'admin')
    def save_grade(submission_id):
        grade = request.form.get('grade', '')
        feedback = request.form.get('feedback', '')
        
        g.db.execute(
            'UPDATE assignment_submissions SET grade = ?, feedback = ? WHERE id = ?',
            (grade, feedback, submission_id)
        )
        g.db.commit()
        
        # Get student and assignment info for notification
        info = g.db.execute('''
            SELECT s.student_id, a.title as assignment_title, c.title as course_title, 
                   u.email as student_email, u.full_name as student_name
            FROM assignment_submissions s 
            JOIN assignments a ON s.assignment_id = a.id 
            JOIN courses c ON a.course_id = c.id
            JOIN users u ON s.student_id = u.id
            WHERE s.id = ?
        ''', (submission_id,)).fetchone()

        # In-app notification
        create_notification(
            user_id=info['student_id'],
            title='Assignment Graded',
            message=f"Your assignment '{info['assignment_title']}' in '{info['course_title']}' has been graded. Grade: {grade}",
            link=url_for('student_grades')
        )

        # Email notification
        send_notification_email(
            subject=f"Grade Updated: {info['assignment_title']}",
            text_part=f"Your assignment '{info['assignment_title']}' has been graded. New grade: {grade}",
            html_part=f"<h3>Assignment Graded</h3><p>Your assignment <b>{info['assignment_title']}</b> has been graded.</p><p><b>Grade:</b> {grade}</p><p><a href='{url_for('student_grades', _external=True)}'>View details</a></p>",
            specific_emails=[{"Email": info['student_email'], "Name": info['student_name']}]
        )
        
        flash('Grade and feedback saved and student notified.', 'success')
        
        assignment_info = g.db.execute('''
            SELECT a.id as assignment_id, a.course_id 
            FROM assignment_submissions s 
            JOIN assignments a ON s.assignment_id = a.id 
            WHERE s.id = ?
        ''', (submission_id,)).fetchone()
        
        return redirect(url_for('view_assignment', course_id=assignment_info['course_id'], assignment_id=assignment_info['assignment_id']))
