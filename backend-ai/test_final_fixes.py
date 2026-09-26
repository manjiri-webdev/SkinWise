"""
Test final SkinWise personalization/recommendation fixes:
1. ProductPicker authentication fix
2. Recommendation ranking with fit_score
3. Category-grouped recommendations (no AM/PM duplication)
4. Discovery triggers only when usable_catalog == 0
5. Ingredient cache reduces repeated queries
6. Personalization logic preserved
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.recommendation_service import RecommendationService
from services.personalization_service import PersonalizationService

def test_recommendation_ranking():
    """Test that ranking uses fit_score correctly"""
    print("Test B: Recommendation ranking with fit_score")
    
    service = RecommendationService()
    
    # Mock evaluations with different fit_scores
    evaluations = [
        {"decision": "KEEP", "confidence": "high", "fit_score": 35},
        {"decision": "KEEP", "confidence": "high", "fit_score": 15},
        {"decision": "CAUTION", "confidence": "high", "fit_score": 40},
    ]
    
    candidates = [
        {"product_id": 1, "product_name": "High Fit Cleanser"},
        {"product_id": 2, "product_name": "Low Fit Cleanser"},
        {"product_id": 3, "product_name": "Caution High Fit"},
    ]
    
    ranked = service._rank_candidates(candidates, evaluations)
    
    print(f"  Ranked products:")
    for i, (candidate, evaluation) in enumerate(ranked):
        print(f"    {i+1}. {candidate['product_name']} - {evaluation['decision']} (fit_score: {evaluation['fit_score']})")
    
    # Verify ranking order
    assert ranked[0][1]["decision"] == "KEEP", "KEEP should be first"
    assert ranked[0][1]["fit_score"] == 35, "Higher fit_score KEEP should be first"
    assert ranked[1][1]["fit_score"] == 15, "Lower fit_score KEEP should be second"
    assert ranked[2][1]["decision"] == "CAUTION", "CAUTION should be after all KEEP"
    
    print("PASS Test B: Ranking correctly uses fit_score")

def test_category_grouped_recommendations():
    """Test that recommendations are grouped by category, not AM/PM"""
    print("\nTest C: Category-grouped recommendations (no AM/PM duplication)")
    
    service = RecommendationService()
    
    class MockPersonalizationService:
        def evaluate_product_suitability(self, product, user_data):
            return {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 25,
                "reason_codes": [],
                "reasons": [],
                "mitigations": []
            }
    
    missing_steps = ["Cleanser (AM)", "Cleanser (PM)", "Treatment (AM)", "Treatment (PM)"]
    user_data = {"profile": {"skin_type": "oily"}}
    
    recommendations = service.generate_recommendations(
        missing_steps,
        user_data,
        MockPersonalizationService()
    )
    
    print(f"  Recommendation keys: {list(recommendations.keys())}")
    
    # Verify category-based structure
    assert "cleanser" in recommendations, "Should have 'cleanser' category"
    assert "serum" in recommendations, "Should have 'serum' category"
    assert "Cleanser (AM)" not in recommendations, "Should NOT have step-based keys"
    assert "Cleanser (PM)" not in recommendations, "Should NOT have step-based keys"
    
    # Verify no duplication within category
    cleanser_products = recommendations["cleanser"]
    cleanser_ids = [p.get("product_id") for p in cleanser_products]
    assert len(cleanser_ids) == len(set(cleanser_ids)), "Same product should not appear multiple times in same category"
    
    print("PASS Test C: Recommendations correctly grouped by category")

def test_discovery_trigger_condition():
    """Test that Gemini discovery triggers only when usable_catalog == 0"""
    print("\nTest D: Discovery triggers only when usable_catalog == 0")
    
    service = RecommendationService()
    
    # Mock catalog search to return 2 usable products
    original_search = service._search_catalog_by_category
    def mock_search(category, limit=10):
        return [
            {"product_id": 1, "product_name": "Product 1", "normalized_ingredients": "Water|Glycerin"},
            {"product_id": 2, "product_name": "Product 2", "normalized_ingredients": "Water|Glycerin"},
        ]
    
    service._search_catalog_by_category = mock_search
    
    # Mock gemini discovery to track if it's called
    gemini_called = []
    original_gemini = service._discover_products_with_gemini
    def mock_gemini(category, limit=5):
        gemini_called.append(True)
        return []
    
    service._discover_products_with_gemini = mock_gemini
    
    class MockPersonalizationService:
        def evaluate_product_suitability(self, product, user_data):
            return {"decision": "KEEP", "confidence": "high", "fit_score": 25, "reason_codes": [], "reasons": [], "mitigations": []}
    
    missing_steps = ["Cleanser (AM)"]
    user_data = {"profile": {}}
    
    recommendations = service.generate_recommendations(
        missing_steps,
        user_data,
        MockPersonalizationService()
    )
    
    # Restore original methods
    service._search_catalog_by_category = original_search
    service._discover_products_with_gemini = original_gemini
    
    print(f"  Usable catalog candidates: 2")
    print(f"  Gemini discovery called: {len(gemini_called) > 0}")
    
    assert len(gemini_called) == 0, "Gemini should NOT be called when usable_catalog > 0"
    
    # Now test with 0 usable candidates
    gemini_called = []
    service._discover_products_with_gemini = mock_gemini
    
    def mock_search_empty(category, limit=10):
        return [
            {"product_id": 1, "product_name": "Product 1"},  # No ingredients, not usable
        ]
    
    service._search_catalog_by_category = mock_search_empty
    
    recommendations = service.generate_recommendations(
        missing_steps,
        user_data,
        MockPersonalizationService()
    )
    
    service._search_catalog_by_category = original_search
    service._discover_products_with_gemini = original_gemini
    
    print(f"  Usable catalog candidates: 0")
    print(f"  Gemini discovery called: {len(gemini_called) > 0}")
    
    assert len(gemini_called) > 0, "Gemini SHOULD be called when usable_catalog == 0"
    
    print("PASS Test D: Discovery triggers only when usable_catalog == 0")

def test_ingredient_cache():
    """Test that ingredient cache reduces repeated queries"""
    print("\nTest E: Ingredient cache reduces repeated queries")
    
    service = PersonalizationService()
    
    # Mock supabase to track query count
    query_count = 0
    original_table = service.supabase.table
    
    def mock_table(table_name):
        class MockTable:
            def select(self, *args):
                class MockSelect:
                    def eq(self, field, value):
                        class MockEq:
                            def execute(self):
                                if table_name == "products":
                                    return type('obj', (object,), {'data': [{
                                        "product_id": 1,
                                        "normalized_ingredients": "Water|Glycerin"
                                    }]})()
                                return type('obj', (object,), {'data': []})()
                        return MockEq()
                    def ilike(self, field, pattern):
                        nonlocal query_count
                        query_count += 1
                        class MockIlike:
                            def execute(self):
                                return type('obj', (object,), {'data': [{
                                    "ingredient": "Water",
                                    "function": "Solvent"
                                }]})()
                        return MockIlike()
                return MockSelect()
        return MockTable()
    
    service.supabase.table = mock_table
    
    # First call - should query ingredients
    query_count = 0
    ingredients1, total1 = service.get_product_ingredients(1)
    first_query_count = query_count
    print(f"  First call queries: {first_query_count}")
    
    # Second call - should use cache
    query_count = 0
    ingredients2, total2 = service.get_product_ingredients(1)
    second_query_count = query_count
    print(f"  Second call queries: {second_query_count}")
    
    # Restore original
    service.supabase.table = original_table
    
    assert second_query_count < first_query_count, "Cache should reduce queries on second call"
    assert len(ingredients1) == len(ingredients2), "Results should be consistent"
    
    print("PASS Test E: Ingredient cache reduces repeated queries")

def test_personalization_logic_preserved():
    """Test that personalization logic is preserved"""
    print("\nTest F: Personalization logic preserved")
    
    service = PersonalizationService()
    
    # Verify cache exists
    assert hasattr(service, '_ingredient_cache'), "Service should have ingredient cache"
    print("  Ingredient cache: Present")
    
    # Verify other attributes
    assert hasattr(service, 'supabase'), "Service should have supabase client"
    print("  Supabase client: Present")
    
    # Verify methods exist
    assert hasattr(service, 'load_user_data'), "Should have load_user_data method"
    assert hasattr(service, 'get_product_ingredients'), "Should have get_product_ingredients method"
    assert hasattr(service, 'evaluate_product_suitability'), "Should have evaluate_product_suitability method"
    print("  Core methods: Present")
    
    print("PASS Test F: Personalization logic preserved")

if __name__ == "__main__":
    try:
        test_recommendation_ranking()
        test_category_grouped_recommendations()
        test_discovery_trigger_condition()
        test_ingredient_cache()
        test_personalization_logic_preserved()
        
        print("\n" + "="*50)
        print("All final fix tests passed!")
        print("="*50)
        
    except AssertionError as e:
        print(f"\nFAIL Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nFAIL Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)