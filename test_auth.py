import requests
import json

print("Testing Stdytime licensing flow...")

# Test 1: Check license page loads
print("\n[Test 1] GET /license")
response = requests.get('http://localhost:5000/license')
print(f"  Status: {response.status_code} - {'✓ OK' if response.status_code == 200 else '✗ Failed'}")
if "License" in response.text:
    print("  ✓ License page loaded")

# Test 2: Legacy auth should redirect to licensing
print("\n[Test 2] GET /auth/login redirects to /license")
response = requests.get('http://localhost:5000/auth/login', allow_redirects=False)
print(f"  Status: {response.status_code}")
if response.status_code in (301, 302, 303, 307, 308):
    print(f"  ✓ Redirect to: {response.headers.get('Location')}")

# Test 3: App root should redirect to licensing when not activated
print("\n[Test 3] GET / redirects to licensing or expired page when no valid license exists")
response = requests.get('http://localhost:5000/', allow_redirects=False)
print(f"  Status: {response.status_code}")
if response.status_code in (301, 302, 303, 307, 308):
    print(f"  ✓ Redirect to: {response.headers.get('Location')}")

print("\n✓ All tests completed!")
