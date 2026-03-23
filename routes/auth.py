import os, json
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, g, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required, role_required, send_notification_email, send_reset_email

def register_auth(app):


    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        # Get stats for landing page
        stats = {
            'courses': g.db.execute('SELECT COUNT(*) FROM courses WHERE is_published = 1').fetchone()[0],
            'students': g.db.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0],
            'lecturers': g.db.execute("SELECT COUNT(*) FROM users WHERE role = 'lecturer'").fetchone()[0],
        }

        # Get featured courses
        featured = g.db.execute('''
            SELECT c.*, u.full_name as lecturer_name,
                   (SELECT COUNT(*) FROM enrollments WHERE course_id = c.id) as student_count,
                   (SELECT COUNT(*) FROM lessons WHERE course_id = c.id) as lesson_count
            FROM courses c JOIN users u ON c.lecturer_id = u.id
            WHERE c.is_published = 1
            ORDER BY c.created_at DESC LIMIT 6
        ''').fetchall()

        return render_template('index.html', stats=stats, featured=featured)


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            user = g.db.execute('SELECT * FROM users WHERE username = ? OR email = ?',
                               (username, username)).fetchone()

            if user and check_password_hash(user['password_hash'], password):
                if not user['is_active']:
                    flash('Your account has been deactivated. Contact admin.', 'danger')
                    return redirect(url_for('login'))

                if user['role'] == 'lecturer' and not user['is_verified']:
                    flash('Your lecturer account is pending admin verification.', 'warning')
                    return redirect(url_for('login'))

                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['full_name'] = user['full_name']
                flash(f'Welcome back, {user["full_name"]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'danger')

        return render_template('auth/login.html')


    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            username = request.form.get('username', '').strip().lower()
            email = request.form.get('email', '').strip().lower()
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password', '')
            confirm = request.form.get('confirm_password', '')
            role = request.form.get('role', 'student')

            errors = []
            if not full_name or not username or not email or not password:
                errors.append('All required fields must be filled.')
            if password != confirm:
                errors.append('Passwords do not match.')
            if len(password) < 6:
                errors.append('Password must be at least 6 characters.')
            if role not in ('student', 'lecturer'):
                errors.append('Invalid role selected.')

            # Check uniqueness
            existing = g.db.execute('SELECT id FROM users WHERE username = ? OR email = ?',
                                   (username, email)).fetchone()
            if existing:
                errors.append('Username or email already exists.')

            if errors:
                for e in errors:
                    flash(e, 'danger')
            else:
                is_verified = 1 if role == 'student' else 0
                import random
                avatars = [
                    'https://images.unsplash.com/photo-1531384441138-2736e62e0919?auto=format&fit=crop&q=80&w=200',
                    'https://images.unsplash.com/photo-1506803682981-6e718a9dd3ee?auto=format&fit=crop&q=80&w=200',
                    'https://images.unsplash.com/photo-1523824922871-2292f3cbdb05?auto=format&fit=crop&q=80&w=200',
                    'https://images.unsplash.com/photo-1544928147-79a2dbc1f389?auto=format&fit=crop&q=80&w=200',
                    'https://images.unsplash.com/photo-1580894732444-8ecded7900cd?auto=format&fit=crop&q=80&w=200',
                    'https://images.unsplash.com/photo-1504275107785-981de7673fa1?auto=format&fit=crop&q=80&w=200'
                ]
                profile_pic = random.choice(avatars)
                
                g.db.execute(
                    'INSERT INTO users (username, email, password_hash, role, full_name, phone, is_verified, profile_pic_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (username, email, generate_password_hash(password), role, full_name, phone, is_verified, profile_pic)
                )
                g.db.commit()
                
                # Send welcome email
                send_notification_email(
                    subject="Welcome to LearnUG!",
                    text_part=f"Hello {full_name}, welcome to LearnUG! Your account as a {role} has been created.",
                    html_part=f"<h3>Welcome to LearnUG!</h3><p>Hello <b>{full_name}</b>, welcome to LearnUG!</p><p>Your account as a <b>{role}</b> has been created successfully.</p>",
                    specific_emails=[{"Email": email, "Name": full_name}]
                )
                
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))

        return render_template('auth/register.html')


    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))


    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            if email:
                user = g.db.execute('SELECT full_name FROM users WHERE email = ?', (email,)).fetchone()
                if user:
                    send_reset_email(email, user['full_name'])

                flash('If an account exists with that email, a password reset link has been sent.', 'info')
                return redirect(url_for('login'))
        return render_template('auth/forgot_password.html')


