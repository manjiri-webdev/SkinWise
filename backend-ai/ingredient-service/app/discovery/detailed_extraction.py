from typing import Dict
from app.discovery.extractor import extract_product_details, is_generic_logo_image, is_contaminated_main_purpose

def extract_product_from_url(source_url: str) -> Dict:
    """
    Extract detailed product information from a source URL.
    
    This function uses the exact source_url to extract:
    - brand
    - product_name (exact from source)
    - category
    - main_purpose
    - full_ingredient_list (complete INCI list exactly as published)
    - image_url
    
    Args:
        source_url: The exact URL of the product page
        
    Returns:
        Dictionary with the six required fields or error information
    """
    if not source_url or not source_url.strip():
        return {
            "success": False,
            "error": "source_url is required"
        }
    
    # Clean the URL
    source_url = source_url.strip()
    
    print(f"[EXTRACTION] Starting extraction from: {source_url}")
    
    # Extract product details
    result = extract_product_details(source_url)
    
    # Check if extraction was successful
    if result.get("error"):
        print(f"[EXTRACTION] Extraction failed: {result['error']}")
        return {
            "success": False,
            "error": result["error"],
            "source_url": source_url
        }
    
    # VALIDATION: Reject extraction if critical fields are null
    # This prevents accepting research/article pages as product sources
    brand = result.get("brand")
    category = result.get("category")
    full_ingredient_list = result.get("full_ingredient_list")
    image_url = result.get("image_url")
    main_purpose = result.get("main_purpose")
    
    # Reject if both brand and category are null (indicates non-product page)
    if not brand and not category:
        print(f"[EXTRACTION] REJECTED: Both brand and category are null - likely not a product page")
        return {
            "success": False,
            "error": "Invalid product source: brand and category are both null",
            "source_url": source_url
        }
    
    # Reject if ingredient list is null (critical for product analysis)
    if not full_ingredient_list:
        print(f"[EXTRACTION] REJECTED: Ingredient list is null - cannot analyze product")
        return {
            "success": False,
            "error": "Invalid product source: ingredient list is null",
            "source_url": source_url
        }
    
    # Reject if image is a generic logo (indicates non-product page)
    if image_url and is_generic_logo_image(image_url):
        print(f"[EXTRACTION] REJECTED: Image appears to be a generic logo, not a product image: {image_url}")
        return {
            "success": False,
            "error": "Invalid product source: image is a generic logo, not a product image",
            "source_url": source_url
        }
    
    # Reject if main_purpose contains ingredient/article text
    if main_purpose:
        is_contaminated, reason = is_contaminated_main_purpose(main_purpose)
        if is_contaminated:
            print(f"[EXTRACTION] REJECTED: main_purpose contains ingredient/article text: {reason}")
            return {
                "success": False,
                "error": f"Invalid product source: main_purpose contains ingredient/article text: {reason}",
                "source_url": source_url
            }
    
    # Log the extracted fields for verification
    print(f"[EXTRACTION] Successfully extracted from: {source_url}")
    print(f"[EXTRACTION] brand: {brand}")
    print(f"[EXTRACTION] product_name: {result.get('product_name')}")
    print(f"[EXTRACTION] category: {category}")
    print(f"[EXTRACTION] main_purpose: {result.get('main_purpose')}")
    print(f"[EXTRACTION] full_ingredient_list length: {len(full_ingredient_list) if full_ingredient_list else 0}")
    print(f"[EXTRACTION] image_url: {result.get('image_url')}")
    print(f"[EXTRACTION] Extracted category value: {category}")
    
    # Check if we got at least some basic information
    if not result.get("product_name") and not result.get("brand"):
        return {
            "success": False,
            "error": "Could not extract basic product information from the source",
            "source_url": source_url
        }
    
    return {
        "success": True,
        "source_url": source_url,
        "data": result
    }