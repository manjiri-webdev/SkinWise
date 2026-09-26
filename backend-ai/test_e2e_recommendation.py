"""
Test end-to-end recommendation flow with real user.
"""
import requests
import json

def test_e2e_recommendation():
    """Test the complete recommendation flow."""
    
    print("Testing end-to-end recommendation flow...")
    
    # First test personalization/analyze endpoint
    analyze_url = "http://localhost:8000/personalization/analyze"
    
    try:
        print("Calling personalization/analyze endpoint...")
        response = requests.post(analyze_url, json={}, timeout=120)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            
            if data.get('recommendations'):
                recommendations = data['recommendations']
                print(f"Recommendations keys: {list(recommendations.keys())}")
                
                for step, recs in recommendations.items():
                    print(f"\nStep: {step}")
                    print(f"Number of recommendations: {len(recs)}")
                    if recs:
                        first_rec = recs[0]
                        print(f"First recommendation: {first_rec.get('brand')} - {first_rec.get('product_name')}")
                        print(f"Product ID: {first_rec.get('product_id')}")
                        print(f"Evaluation: {first_rec.get('evaluation')}")
                
                return True
            else:
                print("No recommendations returned")
                print(f"Missing steps: {data.get('missing_steps')}")
                return False
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    test_e2e_recommendation()
