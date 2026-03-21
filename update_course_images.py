import sqlite3

db_path = 'database.db'

def update_courses():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    updates = [
        ('https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&q=60&w=500', 'Introduction to Computer Science'),
        ('https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&q=60&w=500', 'Web Development Fundamentals'),
        ('https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&q=60&w=500', 'Database Management Systems'),
        ('https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&q=60&w=500', 'Python Programming'),
        ('https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&q=60&w=500', 'ICT for Development'),
        ('https://images.unsplash.com/photo-1558494949-ef010cbdcc51?auto=format&fit=crop&q=60&w=500', 'Networking Essentials'),
    ]
    
    for url, title in updates:
        cursor.execute('UPDATE courses SET image_url = ? WHERE title = ?', (url, title))
    
    conn.commit()
    conn.close()
    print("Courses updated with images!")

if __name__ == '__main__':
    update_courses()
