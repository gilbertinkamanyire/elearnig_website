from flask import g, session
from models import get_db

def setup_helpers(app):
    @app.before_request
    def before_request():
        g.db = get_db()

    @app.teardown_appcontext
    def close_db(exception):
        db = getattr(g, 'db', None)
        if db is not None:
            db.close()

    @app.context_processor
    def inject_user():
        if 'user_id' in session:
            user = g.db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            return {'current_user': user}
        return {'current_user': None}
