import supabase_config
from typing import Dict, List, Optional, Any
import requests
import os
from dotenv import load_dotenv

load_dotenv()


class RecommendationService:
    """
    Minimum MVP Product Recommendation Engine for SkinWise.
    
    For each missing routine step:
    1. Search Supabase products by category
    2. If 3+ usable candidates exist, use catalog only
    3. If fewer than 3, trigger grounded Gemini discovery
    4. Send discovered candidates through existing extraction/analysis pipeline
    5. Evaluate using existing evaluate_product_suitability()
    6. Rank deterministically: KEEP > CAUTION, then confidence, then score, then product_id
    7. Return at most 3 recommendations per step
    """
    
    def __init__(self):
        self.supabase = supabase_config.supabase
        self.ingredient_service_url = os.getenv("INGREDIENT_SERVICE_URL", "http://localhost:8001")
    
    def _map_step_to_category(self, step: str) -> str:
        """
        Map routine step to product category for catalog search.
        """
        step_lower = step.lower()
        
        if "cleanser" in step_lower:
            return "cleanser"
        elif "sunscreen" in step_lower:
            return "sunscreen"
        elif "treatment" in step_lower:
            return "serum"
        elif "moisturizer" in step_lower:
            return "moisturizer"
        else:
            return "cleanser"  # Default fallback
    
    def _search_catalog_by_category(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search Supabase products by category.
        """
        try:
            category_map = {
                "cleanser": ["cleanser", "face wash"],
                "sunscreen": ["sunscreen", "spf"],
                "serum": ["serum", "toner", "treatment"],
                "moisturizer": ["moisturizer", "cream", "lotion"]
            }
            
            search_terms = category_map.get(category, [category])
            
            # Build OR query for category only (product_type column doesn't exist)
            all_products = []
            for term in search_terms:
                response = self.supabase.table("products").select("*").ilike("category", f"%{term}%").limit(limit).execute()
                if response.data:
                    all_products.extend(response.data)
            
            # Deduplicate by product_id
            seen_ids = set()
            unique_products = []
            for p in all_products:
                pid = p.get("product_id")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    unique_products.append(p)
            
            return unique_products[:limit]
        except Exception as e:
            print(f"Error searching catalog by category: {e}")
            return []
    
    def _discover_products_with_gemini(self, category: str, user_data: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Use Gemini to discover real candidate products with user context.
        Gemini ONLY returns: brand, product_name, source_url, category
        NO safety decisions, ingredient lists, or recommendations.
        """
        try:
            # Extract user context for discovery
            profile = user_data.get("profile") or {}
            skin_type = profile.get("skin_type", "Not specified")
            skin_concerns = profile.get("skin_concerns", [])
            skincare_goals = profile.get("skincare_goals", [])
            skin_sensitivity = profile.get("skin_sensitivity", "Not specified")
            
            # Construct prompt for Gemini
            category_descriptions = {
                "cleanser": "gentle face cleanser suitable for daily use",
                "sunscreen": "broad spectrum sunscreen SPF 30+",
                "serum": "treatment serum with active ingredients",
                "moisturizer": "daily moisturizer for skin hydration"
            }
            
            description = category_descriptions.get(category, "skincare product")
            
            # Build user context section
            user_context = f"""Find real products for:
Skin type: {skin_type}
Concerns: {', '.join(skin_concerns) if skin_concerns else 'None specified'}
Goals: {', '.join(skincare_goals) if skincare_goals else 'None specified'}
Sensitivity: {skin_sensitivity}"""
            
            prompt = f"""You are a skincare product discovery assistant. Find {limit} real, commercially available {description} products.

{user_context}

For each product, provide ONLY:
1. brand: The brand name
2. product_name: The exact product name
3. source_url: A real URL where this product can be purchased (Amazon, Sephora, brand website, etc.)
4. category: "{category}"

DO NOT provide:
- Safety assessments
- Ingredient lists
- Recommendations
- Prices or ratings
- Any analysis beyond basic product identification

Return strictly in this JSON format:
{{
  "products": [
    {{
      "brand": "...",
      "product_name": "...",
      "source_url": "...",
      "category": "{category}"
    }}
  ]
}}"""
            
            # Call Gemini discovery endpoint
            gemini_url = f"{self.ingredient_service_url}/research/discover-products"
            
            response = requests.post(
                gemini_url,
                json={"prompt": prompt, "category": category},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("products"):
                    return data["products"][:limit]
            
            print(f"Gemini discovery failed or returned no results for category: {category}")
            return []
            
        except Exception as e:
            print(f"Error in Gemini discovery: {e}")
            return []
    
    def _extract_and_analyze_product(self, brand: str, product_name: str, source_url: str, category: str) -> Optional[Dict[str, Any]]:
        """
        Send discovered product through existing extraction/analysis pipeline.
        """
        try:
            # Call existing product analysis endpoint
            analyze_url = f"{self.ingredient_service_url}/product/analyze"
            
            response = requests.post(
                analyze_url,
                json={
                    "brand": brand,
                    "product_name": product_name,
                    "source_url": source_url
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("product"):
                    return data["product"]
            
            print(f"Product extraction failed for: {brand} - {product_name}")
            return None
            
        except Exception as e:
            print(f"Error extracting product: {e}")
            return None
    
    def _filter_usable_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter candidates that have enough data for evaluation.
        """
        usable = []
        for c in candidates:
            # Must have product_id and ingredient data
            if c.get("product_id") and (c.get("normalized_ingredients") or c.get("full_ingredient_list")):
                usable.append(c)
        return usable
    
    def _rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        evaluations: List[Dict[str, Any]]
    ) -> List[tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Rank KEEP candidates deterministically:
        1. Higher fit_score
        2. Confidence: high > medium > low
        3. Stable product_id tie-breaker
        
        Returns: List of (candidate, evaluation) tuples
        """
        # Pair candidates with evaluations
        paired = list(zip(candidates, evaluations))
        
        # Define ranking key (only KEEP candidates are passed now)
        def rank_key(pair):
            candidate, evaluation = pair
            
            # Higher fit_score first (use negative for descending sort)
            fit_score = -(evaluation.get("fit_score", 0))
            
            confidence_order = {"high": 0, "medium": 1, "low": 2}
            confidence_score = confidence_order.get(evaluation.get("confidence", "low"), 2)
            
            # Stable product_id tie-breaker
            product_id = str(candidate.get("product_id", ""))
            
            return (fit_score, confidence_score, product_id)
        
        # Sort
        paired.sort(key=rank_key)
        
        return paired
    
    def generate_recommendations(
        self,
        missing_steps: List[str],
        user_data: Dict[str, Any],
        personalization_service
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate recommendations for missing routine steps, grouped by product category.
        
        Args:
            missing_steps: List of missing routine steps (e.g., ["Cleanser (AM)", "Sunscreen (AM)"])
            user_data: User profile and analysis data
            personalization_service: PersonalizationService instance for evaluation
            
        Returns:
            Dictionary mapping category names to lists of recommended products
            (e.g., {"cleanser": [...], "treatment": [...], "moisturizer": [...], "sunscreen": [...]})
        """
        recommendations = {}
        
        # Group missing steps by category to avoid duplicate discovery
        category_to_steps = {}
        for step in missing_steps:
            category = self._map_step_to_category(step)
            if category not in category_to_steps:
                category_to_steps[category] = []
            category_to_steps[category].append(step)
        
        print(f"Grouped missing steps by category: {category_to_steps}")
        
        # Process each category once
        for category, steps in category_to_steps.items():
            print(f"\nProcessing category: {category} for steps: {steps}")
            
            # Step 1: Search catalog
            catalog_candidates = self._search_catalog_by_category(category, limit=10)
            usable_catalog = self._filter_usable_candidates(catalog_candidates)
            
            print(f"Catalog candidates: {len(catalog_candidates)}, Usable: {len(usable_catalog)}")
            
            # Step 2: Deduplicate catalog candidates and exclude test products
            seen_identifiers = set()
            deduplicated_catalog = []
            for candidate in usable_catalog:
                product_id = candidate.get("product_id")
                product_name = candidate.get("product_name", "")
                brand = candidate.get("brand", "")
                
                # Exclude test products (check both brand and product_name)
                if "Test Brand" in brand or "Test Brand" in product_name or "Test Product" in product_name:
                    print(f"Excluding test product: {brand} - {product_name}")
                    continue
                
                # Create a unique identifier for deduplication
                if product_id:
                    unique_id = f"pid:{product_id}"
                else:
                    # Fallback to brand + product_name for products without product_id
                    unique_id = f"brand_name:{brand.lower().strip()}|{product_name.lower().strip()}"
                
                # Check if we've already seen this product
                if unique_id not in seen_identifiers:
                    seen_identifiers.add(unique_id)
                    deduplicated_catalog.append(candidate)
            
            print(f"Deduplicated catalog candidates: {len(deduplicated_catalog)}")
            
            # Step 3: Evaluate catalog candidates
            catalog_evaluated_pairs = []
            for candidate in deduplicated_catalog:
                evaluation = personalization_service.evaluate_product_suitability(
                    candidate,
                    user_data
                )
                catalog_evaluated_pairs.append((candidate, evaluation))
            
            # Step 4: Filter catalog candidates to KEEP only
            catalog_keep_pairs = [p for p in catalog_evaluated_pairs if p[1].get("decision") == "KEEP"]
            print(f"Catalog KEEP candidates: {len(catalog_keep_pairs)}")
            
            candidates_to_evaluate = deduplicated_catalog
            evaluated_pairs = catalog_evaluated_pairs
            
            # Step 5: Gemini discovery fallback only if no KEEP catalog candidates
            if len(catalog_keep_pairs) == 0:
                print(f"No KEEP catalog candidates, triggering Gemini discovery...")
                discovered_raw = self._discover_products_with_gemini(category, user_data, limit=5)
                
                # Extract and analyze discovered products
                discovered_products = []
                for d in discovered_raw:
                    brand = d.get("brand", "")
                    product_name = d.get("product_name", "")
                    source_url = d.get("source_url", "")
                    
                    if brand and product_name:
                        extracted = self._extract_and_analyze_product(brand, product_name, source_url, category)
                        if extracted:
                            discovered_products.append(extracted)
                
                usable_discovered = self._filter_usable_candidates(discovered_products)
                print(f"Discovered products: {len(discovered_products)}, Usable: {len(usable_discovered)}")
                
                # Deduplicate discovered candidates
                discovered_deduplicated = []
                for candidate in usable_discovered:
                    product_id = candidate.get("product_id")
                    product_name = candidate.get("product_name", "")
                    brand = candidate.get("brand", "")
                    
                    # Exclude test products
                    if "Test Brand" in brand or "Test Brand" in product_name or "Test Product" in product_name:
                        print(f"Excluding test product: {brand} - {product_name}")
                        continue
                    
                    # Create unique identifier
                    if product_id:
                        unique_id = f"pid:{product_id}"
                    else:
                        unique_id = f"brand_name:{brand.lower().strip()}|{product_name.lower().strip()}"
                    
                    # Check against catalog identifiers
                    if unique_id not in seen_identifiers:
                        seen_identifiers.add(unique_id)
                        discovered_deduplicated.append(candidate)
                
                print(f"Deduplicated discovered candidates: {len(discovered_deduplicated)}")
                
                # Evaluate discovered candidates
                discovered_evaluated_pairs = []
                for candidate in discovered_deduplicated:
                    evaluation = personalization_service.evaluate_product_suitability(
                        candidate,
                        user_data
                    )
                    discovered_evaluated_pairs.append((candidate, evaluation))
                
                # Filter discovered candidates to KEEP only
                discovered_keep_pairs = [p for p in discovered_evaluated_pairs if p[1].get("decision") == "KEEP"]
                print(f"Discovered KEEP candidates: {len(discovered_keep_pairs)}")
                
                # Combine all evaluated pairs
                evaluated_pairs = catalog_evaluated_pairs + discovered_evaluated_pairs
            
            # Step 6: Filter all evaluated candidates to KEEP only
            keep_pairs = [p for p in evaluated_pairs if p[1].get("decision") == "KEEP"]
            print(f"Total KEEP candidates for ranking: {len(keep_pairs)}")
            
            # Step 7: Rank KEEP candidates only
            ranked_pairs = self._rank_candidates([p[0] for p in keep_pairs], [p[1] for p in keep_pairs])
            
            # Step 8: Attach evaluations and limit to 3
            final_recommendations = []
            for candidate, evaluation in ranked_pairs[:3]:
                candidate_copy = candidate.copy()
                candidate_copy["evaluation"] = evaluation
                final_recommendations.append(candidate_copy)
            
            # Assign recommendations by category (not by step)
            recommendations[category] = final_recommendations
            print(f"Final recommendations for category {category}: {len(final_recommendations)}")
        
        return recommendations