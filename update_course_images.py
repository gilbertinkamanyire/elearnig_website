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
        ('https://images.unsplash.com/photo-1531123897727-8f129e1bfd8c?auto=format&fit=crop&q=80&w=500', 'Introduction to Computer Science'),
        ('https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&q=80&w=500', 'Web Development Fundamentals'),
        ('https://images.unsplash.com/photo-1516321497487-e288fb19713f?auto=format&fit=crop&q=80&w=500', 'Database Management Systems'),
        ('https://images.unsplash.com/photo-1531123414708-20ddcb1e3ce1?auto=format&fit=crop&q=80&w=500', 'Python Programming'),
        ('https://images.unsplash.com/photo-1573164713988-8665fc963095?auto=format&fit=crop&q=80&w=500', 'ICT for Development'),
        ('https://images.unsplash.com/photo-1544928147-79a2dbc1f389?auto=format&fit=crop&q=80&w=500', 'Networking Essentials'),
    ]
    
    for url, title in updates:
        cursor.execute('UPDATE courses SET image_url = ? WHERE title = ?', (url, title))
    
    conn.commit()
    conn.close()
    print("Courses updated with images!")

if __name__ == '__main__':
    update_courses()
