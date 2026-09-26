import requests
import json

url = "http://localhost:8000/product/discover"

print("Testing deduplication with Dot & Key + Watermelon Sunscreen")
print("="*60)

data = {
    "product_name": "Watermelon Sunscreen",
    "brand": "Dot & Key"
}

try:
    response = requests.post(url, json=data, timeout=60)
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Success: {result['success']}")
    print(f"Count: {result['count']}")
    print(f"Query: {result['query']}")
    print(f"\nFull Response:")
    print(json.dumps(result, indent=2))
    
    # Check for duplicates
    product_names = [opt['product_name'] for opt in result['options']]
    print(f"\nProduct names: {product_names}")
    print(f"Unique products: {len(set(product_names))}")
    
except Exception as e:
    print(f"Error: {e}")
