from typing import List, Dict, Optional, Set
from app.ingredients.service import normalize_name
from app.discovery.source_selector import get_source_priority, get_source_name, is_official_brand_site, is_retailer_source
import re

# Common brand name patterns and their normalized forms
BRAND_PATTERNS = {
    "dotandkey": "Dot & Key",
    "dot key": "Dot & Key",
    "dot&key": "Dot & Key",
    "minimalist": "Minimalist",
    "the ordinary": "The Ordinary",
    "ordinary": "The Ordinary",
    "plum": "Plum",
    "good vibes": "Good Vibes",
    "foxtale": "Foxtale",
    "skinsmith": "SkinSmith",
    "skin smith": "SkinSmith",
    "deciem": "The Ordinary",
}

def normalize_product_identity(product_name: str) -> str:
    """
    Normalize product name for identity comparison.
    Removes packaging details, sizes, and marketing text to identify the core product.
    
    Args:
        product_name: Raw product name
        
    Returns:
        Normalized product identity string
    """
    if not product_name:
        return ""
    
    normalized = product_name.lower()
    
    # Remove packaging details (pack sizes, ml, g, etc.) - main source of duplicates
    packaging_patterns = [
        r"\b(pack of \d+|pack of \d|pack-\d+|pack \d+)",
        r"\b(\d+ml|\d+g|\d+oz|\d+mg)",
        r"\b(\d+ pack|multi pack|value pack)",
        r"\b(bundle|combo|set|kit)",
    ]
    
    for pattern in packaging_patterns:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
    
    # Remove common marketing fluff
    marketing_patterns = [
        r"\b(for glowing skin|for bright skin|for even skin tone)",
        r"\b(with new-age|with advanced|with improved)",
        r"\b(in-vivo tested|clinically tested|dermatologically tested)",
    ]
    
    for pattern in marketing_patterns:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
    
    # Clean up whitespace and punctuation
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"[,\-–—]+", " ", normalized)
    
    # Remove trailing words that are often variations
    trailing_patterns = [
        r"\s+(pa\+\+\+\+|pa\+\+\+|pa\+\+|pa\+)",
        r"\s+(spf \d+|spf\d+)",
    ]
    
    for pattern in trailing_patterns:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
    
    # Clean up again
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    return normalized

def deduplicate_by_product_identity(results: List[Dict]) -> List[Dict]:
    """
    Deduplicate results by actual product identity, preferring official results.
    
    Args:
        results: List of product results with brand, product_name, etc.
        
    Returns:
        Deduplicated list of results
    """
    if not results:
        return []
    
    # Group by normalized product identity
    identity_groups = {}
    
    for result in results:
        product_identity = normalize_product_identity(result["product_name"])
        
        if not product_identity:
            continue
        
        if product_identity not in identity_groups:
            identity_groups[product_identity] = []
        
        identity_groups[product_identity].append(result)
    
    # For each identity group, keep the best result
    deduplicated = []
    
    for identity, group in identity_groups.items():
        if len(group) == 1:
            # Only one result, keep it
            deduplicated.append(group[0])
        else:
            # Multiple results for same product, prefer official results
            # Sort by: official status first, then by match score
            group.sort(key=lambda x: (
                # Prefer official brand site
                0 if "official brand site" in x.get("match_reason", "") else 1,
                # Prefer results with images
                0 if x.get("image_url") else 1,
                # Prefer shorter, cleaner names
                len(x["product_name"])
            ))
            
            # Keep the best one
            deduplicated.append(group[0])
    
    return deduplicated

def normalize_brand(brand: str) -> str:
    """
    Normalize brand name to a standard form.
    
    Args:
        brand: Brand name to normalize
        
    Returns:
        Normalized brand name
    """
    if not brand:
        return ""
    
    normalized = normalize_name(brand)
    
    # Check against known brand patterns
    for pattern, standard in BRAND_PATTERNS.items():
        if pattern in normalized or normalized in pattern:
            return standard
    
    # Return original if no pattern match, but properly capitalized
    return brand.strip()

def clean_product_name(name: str) -> str:
    """
    Clean product name by removing retailer noise and common patterns.
    
    Args:
        name: Raw product name
        
    Returns:
        Cleaned product name
    """
    if not name:
        return ""
    
    cleaned = name
    
    # Remove common noise patterns
    noise_patterns = [
        r"amazon\.com.*",
        r"amazon\.in.*",
        r"nykaa\.com.*",
        r"ulta\.com.*",
        r"sephora\.com.*",
        r"ingredients.*explained?",
        r"\.\.\.+$",
        r"buy.*$",
        r"shop.*$",
        r"official.*site.*$",
        r" - amazon\.com.*$",
        r" - amazon\.in.*$",
    ]
    
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    
    # Clean up whitespace and repeated text
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    
    # Remove obvious duplicates (common in search results)
    words = cleaned.split()
    if len(words) > 10:  # If too long, likely has duplicates
        # Try to remove repeated phrases
        seen_phrases = set()
        cleaned_words = []
        i = 0
        while i < len(words):
            phrase = " ".join(words[i:i+3])
            if phrase.lower() not in seen_phrases:
                seen_phrases.add(phrase.lower())
                cleaned_words.extend(words[i:i+3])
                i += 3
            else:
                i += 1
        cleaned = " ".join(cleaned_words)
    
    return cleaned if cleaned else name

def extract_brand_from_title(title: str, known_brands: Set[str] = None) -> Optional[str]:
    """
    Attempt to extract brand name from a title.
    
    Args:
        title: The title to extract brand from
        known_brands: Set of known brand names to match against
        
    Returns:
        Extracted brand name or None
    """
    if not title:
        return None
    
    # If we have known brands, try to match them first
    if known_brands:
        title_lower = title.lower()
        for brand in sorted(known_brands, key=len, reverse=True):  # Try longer brands first
            if brand.lower() in title_lower:
                return brand
    
    # Common patterns for brand extraction
    # Brands often appear at the start of titles
    words = title.split()
    
    if len(words) >= 2:
        # Try first word as brand
        potential_brand = words[0]
        # Skip common non-brand words
        skip_words = ["buy", "shop", "get", "order", "best", "top", "review", "reviews"]
        if potential_brand.lower() not in skip_words:
            # Check if it might be a multi-word brand (like "Dot & Key")
            if len(words) >= 3 and words[1] in ["&", "+", "and", "-"]:
                # Potential multi-word brand
                multi_word_brand = f"{words[0]} {words[1]} {words[2]}"
                return multi_word_brand
            return potential_brand
    
    return None

def calculate_string_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity between two strings using token overlap.
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        Similarity score between 0 and 1
    """
    if not str1 or not str2:
        return 0.0
    
    # Normalize both strings
    norm1 = normalize_name(str1)
    norm2 = normalize_name(str2)
    
    # Split into tokens
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    
    if not tokens1 or not tokens2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    
    if not union:
        return 0.0
    
    return len(intersection) / len(union)

def calculate_match_score(
    search_result: Dict,
    query_product_name: str,
    query_brand: str,
    known_brands: Set[str] = None
) -> Dict:
    """
    Calculate match score for a search result against the query.
    
    Args:
        search_result: Dictionary with title, url, body
        query_product_name: The product name from query
        query_brand: Optional brand from query
        known_brands: Set of known brand names to match against
        
    Returns:
        Dictionary with match_score, match_reason, and extracted info
    """
    title = search_result.get("title", "")
    url = search_result.get("url", "")
    
    # Extract brand from title with known brands
    title_brand = extract_brand_from_title(title, known_brands)
    
    # Normalize query brand if provided
    normalized_query_brand = normalize_brand(query_brand) if query_brand else None
    
    # Clean the title for better matching
    cleaned_title = clean_product_name(title)
    
    # Calculate product name similarity using cleaned title
    product_similarity = calculate_string_similarity(query_product_name, cleaned_title)
    
    # Brand matching - much stricter when brand is provided
    brand_score = 0.0
    brand_match = False
    brand_similarity = 0.0
    
    if normalized_query_brand:
        # Check if query brand matches title brand
        if title_brand:
            normalized_title_brand = normalize_brand(title_brand)
            brand_similarity = calculate_string_similarity(normalized_query_brand, normalized_title_brand)
            
            # Very high brand similarity required when brand is provided
            if brand_similarity >= 0.9:
                brand_score = 0.5
                brand_match = True
            elif brand_similarity >= 0.8:
                brand_score = 0.4
                brand_match = True
        
        # Check if normalized query brand appears in title
        if normalize_name(normalized_query_brand) in normalize_name(cleaned_title):
            brand_score = max(brand_score, 0.3)
            brand_match = True
        
        # Check if it's official brand site (big bonus)
        if is_official_brand_site(url, normalized_query_brand):
            brand_score = max(brand_score, 0.6)
            brand_match = True
    
    # Source priority (lower priority number = better source)
    source_priority = get_source_priority(url)
    source_score = max(0, 1 - (source_priority / 100))  # Normalize to 0-1
    
    # Penalize retailers heavily when brand is provided
    if normalized_query_brand and is_retailer_source(url):
        source_score = source_score * 0.3  # Heavy penalty for retailers
    
    # Keyword overlap check for better product matching
    query_keywords = set(normalize_name(query_product_name).split())
    title_keywords = set(normalize_name(cleaned_title).split())
    keyword_overlap = len(query_keywords.intersection(title_keywords)) / max(len(query_keywords), 1)
    
    # Combine scores with stricter weighting
    # Product similarity (0-1) - most important
    # Brand match (0-0.6) - critical when brand provided
    # Source quality (0-1) - bonus for trusted sources, penalty for retailers
    # Keyword overlap (0-1) - additional relevance signal
    
    if normalized_query_brand:
        # When brand is provided, brand match is critical
        total_score = (product_similarity * 0.3) + (brand_score * 0.4) + (source_score * 0.2) + (keyword_overlap * 0.1)
    else:
        # When no brand, focus on product matching
        total_score = (product_similarity * 0.5) + (source_score * 0.3) + (keyword_overlap * 0.2)
    
    # Build match reason
    reasons = []
    
    if product_similarity >= 0.6:
        reasons.append("strong product-name match")
    elif product_similarity >= 0.4:
        reasons.append("moderate product-name match")
    else:
        reasons.append("weak product-name match")
    
    if brand_match:
        if brand_similarity >= 0.9:
            reasons.append("exact brand match")
        else:
            reasons.append("brand match")
    
    if is_official_brand_site(url, normalized_query_brand) if normalized_query_brand else False:
        reasons.append("official brand site")
    
    if is_retailer_source(url):
        reasons.append("retailer")
    elif source_priority <= 3:
        reasons.append("highly trusted source")
    elif source_priority <= 10:
        reasons.append("trusted source")
    
    if keyword_overlap >= 0.6:
        reasons.append("strong keyword overlap")
    
    match_reason = ", ".join(reasons) if reasons else "basic match"
    
    # Use query brand if provided, otherwise use extracted brand
    display_brand = normalized_query_brand if normalized_query_brand else (title_brand or "Unknown")
    
    return {
        "match_score": round(min(total_score, 1.0), 2),
        "match_reason": match_reason,
        "extracted_brand": display_brand,
        "extracted_product_name": cleaned_title
    }

def rank_and_filter_results(
    search_results: List[Dict],
    query_product_name: str,
    query_brand: str,
    max_results: int = 8
) -> List[Dict]:
    """
    Rank and filter search results based on match scores.
    
    Args:
        search_results: List of search results
        query_product_name: The product name from query
        query_brand: Brand from query (now required)
        max_results: Maximum number of results to return
        
    Returns:
        Ranked and filtered list of product options
    """
    if not search_results:
        return []
    
    # Separate official brand site results from others
    official_results = []
    other_results = []
    
    for result in search_results:
        if result.get("is_official", False):
            official_results.append(result)
        else:
            other_results.append(result)
    
    # If we have official brand site results, prioritize those
    if official_results:
        print(f"Using {len(official_results)} official brand site results")
        search_results = official_results
    else:
        print(f"No official brand site results, using {len(other_results)} general results")
        search_results = other_results
    
    # Build known brands set from query and results
    known_brands = set()
    known_brands.add(normalize_brand(query_brand))
    
    # Extract potential brands from search results
    for result in search_results:
        title = result.get("title", "")
        extracted_brand = extract_brand_from_title(title)
        if extracted_brand:
            known_brands.add(extracted_brand)
    
    # Calculate match scores for all results
    scored_results = []
    
    for result in search_results:
        match_info = calculate_match_score(result, query_product_name, query_brand, known_brands)
        
        # Minimum threshold for relevance (lower for official site results)
        min_threshold = 0.2 if official_results else 0.3
        
        # Check if query contains specific product type (e.g., "moisturizer", "serum", "sunscreen")
        # and filter results accordingly
        query_lower = normalize_name(query_product_name).lower()
        product_types = ["moisturizer", "serum", "sunscreen", "lotion", "cream", "face wash", "cleanser"]
        query_product_type = None
        for ptype in product_types:
            if ptype in query_lower:
                query_product_type = ptype
                break
        
        if query_product_type:
            # Check if result contains the product type or a variant
            result_lower = normalize_name(match_info["extracted_product_name"]).lower()
            # Be more lenient - check for partial matches or related terms
            type_variants = {
                "sunscreen": ["sunscreen", "spf", "uv", "sun"],
                "moisturizer": ["moisturizer", "cream", "lotion", "hydration"],
                "serum": ["serum", "concentrate", "elixir"],
                "face wash": ["face wash", "cleanser", "cleanse"],
            }
            
            if query_product_type in type_variants:
                matched = any(variant in result_lower for variant in type_variants[query_product_type])
                if not matched:
                    continue  # Skip if result doesn't match the product type
            else:
                if query_product_type not in result_lower:
                    continue  # Skip if result doesn't match the product type
        
        # Skip brand homepage and collection pages
        skip_patterns = ["buy", "shop", "collection", "catalog", "all products", "online at best price", "sunscreens", "products", "benefits", "blogs"]
        result_lower = normalize_name(match_info["extracted_product_name"]).lower()
        if any(pattern in result_lower for pattern in skip_patterns):
            continue  # Skip generic pages
        
        if match_info["match_score"] >= min_threshold:
            scored_results.append({
                "brand": match_info["extracted_brand"] or "Unknown",
                "product_name": match_info["extracted_product_name"],
                "source_name": get_source_name(result["url"]),
                "source_url": result["url"],
                "image_url": result.get("image", None),
                "match_reason": match_info["match_reason"],
                "_match_score": match_info["match_score"]  # Internal use for sorting
            })
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_results = []
    for result in scored_results:
        if result["source_url"] not in seen_urls:
            seen_urls.add(result["source_url"])
            unique_results.append(result)
    
    # Deduplicate by product identity (remove same product with different packaging)
    deduplicated_results = deduplicate_by_product_identity(unique_results)
    
    # Sort by match score (descending)
    deduplicated_results.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
    
    # Remove internal match_score before returning
    for result in deduplicated_results:
        result.pop("_match_score", None)
    
    # Return top results (limited to 5-8)
    return deduplicated_results[:max_results]
