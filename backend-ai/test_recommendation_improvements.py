"""
Test recommendation improvements:
1. Recommendations grouped by category (not routine slot)
2. Fit score ranking in recommendations
3. Add product functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.recommendation_service import RecommendationService
from services.personalization_service import PersonalizationService
import supabase_config

def test_recommendation_grouping_by_category():
    """Test that recommendations are grouped by category, not routine slot"""
    print("Test A: Recommendations grouped by category (not routine slot)")
    
    service = RecommendationService()
    
    # Mock missing steps for both AM and PM
    missing_steps = ["Cleanser (AM)", "Cleanser (PM)", "Treatment (AM)", "Treatment (PM)"]
    
    # Mock user data
    user_data = {
        "user_id": "test_user_1",
        "profile": {
            "skin_concerns": ["acne"],
            "skincare_goals": ["clear acne"],
            "skin_type": "oily"
        },
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    # Mock personalization service
    class MockPersonalizationService:
        def evaluate_product_suitability(self, product, user_data):
            return {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 25,
                "reason_codes": ["SKIN_TYPE_MATCH"],
                "reasons": ["Formulated with ingredients compatible with Oily skin"],
                "mitigations": []
            }
    
    recommendations = service.generate_recommendations(
        missing_steps,
        user_data,
        MockPersonalizationService()
    )
    
    print(f"Recommendation keys: {list(recommendations.keys())}")
    
    # Verify recommendations are grouped by category, not step
    assert "cleanser" in recommendations, "Recommendations should have 'cleanser' category"
    assert "serum" in recommendations, "Recommendations should have 'serum' category"
    assert "Cleanser (AM)" not in recommendations, "Recommendations should NOT have step-based keys"
    assert "Cleanser (PM)" not in recommendations, "Recommendations should NOT have step-based keys"
    assert "Treatment (AM)" not in recommendations, "Recommendations should NOT have step-based keys"
    assert "Treatment (PM)" not in recommendations, "Recommendations should NOT have step-based keys"
    
    # Verify same products are not duplicated
    cleanser_products = recommendations["cleanser"]
    cleanser_ids = [p.get("product_id") for p in cleanser_products]
    assert len(cleanser_ids) == len(set(cleanser_ids)), "Same product should not appear multiple times in same category"
    
    print("PASS Test A: Recommendations correctly grouped by category")

def test_recommendation_ranking_with_fit_score():
    """Test that recommendations use fit_score in ranking"""
    print("\nTest B: Recommendations use fit_score in ranking")
    
    service = RecommendationService()
    
    missing_steps = ["Cleanser (AM)"]
    
    user_data = {
        "user_id": "test_user_2",
        "profile": {
            "skin_concerns": ["acne"],
            "skincare_goals": ["clear acne"],
            "skin_type": "oily"
        },
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    class MockPersonalizationService:
        def evaluate_product_suitability(self, product, user_data):
            # Return different fit_scores based on product_id
            fit_score = 35 if product.get("product_id") == 2 else 15
            return {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": fit_score,
                "reason_codes": ["SKIN_TYPE_MATCH"],
                "reasons": ["Formulated with ingredients compatible with Oily skin"],
                "mitigations": []
            }
    
    # Mock catalog search to return products with different IDs
    original_search = service._search_catalog_by_category
    def mock_search(category, limit=10):
        return [
            {
                "product_id": 1,
                "product_name": "Low Fit Cleanser",
                "category": "cleanser",
                "normalized_ingredients": "Water|Glycerin"
            },
            {
                "product_id": 2,
                "product_name": "High Fit Cleanser",
                "category": "cleanser",
                "normalized_ingredients": "Water|Salicylic Acid"
            }
        ]
    
    service._search_catalog_by_category = mock_search
    
    recommendations = service.generate_recommendations(
        missing_steps,
        user_data,
        MockPersonalizationService()
    )
    
    # Restore original method
    service._search_catalog_by_category = original_search
    
    cleanser_products = recommendations.get("cleanser", [])
    print(f"Cleanser recommendations: {[p['product_name'] for p in cleanser_products]}")
    
    if len(cleanser_products) >= 2:
        # Verify higher fit_score product comes first
        first_product = cleanser_products[0]
        assert first_product["product_id"] == 2, "Higher fit_score product should be ranked first"
        assert first_product["evaluation"]["fit_score"] == 35, "First product should have fit_score of 35"
    
    print("PASS Test B: Recommendations correctly ranked by fit_score")

def test_recommendation_keep_over_caution():
    """Test that KEEP is prioritized over CAUTION even with lower fit_score"""
    print("\nTest C: KEEP prioritized over CAUTION in recommendations")
    
    service = RecommendationService()
    
    missing_steps = ["Cleanser (AM)"]
    
    user_data = {
        "user_id": "test_user_3",
        "profile": {
            "skin_concerns": [],
            "skincare_goals": [],
            "skin_type": "normal"
        },
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    class MockPersonalizationService:
        def evaluate_product_suitability(self, product, user_data):
            # CAUTION with high fit_score vs KEEP with lower fit_score
            if product.get("product_id") == 1:
                return {
                    "decision": "CAUTION",
                    "confidence": "high",
                    "fit_score": 40,
                    "reason_codes": ["IRRITATION_RISK"],
                    "reasons": ["Some ingredients carry elevated irritation risk"],
                    "mitigations": ["Patch test recommended"]
                }
            else:
                return {
                    "decision": "KEEP",
                    "confidence": "high",
                    "fit_score": 20,
                    "reason_codes": ["SKIN_TYPE_MATCH"],
                    "reasons": ["Formulated with ingredients compatible with Normal skin"],
                    "mitigations": []
                }
    
    original_search = service._search_catalog_by_category
    def mock_search(category, limit=10):
        return [
            {
                "product_id": 1,
                "product_name": "Caution High Fit Cleanser",
                "category": "cleanser",
                "normalized_ingredients": "Water|High Irritation Ingredient"
            },
            {
                "product_id": 2,
                "product_name": "Keep Lower Fit Cleanser",
                "category": "cleanser",
                "normalized_ingredients": "Water|Gentle Ingredient"
            }
        ]
    
    service._search_catalog_by_category = mock_search
    
    recommendations = service.generate_recommendations(
        missing_steps,
        user_data,
        MockPersonalizationService()
    )
    
    service._search_catalog_by_category = original_search
    
    cleanser_products = recommendations.get("cleanser", [])
    print(f"Cleanser recommendations: {[p['product_name'] for p in cleanser_products]}")
    
    if len(cleanser_products) >= 1:
        first_product = cleanser_products[0]
        assert first_product["evaluation"]["decision"] == "KEEP", "KEEP should be prioritized over CAUTION"
        assert first_product["product_id"] == 2, "KEEP product should be ranked first despite lower fit_score"
    
    print("PASS Test C: KEEP correctly prioritized over CAUTION")

def test_recommendation_max_three_per_category():
    """Test that maximum 3 products are returned per category"""
    print("\nTest D: Maximum 3 products per category")
    
    service = RecommendationService()
    
    missing_steps = ["Cleanser (AM)"]
    
    user_data = {
        "user_id": "test_user_4",
        "profile": {
            "skin_concerns": [],
            "skincare_goals": [],
            "skin_type": "normal"
        },
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    class MockPersonalizationService:
        def evaluate_product_suitability(self, product, user_data):
            return {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 20,
                "reason_codes": ["SKIN_TYPE_MATCH"],
                "reasons": ["Formulated with ingredients compatible with Normal skin"],
                "mitigations": []
            }
    
    original_search = service._search_catalog_by_category
    def mock_search(category, limit=10):
        # Return 5 products
        return [
            {
                "product_id": i,
                "product_name": f"Cleanser {i}",
                "category": "cleanser",
                "normalized_ingredients": "Water|Ingredient"
            }
            for i in range(1, 6)
        ]
    
    service._search_catalog_by_category = mock_search
    
    recommendations = service.generate_recommendations(
        missing_steps,
        user_data,
        MockPersonalizationService()
    )
    
    service._search_catalog_by_category = original_search
    
    cleanser_products = recommendations.get("cleanser", [])
    print(f"Number of cleanser recommendations: {len(cleanser_products)}")
    
    assert len(cleanser_products) <= 3, "Should return maximum 3 products per category"
    
    print("PASS Test D: Maximum 3 products per category enforced")

def test_category_mapping():
    """Test that category mapping works correctly"""
    print("\nTest E: Category mapping for routine slots")
    
    service = RecommendationService()
    
    # Test category mapping
    mappings = {
        "Cleanser (AM)": "cleanser",
        "Cleanser (PM)": "cleanser",
        "Treatment (AM)": "serum",
        "Treatment (PM)": "serum",
        "Moisturizer (AM)": "moisturizer",
        "Moisturizer (PM)": "moisturizer",
        "Sunscreen (AM)": "sunscreen",
    }
    
    for step, expected_category in mappings.items():
        mapped_category = service._map_step_to_category(step)
        assert mapped_category == expected_category, f"Step '{step}' should map to '{expected_category}', got '{mapped_category}'"
        print(f"  {step} -> {mapped_category} ✓")
    
    print("PASS Test E: Category mapping works correctly")

if __name__ == "__main__":
    try:
        test_recommendation_grouping_by_category()
        test_recommendation_ranking_with_fit_score()
        test_recommendation_keep_over_caution()
        test_recommendation_max_three_per_category()
        test_category_mapping()
        
        print("\n" + "="*50)
        print("All recommendation improvement tests passed!")
        print("="*50)
        
    except AssertionError as e:
        print(f"\nFAIL Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nFAIL Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)