from models import get_db

def log_attendance(user_id, course_id, lesson_id, activity_type):
    db = get_db()
    # Log the general attendance record
    db.execute(
        'INSERT INTO attendance (user_id, course_id, lesson_id, activity_type) VALUES (?, ?, ?, ?)',
        (user_id, course_id, lesson_id, activity_type)
    )
    
    # Update participation points in enrollments (1 point per click)
    db.execute('''
        UPDATE enrollments 
        SET participation_points = participation_points + 1 
        WHERE student_id = ? AND course_id = ?
    ''', (user_id, course_id))
    
    db.commit()
    db.close()
