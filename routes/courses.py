import os, json
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, g, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from helpers import login_required, role_required, send_notification_email, send_reset_email

def register_courses(app):


    @app.route('/courses')
    def courses_list():
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '').strip()
        dept_id = request.args.get('dept', type=int)

        query = '''
            SELECT c.*, u.full_name as lecturer_name, d.name as department_name,
                   (SELECT COUNT(*) FROM enrollments WHERE course_id = c.id) as student_count,
                   (SELECT COUNT(*) FROM lessons WHERE course_id = c.id) as lesson_count
            FROM courses c 
            JOIN users u ON c.lecturer_id = u.id
            LEFT JOIN departments d ON c.department_id = d.id
            WHERE c.is_published = 1
        '''
        params = []

        if search:
            query += ' AND (c.title LIKE ? OR c.description LIKE ?)'
            params.extend([f'%{search}%', f'%{search}%'])

        if dept_id:
            query += ' AND c.department_id = ?'
            params.append(dept_id)

        total = g.db.execute(f'SELECT COUNT(*) FROM courses c WHERE c.is_published = 1' +
                            (' AND (c.title LIKE ? OR c.description LIKE ?)' if search else '') +
                            (' AND c.department_id = ?' if dept_id else ''),
                            params).fetchone()[0]

        per_page = Config.ITEMS_PER_PAGE
        total_pages = max(1, (total + per_page - 1) // per_page)
        offset = (page - 1) * per_page

        query += f' ORDER BY c.created_at DESC LIMIT {per_page} OFFSET {offset}'
        courses = g.db.execute(query, params).fetchall()

        # Get departments for filter
        departments = g.db.execute('SELECT * FROM departments ORDER BY name').fetchall()

        return render_template('courses/list.html',
                             courses=courses,
                             departments=departments,
                             page=page,
                             total_pages=total_pages,
                             search=search,
                             current_dept=dept_id)


    @app.route('/courses/<int:course_id>')
    def course_detail(course_id):
        course = g.db.execute('''
            SELECT c.*, u.full_name as lecturer_name, u.email as lecturer_email, u.bio as lecturer_bio,
                   (SELECT COUNT(*) FROM enrollments WHERE course_id = c.id) as student_count,
                   (SELECT COUNT(*) FROM lessons WHERE course_id = c.id) as lesson_count
            FROM courses c JOIN users u ON c.lecturer_id = u.id
            WHERE c.id = ?
        ''', (course_id,)).fetchone()

        if not course:
            abort(404)

        # Determine if current user is the lecturer of this course or an admin
        is_manage_role = session['role'] in ('lecturer', 'admin')
        is_owner = (session['role'] == 'admin' or course['lecturer_id'] == session['user_id'])
        is_instructor = is_manage_role and is_owner

        # Get lessons - filter hidden for students
        lesson_query = '''
            SELECT l.*,
                   (SELECT completed FROM lesson_progress WHERE student_id = ? AND lesson_id = l.id) as is_completed
            FROM lessons l WHERE l.course_id = ?
        '''
        if not is_instructor:
            lesson_query += ' AND l.is_hidden = 0'
        
        lesson_query += ' ORDER BY l.order_num'
        lessons = g.db.execute(lesson_query, (session['user_id'], course_id)).fetchall()

        # Check enrollment
        enrollment = g.db.execute(
            'SELECT * FROM enrollments WHERE student_id = ? AND course_id = ?',
            (session['user_id'], course_id)
        ).fetchone()

        # Get assessments - filter hidden for students
        assess_query = '''
            SELECT a.*,
                   (SELECT id FROM submissions WHERE assessment_id = a.id AND student_id = ?) as submission_id,
                   (SELECT score FROM submissions WHERE assessment_id = a.id AND student_id = ?) as my_score,
                   (SELECT max_score FROM submissions WHERE assessment_id = a.id AND student_id = ?) as my_max_score
            FROM assessments a WHERE a.course_id = ?
        '''
        if not is_instructor:
            assess_query += ' AND a.is_hidden = 0'
        
        assess_query += ' ORDER BY a.created_at'
        assessments = g.db.execute(assess_query, (session['user_id'], session['user_id'], session['user_id'], course_id)).fetchall()

        # Add expiration info to assessments
        processed_assessments = []
        for a in assessments:
            a_dict = dict(a)
            a_dict['is_expired'] = False
            if a['available_until']:
                try:
                    expiry = datetime.strptime(a['available_until'], '%Y-%m-%dT%H:%M')
                    if datetime.now() > expiry:
                        a_dict['is_expired'] = True
                except:
                    pass
            processed_assessments.append(a_dict)
        assessments = processed_assessments

        # Get discussions
        # Get assignments
        assign_query = '''
            SELECT a.*, s.id as submission_id 
            FROM assignments a 
            LEFT JOIN assignment_submissions s ON a.id = s.assignment_id AND s.student_id = ?
            WHERE a.course_id = ?
        '''
        if not is_instructor:
            assign_query += ' AND a.is_hidden = 0'
        assignments = g.db.execute(assign_query + ' ORDER BY a.created_at DESC', (session['user_id'], course_id)).fetchall()

        # Get discussions
        discussions = g.db.execute('''
            SELECT d.*, u.full_name as author_name,
                   (SELECT COUNT(*) FROM replies WHERE discussion_id = d.id) as reply_count
            FROM discussions d JOIN users u ON d.user_id = u.id
            WHERE d.course_id = ?
            ORDER BY d.created_at DESC LIMIT 5
        ''', (course_id,)).fetchall()

        # Get participants — all enrolled students + the lecturer (visible to all course members)
        participants = g.db.execute('''
            SELECT u.id, u.full_name, u.role, u.profile_pic_url,
                   e.progress, e.participation_points, e.enrolled_at
            FROM enrollments e
            JOIN users u ON e.student_id = u.id
            WHERE e.course_id = ?
            ORDER BY e.enrolled_at ASC
        ''', (course_id,)).fetchall()

        return render_template('courses/detail.html',
                             course=course,
                             lessons=lessons,
                             enrollment=enrollment,
                             assessments=assessments,
                             assignments=assignments,
                             discussions=discussions,
                             participants=participants)


    @app.route('/courses/<int:course_id>/enroll', methods=['POST'])
    @login_required
    def enroll_course(course_id):
        # Check if already enrolled
        existing = g.db.execute(
            'SELECT id FROM enrollments WHERE student_id = ? AND course_id = ?',
            (session['user_id'], course_id)
        ).fetchone()

        if not existing:
            g.db.execute(
                'INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)',
                (session['user_id'], course_id)
            )
            g.db.commit()
            flash('Successfully enrolled in the course!', 'success')
        else:
            flash('You are already enrolled in this course.', 'info')

        return redirect(url_for('course_detail', course_id=course_id))


    @app.route('/courses/<int:course_id>/unenroll', methods=['POST'])
    @login_required
    def unenroll_course(course_id):
        g.db.execute(
            'DELETE FROM enrollments WHERE student_id = ? AND course_id = ?',
            (session['user_id'], course_id)
        )
        g.db.commit()
        flash('You have been unenrolled from the course.', 'info')
        return redirect(url_for('courses_list'))


    @app.route('/courses/create', methods=['GET', 'POST'])
    @role_required('admin', 'lecturer')
    def create_course():
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            department_id = request.form.get('department_id', type=int)
            lecturer_id = request.form.get('lecturer_id', type=int)
            category = request.form.get('category', 'General').strip()
            is_published = 1 if request.form.get('is_published') else 0

            image_url = ''
            image = request.files.get('image')
            if image and image.filename:
                from werkzeug.utils import secure_filename
                filename = secure_filename(image.filename)
                unique_filename = f"course_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image.save(upload_path)
                image_url = f"/uploads/{unique_filename}"

            if not title or not department_id or not lecturer_id:
                flash('Course title, department, and lecturer are required.', 'danger')
            else:
                g.db.execute(
                    'INSERT INTO courses (title, description, lecturer_id, department_id, image_url, is_published, category) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (title, description, lecturer_id, department_id, image_url, is_published, category)
                )
                g.db.commit()
                if is_published:
                    send_notification_email(
                        subject=f"New Course Added: {title}",
                        text_part=f"A new course '{title}' has been added.",
                        html_part=f"<h3>New Course Added</h3><p>A new course <b>{title}</b> has been published.</p>",
                        notify_roles=['student']
                    )
                flash('Course unit created successfully!', 'success')
                return redirect(url_for('dashboard'))

        departments = g.db.execute('SELECT * FROM departments ORDER BY name').fetchall()
        lecturers = g.db.execute("SELECT id, full_name FROM users WHERE role = 'lecturer' AND is_active = 1").fetchall()
        return render_template('courses/create.html', departments=departments, lecturers=lecturers)


    @app.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
    @role_required('lecturer', 'admin')
    def edit_course(course_id):
        course = g.db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course:
            abort(404)

        # Only owner or admin
        if session['role'] != 'admin' and course['lecturer_id'] != session['user_id']:
            abort(403)

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            department_id = request.form.get('department_id', type=int)
            lecturer_id = request.form.get('lecturer_id', type=int)
            category = request.form.get('category', 'General').strip()
            is_published = 1 if request.form.get('is_published') else 0

            image_url = course['image_url']
            image = request.files.get('image')
            if image and image.filename:
                from werkzeug.utils import secure_filename
                filename = secure_filename(image.filename)
                unique_filename = f"course_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image.save(upload_path)
                image_url = f"/uploads/{unique_filename}"

            if title and department_id and lecturer_id:
                g.db.execute(
                    'UPDATE courses SET title = ?, description = ?, department_id = ?, lecturer_id = ?, is_published = ?, image_url = ?, category = ? WHERE id = ?',
                    (title, description, department_id, lecturer_id, is_published, image_url, category, course_id)
                )
                g.db.commit()
                flash('Course unit updated successfully!', 'success')
                return redirect(url_for('course_detail', course_id=course_id))

        departments = g.db.execute('SELECT * FROM departments ORDER BY name').fetchall()
        lecturers = g.db.execute("SELECT id, full_name FROM users WHERE role = 'lecturer' AND is_active = 1").fetchall()
        return render_template('courses/edit.html', course=course, departments=departments, lecturers=lecturers)
    @app.route('/lessons/<int:lesson_id>/toggle-visibility', methods=['POST'])
    @login_required
    def toggle_lesson_visibility(lesson_id):
        lesson = g.db.execute('SELECT course_id, is_hidden FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
        if not lesson: abort(404)
        
        course = g.db.execute('SELECT lecturer_id FROM courses WHERE id = ?', (lesson['course_id'],)).fetchone()
        if session['role'] != 'admin' and course['lecturer_id'] != session['user_id']:
            abort(403)
            
        new_status = 0 if lesson['is_hidden'] else 1
        g.db.execute('UPDATE lessons SET is_hidden = ? WHERE id = ?', (new_status, lesson_id))
        g.db.commit()
        flash('Lesson visibility updated.', 'success')
        return redirect(url_for('course_detail', course_id=lesson['course_id']))

    @app.route('/assessments/<int:assessment_id>/toggle-visibility', methods=['POST'])
    @login_required
    def toggle_assessment_visibility(assessment_id):
        assess = g.db.execute('SELECT course_id, is_hidden FROM assessments WHERE id = ?', (assessment_id,)).fetchone()
        if not assess: abort(404)
        
        course = g.db.execute('SELECT lecturer_id FROM courses WHERE id = ?', (assess['course_id'],)).fetchone()
        if session['role'] != 'admin' and course['lecturer_id'] != session['user_id']:
            abort(403)
            
        new_status = 0 if assess['is_hidden'] else 1
        g.db.execute('UPDATE assessments SET is_hidden = ? WHERE id = ?', (new_status, assessment_id))
        g.db.commit()
        flash('Assessment visibility updated.', 'success')
        return redirect(url_for('course_detail', course_id=assess['course_id']))

    @app.route('/assignments/<int:assignment_id>/toggle-visibility', methods=['POST'])
    @login_required
    def toggle_assignment_visibility(assignment_id):
        assign = g.db.execute('SELECT course_id, is_hidden FROM assignments WHERE id = ?', (assignment_id,)).fetchone()
        if not assign: abort(404)
        
        course = g.db.execute('SELECT lecturer_id FROM courses WHERE id = ?', (assign['course_id'],)).fetchone()
        if session['role'] != 'admin' and course['lecturer_id'] != session['user_id']:
            abort(403)
            
        new_status = 0 if assign['is_hidden'] else 1
        g.db.execute('UPDATE assignments SET is_hidden = ? WHERE id = ?', (new_status, assignment_id))
        g.db.commit()
        flash('Assignment visibility updated.', 'success')
        return redirect(url_for('course_detail', course_id=assign['course_id']))

    @app.route('/courses/<int:course_id>/delete', methods=['POST'])
    @role_required('admin', 'lecturer')
    def delete_course(course_id):
        course = g.db.execute('SELECT lecturer_id, image_url FROM courses WHERE id = ?', (course_id,)).fetchone()
        if not course: abort(404)
        
        if session['role'] != 'admin' and course['lecturer_id'] != session['user_id']:
            abort(403)
            
        # Delete course image if it exists
        if course['image_url'] and course['image_url'].startswith('/uploads/course_'):
            pic_path = os.path.join(app.root_path, 'static', course['image_url'].lstrip('/static/'))
            if os.path.exists(pic_path):
                try: os.remove(pic_path)
                except: pass

        g.db.execute('DELETE FROM courses WHERE id = ?', (course_id,))
        g.db.commit()
        flash('Course and all its materials have been permanently deleted.', 'warning')
        return redirect(url_for('courses_list'))
