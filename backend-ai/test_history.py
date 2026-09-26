import requests
import json
import jwt
import time
from datetime import date

# Test the history endpoints
BASE_URL = "http://localhost:8000"

import os
from dotenv import load_dotenv

load_dotenv()

# Create a mock JWT token for testing
def create_mock_token(user_id="00000000-0000-0000-0000-000000000000"):
    payload = {
        "sub": user_id,
        "iss": "supabase",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "role": "authenticated"
    }
    secret = os.getenv("SUPABASE_JWT_SECRET", "test-secret-mock")
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token

test_token = create_mock_token()

headers = {
    "Authorization": f"Bearer {test_token}",
    "Content-Type": "application/json"
}

print("Testing History Endpoints")
print("=" * 50)

# Test GET /history/products
print("\n1. Testing GET /history/products (get all product history)")
try:
    response = requests.get(f"{BASE_URL}/history/products", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test POST /history/products (add product)
print("\n2. Testing POST /history/products (add product history)")
product_data = {
    "product_name": "Test Moisturizer",
    "product_type": "Moisturizer"
}
created_entry_id = None
try:
    response = requests.post(f"{BASE_URL}/history/products", headers=headers, json=product_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    if response.status_code == 200:
        created_entry_id = response.json()["data"]["id"]
        print(f"Created entry ID: {created_entry_id}")
except Exception as e:
    print(f"Error: {e}")

# Test GET /history/products again to see the new entry
print("\n3. Testing GET /history/products (after adding product)")
try:
    response = requests.get(f"{BASE_URL}/history/products", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test PUT /history/products/{entry_id} (update product)
if created_entry_id:
    print(f"\n4. Testing PUT /history/products/{created_entry_id} (update product history)")
    update_data = {
        "product_name": "Updated Test Moisturizer",
        "product_type": "Moisturizer",
        "ended_at": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    try:
        response = requests.put(f"{BASE_URL}/history/products/{created_entry_id}", headers=headers, json=update_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

# Test GET /history/environment/today
print("\n5. Testing GET /history/environment/today")
try:
    response = requests.get(f"{BASE_URL}/history/environment/today", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test POST /history/environment (add environment data)
print("\n6. Testing POST /history/environment (add environment history)")
today = date.today().isoformat()
env_data = {
    "date": today,
    "temperature": 25.5,
    "humidity": 65,
    "weather": "Sunny",
    "city": "Test City",
    "notes": "Testing environment history"
}
try:
    response = requests.post(f"{BASE_URL}/history/environment", headers=headers, json=env_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test GET /history/environment/today again to see the new entry
print("\n7. Testing GET /history/environment/today (after adding environment data)")
try:
    response = requests.get(f"{BASE_URL}/history/environment/today", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test GET /history/environment (with date range)
print("\n8. Testing GET /history/environment (with date range)")
try:
    response = requests.get(f"{BASE_URL}/history/environment", headers=headers, params={
        "start_date": today,
        "end_date": today
    })
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test DELETE /history/products/{entry_id} (cleanup)
if created_entry_id:
    print(f"\n9. Testing DELETE /history/products/{created_entry_id} (delete product history)")
    try:
        response = requests.delete(f"{BASE_URL}/history/products/{created_entry_id}", headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "=" * 50)
print("Testing complete!")
print("\nNote: These tests use a mock user ID. For production testing,")
print("use a real Supabase JWT token from an authenticated user.")
