"""
Test personalization improvements:
1. Missing routine steps (Treatment/Serum, Moisturizer)
2. Fit score based product selection
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.personalization_service import PersonalizationService
import supabase_config

def test_missing_steps_with_concerns():
    """Test that users with relevant concerns get Treatment in missing_steps"""
    print("Test A: User with acne concerns gets Treatment (AM/PM) in missing_steps")
    
    service = PersonalizationService()
    
    # Mock user data with acne concerns
    user_data = {
        "user_id": "test_user_1",
        "profile": {
            "skin_concerns": ["acne", "dryness"],
            "skincare_goals": ["clear acne"],
            "skin_type": "oily"
        },
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    # Mock evaluated products - no treatment products, but include sunscreen
    evaluated_products = [
        {
            "product_id": 1,
            "product_name": "Test Cleanser",
            "product_type": "cleanser",
            "category": "cleanser",
            "evaluation": {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 25,
                "reason_codes": ["SKIN_TYPE_MATCH"],
                "reasons": ["Formulated with ingredients compatible with Oily skin"],
                "mitigations": []
            },
            "_resolved_ingredients": []
        },
        {
            "product_id": 2,
            "product_name": "Test Moisturizer",
            "product_type": "moisturizer",
            "category": "moisturizer",
            "evaluation": {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 20,
                "reason_codes": ["SKIN_TYPE_MATCH"],
                "reasons": ["Formulated with ingredients compatible with Oily skin"],
                "mitigations": []
            },
            "_resolved_ingredients": []
        },
        {
            "product_id": 3,
            "product_name": "Test Sunscreen",
            "product_type": "sunscreen",
            "category": "sunscreen",
            "evaluation": {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 15,
                "reason_codes": [],
                "reasons": ["Product formulation is compatible with your skin profile"],
                "mitigations": []
            },
            "_resolved_ingredients": []
        }
    ]
    
    am_routine = service.build_am_routine(evaluated_products, user_data)
    pm_routine = service.build_pm_routine(evaluated_products, user_data)
    
    print(f"AM missing_steps: {am_routine['missing_steps']}")
    print(f"PM missing_steps: {pm_routine['missing_steps']}")
    
    # Verify Treatment is in missing_steps for both AM and PM
    assert "Treatment (AM)" in am_routine['missing_steps'], f"Treatment (AM) should be in missing_steps for user with acne concerns. Got: {am_routine['missing_steps']}"
    assert "Treatment (PM)" in pm_routine['missing_steps'], f"Treatment (PM) should be in missing_steps for user with acne concerns. Got: {pm_routine['missing_steps']}"
    # Note: Sunscreen (AM) will also be in missing_steps since we don't have a sunscreen product
    
    print("PASS Test A: Treatment (AM/PM) correctly added to missing_steps for user with acne concerns")

def test_missing_steps_without_concerns():
    """Test that users without relevant concerns do NOT get Treatment in missing_steps"""
    print("\nTest B: User without treatment-relevant concerns does NOT get Treatment in missing_steps")
    
    service = PersonalizationService()
    
    # Mock user data without treatment-relevant concerns
    user_data = {
        "user_id": "test_user_2",
        "profile": {
            "skin_concerns": ["dryness"],  # Only dryness, not treatment-relevant
            "skincare_goals": ["hydrate skin"],  # Only hydration, not treatment-relevant
            "skin_type": "dry"
        },
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    # Same evaluated products - no treatment products
    evaluated_products = [
        {
            "product_id": 1,
            "product_name": "Test Cleanser",
            "product_type": "cleanser",
            "category": "cleanser",
            "evaluation": {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 25,
                "reason_codes": ["SKIN_TYPE_MATCH"],
                "reasons": ["Formulated with ingredients compatible with Dry skin"],
                "mitigations": []
            },
            "_resolved_ingredients": []
        }
    ]
    
    am_routine = service.build_am_routine(evaluated_products, user_data)
    pm_routine = service.build_pm_routine(evaluated_products, user_data)
    
    print(f"AM missing_steps: {am_routine['missing_steps']}")
    print(f"PM missing_steps: {pm_routine['missing_steps']}")
    
    # Verify Treatment is NOT in missing_steps
    assert "Treatment (AM)" not in am_routine['missing_steps'], "Treatment (AM) should NOT be in missing_steps for user without treatment-relevant concerns"
    assert "Treatment (PM)" not in pm_routine['missing_steps'], "Treatment (PM) should NOT be in missing_steps for user without treatment-relevant concerns"
    
    print("PASS Test B: Treatment correctly NOT added to missing_steps for user without treatment-relevant concerns")

def test_moisturizer_missing_steps():
    """Test that missing moisturizer is detected in both AM and PM"""
    print("\nTest C: User missing moisturizer gets Moisturizer (AM/PM) in missing_steps")
    
    service = PersonalizationService()
    
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
    
    # Only cleanser, no moisturizer
    evaluated_products = [
        {
            "product_id": 1,
            "product_name": "Test Cleanser",
            "product_type": "cleanser",
            "category": "cleanser",
            "evaluation": {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 25,
                "reason_codes": ["SKIN_TYPE_MATCH"],
                "reasons": ["Formulated with ingredients compatible with Normal skin"],
                "mitigations": []
            },
            "_resolved_ingredients": []
        }
    ]
    
    am_routine = service.build_am_routine(evaluated_products, user_data)
    pm_routine = service.build_pm_routine(evaluated_products, user_data)
    
    print(f"AM missing_steps: {am_routine['missing_steps']}")
    print(f"PM missing_steps: {pm_routine['missing_steps']}")
    
    # Verify Moisturizer is in missing_steps for both AM and PM
    assert "Moisturizer (AM)" in am_routine['missing_steps'], "Moisturizer (AM) should be in missing_steps"
    assert "Moisturizer (PM)" in pm_routine['missing_steps'], "Moisturizer (PM) should be in missing_steps"
    
    print("PASS Test C: Moisturizer (AM/PM) correctly added to missing_steps")

def test_fit_score_product_selection():
    """Test that products with higher fit_score are selected over lower fit_score"""
    print("\nTest D: Product with higher fit_score is selected over lower fit_score")
    
    service = PersonalizationService()
    
    user_data = {
        "user_id": "test_user_4",
        "profile": {
            "skin_concerns": ["acne"],
            "skincare_goals": ["clear acne"],
            "skin_type": "oily"
        },
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    # Two cleansers with different fit_scores
    evaluated_products = [
        {
            "product_id": 1,
            "product_name": "Low Fit Cleanser",
            "product_type": "cleanser",
            "category": "cleanser",
            "evaluation": {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 10,  # Lower fit_score
                "reason_codes": ["SKIN_TYPE_MATCH"],
                "reasons": ["Formulated with ingredients compatible with Oily skin"],
                "mitigations": []
            },
            "_resolved_ingredients": []
        },
        {
            "product_id": 2,
            "product_name": "High Fit Cleanser",
            "product_type": "cleanser",
            "category": "cleanser",
            "evaluation": {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 35,  # Higher fit_score
                "reason_codes": ["SKIN_TYPE_MATCH", "CONCERN_MATCH"],
                "reasons": ["Formulated with ingredients compatible with Oily skin", "Active ingredients target concerns: acne"],
                "mitigations": []
            },
            "_resolved_ingredients": []
        }
    ]
    
    am_routine = service.build_am_routine(evaluated_products, user_data)
    
    selected_cleanser = am_routine['slots']['cleanser']
    print(f"Selected cleanser: {selected_cleanser['product_name']} with fit_score: {selected_cleanser['evaluation']['fit_score']}")
    
    # Verify the higher fit_score product is selected
    assert selected_cleanser['product_id'] == 2, "Higher fit_score product should be selected"
    assert selected_cleanser['evaluation']['fit_score'] == 35, "Selected product should have fit_score of 35"
    
    print("PASS Test D: Product with higher fit_score (35) correctly selected over lower fit_score (10)")

def test_keep_over_caution_with_fit_score():
    """Test that KEEP is prioritized over CAUTION even when CAUTION has higher fit_score"""
    print("\nTest E: KEEP prioritized over CAUTION regardless of fit_score")
    
    service = PersonalizationService()
    
    user_data = {
        "user_id": "test_user_5",
        "profile": {
            "skin_concerns": [],
            "skincare_goals": [],
            "skin_type": "normal"
        },
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    # CAUTION product with high fit_score vs KEEP product with lower fit_score
    evaluated_products = [
        {
            "product_id": 1,
            "product_name": "Caution High Fit Cleanser",
            "product_type": "cleanser",
            "category": "cleanser",
            "evaluation": {
                "decision": "CAUTION",
                "confidence": "high",
                "fit_score": 40,  # High fit_score but CAUTION
                "reason_codes": ["IRRITATION_RISK"],
                "reasons": ["Some ingredients carry elevated irritation risk"],
                "mitigations": ["Patch test recommended"]
            },
            "_resolved_ingredients": []
        },
        {
            "product_id": 2,
            "product_name": "Keep Lower Fit Cleanser",
            "product_type": "cleanser",
            "category": "cleanser",
            "evaluation": {
                "decision": "KEEP",
                "confidence": "high",
                "fit_score": 20,  # Lower fit_score but KEEP
                "reason_codes": ["SKIN_TYPE_MATCH"],
                "reasons": ["Formulated with ingredients compatible with Normal skin"],
                "mitigations": []
            },
            "_resolved_ingredients": []
        }
    ]
    
    am_routine = service.build_am_routine(evaluated_products, user_data)
    
    selected_cleanser = am_routine['slots']['cleanser']
    print(f"Selected cleanser: {selected_cleanser['product_name']} with decision: {selected_cleanser['evaluation']['decision']}")
    
    # Verify KEEP is selected over CAUTION despite lower fit_score
    assert selected_cleanser['product_id'] == 2, "KEEP product should be selected over CAUTION"
    assert selected_cleanser['evaluation']['decision'] == "KEEP", "Selected product should be KEEP"
    
    print("PASS Test E: KEEP correctly prioritized over CAUTION despite lower fit_score")

def test_fit_score_exposure():
    """Test that fit_score is exposed in evaluation object"""
    print("\nTest F: fit_score is exposed in evaluation object")
    
    service = PersonalizationService()
    
    user_data = {
        "user_id": "test_user_6",
        "profile": {
            "skin_concerns": ["acne"],
            "skincare_goals": [],
            "skin_type": "oily"
        },
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    product = {
        "product_id": 1,
        "product_name": "Test Product",
        "product_type": "cleanser",
        "category": "cleanser"
    }
    
    evaluation = service.evaluate_product_suitability(product, user_data)
    
    print(f"Evaluation keys: {evaluation.keys()}")
    print(f"fit_score value: {evaluation.get('fit_score')}")
    
    # Verify fit_score is in evaluation
    assert "fit_score" in evaluation, "fit_score should be exposed in evaluation"
    assert isinstance(evaluation["fit_score"], int), "fit_score should be an integer"
    
    print("PASS Test F: fit_score correctly exposed in evaluation object")

if __name__ == "__main__":
    try:
        test_missing_steps_with_concerns()
        test_missing_steps_without_concerns()
        test_moisturizer_missing_steps()
        test_fit_score_product_selection()
        test_keep_over_caution_with_fit_score()
        test_fit_score_exposure()
        
        print("\n" + "="*50)
        print("All personalization improvement tests passed!")
        print("="*50)
        
    except AssertionError as e:
        print(f"\nFAIL Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nFAIL Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)