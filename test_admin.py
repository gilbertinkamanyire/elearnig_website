import requests
import sys

base_url = "https://elearnig-website.vercel.app"

def test_login(username, password):
    session = requests.Session()
    login_url = f"{base_url}/login"
    login_data = {
        'username': username,
        'password': password
    }
    
    resp = session.post(login_url, data=login_data, allow_redirects=True)
    if "Dashboard" in resp.text or 'id="logout"' in resp.text:
        print(f"Login SUCCESS for {username} / {password}")
    else:
        print(f"Login FAILED for {username} / {password}")

if __name__ == "__main__":
    test_login("admin", "admin123")
    test_login("admin_user", "AdminPassword123")
