import os, json, secrets
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, g, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required, role_required, send_notification_email, send_reset_email

def register_admin(app):


    @app.route('/admin/users')
    @role_required('admin')
    def admin_users():
        role_filter = request.args.get('role', '')
        search = request.args.get('search', '').strip()

        query = 'SELECT * FROM users WHERE 1=1'
        params = []

        if role_filter:
            query += ' AND role = ?'
            params.append(role_filter)

        if search:
            query += ' AND (full_name LIKE ? OR username LIKE ? OR email LIKE ?)'
            params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])

        query += ' ORDER BY created_at DESC'
        users = g.db.execute(query, params).fetchall()

        return render_template('admin/users.html', users=users, role_filter=role_filter, search=search)


    @app.route('/admin/users/<int:user_id>/verify', methods=['POST'])
    @role_required('admin')
    def verify_lecturer(user_id):
        user = g.db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if user and user['role'] == 'lecturer':
            g.db.execute('UPDATE users SET is_verified = 1 WHERE id = ?', (user_id,))
            g.db.commit()
            flash('Lecturer verified successfully.', 'success')
            
            # Notify the lecturer
            send_notification_email(
                subject="Account Verified: Lecturer Access Granted",
                text_part="Your lecturer account has been verified by the admin. You can now log in and manage courses.",
                html_part="<h3>Account Verified</h3><p>Your lecturer account has been verified by the admin. You can now log in and manage courses.</p>",
                specific_emails=[{"Email": user['email'], "Name": user['full_name']}] if 'email' in user.keys() else []
            )
        return redirect(url_for('admin_users'))


    @app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
    @role_required('admin')
    def toggle_user(user_id):
        if user_id == session['user_id']:
            flash('Cannot deactivate your own account. Use the profile delete option if available!', 'danger')
        else:
            user = g.db.execute('SELECT is_active FROM users WHERE id = ?', (user_id,)).fetchone()
            if user:
                new_status = 0 if user['is_active'] else 1
                g.db.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
                g.db.commit()
                flash(f'User {"activated" if new_status else "deactivated"} successfully.', 'success')

        return redirect(url_for('admin_users'))

    @app.route('/admin/users/add', methods=['POST'])
    @role_required('admin')
    def admin_add_user():
        fullname = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'student')
        
        if not (fullname and username and email and password):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_users'))
        
        try:
            g.db.execute(
                'INSERT INTO users (full_name, username, email, password_hash, role) VALUES (?, ?, ?, ?, ?)',
                (fullname, username, email, generate_password_hash(password), role)
            )
            g.db.commit()
            flash(f'User {username} added successfully.', 'success')
        except Exception as e:
            flash(f'Error adding user: {str(e)}', 'danger')
            
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @role_required('admin')
    def admin_delete_user(user_id):
        if user_id == session['user_id']:
            flash('You cannot delete your own admin account through this panel.', 'danger')
            return redirect(url_for('admin_users'))
            
        try:
            user = g.db.execute('SELECT role FROM users WHERE id=?', (user_id,)).fetchone()
            if not user:
                return redirect(url_for('admin_users'))
                
            if user['role'] == 'lecturer' or user['role'] == 'admin':
                courses = g.db.execute('SELECT id FROM courses WHERE lecturer_id = ?', (user_id,)).fetchall()
                for c in courses:
                    cid = c['id']
                    g.db.execute('DELETE FROM lessons WHERE course_id=?', (cid,))
                    g.db.execute('DELETE FROM submissions WHERE assessment_id IN (SELECT id FROM assessments WHERE course_id=?)', (cid,))
                    g.db.execute('DELETE FROM assessments WHERE course_id=?', (cid,))
                    g.db.execute('DELETE FROM enrollments WHERE course_id=?', (cid,))
                    g.db.execute('DELETE FROM attendance WHERE course_id=?', (cid,))
                    g.db.execute('DELETE FROM discussions WHERE course_id=?', (cid,))
                g.db.execute('DELETE FROM courses WHERE lecturer_id = ?', (user_id,))
                
            g.db.execute('DELETE FROM discussions WHERE user_id = ?', (user_id,))
            g.db.execute('DELETE FROM replies WHERE user_id = ?', (user_id,))
            g.db.execute('DELETE FROM notifications WHERE user_id = ?', (user_id,))
            g.db.execute('DELETE FROM announcements WHERE user_id = ?', (user_id,))
            g.db.execute('DELETE FROM enrollments WHERE student_id = ?', (user_id,))
            g.db.execute('DELETE FROM lesson_progress WHERE student_id = ?', (user_id,))
            g.db.execute('DELETE FROM submissions WHERE student_id = ?', (user_id,))
            g.db.execute('DELETE FROM attendance WHERE user_id = ?', (user_id,))
            try: g.db.execute('DELETE FROM learning_insights WHERE user_id = ?', (user_id,))
            except: pass
            
            g.db.execute('DELETE FROM users WHERE id = ?', (user_id,))
            g.db.commit()
            flash('User and all associated data deleted permanently.', 'warning')
        except Exception as e:
            flash(f'Error deleting user: {str(e)}', 'danger')
            
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/password', methods=['POST'])
    @role_required('admin')
    def admin_edit_password(user_id):
        new_pass = request.form.get('new_password', '')
        confirm_pass = request.form.get('confirm_password', '')
        
        if not new_pass or len(new_pass) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('admin_users'))
            
        if new_pass != confirm_pass:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('admin_users'))
            
        g.db.execute('UPDATE users SET password_hash = ? WHERE id = ?', (generate_password_hash(new_pass), user_id))
        g.db.commit()
        flash('User password updated.', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/send-reset', methods=['POST'])
    @role_required('admin')
    def admin_send_reset(user_id):
        user = g.db.execute('SELECT id, full_name, email FROM users WHERE id = ?', (user_id,)).fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            expiry = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            g.db.execute('UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?',
                       (token, expiry, user_id))
            g.db.commit()
            
            reset_link = url_for('reset_password', token=token, _external=True)
            send_reset_email(user['email'], user['full_name'], reset_link)
            flash(f'Password reset link sent to {user["full_name"]}.', 'success')
        else:
            flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/clear/<role>', methods=['POST'])
    @role_required('admin')
    def admin_clear_role(role):
        if role not in ['student', 'lecturer']:
            flash('Invalid role specified.', 'danger')
            return redirect(url_for('admin_users'))

        # Get all users of this role (excluding admin just in case)
        users = g.db.execute('SELECT id, profile_pic_url FROM users WHERE role = ? AND username != "admin"', (role,)).fetchall()
        user_ids = [u['id'] for u in users]
        
        if not user_ids:
            flash(f'No users with role {role} found to clear.', 'info')
            return redirect(url_for('admin_users'))

        # Bulk cleanup related data
        placeholders = ', '.join(['?'] * len(user_ids))
        
        # Cleanup foreign key tables
        g.db.execute(f'DELETE FROM enrollments WHERE student_id IN ({placeholders})', user_ids)
        g.db.execute(f'DELETE FROM lesson_progress WHERE student_id IN ({placeholders})', user_ids)
        g.db.execute(f'DELETE FROM submissions WHERE student_id IN ({placeholders})', user_ids)
        g.db.execute(f'DELETE FROM attendance WHERE user_id IN ({placeholders})', user_ids)
        g.db.execute(f'DELETE FROM notifications WHERE user_id IN ({placeholders})', user_ids)
        g.db.execute(f'DELETE FROM replies WHERE user_id IN ({placeholders})', user_ids)
        g.db.execute(f'DELETE FROM learning_insights WHERE user_id IN ({placeholders})', user_ids)
        
        if role == 'lecturer':
            # Handle lecturer's courses
            courses = g.db.execute(f'SELECT id FROM courses WHERE lecturer_id IN ({placeholders})', user_ids).fetchall()
            if courses:
                course_ids = [c['id'] for c in courses]
                c_placeholders = ', '.join(['?'] * len(course_ids))
                g.db.execute(f'DELETE FROM courses WHERE id IN ({c_placeholders})', course_ids)

        # Delete users
        g.db.execute(f'DELETE FROM users WHERE id IN ({placeholders})', user_ids)
        g.db.commit()

        # Try to delete profile pics after commit
        for u in users:
            if u['profile_pic_url'] and u['profile_pic_url'].startswith('/uploads/avatar_'):
                pic_path = os.path.join(app.root_path, u['profile_pic_url'].lstrip('/'))
                if os.path.exists(pic_path):
                    try: os.remove(pic_path)
                    except: pass

        flash(f'All {role} accounts and associated data have been cleared.', 'warning')
        return redirect(url_for('admin_users'))


    @app.route('/admin/courses/<int:course_id>/clear-enrollments', methods=['POST'])
    @role_required('admin')
    def admin_clear_course_enrollments(course_id):
        g.db.execute('DELETE FROM enrollments WHERE course_id = ?', (course_id,))
        g.db.execute('DELETE FROM lesson_progress WHERE lesson_id IN (SELECT id FROM lessons WHERE course_id = ?)', (course_id,))
        g.db.execute('DELETE FROM submissions WHERE assessment_id IN (SELECT id FROM assessments WHERE course_id = ?)', (course_id,))
        g.db.commit()
        flash('All student enrollments and progress for this course have been cleared.', 'warning')
        return redirect(request.referrer or url_for('admin_analytics'))


    @app.route('/admin/announcements', methods=['GET', 'POST'])
    @role_required('admin', 'lecturer')
    def manage_announcements():
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            target = request.form.get('target_role', 'all')

            if title and content:
                g.db.execute(
                    'INSERT INTO announcements (user_id, title, content, target_role) VALUES (?, ?, ?, ?)',
                    (session['user_id'], title, content, target)
                )
                g.db.commit()
                roles_to_notify = ['student', 'lecturer'] if target == 'all' else [target]
                send_notification_email(
                    subject=f"New Announcement: {title}",
                    text_part=content,
                    html_part=f"<h3>{title}</h3><p>{content}</p>",
                    notify_roles=roles_to_notify
                )
                flash('Announcement posted!', 'success')

        announcements = g.db.execute('''
            SELECT a.*, u.full_name as author_name
            FROM announcements a JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
        ''').fetchall()

        return render_template('admin/announcements.html', announcements=announcements)


    @app.route('/admin/analytics')
    @role_required('admin')
    def admin_analytics():
        stats = {
            'total_users': g.db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
            'students': g.db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
            'lecturers': g.db.execute("SELECT COUNT(*) FROM users WHERE role='lecturer'").fetchone()[0],
            'courses': g.db.execute('SELECT COUNT(*) FROM courses').fetchone()[0],
            'published_courses': g.db.execute('SELECT COUNT(*) FROM courses WHERE is_published=1').fetchone()[0],
            'enrollments': g.db.execute('SELECT COUNT(*) FROM enrollments').fetchone()[0],
            'lessons': g.db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0],
            'discussions': g.db.execute('SELECT COUNT(*) FROM discussions').fetchone()[0],
            'submissions': g.db.execute('SELECT COUNT(*) FROM submissions').fetchone()[0],
        }

        # Top courses by enrollment
        top_courses = g.db.execute('''
            SELECT c.title, COUNT(e.id) as enrollments
            FROM courses c LEFT JOIN enrollments e ON c.id = e.course_id
            GROUP BY c.id ORDER BY enrollments DESC LIMIT 10
        ''').fetchall()

        # Users by role
        roles = g.db.execute('''
            SELECT role, COUNT(*) as count FROM users GROUP BY role
        ''').fetchall()

        return render_template('admin/analytics.html', stats=stats, top_courses=top_courses, roles=roles)


    @app.route('/admin/clear-student-dashboards', methods=['POST'])
    @role_required('admin')
    def admin_clear_student_dashboards():
        """Clear all student dashboard data: enrollments, progress, submissions, attendance."""
        try:
            g.db.execute('DELETE FROM lesson_progress')
            g.db.execute('DELETE FROM submissions')
            g.db.execute('DELETE FROM enrollments')
            g.db.execute('DELETE FROM attendance WHERE user_id IN (SELECT id FROM users WHERE role = "student")')
            g.db.commit()
            flash('All student dashboard data (enrollments, progress, submissions, attendance) has been cleared.', 'warning')
        except Exception as e:
            flash(f'Error clearing student data: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


    @app.route('/admin/clear-lecturer-dashboards', methods=['POST'])
    @role_required('admin')
    def admin_clear_lecturer_dashboards():
        """Clear all lecturer dashboard data: courses, lessons, assessments, assignments, discussions."""
        try:
            # Delete in dependency order
            g.db.execute('DELETE FROM assignment_submissions')
            g.db.execute('DELETE FROM submissions')
            g.db.execute('DELETE FROM lesson_progress')
            g.db.execute('DELETE FROM enrollments')
            g.db.execute('DELETE FROM replies')
            g.db.execute('DELETE FROM discussions')
            g.db.execute('DELETE FROM attendance')
            g.db.execute('DELETE FROM assessments')
            g.db.execute('DELETE FROM assignments')
            g.db.execute('DELETE FROM lessons')
            g.db.execute('DELETE FROM courses')
            g.db.commit()
            flash('All lecturer dashboard data (courses, lessons, assessments, assignments, discussions) has been cleared.', 'warning')
        except Exception as e:
            flash(f'Error clearing lecturer data: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

