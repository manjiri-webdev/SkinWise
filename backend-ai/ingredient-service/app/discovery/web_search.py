from ddgs import DDGS
from typing import List, Dict, Optional
from urllib.parse import urlparse
import re
from app.discovery.source_selector import is_official_brand_site

def search_products(product_name: str, brand: Optional[str] = None, max_results: int = 15) -> List[Dict]:
    """
    Search for cosmetic products using DuckDuckGo.
    """
    ddgs = DDGS()
    results = []

    if brand:
        brand_clean = brand.strip()
        prod_clean = product_name.strip()
        if prod_clean.lower().startswith(brand_clean.lower()):
            query = prod_clean
        else:
            query = f'{brand_clean} {prod_clean}'
    else:
        query = f'"{product_name}" skincare'

    try:
        search_results = []

        query_variants = [
            query,
            query.replace("&", "and"),
            f'site:{get_brand_domain(brand)} "{product_name}"' if brand and get_brand_domain(brand) else None,
            f'"{brand}" "{product_name}" official' if brand else query,
        ]

        for q in query_variants:
            if not q:
                continue

            try:
                found = list(
                    ddgs.text(
                        q,
                        max_results=max_results,
                        region="in-en"
                    )
                )

                if found:
                    print(f"Search succeeded with query: {q}")
                    search_results.extend(found)

            except Exception as e:
                print(f"Search failed for '{q}': {e}")
                continue

        # Fallback queries if no results found
        if not search_results:
            print("No results from initial queries, trying fallback queries...")
            
            # Generate fallback queries by progressively simplifying
            fallback_queries = []
            
            # Replace + with "and" and spaces
            fallback_queries.append(query.replace("+", " and "))
            fallback_queries.append(query.replace("+", " "))
            
            # Remove % signs
            fallback_queries.append(query.replace("%", ""))
            
            # Remove specific suffixes like "+ E", "+ C", etc.
            simplified_product = re.sub(r'\s*\+\s*[A-Z]$', '', product_name, flags=re.IGNORECASE)
            if simplified_product != product_name:
                if brand:
                    fallback_queries.append(f'{brand} {simplified_product}')
                else:
                    fallback_queries.append(f'"{simplified_product}" skincare')
            
            # Extract important keywords and search with brand
            if brand:
                # Remove common words and keep key product terms
                keywords = re.sub(r'\b(?:with|for|the|and|or|a|an)\b', '', product_name, flags=re.IGNORECASE)
                keywords = ' '.join(keywords.split())  # Clean up spaces
                if keywords:
                    fallback_queries.append(f'{brand} {keywords}')
                
                # Try just the brand + main product type (serum, moisturizer, etc.)
                product_type = re.search(r'(serum|moisturizer|sunscreen|cream|lotion|face wash|cleanser)', product_name, re.IGNORECASE)
                if product_type:
                    fallback_queries.append(f'{brand} {product_type.group(1)}')
            
            # Official domain query without strict quotes
            if brand and get_brand_domain(brand):
                fallback_queries.append(f'site:{get_brand_domain(brand)} {product_name}')
            
            # Try broader brand-only search
            if brand:
                fallback_queries.append(f'{brand} skincare products')
            
            # Try product name without quotes
            if not brand:
                fallback_queries.append(f'{product_name} skincare')
            
            # Remove duplicates and try fallback queries
            fallback_queries = list(set(fallback_queries))
            
            for q in fallback_queries:
                if not q or q in query_variants:
                    continue
                
                try:
                    found = list(
                        ddgs.text(
                            q,
                            max_results=max_results,
                            region="in-en"
                        )
                    )

                    if found:
                        print(f"Fallback search succeeded with query: {q}")
                        search_results.extend(found)
                        break  # Stop after first successful fallback

                except Exception as e:
                    print(f"Fallback search failed for '{q}': {e}")
                    continue

        # Remove duplicate URLs and normalize result keys
        unique = {}
        for result in search_results:
            url = result.get("href", "")
            if url:
                # Normalize result keys to match what matcher expects
                normalized_result = {
                    "url": url,
                    "title": result.get("title", ""),
                    "body": result.get("body", ""),
                    "is_official": is_official_brand_site(url, brand) if brand else False
                }
                unique[url] = normalized_result

        search_results = list(unique.values())
        
        print(f"DISCOVERY RAW RESULTS: {len(search_results)}")
        for r in search_results[:10]:
            print("RAW:", r.get("title"), "|", r.get("url"))

    except Exception as e:
        print(f"Search error for query '{query}': {e}")
        return []

    # Assign search results to results
    results = search_results

    # Image search is kept, but only after text results are successfully found
    if results:
        results = add_images_to_results(
            results,
            f"{brand} {product_name}" if brand else product_name
        )

    return results

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
        "the ordinary": "theordinary.com",
        "ordinary": "theordinary.com",
        "deciem": "theordinary.com",
        "plum": "plumgoodness.com",
        "re'equil": "reequil.com",
        "reequil": "reequil.com",
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
    Attach a product-specific image to each search result.

    Priority:
    1. Direct product-page image for official brand sites
    2. Existing DuckDuckGo image matching as fallback
    """

    from app.ingredients.service import normalize_name
    from urllib.parse import urlparse
    import requests
    from bs4 import BeautifulSoup
    import json

    ddgs = DDGS()

    def domain(url: str) -> str:
        try:
            return urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            return ""

    def token_similarity(text1: str, text2: str) -> float:
        tokens1 = set(normalize_name(text1).split())
        tokens2 = set(normalize_name(text2).split())

        if not tokens1 or not tokens2:
            return 0.0

        return len(tokens1 & tokens2) / len(tokens1 | tokens2)

    def extract_direct_product_image(product_url: str) -> Optional[str]:
        """
        Extract the main image directly from the product page.
        Uses the same sources as the detailed extractor.
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }

            response = requests.get(
                product_url,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 1. og:image
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                return og_image.get("content").strip()

            # 2. Twitter/product image
            for meta_property in [
                "twitter:image",
                "product:image"
            ]:
                meta = soup.find("meta", property=meta_property)

                if not meta:
                    meta = soup.find(
                        "meta",
                        attrs={"name": meta_property}
                    )

                if meta and meta.get("content"):
                    return meta.get("content").strip()

            # 3. JSON-LD
            json_ld = soup.find(
                "script",
                type="application/ld+json"
            )

            if json_ld:
                try:
                    data = json.loads(json_ld.string or "")

                    items = data if isinstance(data, list) else [data]

                    for item in items:
                        if not isinstance(item, dict):
                            continue

                        image = item.get("image")

                        if isinstance(image, list) and image:
                            return str(image[0]).strip()

                        if isinstance(image, str) and image.strip():
                            return image.strip()

                except Exception:
                    pass

            # 4. Product/main/primary image
            main_image = soup.find(
                "img",
                class_=re.compile(
                    r"product|main|primary",
                    re.IGNORECASE
                )
            )

            if main_image:
                src = (
                    main_image.get("src")
                    or main_image.get("data-src")
                    or main_image.get("data-image")
                )

                if src:
                    if src.startswith("//"):
                        return "https:" + src

                    if src.startswith("/"):
                        from urllib.parse import urljoin
                        return urljoin(product_url, src)

                    return src.strip()

        except Exception as e:
            print(
                f"Direct product image extraction failed "
                f"for '{product_url}': {e}"
            )

        return None

    try:
        for result in results:
            result["image"] = None

            product_title = result.get("title", "")
            product_url = result.get("url", "")
            is_official = result.get("is_official", False)

            if not product_url:
                continue

            # -------------------------------------------------
            # 1. OFFICIAL PRODUCT PAGE -> DIRECT IMAGE
            # -------------------------------------------------
            if is_official:
                direct_image = extract_direct_product_image(
                    product_url
                )

                if direct_image:
                    result["image"] = direct_image
                    print(
                        f"Direct product image found: "
                        f"{product_url}"
                    )
                    continue

            # -------------------------------------------------
            # 2. FALLBACK -> DUCKDUCKGO IMAGE SEARCH
            # -------------------------------------------------
            if not product_title:
                continue

            product_domain = domain(product_url)

            image_queries = [
                f'"{product_title}"',
                f'{product_title} {image_query.split()[0] if image_query else ""}'
            ]

            best_image = None
            best_score = 0.0

            for query in image_queries:
                try:
                    image_results = list(
                        ddgs.images(
                            query.strip(),
                            max_results=12
                        )
                    )

                    for img_result in image_results:
                        img_url = img_result.get("image", "")
                        source_url = img_result.get("url", "")
                        img_title = img_result.get("title", "")

                        if not img_url:
                            continue

                        score = 0.0

                        # Same source domain
                        if (
                            source_url
                            and product_domain
                            and domain(source_url) == product_domain
                        ):
                            score += 0.3

                        # Product-name similarity
                        combined_text = (
                            f"{img_title} "
                            f"{source_url} "
                            f"{img_url}"
                        )

                        name_score = token_similarity(
                            product_title,
                            combined_text
                        )

                        score += name_score * 0.7

                        if score > best_score:
                            best_score = score
                            best_image = img_url

                    if best_score >= 0.8:
                        break

                except Exception as e:
                    print(
                        f"Image search failed for "
                        f"'{query}': {e}"
                    )
                    continue

            if best_image and best_score >= 0.35:
                result["image"] = best_image

    except Exception as e:
        print(f"Image processing error: {e}")

    return results