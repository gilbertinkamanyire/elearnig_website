import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'learnug-2026-platform-secret-key')
    DATABASE = os.path.join(BASE_DIR, 'database.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max upload
    ITEMS_PER_PAGE = 10
    
    # Mailjet Config
    MAILJET_API_KEY = os.environ.get('MAILJET_API_KEY', 'd44fbbd7724c453cb6eb707c803beae6')
    MAILJET_API_SECRET = os.environ.get('MAILJET_API_SECRET', 'e0a275bf5d41b9aab19970466be8f148')
    MAILJET_SENDER_EMAIL = os.environ.get('MAILJET_SENDER_EMAIL', 'support@learnug.edu')
