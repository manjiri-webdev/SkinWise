from ddgs import DDGS
from typing import List, Dict, Optional
from urllib.parse import urlparse

def search_products(product_name: str, brand: Optional[str] = None, max_results: int = 15) -> List[Dict]:
    """
    Search for cosmetic products using DuckDuckGo.
    
    Args:
        product_name: The product name to search for
        brand: Optional brand name to include in search
        max_results: Maximum number of results to return
        
    Returns:
        List of search results with title, url, body, and potential image
    """
    ddgs = DDGS()
    results = []
    
    # Build multiple search queries for better coverage
    queries = []
    
    if brand:
        # Prioritize official brand site
        queries.append(f'"{brand}" {product_name} skincare')
        queries.append(f'{brand.replace("&", "and")} {product_name} ingredients')
    else:
        queries.append(f'"{product_name}" skincare')
        queries.append(f'{product_name} ingredients')
    
    try:
        # Perform text searches for each query
        for query in queries:
            try:
                search_results = ddgs.text(query, max_results=max_results // len(queries) + 5)
                
                for result in search_results:
                    url = result.get("href", "")
                    # Filter out obvious non-product URLs and retailers when brand is provided
                    if brand:
                        # When brand is provided, be more selective
                        if any(skip in url.lower() for skip in ['facebook', 'instagram', 'twitter', 'youtube', 'pinterest', 'amazon', 'nykaa', 'flipkart']):
                            continue
                    else:
                        # When no brand, still filter social media
                        if any(skip in url.lower() for skip in ['facebook', 'instagram', 'twitter', 'youtube', 'pinterest']):
                            continue
                    
                    # Mark official brand site results
                    is_official = False
                    if brand:
                        brand_domain = get_brand_domain(brand)
                        if brand_domain and brand_domain in url.lower():
                            is_official = True
                    
                    results.append({
                        "title": result.get("title", ""),
                        "url": url,
                        "body": result.get("body", ""),
                        "image": None,
                        "is_official": is_official
                    })
                
                # Stop if we have enough results
                if len(results) >= max_results:
                    break
            except Exception as e:
                print(f"Search error for query '{query}': {e}")
                continue
        
        # Perform image search to get product images
        image_query = f"{brand} {product_name}" if brand else product_name
        results = add_images_to_results(results, image_query)
            
    except Exception as e:
        print(f"Search error: {e}")
        return []
    
    return results[:max_results]

def get_brand_domain(brand: str) -> Optional[str]:
    """
    Try to guess the official domain for a brand.
    
    Args:
        brand: Brand name
        
    Returns:
        Domain if found, None otherwise
    """
    if not brand:
        return None
    
    # Known brand domains (highest priority)
    known_domains = {
        "dot": "dotandkey.com",
        "dot & key": "dotandkey.com",
        "dotandkey": "dotandkey.com",
        "minimalist": "minimalist.in",
        "the ordinary": "deciem.com",
        "ordinary": "deciem.com",
        "plum": "plumgoodness.com",
    }
    
    brand_lower = brand.lower().strip()
    
    # Check known domains first
    for key, domain in known_domains.items():
        if key in brand_lower or brand_lower in key:
            return domain
    
    # Try to construct domain from brand name
    brand_normalized = brand_lower.replace(" ", "").replace("&", "").replace(".", "")
    if len(brand_normalized) > 3:
        return f"{brand_normalized}.com"
    
    return None

def add_images_to_results(results: List[Dict], image_query: str) -> List[Dict]:
    """
    Add images to search results using DuckDuckGo image search.
    
    Args:
        results: List of search results
        image_query: Query for image search
        
    Returns:
        Results with images added
    """
    ddgs = DDGS()
    
    try:
        # Try multiple image search queries
        image_queries = [
            image_query,
            image_query.replace("sunscreen", "SPF"),
            image_query.replace("moisturizer", "cream"),
        ]
        
        url_to_images = {}
        
        for query in image_queries:
            try:
                image_results = ddgs.images(query, max_results=len(results) * 3)
                
                for img_result in image_results:
                    img_url = img_result.get("image", "")
                    source_url = img_result.get("url", "")
                    if img_url and source_url:
                        # Direct URL matching
                        url_to_images[source_url] = img_url
                        
                        # Also try matching by partial URL (for similar URLs)
                        for existing_url in list(url_to_images.keys()):
                            if source_url[:50] in existing_url or existing_url[:50] in source_url:
                                url_to_images[existing_url] = img_url
                                
            except Exception as e:
                print(f"Image search error for query '{query}': {e}")
                continue
        
        # Match images to text results by URL
        for result in results:
            result_url = result["url"]
            
            # Try exact URL match first
            if result_url in url_to_images:
                result["image"] = url_to_images[result_url]
                continue
            
            # Try partial URL match
            for source_url, img_url in url_to_images.items():
                if result_url[:50] in source_url or source_url[:50] in result_url:
                    result["image"] = img_url
                    break
            
            # If still no image, try domain matching as fallback
            if not result.get("image"):
                try:
                    result_domain = urlparse(result["url"]).netloc
                    result_domain = result_domain.replace("www.", "") if result_domain else result_domain
                    if result_domain:
                        # Try to find any image from this domain
                        for source_url, img_url in url_to_images.items():
                            source_domain = urlparse(source_url).netloc
                            source_domain = source_domain.replace("www.", "") if source_domain else source_domain
                            if source_domain == result_domain:
                                result["image"] = img_url
                                break
                except Exception:
                    continue
                
    except Exception as e:
        print(f"Image search error: {e}")
        # Continue without images if image search fails
    
    return results
