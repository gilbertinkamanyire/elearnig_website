import os

file_path = r'c:\Users\MATRIXCOMPUTER\elerning_system\routes\courses.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace assignments query
old_assign = """        assignments = g.db.execute('''
            SELECT a.*, s.id as submission_id 
            FROM assignments a 
            LEFT JOIN assignment_submissions s ON a.id = s.assignment_id AND s.student_id = ?
            WHERE a.course_id = ?
            ORDER BY a.created_at DESC
        ''', (session['user_id'], course_id)).fetchall()"""

new_assign = """        assign_query = '''
            SELECT a.*, s.id as submission_id 
            FROM assignments a 
            LEFT JOIN assignment_submissions s ON a.id = s.assignment_id AND s.student_id = ?
            WHERE a.course_id = ?
        '''
        if not is_instructor:
            assign_query += ' AND a.is_hidden = 0'
        assignments = g.db.execute(assign_query + ' ORDER BY a.created_at DESC', (session['user_id'], course_id)).fetchall()"""

if old_assign.replace('\r\n', '\n') in content.replace('\r\n', '\n'):
    content = content.replace('\r\n', '\n').replace(old_assign.replace('\r\n', '\n'), new_assign.replace('\r\n', '\n'))

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Assignments query fixed.")
