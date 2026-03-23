import sqlite3
import os
from config import Config

def update_courses():
    db_path = Config.DATABASE
    if not os.path.exists(db_path):
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    updates = [
        ('/static/images/backgrounds/bg1.jpeg', 'Introduction to Computer Science'),
        ('/static/images/backgrounds/bg2.jpeg', 'Web Development Fundamentals'),
        ('/static/images/backgrounds/bg3.jpeg', 'Database Management Systems'),
        ('/static/images/backgrounds/hero_main.jpeg', 'Python Programming'),
        ('/static/images/backgrounds/bg1.jpeg', 'ICT for Development'),
        ('/static/images/backgrounds/bg2.jpeg', 'Networking Essentials'),
    ]
    
    for url, title in updates:
        cursor.execute('UPDATE courses SET image_url = ? WHERE title = ?', (url, title))
    
    conn.commit()
    conn.close()
    print("Courses updated with images!")

if __name__ == '__main__':
    update_courses()
