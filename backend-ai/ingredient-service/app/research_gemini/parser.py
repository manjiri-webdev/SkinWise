import re
import unicodedata
from typing import List

def normalize_name(value: str) -> str:
    """Normalize ingredient name for matching"""
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

def parse_ingredient_list(full_ingredient_list: str) -> List[str]:
    """
    Safely parse individual ingredients from a full ingredient list.
    
    This function carefully handles:
    - Compound ingredients (e.g., "Caprylic/Capric Triglyceride")
    - "(and)" expressions (e.g., "Butylene Glycol (and) Caprylyl Glycol")
    - Nested parentheses
    - Various separators (commas, periods, plus signs)
    
    Args:
        full_ingredient_list: The complete INCI ingredient list as a string
        
    Returns:
        List of individual ingredient names as they appear in the original list
    """
    if not full_ingredient_list or not full_ingredient_list.strip():
        return []
    
    # Clean the input but preserve structure
    ingredient_list = full_ingredient_list.strip()
    
    # Protect commas between digits in chemical names (e.g., "1,2-Hexanediol")
    ingredient_list = re.sub(r'(\d),(\s*\d)', r'\1__NUM_COMMA__\2', ingredient_list)
    
    # Parse the ingredient list while preserving structure
    ingredients = []
    current_ingredient = ""
    paren_depth = 0
    i = 0
    
    while i < len(ingredient_list):
        char = ingredient_list[i]
        
        # Track parentheses depth
        if char == '(':
            paren_depth += 1
            current_ingredient += char
        elif char == ')':
            paren_depth -= 1
            current_ingredient += char
        # Split on commas when not inside parentheses
        elif char == ',' and paren_depth == 0:
            # Finish current ingredient
            if current_ingredient.strip():
                ingredients.append(current_ingredient.strip())
            current_ingredient = ""
        # Handle other characters
        else:
            current_ingredient += char
        
        i += 1
    
    # Don't forget the last ingredient
    if current_ingredient.strip():
        ingredients.append(current_ingredient.strip())
    
    # Clean up each ingredient
    cleaned_ingredients = []
    for ingredient in ingredients:
        cleaned = clean_ingredient_name(ingredient)
        if cleaned:
            cleaned_ingredients.append(cleaned)
    
    return cleaned_ingredients

def clean_ingredient_name(ingredient: str) -> str:
    """
    Clean an individual ingredient name while preserving its structure.
    
    Args:
        ingredient: Raw ingredient name
        
    Returns:
        Cleaned ingredient name
    """
    if not ingredient:
        return ""
    
    cleaned = ingredient
    
    # Remove trailing periods (common in ingredient lists)
    cleaned = re.sub(r'\.+$', '', cleaned).strip()
    
    # Remove numbering (e.g., "1.", "2.")
    cleaned = re.sub(r'^\d+\.\s*', '', cleaned).strip()
    
    # Remove leading bullet points
    cleaned = re.sub(r'^[\-\*•]\s*', '', cleaned).strip()
    
    # Restore protected commas between digits
    cleaned = cleaned.replace('__NUM_COMMA__', ',')
    
    return cleaned
