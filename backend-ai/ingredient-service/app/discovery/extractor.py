import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import re
import json
import time

def extract_product_details(source_url: str) -> Dict:
    """
    Extract detailed product information from the source URL.
    
    Extracts only:
    - brand
    - product_name (exact from source)
    - category
    - main_purpose
    - full_ingredient_list (complete INCI list exactly as published)
    - image_url
    
    Cleans out navigation, scripts, JSON, and unrelated marketing content.
    Does not invent, summarize, reorder, or omit ingredients.
    
    Args:
        source_url: The exact URL of the product page
        
    Returns:
        Dictionary with the six required fields
    """
    try:
        # Reject explanatory ingredient websites (not official product pages)
        # These sites are for ingredient research only, not canonical product data
        blocked_domains = [
            'incidecoder.com',
            'incidecoder',
            'incidecoder.co',
            'incidecoder.in',
            'cosdna.com',
            'cosdna',
            'ewg.org',
            'ewg.org/skindeep',
            'skinvasion.com',
            'cosmeticingredientreview.com',
        ]
        
        from urllib.parse import urlparse
        domain = urlparse(source_url).netloc.lower()
        
        for blocked in blocked_domains:
            if blocked in domain:
                print(f"[EXTRACTION] Blocked explanatory website: {domain}")
                return {
                    "brand": None,
                    "product_name": None,
                    "category": None,
                    "main_purpose": None,
                    "full_ingredient_list": None,
                    "image_url": None,
                    "error": f"Blocked explanatory website: {domain}"
                }
        
        # Fetch the page with multiple user agents and retry logic
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
        
        response = None
        last_error = None
        
        for attempt, user_agent in enumerate(user_agents):
            try:
                headers = {'User-Agent': user_agent}
                response = requests.get(source_url, headers=headers, timeout=15)
                response.raise_for_status()
                break  # Success, exit retry loop
            except requests.exceptions.HTTPError as e:
                last_error = e
                if e.response.status_code == 403:
                    print(f"[EXTRACTION] 403 Forbidden with user agent {attempt + 1}, trying next...")
                    time.sleep(1)  # Wait before retry
                    continue
                else:
                    raise  # Re-raise other HTTP errors
            except requests.exceptions.RequestException as e:
                last_error = e
                print(f"[EXTRACTION] Request failed with user agent {attempt + 1}: {e}")
                if attempt < len(user_agents) - 1:
                    time.sleep(1)
                    continue
                else:
                    raise
        
        if response is None:
            raise last_error if last_error else Exception("Failed to fetch page after all retries")
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
    
        # Extract brand
        brand = extract_brand(soup, source_url)
        
        # Extract product name first (needed for category fallback)
        product_name = extract_product_name(soup)
        
        # Extract category (now can use product_name for fallback)
        category = extract_category(soup, product_name)
        
        # Extract main purpose
        main_purpose = extract_main_purpose(soup)
        
        # Extract full ingredient list
        full_ingredient_list = extract_ingredients(soup)
        
        # Extract image URL
        image_url = extract_image_url(soup, source_url)
        
        #  # Remove scripts, styles, navigation, and other non-content elements
        # for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
        #     element.decompose()
        
        return {
            "brand": brand,
            "product_name": product_name,
            "category": category,
            "main_purpose": main_purpose,
            "full_ingredient_list": full_ingredient_list,
            "image_url": image_url
        }
        
    except Exception as e:
        print(f"Error extracting product details from {source_url}: {e}")
        return {
            "brand": None,
            "product_name": None,
            "category": None,
            "main_purpose": None,
            "full_ingredient_list": None,
            "image_url": None,
            "error": str(e)
        }

def get_all_jsonld_objects(soup: BeautifulSoup):
    """Return all usable JSON-LD objects from the page."""
    objects = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()

        if not raw.strip():
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        if isinstance(data, list):
            objects.extend(
                item for item in data
                if isinstance(item, dict)
            )
        elif isinstance(data, dict):
            # Handle @graph
            graph = data.get("@graph")
            if isinstance(graph, list):
                objects.extend(
                    item for item in graph
                    if isinstance(item, dict)
                )
            else:
                objects.append(data)

    return objects

def extract_brand(soup: BeautifulSoup, source_url: str) -> Optional[str]:
    """Extract the actual product brand."""

    # 1. JSON-LD Product brand
    for item in get_all_jsonld_objects(soup):
        if item.get("@type") == "Product":
            brand = item.get("brand")

            if isinstance(brand, dict):
                name = brand.get("name")
                if name:
                    return name.strip()

            if isinstance(brand, str) and brand.strip():
                return brand.strip()

    # 2. Meta tags
    for attrs in [
        {"property": "og:brand"},
        {"name": "brand"},
        {"name": "product:brand"},
        {"name": "twitter:brand"},
    ]:
        meta = soup.find("meta", attrs=attrs)

        if meta and meta.get("content"):
            return meta["content"].strip()

    # 3. Known official domains
    from urllib.parse import urlparse

    domain = urlparse(source_url).netloc.lower()

    brand_domains = {
        "dotandkey.com": "Dot & Key",
        "minimalist.in": "Minimalist",
        "deciem.com": "The Ordinary",
        "plumgoodness.com": "Plum",
        "cerave.com": "CeraVe",
        "reequil.com": "Re'equil",
    }

    for known_domain, brand_name in brand_domains.items():
        if domain == known_domain or domain.endswith("." + known_domain):
            return brand_name

    # 4. Page title fallback
    title = soup.find("title")

    if title:
        title_text = title.get_text(" ", strip=True)

        # Common "Brand | Product" / "Brand - Product"
        for separator in ["|", " - "]:
            if separator in title_text:
                potential = title_text.split(separator, 1)[0].strip()

                if 1 < len(potential) < 50:
                    return potential

    return None

def extract_product_name(soup: BeautifulSoup) -> Optional[str]:
    """Extract the actual product name, avoiding marketing copy."""

    # 1. JSON-LD Product name — highest priority
    for item in get_all_jsonld_objects(soup):
        if item.get("@type") == "Product":
            name = item.get("name")

            if isinstance(name, str):
                name = name.strip()

                if name and len(name) < 200:
                    return name

    # 2. Product meta tags
    for attrs in [
        {"property": "og:title"},
        {"name": "twitter:title"},
        {"property": "product:name"},
        {"name": "product:name"},
    ]:
        meta = soup.find("meta", attrs=attrs)

        if meta and meta.get("content"):
            value = meta["content"].strip()

            if value and len(value) < 200:
                return value

    # 3. Look for explicit product title elements
    selectors = [
        "[itemprop='name']",
        ".product-title",
        ".product__title",
        ".product-name",
        "#product-title",
    ]

    for selector in selectors:
        element = soup.select_one(selector)

        if element:
            text = element.get_text(" ", strip=True)

            if text and len(text) < 200:
                return text

    # 4. H1 fallback — reject obvious marketing copy
    h1 = soup.find("h1")

    if h1:
        text = h1.get_text(" ", strip=True)

        marketing_prefixes = [
            "i love",
            "you will too",
            "why you'll love",
            "why you will love",
            "say goodbye",
            "discover",
            "experience",
        ]

        lower = text.lower()

        if text and len(text) < 200:
            if not any(lower.startswith(prefix) for prefix in marketing_prefixes):
                return text

    # 5. Page title fallback
    title = soup.find("title")

    if title:
        text = title.get_text(" ", strip=True)

        # Remove site/brand suffixes
        text = re.split(r"\s+\|\s+|\s+-\s+", text, maxsplit=1)[0].strip()

        if text and len(text) < 200:
            return text

    return None

def extract_category(soup: BeautifulSoup, product_name: str = None) -> Optional[str]:
    """Extract the product category."""

    # 1. JSON-LD Product category
    for item in get_all_jsonld_objects(soup):
        if item.get("@type") == "Product":
            category = item.get("category")

            if isinstance(category, str) and category.strip():
                normalized = normalize_product_category(category)
                if normalized and normalized.lower() not in ["skin care", "skincare", "beauty", "personal care", "health & beauty"]:
                    print(f"[EXTRACTION] Category from JSON-LD: {normalized}")
                    return normalized

    # 2. Meta category
    for attrs in [
        {"property": "product:category"},
        {"name": "product:category"},
    ]:
        meta = soup.find("meta", attrs=attrs)

        if meta and meta.get("content"):
            normalized = normalize_product_category(
                meta["content"]
            )
            if normalized and normalized.lower() not in ["skin care", "skincare", "beauty", "personal care", "health & beauty"]:
                print(f"[EXTRACTION] Category from meta tag: {normalized}")
                return normalized

    # 3. Breadcrumbs
    breadcrumb = (
        soup.find("nav", {"aria-label": re.compile("breadcrumb", re.I)})
        or soup.find(
            "ol",
            class_=re.compile("breadcrumb", re.I)
        )
        or soup.find(
            "ul",
            class_=re.compile("breadcrumb", re.I)
        )
    )

    if breadcrumb:
        items = breadcrumb.find_all(["li", "a"])

        texts = [
            item.get_text(" ", strip=True)
            for item in items
            if item.get_text(" ", strip=True)
        ]

        # Search backwards for a meaningful category
        for text in reversed(texts[:-1]):
            normalized = normalize_product_category(text)

            if normalized and normalized.lower() not in [
                "home",
                "products",
                "product",
            ]:
                print(f"[EXTRACTION] Category from breadcrumbs: {normalized}")
                return normalized

    # 4. Try to infer from product name as fallback
    if product_name:
        normalized_name = product_name.lower()
        category_map = {
            "serum": "Serum",
            "moisturizer": "Moisturizer",
            "cream": "Moisturizer",
            "cleanser": "Cleanser",
            "face wash": "Cleanser",
            "toner": "Toner",
            "sunscreen": "Sunscreen",
            "mask": "Mask",
        }
        
        for keyword, category in category_map.items():
            if keyword in normalized_name:
                print(f"[EXTRACTION] Category inferred from product name: {category}")
                return category

    print(f"[EXTRACTION] No category found, returning None")
    return None


def normalize_product_category(category: str) -> Optional[str]:
    """Normalize category to a simple SkinWise product category."""

    if not category:
        return None

    value = category.strip()

    # Take the final part of breadcrumb-style categories
    if ">" in value:
        value = value.split(">")[-1].strip()

    if "/" in value:
        parts = [p.strip() for p in value.split("/")]
        value = parts[-1]

    lower = value.lower()

    category_map = {
        "moisturizer": "Moisturizer",
        "moisturizers": "Moisturizer",
        "cream": "Moisturizer",
        "face cream": "Moisturizer",
        "body cream": "Moisturizer",
        "serum": "Serum",
        "cleanser": "Cleanser",
        "cleansers": "Cleanser",
        "toner": "Toner",
        "sunscreen": "Sunscreen",
        "sunscreens": "Sunscreen",
        "mask": "Mask",
        "masks": "Mask",
        "eye cream": "Eye Care",
        "lip balm": "Lip Care",
    }

    if lower in category_map:
        return category_map[lower]

    return value
    
def extract_main_purpose(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract main purpose of the product from actual product metadata only.
    
    Priority:
    1. JSON-LD Product description
    2. Meta description (first sentence only, validated)
    3. Product-specific description sections
    
    Rejects any content that looks like ingredient explanations or article text.
    """
    # 1. JSON-LD Product description (highest priority - cleanest source)
    for item in get_all_jsonld_objects(soup):
        if item.get("@type") == "Product":
            description = item.get("description")
            
            if isinstance(description, str) and description.strip():
                desc = description.strip()
                # Take first sentence if it's long
                if len(desc) > 200:
                    sentences = desc.split('.')
                    if sentences:
                        desc = sentences[0].strip()
                
                # Validate it's not contaminated with ingredient/article text
                is_contaminated, reason = is_contaminated_main_purpose(desc)
                if not is_contaminated and len(desc) < 200:
                    print(f"[EXTRACTION] Using main_purpose from JSON-LD")
                    return desc
                else:
                    print(f"[EXTRACTION] Rejecting contaminated JSON-LD description: {reason}")
    
    # 2. Meta description (second priority)
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        desc = meta_desc.get('content').strip()
        # First sentence often contains the main purpose
        sentences = desc.split('.')
        if sentences:
            first_sentence = sentences[0].strip()
            # Validate that the main purpose doesn't contain ingredient/article text
            is_contaminated, reason = is_contaminated_main_purpose(first_sentence)
            if not is_contaminated and len(first_sentence) < 200:
                print(f"[EXTRACTION] Using main_purpose from meta description")
                return first_sentence
            else:
                print(f"[EXTRACTION] Rejecting contaminated meta description: {reason}")
    
    # 3. Try og:description (third priority)
    og_desc = soup.find('meta', property='og:description')
    if og_desc and og_desc.get('content'):
        desc = og_desc.get('content').strip()
        # Take first sentence if it's long
        if len(desc) > 200:
            sentences = desc.split('.')
            if sentences:
                desc = sentences[0].strip()
        
        # Validate it's not contaminated
        is_contaminated, reason = is_contaminated_main_purpose(desc)
        if not is_contaminated and len(desc) < 200:
            print(f"[EXTRACTION] Using main_purpose from og:description")
            return desc
        else:
            print(f"[EXTRACTION] Rejecting contaminated og:description: {reason}")
    
    # 4. Product-specific description sections (last resort, with strict validation)
    purpose_patterns = [
        re.compile(r'purpose[:\s]*([^.]+)', re.I),
        re.compile(r'benefits[:\s]*([^.]+)', re.I),
        re.compile(r'what it does[:\s]*([^.]+)', re.I),
    ]
    
    # Search in main content areas, but be very strict
    for selector in ['div[class*="description"]', 'div[class*="about"]', 'div[class*="purpose"]']:
        element = soup.select_one(selector)
        if element:
            text = element.get_text()
            for pattern in purpose_patterns:
                match = pattern.search(text)
                if match:
                    purpose = match.group(1).strip()
                    if purpose and len(purpose) < 150:  # Stricter length limit for fallback
                        # Validate that the main purpose doesn't contain ingredient/article text
                        is_contaminated, reason = is_contaminated_ingredient_text(purpose)
                        if not is_contaminated:
                            print(f"[EXTRACTION] Using main_purpose from description section")
                            return purpose
                        else:
                            print(f"[EXTRACTION] Rejecting contaminated main_purpose from description section: {reason}")
    
    print(f"[EXTRACTION] Could not extract valid main_purpose from any source")
    return None

def extract_ingredients(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract the complete INCI ingredient list exactly as published.

    Priority:
    1. Dot & Key exact full-ingredients container
    2. Explicit "See Full Ingredients" section
    3. Ingredient-specific HTML sections
    4. Visible "Ingredients:" / "INCI:" text
    5. Aqua/Water/Glycerin fallback

    Never invent, reorder, summarize, or intentionally omit ingredients.
    """

    # ---------------------------------------------------------
    # 1. Dot & Key: exact full ingredient container (HIGHEST PRIORITY)
    # ---------------------------------------------------------
    full_ingredients = soup.find(
        "div",
        class_=re.compile(
            r"collapsable-hero-ingr__full-ingr-body",
            re.I
        )
    )

    if full_ingredients:
        # Get the text content directly from the container
        text = full_ingredients.get_text(" ", strip=True)

        # Remove disclaimer after the actual ingredient list
        text = re.split(
            r"Please be aware that our ingredient list",
            text,
            flags=re.IGNORECASE
        )[0].strip()

        # Remove any trailing footnotes like "* IFRA Certified"
        text = re.sub(r'\s*\*.*$', '', text, flags=re.IGNORECASE).strip()

        # Return immediately if we got a good ingredient list from this container
        # This prevents fallback methods from returning partial matches
        is_valid, validation_reason = is_valid_ingredient_list(text)
        if is_valid:
            cleaned = clean_ingredient_text(text)
            if cleaned:
                print(f"[EXTRACTION] Successfully extracted ingredient list from Dot & Key container")
                return cleaned
        else:
            print(f"[EXTRACTION] Dot & Key container validation failed: {validation_reason}")

    # ---------------------------------------------------------
    # 2. Explicit "See Full Ingredients" section
    # ---------------------------------------------------------
    for element in soup.find_all(
        string=re.compile(r"see\s+full\s+ingredients?", re.I)
    ):
        parent = element.parent

        if not parent:
            continue

        candidates = []

        # Parent container
        if parent.parent:
            candidates.append(parent.parent)

        # Immediate sibling
        if parent.next_sibling:
            candidates.append(parent.next_sibling)

        # Nearby elements
        container = parent.parent

        if container:
            candidates.extend(
                container.find_all_next(limit=5)
            )

        for candidate in candidates:
            if not hasattr(candidate, "get_text"):
                continue

            text = candidate.get_text(" ", strip=True)

            # Remove heading if included
            text = re.sub(
                r"^see\s+full\s+ingredients?\s*",
                "",
                text,
                flags=re.IGNORECASE
            ).strip()

            # Remove disclaimer
            text = re.split(
                r"Please be aware that our ingredient list",
                text,
                flags=re.IGNORECASE
            )[0].strip()

            is_valid, validation_reason = is_valid_ingredient_list(text)
            if is_valid:
                cleaned = clean_ingredient_text(text)
                if cleaned:
                    print(f"[EXTRACTION] Successfully extracted ingredient list from 'See Full Ingredients' section")
                    return cleaned
            else:
                print(f"[EXTRACTION] 'See Full Ingredients' section validation failed: {validation_reason}")

    # ---------------------------------------------------------
    # 3. Ingredient-specific HTML sections
    # ---------------------------------------------------------
    ingredient_selectors = [
        'div[class*="ingredient"]',
        'section[class*="ingredient"]',
        'div[id*="ingredient"]',
        'section[id*="ingredient"]',
        'table[class*="ingredient"]',
        'ul[class*="ingredient"]',
    ]

    for selector in ingredient_selectors:
        elements = soup.select(selector)

        for element in elements:
            text = element.get_text(" ", strip=True)

            # Remove disclaimer
            text = re.split(
                r"Please be aware that our ingredient list",
                text,
                flags=re.IGNORECASE
            )[0].strip()

            is_valid, validation_reason = is_valid_ingredient_list(text)
            if is_valid:
                cleaned = clean_ingredient_text(text)
                if cleaned:
                    print(f"[EXTRACTION] Successfully extracted ingredient list from ingredient-specific HTML section")
                    return cleaned
            else:
                print(f"[EXTRACTION] Ingredient-specific HTML section validation failed: {validation_reason}")

    # ---------------------------------------------------------
    # 3b. Direct leaf element check for INCI lists (Shopify metafields, accordions, custom tabs)
    # ---------------------------------------------------------
    for el in soup.find_all(['span', 'p', 'div', 'li']):
        if not el.find(['div', 'section', 'article', 'main']):
            text = el.get_text(" ", strip=True)
            if re.match(r'^(?:Water/Aqua|Aqua/Water|Aqua|Water|Glycerin)\s*,', text, re.I) and text.count(',') >= 4:
                is_valid, validation_reason = is_valid_ingredient_list(text)
                if is_valid:
                    cleaned = clean_ingredient_text(text)
                    if cleaned:
                        print(f"[EXTRACTION] Successfully extracted ingredient list from leaf element")
                        return cleaned

    # ---------------------------------------------------------
    # 4. Visible "Ingredients:" / "INCI:" text
    # ---------------------------------------------------------
    body_text = soup.get_text("\n", strip=True)

    ingredient_patterns = [
        r'(?:see\s+full\s+)?ingredients?\s*[:\-]\s*(.+?)(?=\n[A-Z][A-Za-z ]{2,40}\n|$)',
        r'full\s+ingredients?\s*[:\-]\s*(.+?)(?=\n[A-Z][A-Za-z ]{2,40}\n|$)',
        r'inci\s*[:\-]\s*(.+?)(?=\n[A-Z][A-Za-z ]{2,40}\n|$)',
    ]

    for pattern in ingredient_patterns:
        match = re.search(
            pattern,
            body_text,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            ingredient_text = match.group(1).strip()

            # Remove disclaimer
            ingredient_text = re.split(
                r"Please be aware that our ingredient list",
                ingredient_text,
                flags=re.IGNORECASE
            )[0].strip()

            is_valid, validation_reason = is_valid_ingredient_list(ingredient_text)
            if is_valid:
                cleaned = clean_ingredient_text(ingredient_text)
                if cleaned:
                    print(f"[EXTRACTION] Successfully extracted ingredient list from visible 'Ingredients:' text")
                    return cleaned
            else:
                print(f"[EXTRACTION] Visible 'Ingredients:' text validation failed: {validation_reason}")

    # ---------------------------------------------------------
    # 5. Aqua / Water / Glycerin fallback
    # ---------------------------------------------------------
    ingredient_start_patterns = [
        r'(?:Water/Aqua|Aqua/Water|Aqua|Water|Glycerin)\s*,.*?(?=\n\s*(?:Please be aware|Product Benefits|How To Use|FAQ|You might also like|Reviews|Related Products|\n\n|$))',
    ]

    for pattern in ingredient_start_patterns:
        match = re.search(
            pattern,
            body_text,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            ingredient_text = match.group(0).strip()

            # Remove disclaimer / known trailing content
            ingredient_text = re.split(
                r"Please be aware that our ingredient list",
                ingredient_text,
                flags=re.IGNORECASE
            )[0].strip()

            is_valid, validation_reason = is_valid_ingredient_list(ingredient_text)
            if is_valid:
                cleaned = clean_ingredient_text(ingredient_text)
                if cleaned:
                    print(f"[EXTRACTION] Successfully extracted ingredient list from Aqua/Water/Glycerin fallback")
                    return cleaned
            else:
                print(f"[EXTRACTION] Aqua/Water/Glycerin fallback validation failed: {validation_reason}")

    return None
    
def is_valid_ingredient_list(text: str) -> tuple[bool, str]:
    """
    Check if text is a valid, uncontaminated ingredient list.
    
    Returns (is_valid, reason) tuple.
    """
    if not text or len(text) < 20:
        return False, "Text too short"
    
    # First check for contamination
    is_contaminated, contamination_reason = is_contaminated_ingredient_text(text)
    if is_contaminated:
        return False, contamination_reason
    
    # Then check if it looks like an ingredient list
    if not is_likely_ingredient_list(text):
        return False, "Does not look like ingredient list"
    
    return True, "Valid ingredient list"

def is_likely_ingredient_list(text: str) -> bool:
    """Check if text looks like an ingredient list."""
    if not text or len(text) < 20:
        return False
    
    # Ingredient lists typically contain commas and chemical-looking terms
    comma_count = text.count(',')
    if comma_count < 2:  # Most products have multiple ingredients
        return False
    
    # Common ingredient patterns
    ingredient_indicators = [
        'water', 'aqua', 'alcohol', 'glycerin', 'niacinamide', 
        'acid', 'extract', 'oil', 'seed', 'fruit', 'leaf'
    ]
    
    text_lower = text.lower()
    indicator_count = sum(1 for indicator in ingredient_indicators if indicator in text_lower)
    
    return indicator_count >= 2

def clean_ingredient_text(text: str) -> str:
    """Clean ingredient text while preserving exact order and content."""
    # Remove extra whitespace but preserve commas and order
    cleaned = re.sub(r'\s+', ' ', text)
    cleaned = cleaned.strip()
    
    # Remove common prefixes/suffixes that aren't ingredients
    cleaned = re.sub(r'^ingredients?\s*[:\s]*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*[:\s]*ingredients?$', '', cleaned, flags=re.IGNORECASE)
    
    # Remove bullet points and numbering if present
    cleaned = re.sub(r'^[\d\.\-\*]+\s*', '', cleaned)
    
    # Remove trailing footnotes (like "* IFRA Certified")
    cleaned = re.sub(r'\s*\*.*$', '', cleaned, flags=re.IGNORECASE).strip()
    
    # Only apply aggressive marketing pattern removal if the text doesn't already look like a clean ingredient list
    # If it starts with Aqua/Water/Glycerin and has multiple commas, it's likely already clean
    if not (re.match(r'^(?:Water/Aqua|Aqua/Water|Aqua|Water|Glycerin)', cleaned, re.IGNORECASE) and cleaned.count(',') >= 4):
        # Remove marketing content that often appears before or after ingredients
        marketing_patterns = [
            r'hero ingredients.*?(?=[A-Z][a-z]+,)',
            r'powered by.*?(?=[A-Z][a-z]+,)',
            r'key benefits.*?(?=[A-Z][a-z]+,)',
            r'what it does.*?(?=[A-Z][a-z]+,)',
            r'full ingredients.*?(?=[A-Z][a-z]+,)',
            r'see full ingredients.*?(?=[A-Z][a-z]+,)',
            r'ingredient list.*?(?=[A-Z][a-z]+,)',
            r'please be aware.*$',  # Remove disclaimer text
            r'rest assured.*$',  # Remove reassurance text
            r'soft, supple skin.*?(?=[A-Z][a-z]+,)',  # Remove ending marketing before ingredients
            r'for.*?(?=[A-Z][a-z]+,)',  # Remove purpose statements before ingredients
        ]
        
        for pattern in marketing_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up any remaining marketing sections that might be mixed in
        # Look for patterns like "INGREDIENT NAME Description" and keep only the ingredient
        cleaned = re.sub(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+[A-Z][a-z].*?\.', r'\1', cleaned)
        
        # Find the start of actual ingredients (usually begins with Aqua, Water, or Glycerin)
        ingredient_start_pattern = r'(?:Aqua|Water|Glycerin)\s*,'
        match = re.search(ingredient_start_pattern, cleaned, re.IGNORECASE)
        if match:
            # Keep everything from the start of the first ingredient
            start_index = match.start()
            cleaned = cleaned[start_index:]
    
    return cleaned.strip()

def is_contaminated_ingredient_text(text: str) -> tuple[bool, str]:
    """
    Check if ingredient text is contaminated with webpage/article content.
    
    Returns (is_contaminated, reason) tuple.
    
    Rejects text containing markers from explanatory websites like Incidecoder:
    - "What-it-does:", "Also-called:", "Irritancy:", "Comedogenicity:"
    - "Read more", "Expand to read more"
    - "goodie", "Ingredient name"
    - Description paragraphs about ingredient functions
    """
    if not text:
        return False, ""
    
    text_lower = text.lower()
    
    # Markers that indicate explanatory webpage content, not actual INCI lists
    contamination_markers = [
        "what-it-does:",
        "also-called:",
        "irritancy:",
        "comedogenicity:",
        "read more",
        "expand to read more",
        "goodie",
        "ingredient name",
        "skin-identical ingredient",
        "what it does:",
        "also called:",
        "function:",
        "viscosity controlling",
    ]
    
    for marker in contamination_markers:
        if marker in text_lower:
            return True, f"Contains contamination marker: '{marker}'"
    
    # Check for patterns like "INGREDIENT: Description" which indicate explanatory content
    if re.search(r'[A-Z][a-z]+\s*:\s*[a-z]+', text):
        return True, "Contains ingredient-description pattern (explanatory content)"
    
    # Check for sentences with verbs (explanatory content)
    # Real ingredient lists don't typically have complete sentences
    sentence_patterns = [
        r'\b[A-Z][a-z]+\s+(?:is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|shall|should|can|could|may|might|must|ought)\s',
        r'\b[A-Z][a-z]+\s+(?:helps|helped|helping|works|worked|working|acts|acted|acting|serves|served|serving)\s',
    ]
    
    for pattern in sentence_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, "Contains explanatory sentences (not INCI list)"
    
    # Check for mixed content - both ingredients and descriptions
    # If text has both commas AND sentence structures, it's likely contaminated
    if text.count(',') > 0 and re.search(r'[.!?]', text):
        # Count sentence endings vs commas
        sentence_endings = len(re.findall(r'[.!?]', text))
        if sentence_endings > 2:  # More than 2 sentences likely means descriptive content
            return True, "Contains too many sentence endings (descriptive content)"
    
    return False, ""

def is_contaminated_main_purpose(text: str) -> tuple[bool, str]:
    """
    Check if main_purpose text is contaminated with ingredient/article content.
    
    This is less strict than is_contaminated_ingredient_text() because product
    descriptions naturally contain marketing language. We only want to block
    actual ingredient explanations and article content.
    
    Returns (is_contaminated, reason) tuple.
    """
    if not text:
        return False, ""
    
    text_lower = text.lower()
    
    # STRONG markers that indicate ingredient explanation content (not product descriptions)
    ingredient_explanation_markers = [
        "what-it-does:",
        "also-called:",
        "irritancy:",
        "comedogenicity:",
        "read more",
        "expand to read more",
        "goodie",
        "ingredient name",
        "skin-identical ingredient",
        "what it does:",
        "also called:",
        "function:",
        "viscosity controlling",
    ]
    
    for marker in ingredient_explanation_markers:
        if marker in text_lower:
            return True, f"Contains ingredient explanation marker: '{marker}'"
    
    # Check for ingredient-specific patterns that indicate explanatory content
    if re.search(r'[A-Z][a-z]+\s*:\s*[a-z]+', text):
        # But allow common product description patterns
        allowed_patterns = [
            r'benefits:\s*(?:for|your|skin)',
            r'purpose:\s*(?:to|for|your)',
            r'key\s+benefits:',
            r'main\s+benefits:',
        ]
        for allowed in allowed_patterns:
            if re.search(allowed, text, re.IGNORECASE):
                return False, ""
        
        return True, "Contains ingredient-description pattern (explanatory content)"
    
    # Check if it looks like an ingredient list (commas + chemical terms)
    # Product descriptions shouldn't look like ingredient lists
    comma_count = text.count(',')
    if comma_count > 5:  # Too many commas suggests ingredient list
        chemical_indicators = ['acid', 'extract', 'oil', 'seed', 'fruit', 'leaf', 'water', 'aqua', 'glycerin']
        chemical_count = sum(1 for indicator in chemical_indicators if indicator in text_lower)
        if chemical_count >= 3:
            return True, "Looks like ingredient list, not product description"
    
    return False, ""

def is_generic_logo_image(image_url: str) -> bool:
    """
    Check if an image URL appears to be a generic logo or site image rather than a product image.
    
    Args:
        image_url: The image URL to check
        
    Returns:
        True if likely a generic logo/site image, False if likely a product image
    """
    if not image_url:
        return True
    
    url_lower = image_url.lower()
    
    # Check if image filename is generic (strip query parameters first)
    clean_url = url_lower.split('?')[0]
    filename = clean_url.split('/')[-1]
    generic_filenames = [
        'logo.png',
        'logo.jpg',
        'logo.jpeg',
        'logo.svg',
        'logo.webp',
        'icon.png',
        'icon.jpg',
        'icon.svg',
        'favicon.ico',
        'default.jpg',
        'placeholder.jpg',
        'no-image.jpg',
    ]
    
    if filename in generic_filenames:
        return True
    
    # Check if path contains common logo directories
    logo_paths = ['/logo/', '/logos/', '/icons/', '/favicon/', '/branding/', '/assets/logo/']
    for path in logo_paths:
        if path in url_lower:
            return True
            
    # Generic logo/site image patterns (targeted to avoid false positives on CMS paths like 'brand-sites')
    logo_patterns = [
        'logo',
        'icon',
        'favicon',
        'site-logo',
        'brand-logo',
        'site_logo',
        'brand_logo',
        'sitelogo',
        'brandlogo',
        'header',
        'footer',
        'banner',
        'background',
        'avatar',
        'profile',
    ]
    
    # Check if URL contains logo-related keywords
    for pattern in logo_patterns:
        if pattern in url_lower:
            return True
    
    return False

def extract_image_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Extract main product image URL, filtering out generic logos."""
    # Try og:image meta tag
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        image_url = og_image.get('content').strip()
        if not is_generic_logo_image(image_url):
            return image_url
        else:
            print(f"[EXTRACTION] Rejected generic logo image from og:image: {image_url}")
    
    # Try other image meta tags
    for meta_property in ['twitter:image', 'product:image']:
        meta = soup.find('meta', property=meta_property)
        if not meta:
            meta = soup.find('meta', attrs={'name': meta_property})
        if meta and meta.get('content'):
            image_url = meta.get('content').strip()
            if not is_generic_logo_image(image_url):
                return image_url
            else:
                print(f"[EXTRACTION] Rejected generic logo image from {meta_property}: {image_url}")
    
    # Try JSON-LD
    json_ld = soup.find('script', type='application/ld+json')
    if json_ld:
        try:
            data = json.loads(json_ld.string)
            if isinstance(data, dict):
                if 'image' in data:
                    image = data['image']
                    if isinstance(image, list) and image:
                        image_url = image[0]
                        if not is_generic_logo_image(image_url):
                            return image_url
                        else:
                            print(f"[EXTRACTION] Rejected generic logo image from JSON-LD: {image_url}")
                    elif isinstance(image, str):
                        image_url = image.strip()
                        if not is_generic_logo_image(image_url):
                            return image_url
                        else:
                            print(f"[EXTRACTION] Rejected generic logo image from JSON-LD: {image_url}")
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'image' in item:
                        image = item['image']
                        if isinstance(image, list) and image:
                            image_url = image[0]
                            if not is_generic_logo_image(image_url):
                                return image_url
                            else:
                                print(f"[EXTRACTION] Rejected generic logo image from JSON-LD: {image_url}")
                        elif isinstance(image, str):
                            image_url = image.strip()
                            if not is_generic_logo_image(image_url):
                                return image_url
                            else:
                                print(f"[EXTRACTION] Rejected generic logo image from JSON-LD: {image_url}")
        except:
            pass
    
    # Try to find main product image in content
    main_image = soup.find('img', class_=re.compile(r'product|main|primary', re.I))
    if main_image and main_image.get('src'):
        image_url = main_image.get('src').strip()
        if not is_generic_logo_image(image_url):
            return image_url
        else:
            print(f"[EXTRACTION] Rejected generic logo image from product img: {image_url}")
    
    # Fallback to first large image (with validation)
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src and (src.endswith('.jpg') or src.endswith('.png') or src.endswith('.jpeg')):
            # Make URL absolute if relative
            if src.startswith('//'):
                image_url = 'https:' + src
            elif src.startswith('/'):
                from urllib.parse import urljoin
                image_url = urljoin(base_url, src)
            else:
                image_url = src.strip()
            
            if not is_generic_logo_image(image_url):
                return image_url
    
    print(f"[EXTRACTION] Could not find valid product image (all appear to be generic logos)")
    return None