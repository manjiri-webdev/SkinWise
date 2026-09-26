from typing import List, Dict, Optional
from app.discovery.web_search import search_products
from app.discovery.matcher import rank_and_filter_results

def discover_products(product_name: str, brand: str) -> Dict:
    """
    Discover candidate products based on product name and brand.
    
    Args:
        product_name: Required product name
        brand: Required brand name for better accuracy
        
    Returns:
        Dictionary with success status, query info, count, and options
    """
    if not product_name or not product_name.strip():
        return {
            "success": False,
            "error": "product_name is required"
        }
    
    if not brand or not brand.strip():
        return {
            "success": False,
            "error": "brand is required for accurate product discovery"
        }
    
    # Preserve original input for the query response
    original_product_name = product_name.strip()
    original_brand = brand.strip()
    
    # Perform web search with reduced results for speed
    search_results = search_products(original_product_name, original_brand, max_results=15)
    
    if not search_results:
        return {
            "success": True,
            "query": {
                "product_name": original_product_name,
                "brand": original_brand
            },
            "count": 0,
            "options": []
        }
    
    # Rank and filter results
    ranked_options = rank_and_filter_results(
        search_results,
        original_product_name,
        original_brand,
        max_results=8
    )
    
    return {
        "success": True,
        "query": {
            "product_name": original_product_name,
            "brand": original_brand
        },
        "count": len(ranked_options),
        "options": ranked_options
    }
