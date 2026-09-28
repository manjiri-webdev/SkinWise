import re
import supabase_config
from typing import Dict, List, Optional, Any
from services.recommendation_service import RecommendationService


class PersonalizationService:
    """
    Minimal personalization service for SkinWise.
    
    Loads user data, evaluates current products, and builds routines
    using existing database records and deterministic rules.
    """
    
    def __init__(self):
        self.supabase = supabase_config.supabase
        # Simple in-memory ingredient cache to reduce repeated queries
        self._ingredient_cache = {}
    
    def _normalize_product_identity(self, product_name: str, brand: str = None) -> str:
        """
        Normalize product name and optional brand to canonical identity for deduplication and reconciliation.
        
        Normalizes:
        - Lowercase
        - Apostrophes/quotes (', ", ', etc.) - removed entirely
        - Punctuation (.,;:!?()[]/\\)
        - Dashes/hyphens (- – — _)
        - Extra whitespace collapsed
        - Equivalent "&"/"and" forms
        - Embedded brand prefixes handled
        """
        if not product_name and not brand:
            return ""
        
        parts = []
        if brand:
            parts.append(str(brand))
        if product_name:
            parts.append(str(product_name))
        raw = " ".join(parts).lower()
        
        # Remove apostrophes and quotes entirely
        normalized = re.sub(r"[\'\"\u2018\u2019\u201c\u201d]", "", raw)
        # Replace punctuation with space
        normalized = re.sub(r"[.,;:!?\(\)\[\]\/\\]", " ", normalized)
        # Replace dashes/hyphens with space
        normalized = re.sub(r"[-–—_]", " ", normalized)
        # Normalize "&" to " and "
        normalized = re.sub(r"\s*&\s*", " and ", normalized)
        # Collapse multiple spaces to single space
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _canonical_product_key(self, product_name: str, brand: str = None) -> str:
        """
        Generate a canonical product key that normalizes brand, punctuation, quotes,
        and strips embedded brand prefixes so that:
        - "re'equil ceramide & hyaluronic acid moisturiser"
        - "Reequil Ceramide & Hyaluronic Acid Moisturiser"
        - "ceramide & hyaluronic acid moisturiser" (with brand "Reequil")
        all yield the EXACT same canonical key:
        "reequil:ceramide and hyaluronic acid moisturiser"
        """
        if not product_name and not brand:
            return ""
        
        norm_brand = self._normalize_product_identity(brand) if brand else ""
        norm_name = self._normalize_product_identity(product_name) if product_name else ""
        
        known_brands = [
            ("reequil", "reequil"),
            ("dot and key", "dot and key"),
            ("cerave", "cerave"),
            ("cetaphil", "cetaphil"),
            ("wishcare", "wishcare"),
            ("mama earth", "mama earth"),
            ("mamaearth", "mama earth"),
            ("the ordinary", "the ordinary"),
            ("minimalist", "minimalist"),
        ]
        
        detected_brand = norm_brand
        stripped_name = norm_name
        
        if not detected_brand:
            for b_key, b_canon in known_brands:
                if norm_name.startswith(b_key + " ") or norm_name == b_key:
                    detected_brand = b_canon
                    stripped_name = norm_name[len(b_key):].strip()
                    break
        else:
            if stripped_name.startswith(detected_brand + " "):
                stripped_name = stripped_name[len(detected_brand):].strip()
            elif stripped_name.startswith(detected_brand):
                stripped_name = stripped_name[len(detected_brand):].strip()
                
        if detected_brand:
            return f"{detected_brand}:{stripped_name}"
        return stripped_name
    
    def load_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Load all relevant user data for personalization.
        
        Returns:
            Dictionary with user profile, skin analysis, products, ingredients, environment
        """
        user_data = {
            "user_id": user_id,
            "profile": None,
            "skin_analysis": None,
            "current_products": [],
            "environment": None
        }
        
        # Load user profile
        try:
            profile_response = self.supabase.table("user_profiles").select("*").eq("id", user_id).execute()
            if profile_response.data:
                user_data["profile"] = profile_response.data[0]
        except Exception as e:
            print(f"Error loading profile: {e}")
        
        # Load latest skin analysis
        try:
            analysis_response = self.supabase.table("skin_analyses").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            if analysis_response.data:
                user_data["skin_analysis"] = analysis_response.data[0]
        except Exception as e:
            print(f"Error loading skin analysis: {e}")
        
        # Load current products from user_product_history
        try:
            history_response = self.supabase.table("user_product_history").select("*").eq("user_id", user_id).eq("status", "current").execute()
            if history_response.data:
                user_data["current_products"] = history_response.data
        except Exception as e:
            print(f"Error loading product history: {e}")
        
        # Load latest environment
        try:
            env_response = self.supabase.table("user_environment_history").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            if env_response.data:
                user_data["environment"] = env_response.data[0]
        except Exception as e:
            print(f"Error loading environment: {e}")
        
        return user_data
    
    def get_product_ingredients(self, product_id: Any) -> tuple[List[Dict[str, Any]], int]:
        """
        Get ingredients for a product with full ingredient records and total parsed count.
        Uses in-memory cache to reduce repeated Supabase queries.
        
        Returns:
            Tuple of (resolved_ingredient_records, total_parsed_ingredient_count)
        """
        ingredients = []
        total_parsed = 0
        
        try:
            product_response = self.supabase.table("products").select("*").eq("product_id", product_id).execute()
            if not product_response.data:
                return ingredients, total_parsed
            
            product = product_response.data[0]
            
            ingredient_list = product.get("normalized_ingredients")
            if not ingredient_list:
                full_list = product.get("full_ingredient_list")
                if full_list:
                    ingredient_list = self._parse_ingredient_list(full_list)
                else:
                    return ingredients, total_parsed
            
            ingredient_names = [name.strip() for name in ingredient_list.split("|") if name.strip()]
            total_parsed = len(ingredient_names)
            
            for ingredient_name in ingredient_names:
                # Check cache first
                cache_key = ingredient_name.lower()
                if cache_key in self._ingredient_cache:
                    ingredients.append(self._ingredient_cache[cache_key])
                    continue
                
                # Not in cache, query Supabase
                try:
                    ing_response = self.supabase.table("ingredients").select("*").ilike("ingredient", f"%{ingredient_name}%").execute()
                    if ing_response.data:
                        ingredient_record = ing_response.data[0]
                        ingredients.append(ingredient_record)
                        # Cache the result
                        self._ingredient_cache[cache_key] = ingredient_record
                except Exception as e:
                    print(f"Error loading ingredient {ingredient_name}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error getting product ingredients: {e}")
        
        return ingredients, total_parsed
    
    def _parse_ingredient_list(self, full_ingredient_list: str) -> str:
        """
        Parse comma-separated ingredient list into pipe-separated format.
        
        Args:
            full_ingredient_list: Comma-separated ingredient string
            
        Returns:
            Pipe-separated ingredient string
        """
        if not full_ingredient_list:
            return ""
        
        # Split by comma and clean up
        ingredients = [ing.strip() for ing in full_ingredient_list.split(",") if ing.strip()]
        
        # Join with pipe
        return "|".join(ingredients)
    
    def _generate_reason_specific_mitigation(
        self,
        reason_code: str,
        product: Dict[str, Any],
        user_data: Dict[str, Any],
        evaluation: Dict[str, Any],
        ingredients: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate deterministic, reason-specific mitigation text based on evaluation context.
        
        Args:
            reason_code: The primary reason code for the caution
            product: Product being evaluated
            user_data: User profile and context
            evaluation: Current evaluation object
            ingredients: Resolved ingredient records (if available)
            
        Returns:
            Specific mitigation text for the reason code
        """
        product_name = product.get("product_name", "Product")
        product_name_lower = product_name.lower()
        profile = user_data.get("profile") or {}
        skin_analysis = user_data.get("skin_analysis")
        environment = user_data.get("environment")
        
        if reason_code == "PRODUCT_UNRESOLVED":
            # Product could not be verified from catalog - ingredients unavailable
            mitigation_parts = [
                f"Verify the complete INCI (ingredient list) from the packaging or official brand source to ensure no known irritants for your skin type; evaluation is incomplete without verified ingredients."
            ]
            
            # Check if product name indicates body-only use
            body_only_indicators = ["body lotion", "body cream", "body butter", "body oil", "body wash", "body scrub"]
            if any(indicator in product_name_lower for indicator in body_only_indicators):
                mitigation_parts.append(
                    "Product name indicates body-only use. Confirm the label explicitly states suitability for facial use before applying to face."
                )
            
            return " ".join(mitigation_parts)
        
        elif reason_code == "EVIDENCE_INCOMPLETE":
            # Some ingredient evidence is incomplete - not unsafe, just less researched
            resolved_count = len(ingredients) if ingredients else 0
            total_parsed = evaluation.get("_total_parsed_ingredients", resolved_count)
            
            if total_parsed > 0 and resolved_count < total_parsed:
                missing_ratio = ((total_parsed - resolved_count) / total_parsed) * 100
                if missing_ratio > 50:
                    mitigation = f"Over {int(missing_ratio)}% of ingredients in '{product_name}' have limited clinical research data."
                else:
                    mitigation = f"Some ingredients in '{product_name}' have limited clinical research data."
            else:
                mitigation = f"Limited scientific research is available for some ingredients in '{product_name}'."
            
            mitigation += " This does not indicate the product is unsafe, but evidence is insufficient for comprehensive evaluation."
            mitigation += " Check the complete INCI and introduce the product gradually into your routine."
            
            return mitigation
        
        elif reason_code == "ENVIRONMENT_MISMATCH":
            # Use actual environmental context
            if environment:
                humidity = environment.get("humidity")
                temperature = environment.get("temperature")
                
                env_context = []
                if isinstance(humidity, (int, float)):
                    if humidity > 70:
                        env_context.append(f"high humidity ({humidity}%)")
                    elif humidity < 30:
                        env_context.append(f"low humidity ({humidity}%)")
                
                if isinstance(temperature, (int, float)):
                    if temperature > 30:
                        env_context.append(f"high temperature ({temperature}°C)")
                    elif temperature < 10:
                        env_context.append(f"low temperature ({temperature}°C)")
                
                if env_context:
                    env_str = " and ".join(env_context)
                    return f"Product may feel less comfortable in {env_str}. Consider adjusting application amount or texture for current conditions."
            
            return "Product may not be optimal for current environmental conditions. Consider adjusting your routine based on humidity and temperature."
        
        elif reason_code == "IRRITATION_RISK":
            # Use existing ingredient/reason data to identify relevant irritation concern
            if ingredients:
                high_irritation_ingredients = []
                for ing in ingredients:
                    ir = (ing.get("irritation_risk") or "").lower()
                    if ir in ["high", "very high"]:
                        ing_name = ing.get("ingredient", "ingredient")
                        high_irritation_ingredients.append(ing_name)
                
                if high_irritation_ingredients:
                    if len(high_irritation_ingredients) == 1:
                        return f"Contains {high_irritation_ingredients[0]} which carries elevated irritation potential. Patch test before daily use and introduce gradually."
                    else:
                        return f"Contains ingredients with elevated irritation potential ({', '.join(high_irritation_ingredients[:2])}). Patch test before daily use and introduce gradually."
            
            return "Contains ingredients with elevated irritation potential. Patch test before daily use and introduce gradually."
        
        elif reason_code == "SENSITIZATION_RISK":
            # Use existing ingredient/reason data for sensitization
            if ingredients:
                sensitizing_ingredients = []
                for ing in ingredients:
                    als = (ing.get("allergy_sensitization") or "").lower()
                    if any(term in als for term in ["high", "frequent", "common allergen", "common sensitizer"]) and not any(neg in als for neg in ["not", "rare", "unlikely"]):
                        ing_name = ing.get("ingredient", "ingredient")
                        sensitizing_ingredients.append(ing_name)
                
                if sensitizing_ingredients:
                    if len(sensitizing_ingredients) == 1:
                        return f"{sensitizing_ingredients[0]} is a known contact sensitizer. Monitor skin closely for allergic reaction, tingling, or redness."
                    else:
                        return f"Contains known sensitizers ({', '.join(sensitizing_ingredients[:2])}). Monitor skin closely for allergic reaction, tingling, or redness."
            
            return "Contains known sensitizers. Monitor skin closely for allergic reaction, tingling, or redness."
        
        elif reason_code == "PREVIOUS_REACTION":
            # Use user's actual stored reaction/notes context
            product_history = evaluation.get("_product_history")
            if product_history:
                reaction = product_history.get("reaction", "").strip()
                notes = product_history.get("notes", "").strip() if isinstance(product_history.get("notes"), str) else ""
                
                if reaction and reaction.lower() not in ["none", "no reaction", ""]:
                    return f"Your previous reaction ('{reaction}') to this product affects this recommendation. Consider consulting a dermatologist if reactions persist."
                
                if notes:
                    return f"Your product history notes indicate prior sensitivity. Use with caution or consider alternative products with gentler formulations."
            
            return "Your product history indicates prior sensitivity. Use with caution or consider alternative products with gentler formulations."
        
        elif reason_code == "ACTIVE_CAUTION":
            # Use existing skin-analysis severity
            if skin_analysis:
                severity = (skin_analysis.get("severity") or "").lower()
                if severity in ["moderate", "severe"]:
                    return f"Current skin analysis shows {severity} severity. Strong active ingredients may worsen inflammation. Consider pausing potent treatments until skin barrier stabilizes."
            
            return "Strong active ingredients may not be suitable during skin barrier recovery. Consider pausing potent treatments until skin stabilizes."
        
        elif reason_code == "CONTRAINDICATION":
            # Use existing contraindication reason from evaluator
            existing_reasons = evaluation.get("reasons", [])
            for reason in existing_reasons:
                if "contraindicated" in reason.lower() or "should avoid" in reason.lower():
                    return reason.replace("is strongly contraindicated", "is not recommended").replace("should avoid", "avoid")
            
            return "Product contains ingredients not recommended for your skin profile based on specific contraindications."
        
        # Fallback for unknown reason codes
        return "Review ingredient list and patch test before use if you have sensitive skin."
    
    def extract_active_classes(self, product: Dict[str, Any], ingredients: List[Dict[str, Any]]) -> set:
        """
        Detect active chemical classes from resolved ingredient records with product name fallback.
        """
        actives = set()
        active_definitions = {
            "retinoids": ["retinol", "retinal", "retinyl", "adapalene", "tretinoin", "bakuchiol", "hydroxypinacolone"],
            "ahas": ["glycolic", "lactic acid", "mandelic", "malic acid", "tartaric acid"],
            "bhas": ["salicylic", "betaine salicylate"],
            "vitamin_c": ["ascorbic acid", "ethyl ascorbic", "ascorbyl", "tetrahexyldecyl"],
            "niacinamide": ["niacinamide"],
            "benzoyl_peroxide": ["benzoyl peroxide"]
        }
        
        # 1. Check resolved ingredient records
        for ing in ingredients:
            ing_name = (ing.get("ingredient") or "").lower()
            for group, keywords in active_definitions.items():
                if any(kw in ing_name for kw in keywords):
                    actives.add(group)
        
        # 2. Fallback check on product title
        product_name = (product.get("product_name") or "").lower()
        for group, keywords in active_definitions.items():
            if any(kw in product_name for kw in keywords):
                actives.add(group)
                
        return actives
    
    def _extract_user_allergies_and_triggers(
        self, 
        user_data: Dict[str, Any], 
        product_history: Optional[Dict[str, Any]] = None
    ) -> set:
        triggers = set()
        profile = user_data.get("profile") or {}
        
        # 1. Explicit allergies in profile (if column exists)
        allergies = profile.get("allergies") or profile.get("known_allergies") or []
        if isinstance(allergies, list):
            for a in allergies:
                triggers.add(str(a).strip().lower())
        elif isinstance(allergies, str):
            for a in allergies.split(","):
                triggers.add(a.strip().lower())
                
        # 2. Profile skin concerns (e.g., "Salicylate allergy", "Rosacea", "Eczema", "Exfoliant reaction")
        concerns = profile.get("skin_concerns") or []
        for c in concerns:
            c_low = str(c).strip().lower()
            if any(term in c_low for term in ["allergy", "allergic", "sensitivity", "rosacea", "eczema"]):
                triggers.add(c_low)
            if any(term in c_low for term in ["exfoliant", "peel", "acid"]):
                triggers.add("exfoliant")
                triggers.add("peel")
                
        # 3. Product history & current products notes/reactions
        all_prods = list(user_data.get("current_products") or [])
        if profile.get("current_products") and isinstance(profile.get("current_products"), list):
            for cp in profile.get("current_products"):
                if cp not in all_prods:
                    all_prods.append(cp)
        if product_history and product_history not in all_prods:
            all_prods.append(product_history)
            
        signal_keywords = [
            "salicylate", "aspirin", "peppermint", "menthol", "fragrance", "parfum", 
            "alcohol denat", "retinol", "glycolic", "lactic", "benzoyl peroxide", 
            "tea tree", "essential oil", "exfoliant", "exfoliating", "exfoliation",
            "peel", "peeling", "chemical peel", "acid peel", "aha", "bha"
        ]
        
        for p in all_prods:
            reaction = (p.get("reaction") or "").strip().lower()
            notes = (p.get("notes") or "").strip().lower() if isinstance(p.get("notes"), str) else ""
            p_name = (p.get("productName") or p.get("product_name") or "").lower()
            p_type = (p.get("product_type") or p.get("type") or "").lower()
            
            has_adverse = reaction in ["mild", "moderate", "severe"] or any(
                sig in notes for sig in ["allergic", "allergy", "burning", "stinging", "rash", "broke out", "breakout", "redness", "itch", "peeling", "irritation"]
            )
            
            if has_adverse:
                if any(t in p_type for t in ["exfoliant", "peel", "scrub"]) or any(t in p_name for t in ["exfoliat", "peel", "aha", "bha"]):
                    triggers.add("exfoliant")
                    triggers.add("peel")

                for kw in signal_keywords:
                    # Make sure not negated (e.g., "no fragrance" or "not allergic")
                    if kw in notes and f"no {kw}" not in notes and f"without {kw}" not in notes and f"not {kw}" not in notes:
                        triggers.add(kw)
                    elif kw in p_name:
                        triggers.add(kw)
                        
        return triggers

    def _detect_formulation_safety_profile(
        self, 
        product: Dict[str, Any], 
        ingredients: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect high-potency formulations such as chemical acid peels, high-concentration AHA/BHA solutions,
        or intensive active treatments that require elevated clinical caution.
        Uses product attributes and ingredient analysis without hardcoding brand names.
        """
        import re
        product_name = (product.get("product_name") or "").lower()
        category = (product.get("category") or product.get("product_type") or "").lower()
        description = (product.get("description") or product.get("main_purpose") or "").lower()
        combined_text = f"{product_name} {category} {description}"

        # 1. Check for explicit chemical peel / peeling solution indicators
        peel_keywords = ["peeling solution", "acid peel", "chemical peel", "exfoliating peel", "facial peel", "aha/bha peel", "peel solution"]
        is_peel_name = any(kw in combined_text for kw in peel_keywords)

        # 2. Check for high concentration acid patterns (e.g. >= 15% AHA, >= 2% BHA, 30%)
        has_high_pct = bool(re.search(r'\b(1[5-9]|[2-9][0-9])%\s*(aha|bha|acid|glycolic|lactic)?', combined_text))
        has_30_pct = "30%" in combined_text or "25%" in combined_text or "20%" in combined_text

        # 3. Analyze active ingredient profile
        aha_actives = []
        bha_actives = []
        for ing in (ingredients or []):
            ing_low = (ing.get("ingredient") or "").lower()
            if any(aha in ing_low for aha in ["glycolic", "lactic", "tartaric", "mandelic", "citric", "malic"]):
                aha_actives.append(ing.get("ingredient"))
            if "salicylic" in ing_low or "betaine salicylate" in ing_low:
                bha_actives.append(ing.get("ingredient"))

        has_multi_acid_system = len(aha_actives) >= 2 and len(bha_actives) >= 1
        is_high_potency_acid_peel = (
            is_peel_name 
            or (has_high_pct and (aha_actives or bha_actives))
            or (has_30_pct and (aha_actives or bha_actives))
            or (has_multi_acid_system and any(term in combined_text for term in ["peel", "exfoliat", "solution"]))
        )

        return {
            "is_high_potency_acid_peel": is_high_potency_acid_peel,
            "aha_actives": aha_actives,
            "bha_actives": bha_actives,
            "is_peel_name": is_peel_name
        }

    def evaluate_ingredients_suitability(
        self,
        ingredients: List[Dict[str, Any]],
        user_data: Dict[str, Any],
        skin_analysis: Optional[Dict[str, Any]] = None,
        product_history: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate individual ingredient compatibility against the user's profile and toxicology data.
        Prevents general informational 'who_should_avoid' advisories from turning into universal
        'Not recommended' labels unless the user's specific profile or history matches.
        """
        evaluations = []
        profile = user_data.get("profile") or {}
        has_profile = bool(profile)
        
        skin_sensitivity = (profile.get("skin_sensitivity") or "").strip().lower()
        is_sensitive = (
            skin_sensitivity in ["yes", "sensitive", "high", "very high", "high sensitivity", "reactive", "moderate"]
            or "sensitive" in skin_sensitivity
            or "high" in skin_sensitivity
        )
        is_high_sensitivity = (
            skin_sensitivity in ["high", "very high", "high sensitivity", "very sensitive"]
            or "high" in skin_sensitivity
        )
        skin_type = (profile.get("skin_type") or "").strip().lower()
        user_concerns = [str(c).strip().lower() for c in (profile.get("skin_concerns") or [])]
        user_goals = [str(g).strip().lower() for g in (profile.get("skincare_goals") or [])]
        
        flareup_severity = (skin_analysis.get("severity") or "").lower() if skin_analysis else ""
        user_triggers = self._extract_user_allergies_and_triggers(user_data, product_history)
        
        for ing in ingredients:
            ing_name = ing.get("ingredient") or ing.get("canonical_name") or "Unknown Ingredient"
            ing_name_lower = ing_name.lower()
            ir = (ing.get("irritation_risk") or "").strip().lower()
            who_avoid = (ing.get("who_should_avoid") or "").strip()
            who_avoid_low = who_avoid.lower()
            als = (ing.get("allergy_sensitization") or "").strip().lower()
            suitable_types = (ing.get("suitable_skin_types") or "").strip().lower()
            benefits = ing.get("benefits") or ""
            benefits_lower = benefits.lower()
            func = ing.get("function") or ""
            
            # Default values
            status = "Suitable"
            reason = "Well tolerated with low irritation risk; compatible with your profile"
            personalized = False
            is_contraindicated = False
            matched_skin_type = False
            matched_concerns = []
            
            # Check user skin type compatibility
            if skin_type:
                if "all" in suitable_types or skin_type in suitable_types:
                    matched_skin_type = True
                elif skin_type == "combination" and any(k in suitable_types for k in ["oily", "dry", "normal"]):
                    matched_skin_type = True

            # Check user concerns compatibility
            for c in user_concerns:
                if c in (ing.get("skin_concerns") or "").lower() or c in benefits_lower:
                    matched_concerns.append(c.capitalize())
            for g in user_goals:
                if g in benefits_lower:
                    matched_concerns.append(g.capitalize())
            matched_concerns = list(dict.fromkeys(matched_concerns))
            
            # Determine if who_avoid mentions sensitive skin (and NOT asthma or other medical conditions)
            sensitive_skin_in_avoid = (
                ("sensitive" in who_avoid_low and "asthma" not in who_avoid_low) or
                "sensitive skin" in who_avoid_low
            ) and "sensitive" not in suitable_types

            # 1. SPECIFIC ALLERGY / ADVERSE REACTION TRIGGER (Personalized Contraindication)
            matched_trigger = None
            for trig in user_triggers:
                if trig in ing_name_lower:
                    matched_trigger = trig
                    break
                if trig in ["salicylate", "aspirin"] and ("salicylate" in who_avoid_low or "aspirin" in who_avoid_low or "salicyl" in ing_name_lower):
                    matched_trigger = trig
                    break
                if trig in ["peppermint", "menthol"] and ("peppermint" in ing_name_lower or "menthol" in ing_name_lower):
                    matched_trigger = trig
                    break
                if trig in ["fragrance", "parfum"] and ("fragrance" in ing_name_lower or "parfum" in ing_name_lower):
                    matched_trigger = trig
                    break
                if trig in ["exfoliant", "exfoliation", "peel", "acid peel", "aha", "bha"] and any(a in ing_name_lower for a in ["glycolic", "salicylic", "lactic", "tartaric", "mandelic", "citric"]):
                    matched_trigger = "prior exfoliant reaction"
                    break
            
            if matched_trigger:
                status = "Not recommended"
                reason = f"Contraindicated: matches your recorded {matched_trigger} allergy / reaction history"
                personalized = True
                is_contraindicated = True
            
            # 2. SENSITIVE SKIN CONTRAINDICATION
            elif is_sensitive and (
                (ir in ["high", "very high"] and (sensitive_skin_in_avoid or "allergen" in als or "fragrance" in who_avoid_low or "peppermint" in ing_name_lower))
                or (is_high_sensitivity and sensitive_skin_in_avoid and ir in ["moderate", "medium"])
            ):
                status = "Not recommended"
                reason = f"Contraindicated: {ir.capitalize()} irritation risk unsuitable for your sensitive skin"
                personalized = True
                is_contraindicated = True
                
            # 3. ACTIVE FLARE-UP CAUTION
            elif flareup_severity in ["moderate", "severe"] and any(act in ing_name_lower for act in ["retinol", "glycolic", "lactic", "salicylic", "benzoyl peroxide"]):
                status = "Use with Caution"
                reason = f"Potent active ingredient during active skin flare-up ({flareup_severity.capitalize()} severity); introduce cautiously"
                personalized = True
                
            # 4. SENSITIVE SKIN CAUTION (Moderate irritation or sensitive skin advisory)
            elif is_sensitive and (ir in ["moderate", "medium"] or sensitive_skin_in_avoid):
                status = "Use with Caution"
                reason = f"Moderate irritation risk ({ir.capitalize() if ir else 'Moderate'}); patch test advised for your sensitive skin"
                personalized = True
                
            # 5. GENERAL HIGH IRRITATION (Non-sensitive user or unauthenticated)
            elif ir in ["high", "very high"]:
                status = "Use with Caution"
                if has_profile and not is_sensitive:
                    reason = f"Elevated irritation risk ({ir.capitalize()}); patch testing recommended before regular use"
                    personalized = True
                else:
                    reason = f"Elevated irritation risk ({ir.capitalize()}); patch testing recommended"
                    personalized = False
                    
            # 6. GENERAL MODERATE IRRITATION OR CONTACT ALLERGEN
            elif ir in ["moderate", "medium"] or any(term in als for term in ["high", "frequent", "common allergen", "common sensitizer"]):
                status = "Use with Caution"
                reason = "Moderate irritation potential or recognized contact sensitizer; introduce gradually"
                personalized = False
                
            # 7. SPECIFIC HARSH INGREDIENTS (fragrance, parfum, alcohol denat)
            elif any(term in ing_name_lower for term in ["fragrance", "parfum", "alcohol denat"]):
                status = "Use with Caution"
                reason = "Common contact sensitizer or drying agent; patch testing recommended"
                personalized = False
                
            # 8. SUITABLE WITH PERSONALIZED EXPLANATION
            else:
                status = "Suitable"
                if has_profile:
                    personalized = True
                    if matched_skin_type and matched_concerns:
                        reason = f"Compatible with your {skin_type.capitalize()} skin; supports {', '.join(matched_concerns[:2])}"
                    elif matched_skin_type:
                        reason = f"Compatible with your {skin_type.capitalize()} skin profile (Low irritation risk)"
                    elif matched_concerns:
                        reason = f"Low irritation risk; supports target goals ({', '.join(matched_concerns[:2])})"
                    elif "salicylate" in who_avoid_low or "aspirin" in who_avoid_low:
                        reason = "Compatible with your profile (Low irritation risk; soothing anti-inflammatory)"
                    else:
                        reason = "Well tolerated with low irritation risk; compatible with your profile"
                else:
                    if "salicylate" in who_avoid_low or "aspirin" in who_avoid_low:
                        reason = "Low irritation risk formulation ingredient (general precaution applies only to salicylate allergy)"
                    else:
                        reason = "Low irritation risk formulation ingredient"
                    personalized = False
            
            evaluations.append({
                "ingredient": ing_name,
                "status": status,
                "reason": reason,
                "personalized": personalized,
                "risk_level": ir.capitalize() if ir else "Low",
                "matched_concerns": matched_concerns,
                "matched_skin_type": matched_skin_type,
                "is_contraindicated": is_contraindicated,
                "general_precaution": who_avoid if who_avoid else None,
                "function": func,
                "benefits": benefits,
                "irritation_risk": ing.get("irritation_risk"),
                "who_should_avoid": who_avoid if who_avoid else None,
                "allergy_sensitization": ing.get("allergy_sensitization"),
            })
            
        return evaluations
    
    def evaluate_product_suitability(
        self,
        product: Dict[str, Any],
        user_data: Dict[str, Any],
        product_history: Optional[Dict[str, Any]] = None,
        ingredients: Optional[List[Dict[str, Any]]] = None,
        total_parsed: int = 0
    ) -> Dict[str, Any]:
        """
        Evaluate if a product is suitable for the user using deterministic hybrid scoring.
        
        Args:
            product: Product record
            user_data: User profile and analysis data
            product_history: User's product history record (reaction, notes)
            ingredients: Pre-fetched ingredient records
            total_parsed: Total parsed ingredient count from product label
            
        Returns:
            Dictionary with evaluation decision (KEEP/CAUTION/REJECT), confidence, reason codes, reasons, and mitigations
        """
        evaluation = {
            "decision": "KEEP",
            "confidence": "medium",
            "reason_codes": [],
            "reasons": [],
            "mitigations": []
        }
        
        profile = user_data.get("profile") or {}
        skin_analysis = user_data.get("skin_analysis")
        environment = user_data.get("environment")
        
        # ------------------------------------------------------------------
        # 1. HARD SAFETY GATES (Strict REJECT)
        # ------------------------------------------------------------------
        if product_history:
            reaction = (product_history.get("reaction") or "").strip().lower()
            notes = (product_history.get("notes") or "").strip().lower() if isinstance(product_history.get("notes"), str) else ""

            severe_reactions = ["severe", "allergic", "breakout (severe)"]
            severe_note_signals = [
                "severe allergic", "chemical burn", "intense burning", 
                "severe burning", "blister", "swelling", "hives", "severe rash", "severe breakout"
            ]

            # Check negation to prevent false positives (e.g. "no swelling", "not allergic")
            matched_severe_note = None
            for sig in severe_note_signals:
                if sig in notes and f"no {sig}" not in notes and f"not {sig}" not in notes:
                    matched_severe_note = sig
                    break

            if reaction in severe_reactions or matched_severe_note:
                evaluation["decision"] = "REJECT"
                evaluation["reason_codes"].append("PREVIOUS_REACTION")
                detail = reaction if reaction in severe_reactions else f"notes report '{matched_severe_note}'"
                evaluation["reasons"].append(f"Recorded severe reaction ({detail}) in your product history")
                evaluation["mitigations"].append("Discontinue use immediately and consult a dermatologist")
                evaluation["confidence"] = "high"
                evaluation["_product_history"] = product_history
                evaluation["ingredient_evaluations"] = self.evaluate_ingredients_suitability(ingredients, user_data, skin_analysis, product_history) if ingredients else []
                return evaluation

        product_id = product.get("product_id")
        if not product_id and not ingredients:
            # Product is unresolved and has no ingredients - mark with explicit CAUTION / PRODUCT_UNRESOLVED only
            product_name = product.get("product_name") or "Product"
            evaluation["decision"] = "CAUTION"
            evaluation["confidence"] = "low"
            evaluation["reason_codes"] = ["PRODUCT_UNRESOLVED", "EVIDENCE_INCOMPLETE"]
            evaluation["reasons"] = [
                f"Product '{product_name}' could not be verified from our catalog; ingredients unavailable for safety evaluation"
            ]
            # Use reason-specific mitigation for PRODUCT_UNRESOLVED
            evaluation["mitigations"] = [
                self._generate_reason_specific_mitigation("PRODUCT_UNRESOLVED", product, user_data, evaluation, ingredients=[])
            ]
            evaluation["ingredient_evaluations"] = []
            return evaluation
        
        if ingredients is None and product_id:
            ingredients, total_parsed = self.get_product_ingredients(product_id)
        elif ingredients is None:
            ingredients, total_parsed = [], 0
        
        fit_score = 0
        risk_score = 0
        
        # Calculate evidence completeness
        resolved_count = len(ingredients)
        researched_count = sum(1 for ing in ingredients if ing.get("evidence_source"))
        evidence_ratio = (researched_count / total_parsed) if total_parsed > 0 else (1.0 if resolved_count > 0 else 0.0)
        evidence_score = round(evidence_ratio * 100)

        # Detect formulation safety profile (e.g. chemical peel, high-potency acid treatment)
        formulation_profile = self._detect_formulation_safety_profile(product, ingredients)
        is_high_potency_peel = formulation_profile.get("is_high_potency_acid_peel", False)

        # Evaluate user sensitivity attributes
        skin_sensitivity = (profile.get("skin_sensitivity") or "").strip().lower()
        is_sensitive = (
            skin_sensitivity in ["yes", "sensitive", "high", "very high", "high sensitivity", "reactive", "moderate"]
            or "sensitive" in skin_sensitivity
            or "high" in skin_sensitivity
        )
        is_high_sensitivity = (
            skin_sensitivity in ["high", "very high", "high sensitivity", "very sensitive"]
            or "high" in skin_sensitivity
            or (is_sensitive and "very" in skin_sensitivity)
        )

        # 1. EVALUATE INGREDIENTS EARLY to inform product-level decision
        ingredient_evaluations = self.evaluate_ingredients_suitability(
            ingredients, user_data, skin_analysis, product_history
        )
        evaluation["ingredient_evaluations"] = ingredient_evaluations

        # Check user-specific allergy / adverse reaction triggers
        user_triggers = self._extract_user_allergies_and_triggers(user_data, product_history)

        # HARD SAFETY GATE 1: Check for contraindicated ingredients
        contraindicated_ings = [
            ie for ie in ingredient_evaluations
            if ie.get("is_contraindicated") or ie.get("status") == "Not recommended"
        ]
        if contraindicated_ings:
            evaluation["decision"] = "REJECT"
            evaluation["confidence"] = "high"
            evaluation["reason_codes"].append("CONTRAINDICATION")

            # Check if any contraindication stems from prior adverse reaction or allergy
            has_reaction_reason = any(
                "reaction" in (ie.get("reason") or "").lower() or "allergy" in (ie.get("reason") or "").lower()
                for ie in contraindicated_ings
            )
            has_exfoliant_trigger = any(t in ["exfoliant", "exfoliation", "peel", "acid peel", "aha", "bha"] for t in user_triggers)
            if has_reaction_reason or has_exfoliant_trigger:
                evaluation["reason_codes"].append("PREVIOUS_REACTION")

            for cie in contraindicated_ings[:3]:
                evaluation["reasons"].append(f"{cie['ingredient']}: {cie['reason']}")

            evaluation["mitigations"].append(
                "Avoid this product; it contains active ingredients that are contraindicated for your skin profile or reaction history."
            )
            evaluation["reason_codes"] = list(dict.fromkeys(evaluation["reason_codes"]))
            evaluation["reasons"] = list(dict.fromkeys(evaluation["reasons"]))
            evaluation["mitigations"] = list(dict.fromkeys(evaluation["mitigations"]))
            return evaluation

        # HARD SAFETY GATE 2: High-potency acid peels with sensitive skin or prior exfoliant reactions
        if is_high_potency_peel:
            has_exfoliant_trigger = any(t in ["exfoliant", "exfoliation", "peel", "acid peel", "aha", "bha"] for t in user_triggers)
            if has_exfoliant_trigger:
                evaluation["decision"] = "REJECT"
                evaluation["confidence"] = "high"
                evaluation["reason_codes"].extend(["CONTRAINDICATION", "PREVIOUS_REACTION"])
                evaluation["reasons"].append(
                    "High-concentration chemical exfoliating formulation is contraindicated due to recorded previous adverse reaction with exfoliating acid treatments"
                )
                evaluation["mitigations"].append(
                    "Avoid strong chemical peels; your profile indicates previous adverse reactions to chemical exfoliants."
                )
                evaluation["reason_codes"] = list(dict.fromkeys(evaluation["reason_codes"]))
                evaluation["reasons"] = list(dict.fromkeys(evaluation["reasons"]))
                evaluation["mitigations"] = list(dict.fromkeys(evaluation["mitigations"]))
                return evaluation

            if is_sensitive:
                evaluation["decision"] = "REJECT"
                evaluation["confidence"] = "high"
                evaluation["reason_codes"].append("CONTRAINDICATION")
                evaluation["reasons"].append(
                    "High-concentration chemical exfoliating peel is contraindicated for sensitive or reactive skin"
                )
                evaluation["mitigations"].append(
                    "Avoid high-potency acid peels; opt for gentle polyhydroxy acids (PHAs) or mild enzymic exfoliants suitable for sensitive skin."
                )
                evaluation["reason_codes"] = list(dict.fromkeys(evaluation["reason_codes"]))
                evaluation["reasons"] = list(dict.fromkeys(evaluation["reasons"]))
                evaluation["mitigations"] = list(dict.fromkeys(evaluation["mitigations"]))
                return evaluation

        # HARD SAFETY GATE 3: Salicylate / aspirin allergy check
        contraindicated_allergy_ing = None
        for ing in ingredients:
            ing_name_low = (ing.get("ingredient") or "").lower()
            who_avoid_low = (ing.get("who_should_avoid") or "").lower()
            for trig in user_triggers:
                if trig in ing_name_low or (trig in ["salicylate", "aspirin"] and ("salicylate" in who_avoid_low or "aspirin" in who_avoid_low or "salicyl" in ing_name_low)):
                    contraindicated_allergy_ing = (ing.get("ingredient"), trig)
                    break
            if contraindicated_allergy_ing:
                break
                
        if contraindicated_allergy_ing:
            ing_name, trig = contraindicated_allergy_ing
            evaluation["decision"] = "REJECT"
            evaluation["reason_codes"].append("CONTRAINDICATION")
            evaluation["reasons"].append(f"{ing_name} is contraindicated due to your recorded {trig} allergy / sensitivity")
            evaluation["mitigations"].append(f"Avoid this product; it contains {ing_name} which conflicts with your {trig} sensitivity")
            evaluation["confidence"] = "high"
            evaluation["reason_codes"] = list(dict.fromkeys(evaluation["reason_codes"]))
            evaluation["reasons"] = list(dict.fromkeys(evaluation["reasons"]))
            evaluation["mitigations"] = list(dict.fromkeys(evaluation["mitigations"]))
            return evaluation
        
        # ------------------------------------------------------------------
        # 2. FIT EVALUATION (Multi-Factor Positive Scoring)
        # ------------------------------------------------------------------
        skin_type = (profile.get("skin_type") or "").strip().lower()
        if skin_type:
            matched_skin_type = False
            for ing in ingredients:
                suitable_text = (ing.get("suitable_skin_types") or "").lower()
                if not suitable_text:
                    continue
                if "all" in suitable_text or skin_type in suitable_text:
                    fit_score += 3
                    matched_skin_type = True
                elif skin_type == "combination" and any(k in suitable_text for k in ["oily", "dry", "normal"]):
                    fit_score += 2
                    matched_skin_type = True
            
            if matched_skin_type:
                evaluation["reason_codes"].append("SKIN_TYPE_MATCH")
                evaluation["reasons"].append(f"Formulated with ingredients compatible with {skin_type.capitalize()} skin")
        
        # Skin concerns matching
        skin_concerns = profile.get("skin_concerns") or []
        concern_keywords = {
            "pigmentation": ["pigment", "dark spot", "tone", "brighten", "discoloration", "niacinamide", "vitamin c"],
            "dryness": ["dry", "hydrat", "moistur", "barrier", "ceramide", "hyaluronic"],
            "acne": ["acne", "blemish", "breakout", "pore", "salicylic", "niacinamide", "sebum"],
            "wrinkles": ["wrinkle", "fine line", "aging", "firm", "elastic", "peptide", "retinol"],
            "redness": ["redness", "sooth", "calm", "anti-inflammatory", "centella", "allantoin"]
        }
        matched_concerns = set()
        for c in skin_concerns:
            c_low = c.lower()
            keywords = concern_keywords.get(c_low, [c_low])
            for ing in ingredients:
                ing_concerns = (ing.get("skin_concerns") or "").lower()
                ing_benefits = (ing.get("benefits") or "").lower()
                if any(kw in ing_concerns or kw in ing_benefits for kw in keywords):
                    matched_concerns.add(c)
                    fit_score += 15
                    break
        
        if matched_concerns:
            evaluation["reason_codes"].append("CONCERN_MATCH")
            evaluation["reasons"].append(f"Active ingredients target concerns: {', '.join(sorted(matched_concerns))}")
        
        # Skincare goals matching
        skincare_goals = profile.get("skincare_goals") or []
        goal_keywords = {
            "strengthen skin barrier": ["barrier", "ceramide", "lipid", "repair", "protect"],
            "even skin tone": ["tone", "brighten", "radiance", "pigment", "complexion"],
            "hydrate skin": ["hydrat", "moistur", "hyaluronic", "humectant", "water"],
            "anti-aging / fine lines": ["wrinkle", "aging", "collagen", "firm", "fine line"],
            "clear acne": ["acne", "blemish", "clear", "salicylic", "purif"]
        }
        matched_goals = set()
        for g in skincare_goals:
            g_low = g.lower()
            keywords = goal_keywords.get(g_low, [g_low])
            for ing in ingredients:
                ing_benefits = (ing.get("benefits") or "").lower()
                if any(kw in ing_benefits for kw in keywords):
                    matched_goals.add(g)
                    fit_score += 10
                    break
        
        if matched_goals:
            evaluation["reason_codes"].append("GOAL_MATCH")
            evaluation["reasons"].append(f"Supports target goals: {', '.join(sorted(matched_goals))}")
        
        # ------------------------------------------------------------------
        # 3. RISK EVALUATION (Irritation, Sensitization, Environmental)
        # ------------------------------------------------------------------
        # Caution ingredients from early ingredient evaluation
        caution_ings = [ie for ie in ingredient_evaluations if ie.get("status") == "Use with Caution"]
        caution_count = len(caution_ings)
        risk_score += caution_count * 6

        # Elevated formulation potency risk (e.g. chemical acid peels)
        if is_high_potency_peel:
            risk_score += 20
            evaluation["reason_codes"].append("FORMULATION_POTENCY_CAUTION")
            evaluation["reasons"].append(
                "High-concentration chemical exfoliating formulation (AHA 30% / BHA 2%): intensive treatment requires acclimatization and elevated caution"
            )

        # Active cautions from caution ingredients
        if caution_count > 0:
            caution_names = [c["ingredient"] for c in caution_ings[:3]]
            evaluation["reason_codes"].append("ACTIVE_CAUTION")
            evaluation["reasons"].append(
                f"Contains {caution_count} caution-grade active ingredient{'s' if caution_count > 1 else ''}: {', '.join(caution_names)}"
            )

        irritation_ingredients = []
        for ing in ingredients:
            ing_name = ing.get("ingredient") or ""
            ir = (ing.get("irritation_risk") or "").lower()
            if ir in ["high", "very high"]:
                risk_score += 20
                evaluation["reason_codes"].append("IRRITATION_RISK")
                evaluation["reasons"].append(f"{ing_name} carries elevated irritation risk")
                irritation_ingredients.append(ing_name)
        
        # Add reason-specific mitigation for IRRITATION_RISK if any high irritation ingredients found
        if irritation_ingredients and "IRRITATION_RISK" in evaluation["reason_codes"]:
            evaluation["mitigations"].append(
                self._generate_reason_specific_mitigation("IRRITATION_RISK", product, user_data, evaluation, ingredients)
            )
        
        sensitization_ingredients = []
        for ing in ingredients:
            ing_name = ing.get("ingredient") or ""
            als = (ing.get("allergy_sensitization") or "").lower()
            if any(term in als for term in ["high", "frequent", "common allergen", "common sensitizer"]) and not any(neg in als for neg in ["not", "rare", "unlikely"]):
                risk_score += 15
                evaluation["reason_codes"].append("SENSITIZATION_RISK")
                evaluation["reasons"].append(f"{ing_name} is a known contact sensitizer for reactive skin")
                sensitization_ingredients.append(ing_name)
        
        # Add reason-specific mitigation for SENSITIZATION_RISK if any sensitizing ingredients found
        if sensitization_ingredients and "SENSITIZATION_RISK" in evaluation["reason_codes"]:
            evaluation["mitigations"].append(
                self._generate_reason_specific_mitigation("SENSITIZATION_RISK", product, user_data, evaluation, ingredients)
            )
        
        if product_history:
            reaction = (product_history.get("reaction") or "").strip().lower()
            notes = (product_history.get("notes") or "").strip().lower() if isinstance(product_history.get("notes"), str) else ""
            adverse_signals = [
                "burning", "stinging", "rash", "itching", "itchy", 
                "redness", "broke out", "breakout", "bumps", "irritation",
                "peeling", "inflamed"
            ]
            
            negations = ["no ", "not ", "never ", "without "]
            found_note_signals = []
            for sig in adverse_signals:
                if sig in notes:
                    # Check if the signal is negated (preceded by negation word)
                    negation_found = False
                    sig_index = notes.lower().find(sig)
                    if sig_index > 0:
                        # Check if there's a negation word before the signal
                        text_before = notes.lower()[:sig_index].strip()
                        for neg in negations:
                            if text_before.endswith(neg.strip()):
                                negation_found = True
                                break
                    
                    if not negation_found:
                        found_note_signals.append(sig)
            
            has_explicit_moderate = reaction in ["moderate", "breakout", "stinging", "redness"]
            if has_explicit_moderate:
                risk_score += 25
                evaluation["reason_codes"].append("PREVIOUS_REACTION")
                evaluation["reasons"].append(f"Recorded previous {reaction} reaction in user history")
                if found_note_signals:
                    evaluation["reasons"].append(f"User notes corroborate symptoms: {', '.join(found_note_signals[:3])}")
                evaluation["mitigations"].append(
                    self._generate_reason_specific_mitigation("PREVIOUS_REACTION", product, user_data, evaluation, ingredients)
                )
                evaluation["_product_history"] = product_history
            elif found_note_signals:
                risk_score += 25
                evaluation["reason_codes"].append("PREVIOUS_REACTION")
                evaluation["reasons"].append(f"Product history notes report adverse reactions: {', '.join(found_note_signals[:3])}")
                evaluation["mitigations"].append(
                    self._generate_reason_specific_mitigation("PREVIOUS_REACTION", product, user_data, evaluation, ingredients)
                )
                evaluation["_product_history"] = product_history
            elif reaction == "mild":
                risk_score += 10
                evaluation["reason_codes"].append("PREVIOUS_REACTION")
                evaluation["reasons"].append("Recorded mild prior reaction in user history")
                evaluation["mitigations"].append(
                    self._generate_reason_specific_mitigation("PREVIOUS_REACTION", product, user_data, evaluation, ingredients)
                )
                evaluation["_product_history"] = product_history
        
        if skin_analysis:
            severity = (skin_analysis.get("severity") or "").lower()
            if severity in ["moderate", "severe"]:
                active_terms = ["retinol", "glycolic", "lactic", "salicylic", "benzoyl peroxide"]
                active_ingredient = None
                for ing in ingredients:
                    ing_name = (ing.get("ingredient") or "").lower()
                    if any(act in ing_name for act in active_terms):
                        active_ingredient = ing.get('ingredient')
                        risk_score += 15
                        evaluation["reason_codes"].append("ACTIVE_CAUTION")
                        evaluation["reasons"].append(f"Contains strong active ({active_ingredient}) during skin flare-up ({severity.capitalize()} severity)")
                        break
                
                if active_ingredient and "ACTIVE_CAUTION" in evaluation["reason_codes"]:
                    evaluation["mitigations"].append(
                        self._generate_reason_specific_mitigation("ACTIVE_CAUTION", product, user_data, evaluation, ingredients)
                    )
        
        if environment:
            humidity = environment.get("humidity")
            if isinstance(humidity, (int, float)) and humidity > 70:
                skin_type = (profile.get("skin_type") or "").strip().lower()
                skin_concerns = [str(c).strip().lower() for c in (profile.get("skin_concerns") or [])] if profile.get("skin_concerns") else []
                is_dry_skin = skin_type in ["dry", "very dry"] or "dryness" in skin_concerns
                heavy_terms = ["petrolatum", "mineral oil", "shea butter", "beeswax"]
                for ing in ingredients:
                    ing_name = (ing.get("ingredient") or "").lower()
                    if any(heavy in ing_name for heavy in heavy_terms):
                        if is_dry_skin:
                            # Occlusives protect dry skin barrier even in humid weather; do not penalize
                            evaluation["reasons"].append(
                                f"{ing.get('ingredient')} provides essential barrier protection for dry skin despite high humidity ({humidity}%)"
                            )
                        else:
                            risk_score += 10
                            evaluation["reason_codes"].append("ENVIRONMENT_MISMATCH")
                            display_type = skin_type.capitalize() if skin_type else "your"
                            evaluation["reasons"].append(
                                f"{ing.get('ingredient')} may feel heavy or occlusive in high humidity ({humidity}%) for {display_type} skin"
                            )
                            evaluation["mitigations"].append(
                                self._generate_reason_specific_mitigation("ENVIRONMENT_MISMATCH", product, user_data, evaluation, ingredients)
                            )
                        break
        
        # ------------------------------------------------------------------
        # 4. DECISION & CONFIDENCE SYNTHESIS
        # ------------------------------------------------------------------
        is_high_risk = is_high_potency_peel or risk_score >= 15 or caution_count >= 2

        if is_high_risk:
            evaluation["decision"] = "CAUTION"
            if evidence_score < 40:
                evaluation["confidence"] = "low"
                evaluation["reason_codes"].append("EVIDENCE_INCOMPLETE")
                evaluation["reasons"].append("Limited scientific research available for some ingredients in this formulation")
                evaluation["mitigations"].append(
                    self._generate_reason_specific_mitigation("EVIDENCE_INCOMPLETE", product, user_data, evaluation, ingredients)
                )
            else:
                evaluation["confidence"] = "medium"
        elif risk_score > 0 and fit_score < 15:
            evaluation["decision"] = "CAUTION"
            evaluation["confidence"] = "medium"
        elif evidence_score < 40:
            evaluation["decision"] = "CAUTION"
            evaluation["confidence"] = "low"
            evaluation["reason_codes"].append("EVIDENCE_INCOMPLETE")
            evaluation["reasons"].append("Limited scientific research available for some ingredients in this formulation")
            evaluation["mitigations"].append(
                self._generate_reason_specific_mitigation("EVIDENCE_INCOMPLETE", product, user_data, evaluation, ingredients)
            )
        else:
            evaluation["decision"] = "KEEP"
            if evidence_score >= 70 and (fit_score >= 20 or risk_score == 0):
                evaluation["confidence"] = "high"
            elif evidence_score >= 40 and fit_score >= 10:
                evaluation["confidence"] = "medium"
            else:
                evaluation["confidence"] = "low"
        
        # Mitigations
        if is_high_potency_peel:
            peel_mitigations = [
                "Perform a patch test on a small area of the forearm 24-48 hours before facial application.",
                "Apply to clean, dry skin for a maximum of 10 minutes; rinse thoroughly with lukewarm water (do not leave on).",
                "Limit usage frequency to no more than 1-2 times weekly, preferably in your evening routine.",
                "Do not combine with other direct acids (glycolic, salicylic), retinoids, or pure Vitamin C in the same routine.",
                "Apply broad-spectrum sunscreen (SPF 30+) daily, as AHAs increase skin sensitivity to UV exposure."
            ]
            for pm in peel_mitigations:
                if pm not in evaluation["mitigations"]:
                    evaluation["mitigations"].append(pm)
        elif caution_count >= 2 and not evaluation["mitigations"]:
            evaluation["mitigations"].append("Formula contains multiple moderate-irritation ingredients; patch test recommended before regular use.")

        # Expose fit_score for routine product selection
        evaluation["fit_score"] = fit_score
        
        # Store total_parsed for mitigation functions
        evaluation["_total_parsed_ingredients"] = total_parsed
        
        # Prioritize safety & formulation cautions above fit reasons
        safety_reasons = []
        fit_reasons = []
        for r in evaluation["reasons"]:
            r_low = r.lower()
            if any(k in r_low for k in ["caution", "contraindicat", "irritat", "peel", "risk", "adverse", "sensitiz", "flare-up", "mismatch"]):
                safety_reasons.append(r)
            else:
                fit_reasons.append(r)
        
        evaluation["reasons"] = list(dict.fromkeys(safety_reasons + fit_reasons))
        evaluation["reason_codes"] = list(dict.fromkeys(evaluation["reason_codes"]))
        evaluation["mitigations"] = list(dict.fromkeys(evaluation["mitigations"]))
        
        if not evaluation["reasons"]:
            evaluation["reasons"].append("Product formulation is compatible with your skin profile")
        
        return evaluation
    
    def detect_cross_product_interactions(
        self, 
        slotted_products: List[Dict[str, Any]], 
        product_actives_map: Dict[Any, set] 
    ) -> List[str]:
        """
        Evaluate pairwise product interactions using database interactions_with_other_ingredients metadata.
        Returns a list of human-readable conflict warnings.
        """
        conflicts = []
        caution_triggers = ["caution", "avoid", "degrade", "incompatible", "conflict", "irritat", "low ph", "contraind"]
        target_map = {
            "retinoid": "retinoids",
            "retinol": "retinoids",
            "aha": "ahas",
            "bha": "bhas",
            "acid": "ahas",
            "benzoyl peroxide": "benzoyl_peroxide",
            "bpo": "benzoyl_peroxide",
            "vitamin c": "vitamin_c",
            "ascorbic": "vitamin_c",
            "niacinamide": "niacinamide"
        }
        
        for i, prod_a in enumerate(slotted_products):
            ings_a = prod_a.get("_resolved_ingredients") or []
            name_a = prod_a.get("product_name") or "Product"
            
            for ing_a in ings_a:
                interaction_text = (ing_a.get("interactions_with_other_ingredients") or "").strip()
                if not interaction_text or interaction_text.lower() in ["none known", "unknown", "none"]:
                    continue
                
                lower_text = interaction_text.lower()
                if not any(trigger in lower_text for trigger in caution_triggers):
                    continue
                
                ing_name = ing_a.get("ingredient") or "Active"
                
                for j, prod_b in enumerate(slotted_products):
                    if i == j:
                        continue
                    
                    id_b = prod_b.get("product_id")
                    actives_b = product_actives_map.get(id_b, set())
                    name_b = prod_b.get("product_name") or "Second Product"
                    
                    for search_term, target_group in target_map.items():
                        if search_term in lower_text and target_group in actives_b:
                            warning = f"Ingredient interaction: {ing_name} in '{name_a}' notes '{interaction_text}' when paired with {target_group.replace('_', ' ').title()} in '{name_b}'."
                            if warning not in conflicts:
                                conflicts.append(warning)
        
        return conflicts
    
    def _generate_lifestyle_insights(self, user_data: Dict[str, Any]) -> List[str]:
        """
        Generate small deterministic lifestyle/environment insights based on user profile.
        Uses existing stored profile/environment fields only.
        Returns at most 2-3 practical, non-diagnostic insights.
        """
        insights = []
        profile = user_data.get("profile") or {}
        environment = user_data.get("environment")
        
        # Sleep and stress insights
        sleep = profile.get("sleep")
        stress_level = profile.get("stress_level")
        
        if sleep and stress_level:
            if sleep in ["less than 6 hours", "6-7 hours"] and stress_level in ["high", "very high"]:
                insights.append("Consider keeping your routine simple during periods of higher stress and shorter sleep to support skin recovery.")
        
        # Hydration insight
        water_intake = profile.get("water_intake")
        if water_intake and water_intake in ["less than 4 glasses", "4-6 glasses"]:
            insights.append("Maintaining consistent hydration supports your skin's natural barrier function.")
        
        # Environment insights
        if environment:
            humidity = environment.get("humidity")
            temperature = environment.get("temperature")
            
            if isinstance(humidity, (int, float)) and humidity > 70:
                insights.append("In high humidity, lighter gel textures may feel more comfortable on your skin.")
            elif isinstance(humidity, (int, float)) and humidity < 30:
                insights.append("In low humidity conditions, focus on barrier-supporting products with hydrating ingredients.")
            
            if isinstance(temperature, (int, float)) and temperature > 30:
                insights.append("In high temperatures, consider gentle cleansing and avoiding over-exfoliation to maintain skin balance.")
        
        # Limit to maximum 3 insights
        return insights[:3]
    
    def build_am_routine(self, evaluated_products: List[Dict[str, Any]], user_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Build AM routine from evaluated products with ingredient-level conflict and overlap detection.
        Order: Cleanser -> Treatment -> Moisturizer -> Sunscreen
        """
        am_routine = {"cleanser": None, "treatment": None, "moisturizer": None, "sunscreen": None}
        conflicts = []
        overlaps = []
        missing_steps = []
        
        # Get user profile data for treatment relevance check
        profile = user_data.get("profile") if user_data else {}
        skin_concerns = profile.get("skin_concerns") or []
        skincare_goals = profile.get("skincare_goals") or []
        
        # Check if treatment is relevant based on concerns/goals
        treatment_relevant_concerns = ["acne", "pigmentation", "wrinkles", "redness"]
        treatment_relevant_goals = ["anti-aging / fine lines", "clear acne", "even skin tone"]
        is_treatment_relevant = any(
            str(c).lower() in treatment_relevant_concerns for c in skin_concerns
        ) or any(
            str(g).lower() in treatment_relevant_goals for g in skincare_goals
        )
        
        # Exclude REJECT products; group KEEP and CAUTION (excluding unresolved products without verified data)
        keep_products = [p for p in evaluated_products if p.get("evaluation", {}).get("decision") == "KEEP"]
        caution_products = [p for p in evaluated_products if p.get("evaluation", {}).get("decision") == "CAUTION"]
        suitable_products = [
            p for p in (keep_products + caution_products)
            if p.get("product_id") is not None and "PRODUCT_UNRESOLVED" not in p.get("evaluation", {}).get("reason_codes", [])
        ]
        
        # Map product active chemical classes from ingredients
        product_actives_map = {}
        for p in suitable_products:
            p_id = p.get("product_id")
            ings = p.get("_resolved_ingredients") or []
            product_actives_map[p_id] = self.extract_active_classes(p, ings)
        
        # Slot definitions with flexible category and product_type matching
        slot_checks = {
            "cleanser": lambda p: any(t in (p.get("product_type") or "").lower() for t in ["cleanser", "face wash"]) or any(t in (p.get("category") or "").lower() for t in ["cleanser", "face wash"]),
            "treatment": lambda p: any(t in (p.get("product_type") or "").lower() for t in ["serum", "toner", "treatment", "essence"]) or any(t in (p.get("category") or "").lower() for t in ["serum", "toner"]),
            "moisturizer": lambda p: any(t in (p.get("product_type") or "").lower() for t in ["moisturizer", "cream", "lotion", "gel"]) or any(t in (p.get("category") or "").lower() for t in ["moisturizer", "face moisturizers"]),
            "sunscreen": lambda p: any(t in (p.get("product_type") or "").lower() for t in ["sunscreen", "spf"]) or any(t in (p.get("category") or "").lower() for t in ["sunscreen", "sun protect"])
        }
        
        for slot, check_fn in slot_checks.items():
            matching_products = [p for p in suitable_products if check_fn(p)]
            if matching_products:
                # Prioritize KEEP over CAUTION, then higher fit_score, then confidence, then stable product_id
                matching_products.sort(
                    key=lambda x: (
                        0 if x.get("evaluation", {}).get("decision") == "KEEP" else 1,
                        -(x.get("evaluation", {}).get("fit_score", 0)),  # Higher fit_score first
                        0 if x.get("evaluation", {}).get("confidence") == "high" else (1 if x.get("evaluation", {}).get("confidence") == "medium" else 2),
                        str(x.get("product_id", ""))  # Stable product_id tie-breaker
                    )
                )
                am_routine[slot] = matching_products[0]
                # Log any alternate products to overlaps rather than silently dropping them
                if len(matching_products) > 1:
                    for alt in matching_products[1:]:
                        overlaps.append(f"Multiple {slot.capitalize()} products: '{matching_products[0].get('product_name')}' active in routine; '{alt.get('product_name')}' held as alternate.")
        
        # Routine-level active conflict checks across slotted products
        slotted_products = [p for p in am_routine.values() if p]
        all_am_actives = set()
        for p in slotted_products:
            p_id = p.get("product_id")
            all_am_actives.update(product_actives_map.get(p_id, set()))
        
        # 1. Database-grounded cross-product interaction checks
        db_conflicts = self.detect_cross_product_interactions(slotted_products, product_actives_map)
        conflicts.extend(db_conflicts)
        
        # 2. Existing fallback active conflict checks
        if "retinoids" in all_am_actives:
            conflicts.append("Retinoids detected in AM routine. Retinoids degrade in UV light and are best reserved for PM.")
        if "retinoids" in all_am_actives and ("ahas" in all_am_actives or "bhas" in all_am_actives):
            fallback_msg = "Retinoids combined with direct acids (AHA/BHA) in the same routine increase irritation risk."
            if not any("retinoid" in c.lower() and ("aha" in c.lower() or "acid" in c.lower()) for c in conflicts):
                conflicts.append(fallback_msg)
        if "ahas" in all_am_actives and "bhas" in all_am_actives:
            overlaps.append("Multiple chemical exfoliants (AHA + BHA) detected in AM routine. Monitor skin barrier tolerance.")
        
        # Missing essential steps
        if not am_routine["cleanser"]:
            missing_steps.append("Cleanser (AM)")
        if not am_routine["treatment"] and is_treatment_relevant:
            missing_steps.append("Treatment (AM)")
        if not am_routine["moisturizer"]:
            missing_steps.append("Moisturizer (AM)")
        if not am_routine["sunscreen"]:
            missing_steps.append("Sunscreen (AM)")
        
        return {
            "slots": am_routine,
            "conflicts": conflicts,
            "overlaps": overlaps,
            "missing_steps": missing_steps
        }
    
    def build_pm_routine(self, evaluated_products: List[Dict[str, Any]], user_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Build PM routine from evaluated products with ingredient-level conflict and overlap detection.
        Order: Cleanser -> Treatment -> Moisturizer
        """
        pm_routine = {"cleanser": None, "treatment": None, "moisturizer": None}
        conflicts = []
        overlaps = []
        missing_steps = []
        
        # Get user profile data for treatment relevance check
        profile = user_data.get("profile") if user_data else {}
        skin_concerns = profile.get("skin_concerns") or []
        skincare_goals = profile.get("skincare_goals") or []
        
        # Check if treatment is relevant based on concerns/goals
        treatment_relevant_concerns = ["acne", "pigmentation", "wrinkles", "redness"]
        treatment_relevant_goals = ["anti-aging / fine lines", "clear acne", "even skin tone"]
        is_treatment_relevant = any(
            str(c).lower() in treatment_relevant_concerns for c in skin_concerns
        ) or any(
            str(g).lower() in treatment_relevant_goals for g in skincare_goals
        )
        
        keep_products = [p for p in evaluated_products if p.get("evaluation", {}).get("decision") == "KEEP"]
        caution_products = [p for p in evaluated_products if p.get("evaluation", {}).get("decision") == "CAUTION"]
        suitable_products = [
            p for p in (keep_products + caution_products)
            if p.get("product_id") is not None and "PRODUCT_UNRESOLVED" not in p.get("evaluation", {}).get("reason_codes", [])
        ]
        
        product_actives_map = {}
        for p in suitable_products:
            p_id = p.get("product_id")
            ings = p.get("_resolved_ingredients") or []
            product_actives_map[p_id] = self.extract_active_classes(p, ings)
        
        slot_checks = {
            "cleanser": lambda p: any(t in (p.get("product_type") or "").lower() for t in ["cleanser", "face wash"]) or any(t in (p.get("category") or "").lower() for t in ["cleanser", "face wash"]),
            "treatment": lambda p: any(t in (p.get("product_type") or "").lower() for t in ["serum", "treatment", "retinol", "essence"]) or any(t in (p.get("category") or "").lower() for t in ["serum", "treatment"]),
            "moisturizer": lambda p: any(t in (p.get("product_type") or "").lower() for t in ["moisturizer", "cream", "sleeping mask", "night cream"]) or any(t in (p.get("category") or "").lower() for t in ["moisturizer", "face moisturizers"])
        }
        
        for slot, check_fn in slot_checks.items():
            matching_products = [p for p in suitable_products if check_fn(p)]
            if matching_products:
                # Prioritize KEEP over CAUTION, then higher fit_score, then confidence, then stable product_id
                matching_products.sort(
                    key=lambda x: (
                        0 if x.get("evaluation", {}).get("decision") == "KEEP" else 1,
                        -(x.get("evaluation", {}).get("fit_score", 0)),  # Higher fit_score first
                        0 if x.get("evaluation", {}).get("confidence") == "high" else (1 if x.get("evaluation", {}).get("confidence") == "medium" else 2),
                        str(x.get("product_id", ""))  # Stable product_id tie-breaker
                    )
                )
                pm_routine[slot] = matching_products[0]
                if len(matching_products) > 1:
                    for alt in matching_products[1:]:
                        overlaps.append(f"Multiple {slot.capitalize()} products: '{matching_products[0].get('product_name')}' active in PM routine; '{alt.get('product_name')}' held as alternate.")
        
        slotted_products = [p for p in pm_routine.values() if p]
        all_pm_actives = set()
        for p in slotted_products:
            p_id = p.get("product_id")
            all_pm_actives.update(product_actives_map.get(p_id, set()))
        
        # 1. Database-grounded cross-product interaction checks
        db_conflicts = self.detect_cross_product_interactions(slotted_products, product_actives_map)
        conflicts.extend(db_conflicts)
        
        # 2. Existing fallback active conflict checks
        if "retinoids" in all_pm_actives and ("ahas" in all_pm_actives or "bhas" in all_pm_actives):
            fallback_msg = "Retinoids paired with direct acids (AHA/BHA) in PM routine may increase sensitivity. Consider alternating nights."
            if not any("retinoid" in c.lower() and ("aha" in c.lower() or "acid" in c.lower()) for c in conflicts):
                conflicts.append(fallback_msg)
        if "ahas" in all_pm_actives and "bhas" in all_pm_actives:
            overlaps.append("Multiple chemical exfoliants (AHA + BHA) detected in PM routine. Monitor barrier integrity.")
        
        if not pm_routine["cleanser"]:
            missing_steps.append("Cleanser (PM)")
        if not pm_routine["treatment"] and is_treatment_relevant:
            missing_steps.append("Treatment (PM)")
        if not pm_routine["moisturizer"]:
            missing_steps.append("Moisturizer (PM)")
        
        return {
            "slots": pm_routine,
            "conflicts": conflicts,
            "overlaps": overlaps,
            "missing_steps": missing_steps
        }
    
    def analyze_user_personalization(self, user_id: str) -> Dict[str, Any]:
        """
        Main personalization analysis method with exception resilience.
        """
        user_data = self.load_user_data(user_id)
        evaluated_products = []
        
        # ------------------------------------------------------------------
        # PRODUCT RECONCILIATION: Match unresolved products to resolved ones
        # ------------------------------------------------------------------
        current_products = user_data.get("current_products", [])
        
        # Build index of resolved products by canonical identity
        resolved_catalog_cache = {}
        resolved_keys_to_product_id = {}
        
        resolved_ids = [p.get("product_id") for p in current_products if p.get("product_id")]
        if resolved_ids:
            try:
                cat_resp = self.supabase.table("products").select("*").in_("product_id", resolved_ids).execute()
                for cat_p in (cat_resp.data or []):
                    resolved_catalog_cache[cat_p["product_id"]] = cat_p
            except Exception as e:
                print(f"Error fetching catalog for resolved products: {e}")
                
        for product_history in current_products:
            p_id = product_history.get("product_id")
            if p_id:
                cat_p = resolved_catalog_cache.get(p_id, {})
                c_brand = cat_p.get("brand") or product_history.get("brand") or ""
                c_name = cat_p.get("product_name") or product_history.get("product_name") or ""
                h_name = product_history.get("product_name") or ""
                
                k1 = self._canonical_product_key(c_name, c_brand)
                k2 = self._canonical_product_key(h_name, c_brand)
                if k1:
                    resolved_keys_to_product_id[k1] = p_id
                if k2:
                    resolved_keys_to_product_id[k2] = p_id
        
        # Reconcile unresolved products in memory
        reconciled_products = []
        for product_history in current_products:
            p_id = product_history.get("product_id")
            p_name = product_history.get("product_name") or ""
            p_brand = product_history.get("brand") or ""
            
            if not p_id:
                canon_key = self._canonical_product_key(p_name, p_brand)
                if canon_key and canon_key in resolved_keys_to_product_id:
                    matched_id = resolved_keys_to_product_id[canon_key]
                    reconciled = dict(product_history)
                    reconciled["product_id"] = matched_id
                    if matched_id in resolved_catalog_cache:
                        reconciled["brand"] = resolved_catalog_cache[matched_id].get("brand") or reconciled.get("brand")
                        reconciled["product_name"] = resolved_catalog_cache[matched_id].get("product_name") or reconciled.get("product_name")
                    reconciled["_reconciled"] = True
                    reconciled_products.append(reconciled)
                else:
                    # Also check directly against catalog for genuine catalog match
                    matched_cat_id = None
                    matched_brand = None
                    matched_name = None
                    try:
                        norm_search = self._normalize_product_identity(p_name, p_brand)
                        extracted_b = p_brand
                        if not extracted_b:
                            for kb, kb_canon in [("reequil", "Reequil"), ("dot and key", "Dot & Key"), ("cerave", "CeraVe"), ("cetaphil", "Cetaphil"), ("wishcare", "WishCare"), ("minimalist", "Minimalist"), ("be minimalist", "Minimalist")]:
                                if norm_search.startswith(kb + " ") or norm_search == kb:
                                    extracted_b = kb_canon
                                    break
                        if extracted_b:
                            res = self.supabase.table("products").select("*").ilike("brand", f"%{extracted_b}%").execute()
                            for cp in (res.data or []):
                                cp_key = self._canonical_product_key(cp.get("product_name"), cp.get("brand"))
                                cp_norm = self._normalize_product_identity(cp.get("product_name"))
                                if cp_key == canon_key or cp_norm == norm_search or (set(cp_norm.split()) == set(norm_search.split())):
                                    matched_cat_id = cp.get("product_id")
                                    matched_brand = cp.get("brand")
                                    matched_name = cp.get("product_name")
                                    break
                        else:
                            # Brandless catalog lookup: search by canonical product_name match
                            # e.g. "Hydrating Facial Cleanser" with missing brand
                            norm_input_name = self._normalize_product_identity(p_name)
                            if norm_input_name:
                                cat_res = self.supabase.table("products").select("product_id,brand,product_name,category").execute()
                                matching_products = []
                                for cp in (cat_res.data or []):
                                    cp_norm_name = self._normalize_product_identity(cp.get("product_name"))
                                    if cp_norm_name == norm_input_name or (set(cp_norm_name.split()) == set(norm_input_name.split())):
                                        matching_products.append(cp)
                                
                                # Unambiguous match: exactly 1 product matches in catalog
                                if len(matching_products) == 1:
                                    matched_cat = matching_products[0]
                                    matched_cat_id = matched_cat.get("product_id")
                                    matched_brand = matched_cat.get("brand")
                                    matched_name = matched_cat.get("product_name")
                    except Exception as e:
                        print(f"Catalog fallback search error: {e}")
                    
                    if matched_cat_id:
                        reconciled = dict(product_history)
                        reconciled["product_id"] = matched_cat_id
                        if matched_brand:
                            reconciled["brand"] = matched_brand
                        if matched_name:
                            reconciled["product_name"] = matched_name
                        reconciled["_reconciled"] = True
                        reconciled_products.append(reconciled)
                    else:
                        # Genuinely unresolved product (e.g. unverified/external products)
                        reconciled_products.append(product_history)
            else:
                reconciled_products.append(product_history)
        
        # Deduplicate reconciled products before evaluation so duplicate entries for the same product are merged
        seen_reconciled = set()
        deduped_reconciled = []
        for rp in reconciled_products:
            rp_id = rp.get("product_id")
            rp_name = rp.get("product_name") or ""
            rp_brand = rp.get("brand") or ""
            key = f"id:{rp_id}" if rp_id else f"raw:{self._canonical_product_key(rp_name, rp_brand)}"
            if key not in seen_reconciled:
                seen_reconciled.add(key)
                deduped_reconciled.append(rp)
                
        reconciled_products = deduped_reconciled
        
        # ------------------------------------------------------------------
        # EVALUATE PRODUCTS
        # ------------------------------------------------------------------
        for product_history in reconciled_products:
            product_id = product_history.get("product_id")
            if not product_id:
                # Handle unresolved product without inventing catalog or ingredient data
                unresolved_product = {
                    "product_id": None,
                    "product_name": product_history.get("product_name") or "Unknown Product",
                    "product_type": product_history.get("product_type"),
                    "status": product_history.get("status", "current"),
                }
                evaluation = self.evaluate_product_suitability(
                    unresolved_product, user_data, product_history, ingredients=[], total_parsed=0
                )
                unresolved_product["evaluation"] = evaluation
                evaluated_products.append(unresolved_product)
                continue
            
            try:
                product_response = self.supabase.table("products").select("*").eq("product_id", product_id).execute()
                if product_response.data:
                    product = product_response.data[0]
                    product["product_type"] = product_history.get("product_type")
                    product["status"] = product_history.get("status")
                    
                    # Fetch ingredients and parsed count
                    ings, total_parsed = self.get_product_ingredients(product_id)
                    # Cache on product object for routine analysis
                    product["_resolved_ingredients"] = ings
                    product["_total_parsed_ingredients"] = total_parsed
                    
                    # Run suitability evaluation
                    evaluation = self.evaluate_product_suitability(
                        product, user_data, product_history, ings, total_parsed
                    )
                    product["evaluation"] = evaluation
                    evaluated_products.append(product)
                else:
                    unresolved_product = {
                        "product_id": None,
                        "product_name": product_history.get("product_name") or f"Product #{product_id}",
                        "product_type": product_history.get("product_type"),
                        "status": product_history.get("status", "current"),
                    }
                    evaluation = self.evaluate_product_suitability(
                        unresolved_product, user_data, product_history, ingredients=[], total_parsed=0
                    )
                    unresolved_product["evaluation"] = evaluation
                    evaluated_products.append(unresolved_product)
            except Exception as e:
                print(f"Error evaluating product {product_id}: {e}")
                # Safe fallback: do not drop product from user evaluation
                fallback_product = {
                    "product_id": product_id,
                    "product_name": product_history.get("product_name") or f"Product #{product_id}",
                    "product_type": product_history.get("product_type"),
                    "status": product_history.get("status", "current"),
                    "evaluation": {
                        "decision": "CAUTION",
                        "confidence": "low",
                        "reason_codes": ["EVIDENCE_INCOMPLETE"],
                        "reasons": ["Automated evaluation encountered an unexpected issue; manual check recommended"],
                        "mitigations": ["Patch test before use and check ingredient list manually"]
                    }
                }
                evaluated_products.append(fallback_product)
        
        # ------------------------------------------------------------------
        # DEDUPLICATE EVALUATED PRODUCTS BY CANONICAL IDENTITY
        # ------------------------------------------------------------------
        seen_eval_keys = set()
        deduplicated_evaluated = []
        for product in evaluated_products:
            p_id = product.get("product_id")
            p_name = product.get("product_name") or ""
            p_brand = product.get("brand") or ""
            eval_key = f"id:{p_id}" if p_id else f"raw:{self._canonical_product_key(p_name, p_brand)}"
            if eval_key not in seen_eval_keys:
                seen_eval_keys.add(eval_key)
                deduplicated_evaluated.append(product)
                
        evaluated_products = deduplicated_evaluated
        
        # Build routines
        am_routine = self.build_am_routine(evaluated_products, user_data)
        pm_routine = self.build_pm_routine(evaluated_products, user_data)
        
        # Overall confidence calculation
        confidence_scores = [p.get("evaluation", {}).get("confidence", "medium") for p in evaluated_products]
        if confidence_scores:
            if all(c == "high" for c in confidence_scores):
                overall_confidence = "high"
            elif any(c == "low" for c in confidence_scores):
                overall_confidence = "medium" if any(c == "high" for c in confidence_scores) else "low"
            else:
                overall_confidence = "medium"
        else:
            overall_confidence = "low"
        
        # Strip internal temporary keys before serialization
        for p in evaluated_products:
            p.pop("_resolved_ingredients", None)
            p.pop("_total_parsed_ingredients", None)
        
        all_conflicts = list(dict.fromkeys(am_routine.get("conflicts", []) + pm_routine.get("conflicts", [])))
        all_overlaps = list(dict.fromkeys(am_routine.get("overlaps", []) + pm_routine.get("overlaps", [])))
        all_missing_steps = list(dict.fromkeys(am_routine.get("missing_steps", []) + pm_routine.get("missing_steps", [])))
        
        # Generate recommendations for missing steps
        recommendations = {}
        if all_missing_steps:
            try:
                recommendation_service = RecommendationService()
                recommendations = recommendation_service.generate_recommendations(
                    all_missing_steps,
                    user_data,
                    self
                )
            except Exception as e:
                print(f"Error generating recommendations: {e}")
                recommendations = {}
        
        # Generate lifestyle/environment insights
        lifestyle_insights = self._generate_lifestyle_insights(user_data)
        
        return {
            "success": True,
            "user_id": user_id,
            "evaluated_products": evaluated_products,
            "am_routine": am_routine.get("slots"),
            "pm_routine": pm_routine.get("slots"),
            "confidence": overall_confidence,
            "conflicts": all_conflicts,
            "overlaps": all_overlaps,
            "missing_steps": all_missing_steps,
            "recommendations": recommendations,
            "lifestyle_insights": lifestyle_insights
        }

    def evaluate_single_product(
        self,
        user_id: str,
        product_id: Optional[int] = None,
        product_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate an arbitrary product (in or out of user routine) against the logged-in user's profile.
        Reuses the exact evaluate_product_suitability engine.
        
        Args:
            user_id: Authenticated user ID
            product_id: Optional catalog product ID
            product_data: Optional product attributes (name, brand, ingredients, etc.)
            
        Returns:
            Dictionary containing evaluation results (decision, confidence, reasons, mitigations)
        """
        user_data = self.load_user_data(user_id)
        
        # 1. Resolve product record
        product = {}
        if product_id:
            try:
                p_resp = self.supabase.table("products").select("*").eq("product_id", product_id).execute()
                if p_resp.data:
                    product = p_resp.data[0]
            except Exception as e:
                print(f"Error fetching product {product_id}: {e}")
        
        if not product and product_data:
            p_name = product_data.get("product_name")
            p_brand = product_data.get("brand")
            if p_name:
                try:
                    q = self.supabase.table("products").select("*")
                    if p_brand:
                        q = q.ilike("brand", f"%{p_brand}%")
                    q = q.ilike("product_name", f"%{p_name}%").limit(1)
                    p_resp = q.execute()
                    if p_resp.data:
                        product = p_resp.data[0]
                except Exception as e:
                    print(f"Error searching product by name: {e}")
            if not product:
                product = dict(product_data)
        
        if not product:
            return {
                "success": False,
                "error": "Product could not be resolved or found",
                "evaluation": None
            }
        
        target_pid = product.get("product_id")
        target_name = (product.get("product_name") or "").lower()
        
        # 2. Check if user has an existing reaction or notes logged for this product
        product_history = None
        for p in user_data.get("current_products", []):
            if target_pid and p.get("product_id") == target_pid:
                product_history = p
                break
            elif target_name and (p.get("product_name") or "").lower() == target_name:
                product_history = p
                break
                
        if not product_history and user_id:
            try:
                q = self.supabase.table("user_product_history").select("*").eq("user_id", user_id)
                if target_pid:
                    q = q.eq("product_id", target_pid)
                elif target_name:
                    q = q.ilike("product_name", f"%{target_name}%")
                h_resp = q.order("created_at", desc=True).limit(1).execute()
                if h_resp.data:
                    product_history = h_resp.data[0]
            except Exception as e:
                print(f"Error checking user product history: {e}")
        
        # 3. Resolve ingredients
        ingredients = []
        total_parsed = 0
        if target_pid:
            ingredients, total_parsed = self.get_product_ingredients(target_pid)
        if not ingredients:
            raw_list = product.get("normalized_ingredients") or product.get("full_ingredient_list")
            if raw_list:
                parsed_names = [n.strip() for n in raw_list.replace("|", ",").split(",") if n.strip()]
                total_parsed = len(parsed_names)
                for ing_name in parsed_names:
                    cache_key = ing_name.lower()
                    if cache_key in self._ingredient_cache:
                        ingredients.append(self._ingredient_cache[cache_key])
                        continue
                    try:
                        ing_resp = self.supabase.table("ingredients").select("*").ilike("ingredient", f"%{ing_name}%").limit(1).execute()
                        if ing_resp.data:
                            ingredients.append(ing_resp.data[0])
                            self._ingredient_cache[cache_key] = ing_resp.data[0]
                    except Exception as e:
                        pass
        
        product["_resolved_ingredients"] = ingredients
        product["_total_parsed_ingredients"] = total_parsed
        
        # 4. Evaluate using the existing suitability engine
        evaluation = self.evaluate_product_suitability(
            product,
            user_data,
            product_history=product_history,
            ingredients=ingredients,
            total_parsed=total_parsed
        )
        
        return {
            "success": True,
            "product_id": target_pid,
            "product_name": product.get("product_name"),
            "brand": product.get("brand"),
            "category": product.get("category"),
            "evaluation": evaluation
        }