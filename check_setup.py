import requests

url = "https://elearnig-website.vercel.app/setup-admin"
try:
    resp = requests.get(url)
    print(f"Status Code: {resp.status_code}")
    print("Response Text:")
    print(resp.text[:1000])
except Exception as e:
    print(f"Error checking {url}: {e}")
