import requests
import json

print("Testing Stdytime Authentication...")

# Test 1: Check login page loads
print("\n[Test 1] GET /auth/login")
response = requests.get('http://localhost:5000/auth/login')
print(f"  Status: {response.status_code} - {'✓ OK' if response.status_code == 200 else '✗ Failed'}")
if "Stdytime" in response.text:
    print("  ✓ Login page contains 'Stdytime'")

# Test 2: Try login with correct credentials
print("\n[Test 2] POST /auth/login with correct credentials")
response = requests.post('http://localhost:5000/auth/login', 
    data={'email': 'admin@Stdytime.local', 'password': 'Stdytime@2025'},
    allow_redirects=False
)
print(f"  Status: {response.status_code}")
if response.status_code == 302:
    print(f"  ✓ Redirect to: {response.headers.get('Location')}")
elif response.status_code == 200:
    if "Welcome" in response.text:
        print("  ✓ Login successful - Welcome message found")
    else:
        print("  Response contains:", response.text[:200])

# Test 3: Try with wrong password
print("\n[Test 3] POST /auth/login with WRONG password")
response = requests.post('http://localhost:5000/auth/login', 
    data={'email': 'admin@Stdytime.local', 'password': 'WrongPassword'},
    allow_redirects=False
)
print(f"  Status: {response.status_code}")
if response.status_code == 200 and "Invalid" in response.text:
    print("  ✓ Correctly rejected with 'Invalid' message")

print("\n✓ All tests completed!")
