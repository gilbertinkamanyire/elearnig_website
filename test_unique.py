import requests

# Assuming the server is running on localhost:5000
BASE_URL = "http://127.0.0.1:5000"

def test_routes():
    session = requests.Session()
    
    # 1. Login
    print("Logging in...")
    login_data = {
        "username": "wabulejo",
        "password": "student123"
    }
    r = session.post(f"{BASE_URL}/login", data=login_data)
    if r.status_code != 200 and r.url == f"{BASE_URL}/login":
        print("Login failed!")
        return

    # 2. Test Cognitive Mirror
    print("Testing Cognitive Mirror...")
    r = session.get(f"{BASE_URL}/cognitive-mirror")
    print(f"Mirror Status: {r.status_code}")
    if "The Cognitive Mirror" in r.text:
        print("Mirror Page Load: Success")
    else:
        print("Mirror Page Load: Failed (Text not found)")

    # 3. Test Synergy Connect
    print("Testing Synergy Connect...")
    r = session.get(f"{BASE_URL}/synergy-connect")
    print(f"Synergy Status: {r.status_code}")
    if "Synergy Connect" in r.text:
        print("Synergy Page Load: Success")
    else:
        print("Synergy Page Load: Failed (Text not found)")

if __name__ == "__main__":
    test_routes()
