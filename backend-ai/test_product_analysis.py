"""
Test product analysis with source_url preservation.
"""
import requests
import json

def test_product_analysis():
    """Test product analysis with source_url."""
    
    print("Testing product analysis with source_url...")
    analyze_url = "http://localhost:8001/product/analyze"
    
    analyze_payload = {
        "brand": "CeraVe",
        "product_name": "Hydrating Facial Cleanser",
        "source_url": "https://www.cerave.com/skincare/cleansers/hydrating-facial-cleanser"
    }
    
    try:
        response = requests.post(analyze_url, json=analyze_payload, timeout=120)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            
            if data.get('product'):
                product = data['product']
                print(f"Product ID: {product.get('product_id')}")
                print(f"Brand: {product.get('brand')}")
                print(f"Product Name: {product.get('product_name')}")
                print(f"Category: {product.get('category')}")
                print(f"Has normalized_ingredients: {bool(product.get('normalized_ingredients'))}")
                print(f"Has full_ingredient_list: {bool(product.get('full_ingredient_list'))}")
                
                if product.get('normalized_ingredients'):
                    ingredients = product.get('normalized_ingredients', '').split('|')
                    print(f"Ingredient count: {len(ingredients)}")
                    print(f"First few ingredients: {ingredients[:3]}")
                
                print(f"Database reuse stats: {data.get('database_reuse_stats')}")
                return True
            else:
                print("No product data returned")
                return False
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    test_product_analysis()
