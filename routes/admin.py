import os, json
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
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
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
            # Cleanup related data (cascading)
            g.db.execute('DELETE FROM enrollments WHERE student_id = ?', (user_id,))
            g.db.execute('DELETE FROM lesson_progress WHERE student_id = ?', (user_id,))
            g.db.execute('DELETE FROM submissions WHERE student_id = ?', (user_id,))
            g.db.execute('DELETE FROM attendance WHERE user_id = ?', (user_id,))
            g.db.execute('DELETE FROM users WHERE id = ?', (user_id,))
            g.db.commit()
            flash('User deleted permanently.', 'warning')
        except Exception as e:
            flash(f'Error deleting user: {str(e)}', 'danger')
            
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/edit-password', methods=['POST'])
    @role_required('admin')
    def admin_edit_password(user_id):
        new_password = request.form.get('new_password', '').strip()
        if not new_password or len(new_password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('admin_users'))
            
        g.db.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (generate_password_hash(new_password), user_id)
        )
        g.db.commit()
        flash('User password updated.', 'success')
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


