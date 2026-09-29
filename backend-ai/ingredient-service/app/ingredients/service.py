from app.database.supabase import supabase

import unicodedata
import re

def normalize_name(value: str) -> str:
    if not value:
        return ""

    value = str(value)
    value = unicodedata.normalize("NFKC", value)

    value = re.sub(
        r"[\u2010\u2011\u2012\u2013\u2014\u2212\uFE58\uFE63\uFF0D]",
        "-",
        value
    )

    value = " ".join(value.strip().lower().split())

    return value

def normalize_ingredient_for_lookup(ingredient: str) -> str:
    """
    Normalize ingredient name for database lookup only.
    Preserves original ingredient string for output/storage.
    
    Handles known variants and standard formatting:
    - Unicode dashes, whitespace, slash spacing, harmless punctuation
    - Known ingredient variants (CAPRYLIC/CAPRIC TRI-GLYCERIDE, etc.)
    
    Args:
        ingredient: Original ingredient string
        
    Returns:
        Normalized string for lookup only
    """
    if not ingredient:
        return ""
    
    # Start with basic normalization
    normalized = normalize_name(ingredient)
    
    # Known variant mappings
    variant_mappings = {
        "caprylic/capric tri-glyceride": "caprylic/capric triglyceride",
        "caprylic/capric triglycerides": "caprylic/capric triglyceride",
        "aqua": "water",
        "simmondsia chinensis seed oil": "jojoba oil",
        "borago officinalis seed oil": "borage seed oil",
        "paraffinum liquidum": "mineral oil",
        "ceramide iii": "ceramide np",
        "ceramide 3": "ceramide np",
        "ceramide i": "ceramide np",
        "ceramide 1": "ceramide np",
    }
    
    # Check for exact variant match
    if normalized in variant_mappings:
        return variant_mappings[normalized]
    
    # Handle ceramide np with parentheses (e.g., "ceramide np (xyz)")
    if normalized.startswith("ceramide np"):
        return "ceramide np"
    
    # Normalize slash spacing (e.g., "CAPRYLIC/ CAPRIC" -> "caprylic/capric")
    normalized = re.sub(r'/\s+', '/', normalized)
    
    # Normalize multiple spaces to single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized

def split_aliases(aliases):
    if not aliases:
        return []

    if isinstance(aliases, list):
        return [
            str(alias).strip()
            for alias in aliases
            if str(alias).strip()
        ]

    aliases = str(aliases)

    if "|" in aliases:
        return [
            alias.strip()
            for alias in aliases.split("|")
            if alias.strip()
        ]
    else:
        return [aliases.strip()] if aliases.strip() else []


import time

_INGREDIENTS_CACHE = None
_INGREDIENTS_CACHE_TIME = 0.0
_CACHE_TTL = 600.0  # 10 minutes

def get_cached_ingredients():
    global _INGREDIENTS_CACHE, _INGREDIENTS_CACHE_TIME
    now = time.time()
    if _INGREDIENTS_CACHE is not None and (now - _INGREDIENTS_CACHE_TIME < _CACHE_TTL):
        return _INGREDIENTS_CACHE
    try:
        response = (
            supabase
            .table("ingredients")
            .select("*")
            .limit(2000)
            .execute()
        )
        if response.data:
            _INGREDIENTS_CACHE = response.data
            _INGREDIENTS_CACHE_TIME = now
            return _INGREDIENTS_CACHE
    except Exception as e:
        print(f"Error loading ingredients: {e}")
    return _INGREDIENTS_CACHE or []

def invalidate_ingredients_cache():
    global _INGREDIENTS_CACHE, _INGREDIENTS_CACHE_TIME
    _INGREDIENTS_CACHE = None
    _INGREDIENTS_CACHE_TIME = 0.0


def find_ingredient(ingredient: str):
    """
    Find ingredient in database using normalization layer for lookup.
    Preserves original ingredient string for output/storage.
    
    Args:
        ingredient: Original ingredient string
        
    Returns:
        Dictionary with found status, match method, and data
    """
    # Use normalization layer for lookup only
    search_name = normalize_ingredient_for_lookup(ingredient)

    ingredients = get_cached_ingredients()

    #Match ingredient column (exact match using normalized lookup)
    for record in ingredients:
        database_name = normalize_ingredient_for_lookup(
            record.get("ingredient")
        )

        if database_name == search_name:

            return {
                "found": True,
                "matched_by": "ingredient",
                "matched_name": record.get("ingredient"),  # Return original DB name
                "data": record
            }

    #Match canonical_name column (exact match using normalized lookup)
    for record in ingredients:
        canonical_name = normalize_ingredient_for_lookup(
            record.get("canonical_name")
        )

        if canonical_name and canonical_name == search_name:

            return {
                "found": True,
                "matched_by": "canonical_name",
                "matched_name": record.get("canonical_name"),  # Return original DB name
                "data": record
            }

    #Match aliases column (exact match using normalized lookup)
    for record in ingredients:
        aliases = split_aliases(
            record.get("aliases")
        )

        for alias in aliases:
            if normalize_ingredient_for_lookup(alias) == search_name:
                return {
                    "found": True,
                    "matched_by": "alias",
                    "matched_name": alias,  # Return original alias
                    "data": record
                }

    return {
        "found": False,
        "matched_by": None,
        "matched_name": None,
        "data": None
    }