import re
from app.database.supabase import supabase
from app.ingredients.service import find_ingredient


def _normalize_search_term(search_term: str) -> str:
    """
    Normalize search term for product matching.
    
    Normalizes:
    - Lowercase
    - Apostrophes/quotes (', ", ') - removed entirely
    - Punctuation (.,;:!?)
    - Dashes/hyphens
    - Extra whitespace
    - Equivalent "&"/"and" forms
    
    Args:
        search_term: Raw search term string
        
    Returns:
        Normalized search term string
    """
    if not search_term:
        return ""
    
    # Convert to lowercase
    normalized = search_term.lower()
    
    # Remove apostrophes and quotes entirely (not replace with space)
    normalized = re.sub(r"[\'\"\u2018\u2019\u201c\u201d]", "", normalized)
    
    # Replace punctuation with space
    normalized = re.sub(r"[.,;:!?\(\)\[\]]", " ", normalized)
    
    # Replace dashes/hyphens with space
    normalized = re.sub(r"[-–—]", " ", normalized)
    
    # Normalize "&" to " and "
    normalized = re.sub(r"\s*&\s*", " and ", normalized)
    
    # Collapse multiple spaces to single space
    normalized = re.sub(r"\s+", " ", normalized)
    
    # Strip leading/trailing whitespace
    normalized = normalized.strip()
    
    return normalized


KNOWN_BRANDS = [
    ("reequil", "Reequil"),
    ("dot and key", "Dot & Key"),
    ("cerave", "CeraVe"),
    ("cetaphil", "Cetaphil"),
    ("wishcare", "WishCare"),
    ("mamaearth", "Mama Earth"),
    ("the ordinary", "The Ordinary"),
    ("minimalist", "Minimalist"),
]


def _extract_brand_from_name(product_name: str, brand: str = None) -> tuple:
    """
    Extract brand prefix from product name if brand is embedded.
    
    Args:
        product_name: Product name string
        brand: Optional brand name to check for
        
    Returns:
        Tuple of (brand, remaining_product_name)
    """
    if not product_name:
        return (brand, "")
    
    norm_name = _normalize_search_term(product_name)
    
    if brand:
        norm_brand = _normalize_search_term(brand)
        if norm_name.startswith(norm_brand):
            if product_name.lower().startswith(brand.lower()):
                remaining = product_name[len(brand):].strip()
                remaining = re.sub(r"^[-–—:\s]+", "", remaining).strip()
            else:
                remaining = norm_name[len(norm_brand):].strip()
            return (brand, remaining)
        return (brand, product_name)
    
    # Check known brands if brand was not explicitly provided
    for brand_key, brand_canon in KNOWN_BRANDS:
        if norm_name.startswith(brand_key + " ") or norm_name == brand_key:
            if product_name.lower().startswith(brand_key.lower()):
                remaining = product_name[len(brand_key):].strip()
                remaining = re.sub(r"^[-–—:\s]+", "", remaining).strip()
            else:
                remaining = norm_name[len(brand_key):].strip()
            return (brand_canon, remaining)
    
    return (brand, product_name)


def find_product(brand: str = None, product_name: str = None):
    search_term = product_name.strip() if product_name else ""
    
    # Extract brand from product name if embedded
    extracted_brand, remaining_name = _extract_brand_from_name(search_term, brand)
    search_brand = extracted_brand if extracted_brand else brand
    
    # Clean normalized versions
    norm_brand = _normalize_search_term(search_brand) if search_brand else ""
    norm_name = _normalize_search_term(remaining_name if remaining_name else search_term)
    full_search = _normalize_search_term(f"{norm_brand} {norm_name}".strip())
    
    search_words = set(w for w in full_search.split() if len(w) > 2 and w not in ["and", "for", "with", "the"])
    
    # Fetch candidate products from Supabase
    candidates = []
    if norm_brand:
        # Try finding by brand (fuzzy ilike matching)
        res = supabase.table("products").select("*").ilike("brand", f"%{norm_brand}%").execute()
        candidates.extend(res.data or [])
    
    if not candidates and search_words:
        # Try finding by major words in product name
        for word in list(search_words)[:3]:
            res = supabase.table("products").select("*").ilike("product_name", f"%{word}%").execute()
            candidates.extend(res.data or [])
            if len(candidates) >= 15:
                break
                
    if not candidates:
        # Fallback to recent products
        res = supabase.table("products").select("*").order("created_at", desc=True).limit(50).execute()
        candidates.extend(res.data or [])
        
    # Deduplicate candidates by product_id
    unique_candidates = {c["product_id"]: c for c in candidates}.values()
    
    # Deterministic scoring
    scored = []
    for c in unique_candidates:
        c_brand = _normalize_search_term(c.get("brand") or "")
        c_name = _normalize_search_term(c.get("product_name") or "")
        c_full = _normalize_search_term(f"{c_brand} {c_name}")
        c_words = set(w for w in c_full.split() if len(w) > 2 and w not in ["and", "for", "with", "the"])
        
        score = 0
        # Exact full match
        if full_search == c_full:
            score = 100
        elif norm_name == c_name:
            score = 95
        elif norm_name in c_name or c_name in norm_name:
            score = 85
        elif full_search in c_full or c_full in full_search:
            score = 80
        else:
            # Word overlap
            if search_words:
                overlap = len(search_words & c_words)
                ratio = overlap / len(search_words)
                if ratio >= 0.5 or overlap >= 2:
                    score = int(ratio * 70)
                    
        if score >= 50:
            scored.append((c, score))
            
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored]


def get_product_ingredients(brand: str = None, product_name: str = None):
    products = find_product(brand, product_name)

    if not products:
        return None

    product = products[0]

    normalized = product.get("normalized_ingredients") or ""
    if not normalized:
        full_list = product.get("full_ingredient_list") or ""
        if full_list:
            ingredient_names = [item.strip() for item in full_list.split(",") if item.strip()]
        else:
            ingredient_names = []
    else:
        ingredient_names = [
            item.strip()
            for item in normalized.split("|")
            if item.strip()
        ]

    ingredient_results = []
    missing_ingredients = []

    for name in ingredient_names:
        result = find_ingredient(name)

        if result["found"]:
            ingredient_results.append({
                "searched_name": name,
                "found": True,
                "matched_by": result["matched_by"],
                "matched_name": result["matched_name"],
                "data": result["data"]
            })
        else:
            ingredient_results.append({
                "searched_name": name,
                "found": False,
                "matched_by": None,
                "matched_name": None,
                "data": None
            })
            missing_ingredients.append(name)

    return {
        "product": product,
        "ingredients": ingredient_results,
        "total_ingredients": len(ingredient_names),
        "found_ingredients": len(ingredient_names) - len(missing_ingredients),
        "missing_ingredients": missing_ingredients
    }