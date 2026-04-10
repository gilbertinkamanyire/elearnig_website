"""Update default course images for older records."""
from models import get_db

def update_courses():
    """Set default images on courses that were created before image support."""
    try:
        db = get_db()
        updates = [
            ('/static/images/backgrounds/bg1.jpeg', 'Introduction to Computer Science'),
            ('/static/images/backgrounds/bg2.jpeg', 'Web Development Fundamentals'),
            ('/static/images/backgrounds/bg3.jpeg', 'Database Management Systems'),
            ('/static/images/backgrounds/hero_main.jpeg', 'Python Programming'),
            ('/static/images/backgrounds/bg1.jpeg', 'ICT for Development'),
            ('/static/images/backgrounds/bg2.jpeg', 'Networking Essentials'),
        ]
        for url, title in updates:
            db.execute('UPDATE courses SET image_url = ? WHERE title = ?', (url, title))
        db.commit()
        db.close()
    except Exception as e:
        print(f"Course image update skipped: {e}")

if __name__ == '__main__':
    update_courses()
    print("Courses updated with images!")
