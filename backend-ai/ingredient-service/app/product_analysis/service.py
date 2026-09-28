import json
import time
from typing import Dict, List, Optional
from google.genai import types
from app.products.service import find_product
from app.ingredients.service import find_ingredient, normalize_ingredient_for_lookup
from app.discovery.service import discover_products
from app.discovery.detailed_extraction import extract_product_from_url
from app.research_gemini.service import GeminiResearchService
from app.research_gemini.parser import parse_ingredient_list
from app.database.supabase import insert_product, insert_ingredient


class ProductAnalysisService:
    """
    Product Analysis Service: Product + Ingredient database reuse service.
    
    This service implements intelligent database reuse:
    - Checks Supabase first for existing products and ingredients
    - Only runs discovery/extraction/research when data is missing
    - Inserts new records when discovered
    - Processes ingredients sequentially
    """
    
    def __init__(self):
        self.gemini_service = GeminiResearchService()
    
    def analyze_product_with_reuse(
        self,
        product_name: str,
        brand: Optional[str] = None,
        source_url: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict:
        """
        Analyze a product with intelligent database reuse.
        
        Flow:
        1. Check Supabase for existing product (brand + product_name match)
        2. If found, use existing product data
        3. If not found, run discovery + extraction and insert new product
        4. Process ingredients sequentially:
           - Check Supabase for each ingredient
           - If found, use existing ingredient data
           - If not found, run Gemini research and insert new ingredient
        5. Return complete analysis
        
        Args:
            product_name: Product name to analyze
            brand: Optional brand name
            source_url: Optional source URL to skip discovery if provided
            category: Optional product category
            
        Returns:
            Dictionary with product data, ingredient research results, and metadata
        """
        if not product_name or not product_name.strip():
            return {
                "success": False,
                "error": "product_name is required"
            }
        
        product_name = product_name.strip()
        brand = brand.strip() if brand else ""
        
        if not brand:
            # Try extracting brand from product name
            from app.products.service import _extract_brand_from_name
            extracted_brand, remaining_name = _extract_brand_from_name(product_name)
            if extracted_brand:
                brand = extracted_brand
                if remaining_name:
                    product_name = remaining_name
            else:
                # Check if catalog has a product matching product_name
                catalog_products = find_product(None, product_name)
                if catalog_products:
                    brand = catalog_products[0].get("brand") or ""
        
        # Step 1: Check Supabase for existing product
        existing_products = find_product(brand if brand else None, product_name)
        
        if existing_products:
            # Use existing product
            product = existing_products[0]
            product_source = "database"
            print(f"[OK] Found existing product in database: {brand} - {product_name}")
        else:
            # Run discovery + extraction
            print(f"[INFO] Product not found in database, running discovery: {brand} - {product_name}")
            product_result = self._discover_and_extract_product(product_name, brand, source_url, category)
            
            if not product_result.get("success"):
                return {
                    "success": False,
                    "error": f"Product discovery failed: {product_result.get('error', 'Unknown error')}"
                }
            
            product = product_result["data"]
            
            # Apply category fallback if category was provided and extracted category is missing/generic
            if category and (not product.get("category") or product.get("category").lower() in ["skin care", "skincare"]):
                product["category"] = category
            
            # Update brand from extracted product if it was discovered
            if not brand and product.get("brand"):
                brand = product.get("brand")
            
            # Log if we're using fallback data
            if product_result.get("fallback"):
                print(f"[WARN] Using fallback product data: {product_result.get('warning')}")
            
            # Insert to database if we have an ingredient list
            if product.get("full_ingredient_list"):
                insert_result = self._insert_product_to_database(product)
                
                if insert_result.get("success") and insert_result.get("data"):
                    print(f"[OK] Inserted new product into database: {brand} - {product_name}")
                    product = insert_result["data"]
                else:
                    print(f"[WARN] Failed to insert product to database: {insert_result.get('error')}")
            else:
                print(f"[INFO] Skipping database insert for fallback/minimal data (no ingredients)")
            
            product_source = "discovery"
        
        # Step 2: Process ingredients sequentially
        ingredient_list = self._extract_ingredient_list(product)
        
        if not ingredient_list:
            # Return product data even without ingredients
            warning_msg = product.get("extraction_error") or product.get("discovery_error") or "No ingredient list found"
            return {
                "success": True,
                "product": product,
                "product_source": product_source,
                "total_ingredients": 0,
                "ingredients": [],
                "database_reuse_stats": {
                    "products_reused": 1 if product_source == "database" else 0,
                    "products_created": 1 if product_source == "discovery" else 0,
                    "ingredients_reused": 0,
                    "ingredients_created": 0
                },
                "warning": f"No ingredients available: {warning_msg}"
            }
        
        print(f"Processing {len(ingredient_list)} ingredients sequentially...")
        
        ingredient_results = []
        ingredients_reused = 0
        ingredients_created = 0
        ingredients_researched = 0
        ingredient_insert_failures = 0
        
        for ingredient_name in ingredient_list:
            print(f"  Processing ingredient: {ingredient_name}")
            
            # Check Supabase for existing ingredient
            existing_ingredient = find_ingredient(ingredient_name)
            
            if existing_ingredient["found"]:
                # Use existing ingredient
                ingredient_results.append({
                    "ingredient": ingredient_name,
                    "source": "database",
                    "matched_by": existing_ingredient["matched_by"],
                    "matched_name": existing_ingredient["matched_name"],
                    "data": existing_ingredient["data"]
                })
                ingredients_reused += 1
                print(f"    [OK] Found in database (matched by: {existing_ingredient['matched_by']})")
            else:
                # Run Gemini research
                print(f"    [INFO] Not found in database, running Gemini research...")
                research_result = self.gemini_service.research_ingredient(ingredient_name)
                ingredients_researched += 1
                
                # Check if research result has usable data before insertion
                if self._has_usable_research_data(research_result):
                    # Insert new ingredient into database
                    print(f"    [INFO] Attempting Supabase insert for '{ingredient_name}'...")
                    insert_result = self._insert_ingredient_to_database(research_result)
                    
                    print(f"    [INFO] Supabase insert response - success: {insert_result.get('success')}, error: {insert_result.get('error')}")
                    
                    if insert_result.get("success"):
                        ingredient_results.append({
                            "ingredient": ingredient_name,
                            "source": "research",
                            "data": insert_result["data"]
                        })
                        ingredients_created += 1
                        print(f"    [OK] Researched and inserted to database")
                    else:
                        # Insert failed - log the error and don't count as created
                        ingredient_insert_failures += 1
                        error_msg = insert_result.get('error', 'Unknown error')
                        print(f"    [ERROR] Supabase insert failed for '{ingredient_name}': {error_msg}")
                        # Still return the research result even if insert failed
                        ingredient_results.append({
                            "ingredient": ingredient_name,
                            "source": "research",
                            "data": research_result.model_dump(),
                            "insert_error": error_msg
                        })
                else:
                    # Research result has no usable data - do not insert
                    print(f"    [WARN] Research result has no usable data - skipping database insertion")
                    ingredient_results.append({
                        "ingredient": ingredient_name,
                        "source": "research",
                        "data": research_result.model_dump(),
                        "skipped": "no_usable_data"
                    })
                    # Don't count as created since we didn't insert
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        return {
            "success": True,
            "product": product,
            "product_source": product_source,
            "total_ingredients": len(ingredient_list),
            "ingredients": ingredient_results,
            "database_reuse_stats": {
                "products_reused": 1 if product_source == "database" else 0,
                "products_created": 1 if product_source == "discovery" else 0,
                "ingredients_reused": ingredients_reused,
                "ingredients_researched": ingredients_researched,
                "ingredients_created": ingredients_created,
                "ingredient_insert_failures": ingredient_insert_failures
            }
        }
    
    def _gemini_extract_product_formulation(
        self,
        product_name: str,
        brand: Optional[str] = None,
        image_url: Optional[str] = None,
        category: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Use Gemini 3.5 Flash Lite to extract official product formulation and INCI ingredient list.
        Used as a high-accuracy fallback when web scrapers are blocked or fail to parse HTML.
        """
        prompt = f"""
You are an expert cosmetic formulation scientist and INCI database analyst.
Retrieve the official product formulation and full INCI ingredient list for:

Brand: {brand or 'Unknown'}
Product Name: {product_name}
Category: {category or 'Skincare'}

Requirements:
1. "brand": The exact official brand name.
2. "product_name": The standardized commercial product name.
3. "category": Standard skincare category (e.g. Exfoliant, Serum, Moisturizer, Cleanser, Toner, Sunscreen, Mask).
4. "main_purpose": Concise description of what the product does.
5. "full_ingredient_list": The COMPLETE, exact official INCI ingredient list separated by commas, in order of concentration (standard INCI declaration). Do not omit or summarize any ingredients.
"""
        try:
            print(f"[GEMINI] Extracting formulation for '{brand} - {product_name}'...")
            response = self.gemini_service.client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "brand": {"type": "string"},
                            "product_name": {"type": "string"},
                            "category": {"type": "string"},
                            "main_purpose": {"type": "string"},
                            "full_ingredient_list": {"type": "string"},
                        },
                        "required": ["product_name", "full_ingredient_list"],
                    },
                ),
            )
            
            raw_text = response.text
            if not raw_text and response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if getattr(part, "text", None):
                        raw_text = part.text
                        break
            
            if not raw_text:
                print(f"[GEMINI] Empty response text from Gemini for '{product_name}'")
                return None
                
            data = json.loads(raw_text)
            full_list = data.get("full_ingredient_list")
            if not full_list or len(full_list.strip()) < 5:
                print(f"[GEMINI] No valid full_ingredient_list returned for '{product_name}'")
                return None
                
            extracted_brand = data.get("brand") or brand or ""
            extracted_name = data.get("product_name") or product_name
            extracted_category = data.get("category") or category
            
            parsed_list = parse_ingredient_list(full_list)
            normalized_pipe = " | ".join(parsed_list) if parsed_list else full_list
            
            return {
                "brand": extracted_brand,
                "product_name": extracted_name,
                "category": extracted_category,
                "main_purpose": data.get("main_purpose") or f"{extracted_brand} {extracted_name}",
                "full_ingredient_list": full_list.strip(),
                "normalized_ingredients": normalized_pipe,
                "image_url": image_url
            }
        except Exception as e:
            print(f"[GEMINI] Error extracting product formulation: {e}")
            return None

    def _discover_and_extract_product(
        self,
        product_name: str,
        brand: str,
        source_url: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict:
        """
        Discover and extract product data with robust multi-stage fallbacks:
        1. If source_url provided: attempt web scraping from that URL.
        2. If discovery needed or source_url scrape yielded no ingredients:
           - Run discovery to get candidate URLs.
           - Try extracting from candidates in rank order.
        3. If web extraction failed or produced no ingredient list:
           - Use Gemini formulation extraction to retrieve accurate INCI list.
        4. If all fail, return minimal fallback data.
        """
        best_image_url = None
        best_category = category

        # Step 1: If source_url is provided, try extracting from it
        if source_url:
            print(f"[INFO] Using provided source_url: {source_url}")
            extraction_result = extract_product_from_url(source_url)
            
            if extraction_result.get("success") and extraction_result.get("data", {}).get("full_ingredient_list"):
                print(f"[OK] Successfully extracted product from provided source_url: {source_url}")
                return {
                    "success": True,
                    "data": extraction_result["data"]
                }
            
            print(f"[WARN] Extraction from provided source_url did not yield ingredients: {extraction_result.get('error')}")

        # Step 2: Run discovery to find candidate product pages
        print(f"[INFO] Discovering product candidate sources for: {brand} - {product_name}")
        discovery_result = discover_products(product_name, brand)
        options = discovery_result.get("options", []) if discovery_result.get("success") else []
        
        # Step 3: Try extracting from candidate options in rank order
        for option in options:
            cand_url = option.get("source_url")
            if not best_image_url and option.get("image_url"):
                best_image_url = option.get("image_url")
            if not best_category and option.get("category"):
                best_category = option.get("category")
                
            if not cand_url or cand_url == source_url:
                continue
                
            print(f"[INFO] Attempting extraction from candidate: {cand_url}")
            ext_res = extract_product_from_url(cand_url)
            if ext_res.get("success") and ext_res.get("data", {}).get("full_ingredient_list"):
                extracted_data = ext_res["data"]
                if not extracted_data.get("image_url") and best_image_url:
                    extracted_data["image_url"] = best_image_url
                if not extracted_data.get("category") and best_category:
                    extracted_data["category"] = best_category
                return {
                    "success": True,
                    "data": extracted_data
                }

        # Step 4: Fallback to Gemini AI formulation extraction
        print(f"[INFO] Web extraction did not yield ingredients. Attempting Gemini formulation fallback for {brand} - {product_name}...")
        gemini_product = self._gemini_extract_product_formulation(
            product_name=product_name,
            brand=brand,
            image_url=best_image_url or (options[0].get("image_url") if options else None),
            category=best_category or (options[0].get("category") if options else category)
        )
        if gemini_product and gemini_product.get("full_ingredient_list"):
            print(f"[OK] Successfully extracted product formulation via Gemini for {brand} - {product_name}")
            return {
                "success": True,
                "data": gemini_product,
                "source": "gemini_formulation"
            }

        # Step 5: Exhausted all extraction and AI methods — return minimal fallback
        fallback_data = {
            "brand": brand,
            "product_name": product_name,
            "category": best_category or (options[0].get("category") if options else category),
            "main_purpose": f"{brand} {product_name}",
            "full_ingredient_list": None,
            "image_url": best_image_url or (options[0].get("image_url") if options else None),
            "discovery_error": "All web extraction candidates and Gemini formulation fallback exhausted"
        }
        return {
            "success": True,
            "data": fallback_data,
            "fallback": True,
            "warning": "No ingredients could be extracted, using minimal product data"
        }
    
    def _extract_ingredient_list(self, product: Dict) -> List[str]:
        """
        Extract and parse ingredient list from product data.
        
        Args:
            product: Product dictionary
            
        Returns:
            List of deduplicated ingredient names
        """
        # Try normalized_ingredients first (pipe-separated)
        normalized = product.get("normalized_ingredients")
        
        if normalized:
            ingredients = [
                item.strip()
                for item in normalized.split("|")
                if item.strip()
            ]
            return self._deduplicate_ingredients(ingredients)
        
        # Fall back to full_ingredient_list
        full_list = product.get("full_ingredient_list")
        
        if full_list:
            print(f"[EXTRACTION] Raw extracted ingredient text: {full_list[:200]}...")
            
            # Try to parse as comma-separated list
            if "," in full_list:
                parsed_ingredients = parse_ingredient_list(full_list)
                print(f"[EXTRACTION] Parsed ingredient count: {len(parsed_ingredients)}")
                deduplicated = self._deduplicate_ingredients(parsed_ingredients)
                print(f"[EXTRACTION] Final ingredient count after deduplication: {len(deduplicated)}")
                print(f"[EXTRACTION] Final ingredient names: {deduplicated}")
                return deduplicated
            else:
                # Treat as single ingredient
                single_ingredient = [full_list.strip()] if full_list.strip() else []
                print(f"[EXTRACTION] Single ingredient: {single_ingredient}")
                return single_ingredient
        
        print(f"[EXTRACTION] No ingredient list found in product data")
        return []
    
    def _deduplicate_ingredients(self, ingredients: List[str]) -> List[str]:
        """
        Deduplicate ingredient names while preserving order.
        
        Args:
            ingredients: List of ingredient names
            
        Returns:
            Deduplicated list of ingredient names
        """
        seen = set()
        deduplicated = []
        
        for ingredient in ingredients:
            # Normalize for comparison but preserve original for output
            normalized = ingredient.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduplicated.append(ingredient.strip())
        
        return deduplicated
    
    def _insert_product_to_database(self, product_data: Dict) -> Dict:
        """
        Insert product data into Supabase products table.
        Ensures normalized_ingredients is populated.
        If insertion fails (e.g. duplicate or conflict), retrieves existing product.
        
        Args:
            product_data: Product data dictionary
            
        Returns:
            Dictionary with success status and inserted data
        """
        full_list = product_data.get("full_ingredient_list")
        normalized = product_data.get("normalized_ingredients")
        
        # Ensure normalized_ingredients is populated if we have full_ingredient_list
        if not normalized and full_list:
            parsed = parse_ingredient_list(full_list)
            normalized = " | ".join(parsed) if parsed else full_list
            product_data["normalized_ingredients"] = normalized
            
        # Prepare data for insertion (only include required fields)
        insert_data = {
            "brand": product_data.get("brand"),
            "category": product_data.get("category"),
            "product_name": product_data.get("product_name"),
            "main_purpose": product_data.get("main_purpose"),
            "full_ingredient_list": full_list,
            "normalized_ingredients": normalized,
            "image_url": product_data.get("image_url")
        }
        
        # Log category value for debugging
        print(f"[INSERT] Category value before insert: {insert_data.get('category')}")
        print(f"[INSERT] Inserting product: {insert_data.get('brand')} - {insert_data.get('product_name')}")
        
        result = insert_product(insert_data)
        
        if result.get("success") and result.get("data"):
            print(f"[INSERT] Successfully inserted product: ID {result['data'].get('product_id')}")
            return result
        
        # On insert failure (e.g. duplicate or constraint), check if product already exists
        print(f"[INSERT] Supabase insert failed: {result.get('error')}. Checking if product already exists...")
        existing = find_product(product_data.get("brand"), product_data.get("product_name"))
        if existing:
            print(f"[INSERT] Recovered existing product ID: {existing[0].get('product_id')}")
            return {
                "success": True,
                "data": existing[0]
            }
        
        return result
    
    def _insert_ingredient_to_database(self, research_result) -> Dict:
        """
        Insert ingredient research result into Supabase ingredients table.
        
        Args:
            research_result: IngredientResearchResult from Gemini service
            
        Returns:
            Dictionary with success status and inserted data
        """
        # Convert research result to dictionary
        if hasattr(research_result, 'model_dump'):
            ingredient_data = research_result.model_dump()
        else:
            ingredient_data = research_result
        
        # Prepare data for insertion
        insert_data = {
            "ingredient": ingredient_data.get("ingredient"),
            "ingredient_type": ingredient_data.get("ingredient_type"),
            "function": ingredient_data.get("function"),
            "benefits": ingredient_data.get("benefits"),
            "suitable_skin_types": ingredient_data.get("suitable_skin_types"),
            "skin_concerns": ingredient_data.get("skin_concerns"),
            "irritation_risk": ingredient_data.get("irritation_risk"),
            "irritation_notes": ingredient_data.get("irritation_notes"),
            "allergy_sensitization": ingredient_data.get("allergy_sensitization"),
            "who_should_avoid": ingredient_data.get("who_should_avoid"),
            "pregnancy_safety": ingredient_data.get("pregnancy_safety"),
            "pregnancy_notes": ingredient_data.get("pregnancy_notes"),
            "interactions_with_other_ingredients": ingredient_data.get("interactions_with_other_ingredients"),
            "evidence_source": ingredient_data.get("evidence_source"),
            "canonical_name": ingredient_data.get("canonical_name"),
            "aliases": ingredient_data.get("aliases"),
            "research_status": "completed" if ingredient_data.get("ingredient_type") else "partial"
        }
        
        return insert_ingredient(insert_data)
    
    def _has_usable_research_data(self, research_result) -> bool:
        """
        Check if research result has usable research data.
        
        A research result is considered usable if it contains at least
        one of the core research fields (ingredient_type, function, benefits).
        
        Args:
            research_result: IngredientResearchResult from Gemini service
            
        Returns:
            True if has usable data, False otherwise
        """
        # Convert to dictionary if needed
        if hasattr(research_result, 'model_dump'):
            data = research_result.model_dump()
        else:
            data = research_result
        
        # Check for core research fields
        core_fields = [
            data.get("ingredient_type"),
            data.get("function"),
            data.get("benefits")
        ]
        
        # Consider it usable if at least one core field has data
        has_data = any(field for field in core_fields if field)
        
        return has_data
