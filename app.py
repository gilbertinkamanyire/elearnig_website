import os
from flask import Flask, redirect, request, session, url_for
from config import Config
from models import init_db, seed_db
from helpers import setup_helpers, register_filters

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

@app.route('/toggle-theme', methods=['POST'])
def toggle_theme():
    current_mode = session.get('theme_mode', 'light')
    new_mode = 'dark' if current_mode == 'light' else 'light'
    session['theme_mode'] = new_mode
    
    if 'user_id' in session:
        db = get_db()
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
        db.execute('INSERT OR REPLACE INTO user_preferences (user_id, bandwidth_mode) VALUES (?, ?)', 
                   (session['user_id'], mode))
        db.commit()
        db.close()
        
    return redirect(request.referrer or url_for('index'))

# Ensure database is initialized
if not os.path.exists(Config.DATABASE):
    init_db()
    seed_db()

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

