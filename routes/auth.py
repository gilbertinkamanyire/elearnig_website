import os, json, secrets
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
            username = request.form.get('username', '').strip().lower()
            password = request.form.get('password', '')

            user = g.db.execute('SELECT * FROM users WHERE username = ? OR email = ?',
                               (username, username)).fetchone()

            if user and check_password_hash(user['password_hash'], password):
                if not user['is_active']:
                    flash('Your account has been deactivated. Please contact the administrator.', 'danger')
                    return redirect(url_for('login'))

                # Specific check for lecturers whose accounts are still pending admin approval
                if user['role'] == 'lecturer' and not user['is_verified']:
                    flash('Welcome, your lecturer account is currently pending administrative verification. Please wait for an email confirmation or contact admin.', 'warning')
                    return redirect(url_for('login'))

                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['full_name'] = user['full_name']
                flash(f'Welcome back, {user["full_name"]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username/email or password. Please try again.', 'danger')

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
                profile_pic = ''
                
                g.db.execute(
                    'INSERT INTO users (username, email, password_hash, role, full_name, phone, is_verified, profile_pic_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (username, email, generate_password_hash(password), role, full_name, phone, is_verified, profile_pic)
                )
                g.db.commit()
                
                # Notification for admin if lecturer registers
                if role == 'lecturer':
                    send_notification_email(
                        subject="New Lecturer Registration Pending Approval",
                        text_part=f"A new lecturer account has been created: {full_name} ({username}). Please visit the admin panel to verify.",
                        html_part=f"<h3>New Lecturer Registration</h3><p><b>{full_name}</b> ({username}) has registered as a lecturer and is pending approval.</p><p><a href='/admin/users'>Visit Admin Panel</a></p>",
                        notify_roles=['admin']
                    )
                
                # Send welcome email
                send_notification_email(
                    subject="Welcome to LearnUG!",
                    text_part=f"Hello {full_name}, welcome to LearnUG! Your account as a {role} has been created.",
                    html_part=f"<h3>Welcome to LearnUG!</h3><p>Hello <b>{full_name}</b>, welcome to LearnUG!</p><p>Your account as a <b>{role}</b> has been created successfully.</p>",
                    specific_emails=[{"Email": email, "Name": full_name}]
                )
                
                if role == 'lecturer':
                    flash('Registration successful! Your account is pending admin approval before you can log in.', 'info')
                else:
                    flash('Registration successful! You can now log in.', 'success')
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
                user = g.db.execute('SELECT id, full_name, email FROM users WHERE email = ?', (email,)).fetchone()
                if user:
                    token = secrets.token_urlsafe(32)
                    expiry = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # simplistic expiry, could be +1 hour
                    # In a real app we'd set an actual expiry time, for now let's just store the token
                    g.db.execute('UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?',
                               (token, expiry, user['id']))
                    g.db.commit()
                    
                    reset_link = url_for('reset_password', token=token, _external=True)
                    send_reset_email(user['email'], user['full_name'], reset_link)

                flash('If an account exists with that email, a password reset link has been sent.', 'info')
                return redirect(url_for('login'))
        return render_template('auth/forgot_password.html')

    @app.route('/reset-password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
            
        user = g.db.execute('SELECT id, username FROM users WHERE reset_token = ?', (token,)).fetchone()
        if not user:
            flash('Invalid or expired reset token.', 'danger')
            return redirect(url_for('forgot_password'))
            
        if request.method == 'POST':
            new_pass = request.form.get('password', '')
            confirm = request.form.get('confirm_password', '')
            
            if len(new_pass) < 6:
                flash('Password must be at least 6 characters.', 'danger')
            elif new_pass != confirm:
                flash('Passwords do not match.', 'danger')
            else:
                g.db.execute('UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?',
                           (generate_password_hash(new_pass), user['id']))
                g.db.commit()
                flash('Your password has been reset. You can now log in.', 'success')
                return redirect(url_for('login'))
                
        return render_template('auth/reset_password.html', token=token)


