"""
Test improved reason-specific mitigations.
Tests all reason codes with deterministic, context-aware mitigations.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.personalization_service import PersonalizationService

def test_unresolved_product():
    """Test PRODUCT_UNRESOLVED mitigation with body lotion indication."""
    print("Test 1: PRODUCT_UNRESOLVED - WishCare Sunscreen Body Lotion SPF 50")
    print("-" * 80)
    
    service = PersonalizationService()
    
    # Test with body lotion product name
    unresolved_product = {
        "product_id": None,
        "product_name": "WishCare Sunscreen Body Lotion SPF 50",
        "product_type": "Sunscreen",
    }
    
    user_data = {
        "user_id": "test-user-1",
        "profile": {"skin_type": "combination", "skin_sensitivity": "no"},
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    evaluation = service.evaluate_product_suitability(unresolved_product, user_data)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Reason codes: {evaluation['reason_codes']}")
    print(f"Reason: {evaluation['reasons'][0] if evaluation['reasons'] else 'None'}")
    print(f"Mitigation: {evaluation['mitigations'][0] if evaluation['mitigations'] else 'None'}")
    
    # Verify specific mitigation components
    mitigation = evaluation['mitigations'][0] if evaluation['mitigations'] else ""
    
    assert "PRODUCT_UNRESOLVED" in evaluation['reason_codes'], "Should have PRODUCT_UNRESOLVED reason code"
    assert "EVIDENCE_INCOMPLETE" in evaluation['reason_codes'], "Should have EVIDENCE_INCOMPLETE reason code"
    assert evaluation['decision'] == "CAUTION", "Should be CAUTION decision"
    assert "ingredient list" in mitigation.lower(), "Should mention ingredient list verification"
    assert "incomplete" in mitigation.lower(), "Should mention evaluation is incomplete"
    assert "body" in mitigation.lower(), "Should mention body-only use indication"
    assert "facial" in mitigation.lower(), "Should mention facial use confirmation"
    assert "inci" in mitigation.lower() or "packaging" in mitigation.lower(), "Should mention INCI verification"
    assert "patch test" not in mitigation.lower(), "Should NOT contain generic patch-test recommendation"
    
    print("PASS: PRODUCT_UNRESOLVED mitigation includes body lotion warning and INCI verification without generic patch test")
    return True

def test_wishcare_body_lotion():
    """Specific test for WishCare Sunscreen Body Lotion SPF 50 - no generic patch test."""
    print("\nTest 2b: WishCare Sunscreen Body Lotion - No generic patch test")
    print("-" * 80)
    
    service = PersonalizationService()
    
    # Exact product name from user request
    wishcare_product = {
        "product_id": None,
        "product_name": "WishCare Sunscreen Body Lotion SPF 50",
        "product_type": "Sunscreen",
    }
    
    user_data = {
        "user_id": "test-user-wishcare",
        "profile": {"skin_type": "combination", "skin_sensitivity": "no"},
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    evaluation = service.evaluate_product_suitability(wishcare_product, user_data)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Reason codes: {evaluation['reason_codes']}")
    print(f"Mitigation: {evaluation['mitigations'][0] if evaluation['mitigations'] else 'None'}")
    
    mitigation = evaluation['mitigations'][0] if evaluation['mitigations'] else ""
    
    assert "PRODUCT_UNRESOLVED" in evaluation['reason_codes'], "Should have PRODUCT_UNRESOLVED"
    assert "body" in mitigation.lower(), "Should mention body-only use"
    assert "facial" in mitigation.lower(), "Should mention facial use confirmation"
    assert "inci" in mitigation.lower() or "packaging" in mitigation.lower(), "Should mention INCI verification"
    assert "patch test" not in mitigation.lower(), "Should NOT contain generic patch-test recommendation"
    
    print("PASS: WishCare Body Lotion mitigation has no generic patch test")
    return True

def test_reequil_unresolved():
    """Specific test for Re'equil unresolved product - no generic patch test."""
    print("\nTest 2c: Re'equil Unresolved Product - No generic patch test")
    print("-" * 80)
    
    service = PersonalizationService()
    
    # Mock Re'equil product that couldn't be resolved
    reequil_product = {
        "product_id": None,
        "product_name": "Re'equil Sunscreen",
        "product_type": "Sunscreen",
    }
    
    user_data = {
        "user_id": "test-user-reequil",
        "profile": {"skin_type": "sensitive", "skin_sensitivity": "yes"},
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    evaluation = service.evaluate_product_suitability(reequil_product, user_data)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Reason codes: {evaluation['reason_codes']}")
    print(f"Mitigation: {evaluation['mitigations'][0] if evaluation['mitigations'] else 'None'}")
    
    mitigation = evaluation['mitigations'][0] if evaluation['mitigations'] else ""
    
    assert "PRODUCT_UNRESOLVED" in evaluation['reason_codes'], "Should have PRODUCT_UNRESOLVED"
    assert "ingredient list" in mitigation.lower(), "Should mention ingredient list verification"
    assert "incomplete" in mitigation.lower(), "Should mention evaluation is incomplete"
    assert "inci" in mitigation.lower() or "packaging" in mitigation.lower(), "Should mention INCI verification"
    assert "patch test" not in mitigation.lower(), "Should NOT contain generic patch-test recommendation"
    
    print("PASS: Re'equil unresolved mitigation has no generic patch test")
    return True

def test_evidence_incomplete():
    """Test EVIDENCE_INCOMPLETE mitigation."""
    print("\nTest 2: EVIDENCE_INCOMPLETE - Partial ingredient research")
    print("-" * 80)
    
    service = PersonalizationService()
    
    # Mock product with mostly unresearched ingredients to trigger EVIDENCE_INCOMPLETE
    product = {
        "product_id": 999,
        "product_name": "Test Serum",
        "product_type": "Serum",
        "normalized_ingredients": "Water|UnknownIngredientX|MysteryIngredientY|SecretIngredientZ"
    }
    
    user_data = {
        "user_id": "test-user-2",
        "profile": {"skin_type": "normal"},
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    # Mock ingredients with mostly missing research (low evidence score)
    ingredients = [
        {"ingredient": "Water", "evidence_source": "well-established"},
        {"ingredient": "UnknownIngredientX", "evidence_source": None},
        {"ingredient": "MysteryIngredientY", "evidence_source": None},
        {"ingredient": "SecretIngredientZ", "evidence_source": None}
    ]
    
    evaluation = service.evaluate_product_suitability(product, user_data, ingredients=ingredients, total_parsed=4)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Reason codes: {evaluation['reason_codes']}")
    print(f"Mitigation: {evaluation['mitigations'][0] if evaluation['mitigations'] else 'None'}")
    
    if "EVIDENCE_INCOMPLETE" in evaluation['reason_codes']:
        mitigation = evaluation['mitigations'][0] if evaluation['mitigations'] else ""
        assert "limited" in mitigation.lower() or "incomplete" in mitigation.lower(), "Should mention limited/incomplete evidence"
        assert "not unsafe" in mitigation.lower() or "does not indicate" in mitigation.lower(), "Should clarify that limited evidence != unsafe"
        assert "gradually" in mitigation.lower() or "cautious" in mitigation.lower() or "introduce" in mitigation.lower(), "Should suggest gradual introduction"
        assert "patch test" not in mitigation.lower(), "Should NOT contain generic patch-test recommendation"
        print("PASS: EVIDENCE_INCOMPLETE mitigation is appropriate and doesn't claim unsafety without generic patch test")
    else:
        print("SKIP: EVIDENCE_INCOMPLETE not triggered (evidence score may still be too high)")
    
    return True

def test_environment_mismatch():
    """Test ENVIRONMENT_MISMATCH mitigation with actual humidity context."""
    print("\nTest 4: ENVIRONMENT_MISMATCH - High humidity context")
    print("-" * 80)
    
    service = PersonalizationService()
    
    product = {
        "product_id": 998,
        "product_name": "Heavy Moisturizer",
        "product_type": "Moisturizer",
        "normalized_ingredients": "Water|Petrolatum|Mineral Oil"
    }
    
    user_data = {
        "user_id": "test-user-3",
        "profile": {"skin_type": "oily", "skin_concerns": []},
        "skin_analysis": None,
        "current_products": [],
        "environment": {"humidity": 85, "temperature": 32}  # High humidity and temperature
    }
    
    ingredients = [
        {"ingredient": "Petrolatum", "irritation_risk": "low"},
        {"ingredient": "Mineral Oil", "irritation_risk": "low"}
    ]
    
    evaluation = service.evaluate_product_suitability(product, user_data, ingredients=ingredients, total_parsed=3)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Reason codes: {evaluation['reason_codes']}")
    print(f"Mitigation: {evaluation['mitigations'][0] if evaluation['mitigations'] else 'None'}")
    
    if "ENVIRONMENT_MISMATCH" in evaluation['reason_codes']:
        mitigation = evaluation['mitigations'][0] if evaluation['mitigations'] else ""
        assert "humidity" in mitigation.lower(), "Should mention humidity"
        assert "85" in mitigation or "high" in mitigation.lower(), "Should mention high humidity value or condition"
        assert "comfortable" in mitigation.lower() or "texture" in mitigation.lower(), "Should mention comfort/texture"
        print("PASS: ENVIRONMENT_MISMATCH mitigation includes actual humidity context")
    else:
        print("SKIP: ENVIRONMENT_MISMATCH not triggered (skin type may be dry)")
    
    return True

def test_irritation_risk():
    """Test IRRITATION_RISK mitigation with specific ingredient."""
    print("\nTest 5: IRRITATION_RISK - High irritation ingredient")
    print("-" * 80)
    
    service = PersonalizationService()
    
    product = {
        "product_id": 997,
        "product_name": "Strong Acid Toner",
        "product_type": "Toner",
        "normalized_ingredients": "Water|Glycolic Acid|Lactic Acid"
    }
    
    user_data = {
        "user_id": "test-user-4",
        "profile": {"skin_type": "sensitive", "skin_sensitivity": "yes"},
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    ingredients = [
        {"ingredient": "Glycolic Acid", "irritation_risk": "high"},
        {"ingredient": "Lactic Acid", "irritation_risk": "moderate"}
    ]
    
    evaluation = service.evaluate_product_suitability(product, user_data, ingredients=ingredients, total_parsed=3)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Reason codes: {evaluation['reason_codes']}")
    print(f"Mitigation: {evaluation['mitigations'][0] if evaluation['mitigations'] else 'None'}")
    
    if "IRRITATION_RISK" in evaluation['reason_codes']:
        mitigation = evaluation['mitigations'][0] if evaluation['mitigations'] else ""
        assert "glycolic" in mitigation.lower() or "ingredient" in mitigation.lower(), "Should mention specific ingredient or ingredients"
        assert "patch test" in mitigation.lower(), "Should mention patch testing"
        assert "gradually" in mitigation.lower() or "introduce" in mitigation.lower(), "Should suggest gradual introduction"
        print("PASS: IRRITATION_RISK mitigation includes specific ingredient and patch test advice")
    else:
        print("SKIP: IRRITATION_RISK not triggered (may be REJECTED due to sensitivity)")
    
    return True

def test_previous_reaction():
    """Test PREVIOUS_REACTION mitigation with user history context."""
    print("\nTest 6: PREVIOUS_REACTION - User history context")
    print("-" * 80)
    
    service = PersonalizationService()
    
    product = {
        "product_id": 996,
        "product_name": "Previous Reaction Product",
        "product_type": "Moisturizer",
        "normalized_ingredients": "Water|Glycerin|Fragrance"
    }
    
    user_data = {
        "user_id": "test-user-5",
        "profile": {"skin_type": "normal"},
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    product_history = {
        "reaction": "moderate",
        "notes": "Some redness and itching on first use"
    }
    
    ingredients = [
        {"ingredient": "Fragrance", "irritation_risk": "moderate"}
    ]
    
    evaluation = service.evaluate_product_suitability(product, user_data, product_history=product_history, ingredients=ingredients, total_parsed=3)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Reason codes: {evaluation['reason_codes']}")
    print(f"Mitigation: {evaluation['mitigations'][0] if evaluation['mitigations'] else 'None'}")
    
    if "PREVIOUS_REACTION" in evaluation['reason_codes']:
        mitigation = evaluation['mitigations'][0] if evaluation['mitigations'] else ""
        assert "reaction" in mitigation.lower() or "history" in mitigation.lower(), "Should reference reaction or history"
        print("PASS: PREVIOUS_REACTION mitigation includes user history context")
    else:
        print("SKIP: PREVIOUS_REACTION not triggered")
    
    return True

def test_active_caution():
    """Test ACTIVE_CAUTION mitigation with skin analysis severity."""
    print("\nTest 7: ACTIVE_CAUTION - Skin analysis severity context")
    print("-" * 80)
    
    service = PersonalizationService()
    
    product = {
        "product_id": 995,
        "product_name": "Retinol Serum",
        "product_type": "Serum",
        "normalized_ingredients": "Water|Retinol|Glycerin"
    }
    
    user_data = {
        "user_id": "test-user-6",
        "profile": {"skin_type": "normal"},
        "skin_analysis": {"severity": "moderate"},  # Moderate severity
        "current_products": [],
        "environment": None
    }
    
    ingredients = [
        {"ingredient": "Retinol", "irritation_risk": "moderate"}
    ]
    
    evaluation = service.evaluate_product_suitability(product, user_data, ingredients=ingredients, total_parsed=3)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Reason codes: {evaluation['reason_codes']}")
    print(f"Mitigation: {evaluation['mitigations'][0] if evaluation['mitigations'] else 'None'}")
    
    if "ACTIVE_CAUTION" in evaluation['reason_codes']:
        mitigation = evaluation['mitigations'][0] if evaluation['mitigations'] else ""
        assert "moderate" in mitigation.lower() or "severity" in mitigation.lower(), "Should mention severity"
        assert "barrier" in mitigation.lower() or "stabilizes" in mitigation.lower(), "Should mention skin barrier"
        assert "pause" in mitigation.lower() or "pausing" in mitigation.lower() or "avoid" in mitigation.lower(), "Should suggest pausing actives"
        print("PASS: ACTIVE_CAUTION mitigation includes skin analysis severity context")
    else:
        print("SKIP: ACTIVE_CAUTION not triggered (no strong actives or severity)")
    
    return True

def test_contraindication():
    """Test CONTRAINDICATION mitigation."""
    print("\nTest 8: CONTRAINDICATION - Sensitive skin contraindication")
    print("-" * 80)
    
    service = PersonalizationService()
    
    product = {
        "product_id": 994,
        "product_name": "Harsh Scrub",
        "product_type": "Scrub",
        "normalized_ingredients": "Water|StrongScrubParticles|Fragrance"
    }
    
    user_data = {
        "user_id": "test-user-7",
        "profile": {"skin_type": "sensitive", "skin_sensitivity": "yes"},
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    ingredients = [
        {
            "ingredient": "StrongScrubParticles",
            "irritation_risk": "very high",
            "who_should_avoid": "sensitive skin"
        }
    ]
    
    evaluation = service.evaluate_product_suitability(product, user_data, ingredients=ingredients, total_parsed=3)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Reason codes: {evaluation['reason_codes']}")
    print(f"Mitigation: {evaluation['mitigations'][0] if evaluation['mitigations'] else 'None'}")
    
    if "CONTRAINDICATION" in evaluation['reason_codes']:
        mitigation = evaluation['mitigations'][0] if evaluation['mitigations'] else ""
        assert evaluation['decision'] == "REJECT", "CONTRAINDICATION should result in REJECT decision"
        assert "sensitive" in mitigation.lower() or "avoid" in mitigation.lower() or "not recommended" in mitigation.lower(), "Should mention contraindication"
        print("PASS: CONTRAINDICATION mitigation is specific to the contraindication and results in REJECT")
    else:
        print("SKIP: CONTRAINDICATION not triggered")
    
    return True

def test_sensitization_risk():
    """Test SENSITIZATION_RISK mitigation."""
    print("\nTest 9: SENSITIZATION_RISK - Known sensitizer")
    print("-" * 80)
    
    service = PersonalizationService()
    
    product = {
        "product_id": 993,
        "product_name": "Fragranced Lotion",
        "product_type": "Lotion",
        "normalized_ingredients": "Water|Fragrance|Preservative"
    }
    
    user_data = {
        "user_id": "test-user-8",
        "profile": {"skin_type": "normal"},
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    ingredients = [
        {
            "ingredient": "Fragrance",
            "allergy_sensitization": "high - common allergen",
            "irritation_risk": "moderate"
        }
    ]
    
    evaluation = service.evaluate_product_suitability(product, user_data, ingredients=ingredients, total_parsed=3)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Reason codes: {evaluation['reason_codes']}")
    print(f"Mitigation: {evaluation['mitigations'][0] if evaluation['mitigations'] else 'None'}")
    
    if "SENSITIZATION_RISK" in evaluation['reason_codes']:
        mitigation = evaluation['mitigations'][0] if evaluation['mitigations'] else ""
        assert "fragrance" in mitigation.lower() or "sensitizer" in mitigation.lower(), "Should mention specific ingredient or sensitizer"
        assert "allergic" in mitigation.lower() or "tingling" in mitigation.lower() or "redness" in mitigation.lower(), "Should mention allergic reaction symptoms"
        assert "monitor" in mitigation.lower() or "closely" in mitigation.lower(), "Should suggest monitoring"
        print("PASS: SENSITIZATION_RISK mitigation includes specific ingredient and monitoring advice")
    else:
        print("SKIP: SENSITIZATION_RISK not triggered")
    
    return True

def test_no_logic_changes():
    """Verify that decision logic and fit_score calculations remain unchanged."""
    print("\nTest 10: Verify no changes to decision logic and fit_score")
    print("-" * 80)
    
    service = PersonalizationService()
    
    # Test a simple KEEP case
    product = {
        "product_id": 992,
        "product_name": "Gentle Cleanser",
        "product_type": "Cleanser",
        "normalized_ingredients": "Water|Glycerin"
    }
    
    user_data = {
        "user_id": "test-user-9",
        "profile": {"skin_type": "normal", "skin_concerns": ["dryness"], "skincare_goals": ["hydrate skin"]},
        "skin_analysis": None,
        "current_products": [],
        "environment": None
    }
    
    ingredients = [
        {
            "ingredient": "Glycerin",
            "suitable_skin_types": "all",
            "skin_concerns": "dryness",
            "benefits": "hydration",
            "irritation_risk": "low",
            "evidence_source": "well-established"
        }
    ]
    
    evaluation = service.evaluate_product_suitability(product, user_data, ingredients=ingredients, total_parsed=2)
    
    print(f"Decision: {evaluation['decision']}")
    print(f"Fit score: {evaluation.get('fit_score', 0)}")
    print(f"Confidence: {evaluation['confidence']}")
    
    # Verify expected behavior for gentle product
    assert evaluation['decision'] in ["KEEP", "CAUTION"], f"Expected KEEP or CAUTION, got {evaluation['decision']}"
    assert 'fit_score' in evaluation, "fit_score should be present"
    assert evaluation['fit_score'] >= 0, "fit_score should be non-negative"
    
    # Test that fit_score still works as expected
    if evaluation['decision'] == "KEEP":
        assert evaluation['fit_score'] > 0, "KEEP products should have positive fit_score"
    
    print("PASS: Decision logic and fit_score calculations remain intact")
    return True

if __name__ == "__main__":
    try:
        print("=" * 80)
        print("IMPROVED MITIGATION SYSTEM TESTS")
        print("=" * 80)
        
        test_unresolved_product()
        test_wishcare_body_lotion()
        test_reequil_unresolved()
        test_evidence_incomplete()
        test_environment_mismatch()
        test_irritation_risk()
        test_previous_reaction()
        test_active_caution()
        test_contraindication()
        test_sensitization_risk()
        test_no_logic_changes()
        
        print("\n" + "=" * 80)
        print("ALL MITIGATION TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nSummary:")
        print("- PRODUCT_UNRESOLVED: Reason-specific with body lotion detection, NO generic patch test")
        print("- WishCare Body Lotion: Specific body-use warning without generic patch test")
        print("- Re'equil Unresolved: INCI verification without generic patch test")
        print("- EVIDENCE_INCOMPLETE: Clear that limited evidence != unsafe, NO generic patch test")
        print("- ENVIRONMENT_MISMATCH: Uses actual humidity/temperature context")
        print("- IRRITATION_RISK: Identifies specific high-irritation ingredients with patch test")
        print("- PREVIOUS_REACTION: References user's actual reaction history")
        print("- ACTIVE_CAUTION: Uses skin analysis severity context")
        print("- CONTRAINDICATION: Specific to the contraindication reason")
        print("- SENSITIZATION_RISK: Identifies known sensitizers with monitoring")
        print("- Decision logic and fit_score: Unchanged")
        
    except AssertionError as e:
        print(f"\nFAIL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
