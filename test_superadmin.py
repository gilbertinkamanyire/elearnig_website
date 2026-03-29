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
        print(f"Login SUCCESS! Admin dashboard reached successfully with {username} / {password}!")
    else:
        print(f"Login FAILED for {username}. Checking if error is visible:")
        if "alert" in resp.text.lower():
            print("Alert found on page.")
        print(resp.text[:500])

if __name__ == "__main__":
    test_login("superadmin", "SuperPassword123")
