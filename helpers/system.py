from flask import g, session
from models import get_db
from db_compat import USE_POSTGRES

TRANSLATIONS = {
    'en': {
        'How It Works': 'How It Works',
        'About': 'About',
        'Support': 'Support',
        'Home': 'Home',
        'Dashboard': 'Dashboard',
        'Learning': 'Learning',
        'Share': 'Share',
        'Low Data Mode Enabled': 'Low Data Mode Enabled',
        'Offline support active': 'Offline support active',
        'Student': 'Student',
        'Lecturer': 'Lecturer',
        'Course Lessons': 'Course Lessons',
        'Quiz Required': 'Quiz Required',
        'Quiz Completed': 'Quiz Completed',
        'Mark as Complete': 'Mark as Complete',
        'Take Questionnaire': 'Take Questionnaire',
        'Progress': 'Progress',
        'Participants': 'Participants'
    },
    'lg': {
        'How It Works': 'Enkola Entuufu',
        'About': 'Ku Byo',
        'Support': 'Obuwandiike',
        'Home': 'Wankoko',
        'Dashboard': 'Ekibuga',
        'Learning': 'Okwongera Omuwendo',
        'Share': 'Gula',
        'Low Data Mode Enabled': 'Ekikola ekya Ddata Emitono kikolebwa',
        'Offline support active': 'Okuyamba nga tolina intaneti kukola',
        'Student': 'Muwandiisi',
        'Lecturer': 'Omuyigirizi',
        'Course Lessons': 'Ebikozesebwa by Amakubo',
        'Quiz Required': 'Ekibuuzo kitwaliddwa',
        'Quiz Completed': 'Oluvioolu lussibweddemu',
        'Mark as Complete': 'Laga nga kikende',
        'Take Questionnaire': 'Wangula Ebibuuzo',
        'Progress': 'Okukyusa',
        'Participants': 'Abategeeza'
    },
    'sw': {
        'How It Works': 'Jinsi Inavyofanya Kazi',
        'About': 'Kuhusu',
        'Support': 'Msaada',
        'Home': 'Nyumbani',
        'Dashboard': 'Dashibodi',
        'Learning': 'Kujifunza',
        'Share': 'Shiriki',
        'Low Data Mode Enabled': 'Hali ya Data Chini Imezimwa',
        'Offline support active': 'Msaada wa nje ya mtandao unafanya kazi',
        'Student': 'Mwanafunzi',
        'Lecturer': 'Mwalimu',
        'Course Lessons': 'Masomo ya Kozi',
        'Quiz Required': 'Mtihani Unahitajika',
        'Quiz Completed': 'Mtihani Umefanyika',
        'Mark as Complete': 'Wezesha Kukamilisha',
        'Take Questionnaire': 'Chukua Dodoso',
        'Progress': 'Maendeleo',
        'Participants': 'Washiriki'
    }
}

def setup_helpers(app):
    @app.before_request
    def before_request():
        g.db = get_db()

    @app.teardown_appcontext
    def close_db(exception):
        db = getattr(g, 'db', None)
        if db is not None:
            try:
                db.close()
            except:
                pass

    def translate(text):
        lang = session.get('language', 'en')
        return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(text, text)

    @app.context_processor
    def inject_user():
        try:
            if 'user_id' in session:
                user = g.db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
                return {'current_user': user, '_': translate}
        except:
            pass
        return {'current_user': None, '_': translate}
