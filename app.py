import os
from flask import Flask, redirect, request, session, url_for
from config import Config
from models import init_db, seed_db
from helpers import setup_helpers, register_filters
from db_compat import USE_POSTGRES

from routes.auth import register_auth
from routes.dashboard import register_dashboard
from routes.courses import register_courses
from routes.departments import register_departments
from routes.lessons import register_lessons
from routes.assessments import register_assessments
from routes.discussions import register_discussions
from routes.assignments import register_assignments
from routes.grades import register_grades
from routes.profile import register_profile
from routes.admin import register_admin
from routes.pages import register_pages
from routes.errors import register_errors
from routes.serviceworker import register_serviceworker
from routes.unique import register_unique

app = Flask(__name__)
app.config.from_object(Config)

from models import get_db
import secrets
from werkzeug.security import generate_password_hash

@app.before_request
def auto_guest_account():
    # Only track actual page loads, ignore static assets and auth actions
    if not request.endpoint or request.endpoint.startswith('static') or request.endpoint in ('login', 'register', 'serve_uploads', 'toggle_theme', 'toggle_bandwidth', 'logout'):
        return

    if 'user_id' not in session:
        db = get_db()
        # Generate random unique guest credentials
        random_id = secrets.token_hex(4)
        username = f"guest_{random_id}"
        email = f"{username}@guest.learnug.com"
        password = generate_password_hash('guest123')
        full_name = f"Guest Visitor ({random_id})"
        
        # Insert user so they reflect on the admin side immediately
        if USE_POSTGRES:
            cursor = db._conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role, full_name, is_active, is_verified) VALUES (%s, %s, %s, %s, %s, TRUE, TRUE) RETURNING id",
                (username, email, password, 'student', full_name)
            )
            user_id = cursor.fetchone()[0]
            db.commit()
        else:
            db.execute(
                "INSERT INTO users (username, email, password_hash, role, full_name, is_active, is_verified) VALUES (?, ?, ?, ?, ?, 1, 1)",
                (username, email, password, 'student', full_name)
            )
            db.commit()
            user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            
        db.close()
        
        # Log them in automatically
        session.permanent = True
        session['user_id'] = user_id
        session['username'] = username
        session['role'] = 'student'
        session['full_name'] = full_name

@app.route('/toggle-theme', methods=['POST'])
def toggle_theme():
    current_mode = session.get('theme_mode', 'light')
    new_mode = 'dark' if current_mode == 'light' else 'light'
    session['theme_mode'] = new_mode
    
    if 'user_id' in session:
        db = get_db()
        if USE_POSTGRES:
            db.execute(
                'INSERT INTO user_preferences (user_id, theme) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET theme = EXCLUDED.theme',
                (session['user_id'], new_mode)
            )
        else:
            db.execute('INSERT OR REPLACE INTO user_preferences (user_id, theme) VALUES (?, ?)', 
                       (session['user_id'], new_mode))
        db.commit()
        db.close()
        
    return redirect(request.referrer or url_for('index'))

@app.route('/toggle-bandwidth', methods=['POST'])
def toggle_bandwidth():
    mode = request.form.get('mode', 'standard')
    session['bandwidth_mode'] = mode
    
    if 'user_id' in session:
        db = get_db()
        if USE_POSTGRES:
            db.execute(
                'INSERT INTO user_preferences (user_id, bandwidth_mode) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET bandwidth_mode = EXCLUDED.bandwidth_mode',
                (session['user_id'], mode)
            )
        else:
            db.execute('INSERT OR REPLACE INTO user_preferences (user_id, bandwidth_mode) VALUES (?, ?)', 
                       (session['user_id'], mode))
        db.commit()
        db.close()
        
    return redirect(request.referrer or url_for('index'))

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



# Initialize database
if USE_POSTGRES:
    # Always try to init on Postgres (CREATE IF NOT EXISTS is safe)
    try:
        init_db()
        seed_db()
    except Exception as e:
        print(f"DB init note: {e}")
else:
    if not os.path.exists(Config.DATABASE):
        init_db()
        seed_db()

# Automatically run data fixes for older accounts/courses
try:
    from update_course_images import update_courses
    update_courses()
    
    # Auto-fix admin credentials on remote db
    from werkzeug.security import generate_password_hash
    db_fix = get_db()
    
    admin_hash = generate_password_hash('admin123')
    admin_email = 'admin@learnug.com'
    admin_username = 'admin'
    admin_full_name = 'System Administrator'
    admin_phone = '+256700000001'

    if USE_POSTGRES:
        # Check if admin exists
        existing_admin = db_fix.execute("SELECT id FROM users WHERE username = %s", (admin_username,)).fetchone()
        
        if existing_admin:
            db_fix.execute(
                "UPDATE users SET email = %s, password_hash = %s WHERE username = %s",
                (admin_email, admin_hash, admin_username)
            )
        else:
            db_fix.execute(
                "INSERT INTO users (username, email, password_hash, role, full_name, phone, is_active, is_verified) VALUES (%s, %s, %s, %s, %s, %s, TRUE, TRUE)",
                (admin_username, admin_email, admin_hash, 'admin', admin_full_name, admin_phone)
            )
    else: # SQLite
        existing_admin = db_fix.execute("SELECT id FROM users WHERE username = ?", (admin_username,)).fetchone()
        
        if existing_admin:
            db_fix.execute(
                "UPDATE users SET email = ?, password_hash = ? WHERE username = ?",
                (admin_email, admin_hash, admin_username)
            )
        else:
            db_fix.execute(
                "INSERT INTO users (username, email, password_hash, role, full_name, phone, is_active, is_verified) VALUES (?, ?, ?, ?, ?, ?, 1, 1)",
                (admin_username, admin_email, admin_hash, 'admin', admin_full_name, admin_phone)
            )
    
    db_fix.commit()
    db_fix.close()
except Exception as e:
    print(f"Data fix skipped: {e}")

@app.context_processor
def inject_nav_data():
    from models import get_db
    try:
        db = get_db()
        depts = db.execute('SELECT id, name FROM departments ORDER BY name').fetchall()
        db.close()
        return dict(nav_departments=depts)
    except:
        return dict(nav_departments=[])

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

setup_helpers(app)
register_filters(app)

register_auth(app)
register_dashboard(app)
register_courses(app)
register_departments(app)
register_lessons(app)
register_assessments(app)
register_discussions(app)
register_assignments(app)
register_grades(app)
register_profile(app)
register_admin(app)
register_pages(app)
register_errors(app)
register_serviceworker(app)
register_unique(app)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
