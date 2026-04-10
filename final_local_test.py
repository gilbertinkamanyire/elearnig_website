"""Comprehensive route test — verifies all pages load without 500 errors."""
import sys

def run_tests():
    from app import app
    
    errors = []
    tested = 0
    
    # Public routes (no login needed)
    public_routes = [
        ('GET', '/'),
        ('GET', '/login'),
        ('GET', '/register'),
        ('GET', '/forgot-password'),
        ('GET', '/courses'),
        ('GET', '/help'),
        ('GET', '/about'),
        ('GET', '/terms'),
        ('GET', '/privacy'),
        ('GET', '/how-it-works'),
        ('GET', '/manifest.json'),
        ('GET', '/sw.js'),
    ]
    
    with app.test_client() as client:
        print("=" * 60)
        print("TESTING PUBLIC ROUTES")
        print("=" * 60)
        
        for method, path in public_routes:
            tested += 1
            resp = client.get(path) if method == 'GET' else client.post(path)
            status = resp.status_code
            ok = status < 500
            symbol = "[OK]" if ok else "[FAIL]"
            print(f"  {symbol} {method:4s} {path:45s} -> {status}")
            if not ok:
                errors.append(f"{method} {path} -> {status}")
        
        # Login as admin
        print("\n" + "=" * 60)
        print("LOGGING IN AS ADMIN")
        print("=" * 60)
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=False)
        print(f"  Login response: {resp.status_code}")
        
        # Authenticated routes (admin role)
        auth_routes = [
            ('GET', '/dashboard'),
            ('GET', '/profile'),
            ('GET', '/settings'),
            ('GET', '/grades'),
            ('GET', '/notifications'),
            ('GET', '/admin/users'),
            ('GET', '/admin/departments'),
            ('GET', '/admin/announcements'),
            ('GET', '/admin/analytics'),
            ('GET', '/cognitive-mirror'),
            ('GET', '/synergy-connect'),
        ]
        
        print("\n" + "=" * 60)
        print("TESTING AUTHENTICATED ROUTES (admin)")
        print("=" * 60)
        
        for method, path in auth_routes:
            tested += 1
            resp = client.get(path) if method == 'GET' else client.post(path)
            status = resp.status_code
            ok = status < 500
            symbol = "[OK]" if ok else "[FAIL]"
            print(f"  {symbol} {method:4s} {path:45s} -> {status}")
            if not ok:
                errors.append(f"{method} {path} -> {status}")
        
        # POST routes (toggle actions)
        print("\n" + "=" * 60)
        print("TESTING POST ROUTES")
        print("=" * 60)
        
        post_routes = [
            ('/toggle-theme', {}),
            ('/toggle-bandwidth', {'mode': 'low'}),
            ('/toggle-language', {'language': 'lg'}),
        ]
        
        for path, data in post_routes:
            tested += 1
            resp = client.post(path, data=data, follow_redirects=False)
            status = resp.status_code
            ok = status < 500
            symbol = "[OK]" if ok else "[FAIL]"
            print(f"  {symbol} POST {path:45s} -> {status}")
            if not ok:
                errors.append(f"POST {path} -> {status}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {tested} routes tested, {len(errors)} errors")
    print("=" * 60)
    
    if errors:
        print("\nFAILED ROUTES:")
        for e in errors:
            print(f"  [FAIL] {e}")
        return 1
    else:
        print("\n[OK] ALL ROUTES PASSED!")
        return 0

if __name__ == '__main__':
    sys.exit(run_tests())
