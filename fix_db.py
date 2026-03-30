from models import get_db
from db_compat import USE_POSTGRES

db = get_db()
try:
    if USE_POSTGRES:
        db.execute("ALTER TABLE assessments ADD COLUMN available_until TIMESTAMP")
    else:
        db.execute("ALTER TABLE assessments ADD COLUMN available_until TEXT")
    print("Added available_until to assessments")
except Exception as e:
    print("assessments err:", e)

try:
    if USE_POSTGRES:
        db.execute("ALTER TABLE assignments ADD COLUMN file_url TEXT DEFAULT ''")
    else:
        db.execute("ALTER TABLE assignments ADD COLUMN file_url TEXT DEFAULT ''")
    print("Added file_url to assignments")
except Exception as e:
    print("assignments err:", e)

db.commit()
db.close()
