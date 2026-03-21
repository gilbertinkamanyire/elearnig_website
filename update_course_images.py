import sqlite3

db_path = 'database.db'

def update_courses():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    updates = [
        ('https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&q=80&w=500', 'Introduction to Computer Science'),
        ('https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&q=80&w=500', 'Web Development Fundamentals'),
        ('https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&q=80&w=500', 'Database Management Systems'),
        ('https://images.unsplash.com/photo-1526379095098-d400fd0bf935?auto=format&fit=crop&q=80&w=500', 'Python Programming'),
        ('https://images.unsplash.com/photo-1573164713988-8665fc963095?auto=format&fit=crop&q=80&w=500', 'ICT for Development'),
        ('https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&q=80&w=500', 'Networking Essentials'),
    ]
    
    for url, title in updates:
        cursor.execute('UPDATE courses SET image_url = ? WHERE title = ?', (url, title))
    
    conn.commit()
    conn.close()
    print("Courses updated with images!")

if __name__ == '__main__':
    update_courses()
