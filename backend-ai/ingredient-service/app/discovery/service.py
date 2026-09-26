from typing import List, Dict, Optional
from app.discovery.web_search import search_products
from app.discovery.matcher import rank_and_filter_results

def discover_products(product_name: str, brand: Optional[str] = None) -> Dict:
    """
    Discover candidate products based on product name and brand.
    
    Args:
        product_name: Required product name
        brand: Optional brand name
        
    Returns:
        Dictionary with success status, query info, count, and options
    """
    if not product_name or not product_name.strip():
        return {
            "success": False,
            "error": "product_name is required"
        }

    # Preserve original input for the query response
    original_product_name = product_name.strip()
    original_brand = brand.strip() if brand else ""

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

    print(f"DISCOVERY RANKED RESULTS: {len(ranked_options)}")
    for r in ranked_options:
        print("RANKED:", r.get("product_name"), "|", r.get("source_url")) 
    
    return {
        "success": True,
        "query": {
            "product_name": original_product_name,
            "brand": original_brand
        },
        "count": len(ranked_options),
        "options": ranked_options
    }