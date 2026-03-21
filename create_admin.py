import sqlite3
from werkzeug.security import generate_password_hash
import os

db_path = 'database.db'

def create_admin():
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # We'll create a default admin account
    # Username: admin_user
    # Email: admin@learnug.edu
    # Password: AdminPassword123
    # Role: admin
    
    username = 'admin_user'
    email = 'system_admin@learnug.edu'
    password = 'AdminPassword123'
    role = 'admin'
    full_name = 'LearnUG System Admin'
    phone = '+256700000000'
    
    # Check if exists
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    existing = cursor.fetchone()
    
    if existing:
        print(f"Admin user '{username}' already exists. Updating password...")
        cursor.execute('''
            UPDATE users SET password_hash = ?, email = ?, full_name = ?, phone = ?
            WHERE username = ?
        ''', (generate_password_hash(password), email, full_name, phone, username))
    else:
        print(f"Creating new admin user '{username}'...")
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role, full_name, phone, is_active, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1)
        ''', (username, email, generate_password_hash(password), role, full_name, phone))
    
    conn.commit()
    conn.close()
    print(f"Admin account ready:")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print(f"  Role: {role}")

if __name__ == '__main__':
    create_admin()
