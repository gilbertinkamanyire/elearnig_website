import requests
from app import app
import os
import sqlite3

# Initialize DB locally to make sure it's fresh
print("Initializing database...")
os.system("python models.py")

# Mock the session/g? No, easier to just hit the app using flask test client
with app.test_client() as client:
    print("Testing login with admin/admin123...")
    res = client.post('/login', data={'username': 'admin@learnug.com', 'password': 'admin123'}, follow_redirects=True)
    if '/dashboard' in res.request.url:
        print("Login Success for admin@learnug.com")
    else:
        print(f"Login Failure for admin@learnug.com. URL: {res.request.url}")

    res = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    if '/dashboard' in res.request.url:
        print("Login Success for admin")
    else:
        print(f"Login Failure for admin. URL: {res.request.url}")

    res = client.post('/login', data={'username': 'AdmiN', 'password': 'admin123'}, follow_redirects=True)
    if '/dashboard' in res.request.url:
        print("Login Success for AdmiN (Case insensitivity check)")
    else:
        print(f"Login Failure for AdmiN. URL: {res.request.url}")
