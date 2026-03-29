import requests

import string
import random

def test_auth(base_url):
    print(f"Testing {base_url}...")
    session = requests.Session()
    
    # Generate random username and email
    rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    username = f"test_{rand_str}"
    email = f"{username}@example.com"
    password = "TestPassword123!"
    
    # --- 1. Test Registration ---
    print(f"1. Testing Registration for {username}...")
    reg_url = f"{base_url}/register"
    
    # Sometimes we need a CSRF token. Since this project is lightweight, let's see if it just accepts POST.
    try:
        data = {
            'role': 'student',
            'full_name': 'Test User',
            'username': username,
            'email': email,
            'password': password,
            'confirm_password': password,
            'phone': '+256700123456'
        }
        resp = session.post(reg_url, data=data, allow_redirects=True)
        
        if resp.status_code == 200:
            if "already exists" in resp.text.lower() or "error" in resp.text.lower() or "danger" in resp.text.lower():
                print("Registration failed. See part of response:")
                print(resp.text[:500])
                # Check if it was because we are already logged in or something
            else:
                print("Registration form submitted.")
        else:
            print(f"Registration returned status {resp.status_code}")
            
    except Exception as e:
        print(f"Registration Error: {e}")
        return

    # --- 2. Test Login ---
    print(f"2. Testing Login for {username}...")
    login_url = f"{base_url}/login"
    login_data = {
        'username': username,
        'password': password
    }
    
    try:
        resp = session.post(login_url, data=login_data, allow_redirects=True)
        # Check if we were redirected to dashboard or if dashboard content is present
        if "Dashboard" in resp.text or 'id="logout"' in resp.text or "/logout" in resp.text:
            print("Login successful! Dashboard accessed.")
            print("Signup and Login flows work perfectly.")
        else:
            print(f"Login returned status {resp.status_code}")
            print("Login might have failed.")
            if 'alert' in resp.text:
                print("Found alert message on page!")
            else:
                print(resp.text[:500])
    except Exception as e:
        print(f"Login Error: {e}")

if __name__ == "__main__":
    test_auth("https://elearnig-website.vercel.app")
    print("-------------------------------------------------")
    print("Testing locally just in case deployment hasn't finished...")
    test_auth("http://127.0.0.1:5000")
