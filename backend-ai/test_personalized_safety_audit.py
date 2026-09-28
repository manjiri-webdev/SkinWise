"""
Audit and verification tests for personalized product safety decisions.
Verifies that ingredient-level and formulation-level cautions/contraindications
are not overridden by positive fit scores.
"""
import sys
from services.personalization_service import PersonalizationService

def test_the_ordinary_peeling_solution_profiles():
    service = PersonalizationService()
    
    # 1. Fetch product 55 (The Ordinary AHA 30% + BHA 2% Peeling Solution)
    prod_resp = service.supabase.table("products").select("*").eq("product_id", 55).single().execute()
    product = prod_resp.data
    assert product is not None, "Product ID 55 must exist in Supabase catalog"
    print(f"Loaded product: {product.get('brand')} - {product.get('product_name')}")
    
    ingredients, total_parsed = service.get_product_ingredients(55)
    print(f"Loaded {len(ingredients)} ingredients (total parsed: {total_parsed})")

    # =========================================================================
    # PROFILE A: Combination Skin + Low Sensitivity + No Prior Reactions
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 1: Profile A (Combination + Low Sensitivity + No Prior Reactions)")
    print("=" * 80)
    user_a = {
        "user_id": "test-user-a",
        "profile": {
            "skin_type": "combination",
            "skin_sensitivity": "no",
            "skin_concerns": ["acne", "pigmentation"],
            "skincare_goals": ["clear acne", "even skin tone"],
            "allergies": [],
            "current_products": []
        },
        "skin_analysis": None,
        "environment": None
    }

    eval_a = service.evaluate_product_suitability(
        product, user_a, ingredients=ingredients, total_parsed=total_parsed
    )

    print(f"Decision:   {eval_a['decision']}")
    print(f"Confidence: {eval_a['confidence']}")
    print(f"Reason codes: {eval_a['reason_codes']}")
    print("Reasons:")
    for r in eval_a['reasons']:
        print(f"  • {r}")
    print("Mitigations:")
    for m in eval_a['mitigations']:
        print(f"  > {m}")

    ing_evals_a = eval_a["ingredient_evaluations"]
    suitable_a = [i for i in ing_evals_a if i["status"] == "Suitable"]
    caution_a = [i for i in ing_evals_a if i["status"] == "Use with Caution"]
    not_rec_a = [i for i in ing_evals_a if i["status"] == "Not recommended"]
    print(f"Ingredient counts: {len(suitable_a)} Suitable, {len(caution_a)} Caution, {len(not_rec_a)} Not recommended")

    # Verifications for Profile A
    assert eval_a["decision"] == "CAUTION", f"Expected CAUTION but got {eval_a['decision']}"
    assert eval_a["confidence"] == "medium", f"Expected medium confidence for CAUTION but got {eval_a['confidence']}"
    assert len(not_rec_a) == 0, f"Expected 0 Not recommended ingredients for Profile A, got {len(not_rec_a)}"
    assert len(caution_a) >= 2, f"Expected at least 2 caution ingredients, got {len(caution_a)}"
    assert any("peel" in r.lower() or "formulation" in r.lower() for r in eval_a["reasons"]), "Expected formulation potency warning in reasons"
    assert any("patch test" in m.lower() for m in eval_a["mitigations"]), "Expected patch test mitigation"
    assert any("10 minutes" in m.lower() for m in eval_a["mitigations"]), "Expected max 10 minutes application mitigation"
    assert any("sunscreen" in m.lower() or "spf" in m.lower() for m in eval_a["mitigations"]), "Expected SPF mitigation"
    print(">>> PASS: Profile A correctly evaluated to CAUTION with medium confidence, formulation warnings, and mitigations.")

    # =========================================================================
    # PROFILE B: Combination Skin + High Sensitivity + Previous Exfoliation Reaction
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 2: Profile B (Combination + High Sensitivity + Previous Exfoliant Reaction)")
    print("=" * 80)
    user_b = {
        "user_id": "test-user-b",
        "profile": {
            "skin_type": "combination",
            "skin_sensitivity": "high",
            "skin_concerns": ["acne", "pigmentation"],
            "skincare_goals": ["clear acne", "even skin tone"],
            "allergies": [],
            "current_products": [
                {
                    "product_name": "AHA Exfoliating Glow Tonic",
                    "product_type": "Exfoliant",
                    "reaction": "burning and stinging",
                    "notes": "Severe redness and skin peeling reaction"
                }
            ]
        },
        "skin_analysis": None,
        "environment": None
    }

    eval_b = service.evaluate_product_suitability(
        product, user_b, ingredients=ingredients, total_parsed=total_parsed
    )

    print(f"Decision:   {eval_b['decision']}")
    print(f"Confidence: {eval_b['confidence']}")
    print(f"Reason codes: {eval_b['reason_codes']}")
    print("Reasons:")
    for r in eval_b['reasons']:
        print(f"  • {r}")
    print("Mitigations:")
    for m in eval_b['mitigations']:
        print(f"  > {m}")

    ing_evals_b = eval_b["ingredient_evaluations"]
    suitable_b = [i for i in ing_evals_b if i["status"] == "Suitable"]
    caution_b = [i for i in ing_evals_b if i["status"] == "Use with Caution"]
    not_rec_b = [i for i in ing_evals_b if i["status"] == "Not recommended"]
    print(f"Ingredient counts: {len(suitable_b)} Suitable, {len(caution_b)} Caution, {len(not_rec_b)} Not recommended")

    # Verifications for Profile B
    assert eval_b["decision"] == "REJECT", f"Expected REJECT but got {eval_b['decision']}"
    assert eval_b["confidence"] == "high", f"Expected high confidence for REJECT but got {eval_b['confidence']}"
    assert "CONTRAINDICATION" in eval_b["reason_codes"], "Expected CONTRAINDICATION reason code"
    assert "PREVIOUS_REACTION" in eval_b["reason_codes"], "Expected PREVIOUS_REACTION reason code"
    assert len(not_rec_b) > 0, "Expected at least 1 Not recommended ingredient for Profile B"
    print(">>> PASS: Profile B correctly evaluated to REJECT with high confidence and contraindication reason codes.")

    # =========================================================================
    # PROFILE C: Combination Skin + Sensitive Skin (No Prior Reaction)
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 3: Profile C (Combination + Sensitive Skin, No Prior Reaction)")
    print("=" * 80)
    user_c = {
        "user_id": "test-user-c",
        "profile": {
            "skin_type": "combination",
            "skin_sensitivity": "sensitive",
            "skin_concerns": ["acne"],
            "skincare_goals": ["clear acne"],
            "allergies": [],
            "current_products": []
        },
        "skin_analysis": None,
        "environment": None
    }

    eval_c = service.evaluate_product_suitability(
        product, user_c, ingredients=ingredients, total_parsed=total_parsed
    )
    print(f"Decision:   {eval_c['decision']}")
    print(f"Confidence: {eval_c['confidence']}")
    print(f"Reason codes: {eval_c['reason_codes']}")
    assert eval_c["decision"] == "REJECT", f"Expected REJECT for sensitive skin on 30% acid peel, got {eval_c['decision']}"
    assert "CONTRAINDICATION" in eval_c["reason_codes"]
    print(">>> PASS: Profile C correctly evaluated to REJECT (contraindicated for sensitive skin).")

    # =========================================================================
    # PROFILE D: Gentle / Compatible Product Control Test
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 4: Non-peel Product Control Test (Gentle Cleanser / Compatible Product)")
    print("=" * 80)
    gentle_product = {
        "product_id": 999,
        "product_name": "Gentle Hydrating Cleanser",
        "product_type": "Cleanser",
        "category": "Cleanser",
        "description": "Mild daily cleanser with hyaluronic acid and ceramides"
    }
    gentle_ingredients = [
        {"ingredient": "Water", "irritation_risk": "low", "suitable_skin_types": "all", "evidence_source": "pubmed"},
        {"ingredient": "Glycerin", "irritation_risk": "low", "suitable_skin_types": "all", "benefits": "hydrating", "evidence_source": "pubmed"},
        {"ingredient": "Ceramide NP", "irritation_risk": "low", "suitable_skin_types": "all", "benefits": "barrier repair", "evidence_source": "pubmed"}
    ]
    eval_d = service.evaluate_product_suitability(
        gentle_product, user_a, ingredients=gentle_ingredients, total_parsed=3
    )
    print(f"Decision:   {eval_d['decision']}")
    print(f"Confidence: {eval_d['confidence']}")
    assert eval_d["decision"] == "KEEP", f"Expected KEEP for gentle product, got {eval_d['decision']}"
    assert eval_d["confidence"] in ["medium", "high"], f"Expected medium/high confidence, got {eval_d['confidence']}"
    print(">>> PASS: Control product retains positive KEEP evaluation.")

    print("\n" + "=" * 80)
    print("ALL PERSONALIZED SAFETY AUDIT TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    test_the_ordinary_peeling_solution_profiles()
