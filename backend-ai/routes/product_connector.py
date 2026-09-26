"""
Product Connector for Personalization

Reuses existing product/ingredient pipeline to resolve current_products
from questionnaire and save to user_product_history with proper product_id.
"""

import sys
import os
from typing import Optional

def resolve_product_id(product_name: str, product_type: str) -> Optional[str]:
    """
    Resolve a product name to a product_id using the existing pipeline.
    
    Flow:
    1. Try to find existing product in database
    2. If not found, try to discover and extract product details
    3. Insert new product if successfully extracted
    4. Return product_id or None if resolution fails
    
    Args:
        product_name: The product name from questionnaire
        product_type: The product type from questionnaire
        
    Returns:
        product_id (str) or None if resolution fails
    """
    if not product_name or not product_name.strip():
        return None
    
    # Add ingredient-service to path dynamically
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ingredient-service'))
    
    try:
        from app.products.service import find_product
        from app.database.supabase import insert_product
        import supabase_config
        
        # Step 1: Try to find existing product
        existing_products = find_product(product_name=product_name)
        if existing_products:
            product_id = existing_products[0].get("product_id")
            if product_id:
                return product_id
        
        # Step 2: Try to use the product analysis service for better resolution
        try:
            from app.product_analysis.service import ProductAnalysisService
            analysis_service = ProductAnalysisService()
            
            # Try to analyze with a generic brand to trigger discovery/insertion
            analysis_result = analysis_service.analyze_product_with_reuse(
                product_name=product_name,
                brand="Unknown"  # Use generic brand since questionnaire doesn't provide it
            )
            
            if analysis_result.get("success") and analysis_result.get("product"):
                product_id = analysis_result["product"].get("product_id")
                if product_id:
                    print(f"[OK] Resolved product via analysis service: {product_name} -> {product_id}")
                    return product_id
        except Exception as analysis_error:
            print(f"[WARN] Product analysis service failed: {analysis_error}")
        
        # Step 3: Fallback to basic product entry if analysis fails
        try:
            basic_product_data = {
                "product_name": product_name,
                "category": product_type,
                "brand": "Unknown",  # Will be updated later if discovered
                "main_purpose": f"{product_type} product",
                "full_ingredient_list": None,  # Will be updated if discovered
                "normalized_ingredients": None,
                "image_url": None
            }
            
            result = insert_product(basic_product_data)
            if result.get("success") and result.get("data"):
                return result["data"].get("product_id")
        except Exception as e:
            print(f"Failed to create basic product entry: {e}")
    except Exception as e:
        print(f"Error in product resolution: {e}")
    
    return None


def process_questionnaire_products(current_products: list, user_id: str) -> list:
    """
    Process current_products from questionnaire and save to user_product_history.
    
    Only creates history entries for products that can be successfully resolved
    to a valid product_id. Products that fail resolution are skipped with a warning.
    
    Args:
        current_products: List of {type, productName} from questionnaire
        user_id: The authenticated user ID
        
    Returns:
        List of successfully saved product history entries
    """
    import supabase_config
    
    saved_entries = []
    
    if not current_products:
        return saved_entries
    
    for product in current_products:
        product_name = product.get("productName")
        product_type = product.get("type")
        
        if not product_name:
            continue
        
        # Resolve product_id using existing pipeline
        product_id = resolve_product_id(product_name, product_type)
        
        # Only create history entry if we successfully resolved a product_id
        if not product_id:
            print(f"[WARN] Could not resolve product_id for {product_name}, skipping history entry")
            continue
        
        # Create user_product_history entry
        try:
            history_data = {
                "user_id": user_id,
                "product_id": product_id,
                "product_name": product_name,
                "product_type": product_type,
                "status": "current",
                "started_at": None,  # Will be set by database default
                "ended_at": None,
                "reaction": None,
                "notes": None
            }
            
            response = supabase_config.supabase.table("user_product_history").insert(history_data).execute()
            
            if response.data:
                saved_entries.append(response.data[0])
                
        except Exception as e:
            print(f"Failed to save product history for {product_name}: {e}")
            # Continue with other products even if one fails
    
    return saved_entries