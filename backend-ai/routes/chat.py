import os
import json
import re
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from services.personalization_service import PersonalizationService

router = APIRouter(tags=["chat"])
personalization_service = PersonalizationService()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class CurrentProductContext(BaseModel):
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    decision: Optional[str] = None  # KEEP, CAUTION, REJECT
    match_label: Optional[str] = None
    confidence: Optional[str] = None
    reasons: Optional[List[str]] = Field(default_factory=list)
    mitigations: Optional[List[str]] = Field(default_factory=list)
    reason_codes: Optional[List[str]] = Field(default_factory=list)
    suitable_count: Optional[int] = None
    caution_count: Optional[int] = None
    not_recommended_count: Optional[int] = None


class DermatologistSearchAction(BaseModel):
    type: str = "maps"
    label: str
    query: str
    url: str
    maps_url: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = Field(default_factory=list)
    current_product: Optional[CurrentProductContext] = None


class ChatResponse(BaseModel):
    reply: str
    suggested_actions: Optional[List[str]] = Field(default_factory=list)
    dermatologist_search: Optional[DermatologistSearchAction] = None


def _extract_sanitized_user_context(user_id: str) -> Dict[str, Any]:
    """
    Extract relevant, privacy-safe user context for profile-aware chat.
    Does NOT include: raw UUIDs, tokens, passwords, GPS coordinates, or raw YOLO bounding boxes.
    """
    user_data = personalization_service.load_user_data(user_id)
    profile = user_data.get("profile") or {}
    skin_analysis = user_data.get("skin_analysis") or {}
    environment = user_data.get("environment") or {}
    current_products_raw = user_data.get("current_products") or []

    # 1. Clean profile context
    clean_profile = {
        "skin_type": profile.get("skin_type") or "Not specified",
        "skin_concerns": profile.get("skin_concerns") or [],
        "skin_sensitivity": profile.get("skin_sensitivity") or "Not specified",
        "skincare_goals": profile.get("skincare_goals") or [],
        "allergies": profile.get("allergies") or [],
        "age_range": profile.get("age_range") or "Not specified",
    }
    
    # Lifestyle factors (when available)
    lifestyle = {}
    for k in ["sleep", "water_intake", "stress_level", "diet"]:
        val = profile.get(k)
        if val:
            lifestyle[k] = val
    if lifestyle:
        clean_profile["lifestyle"] = lifestyle

    # 2. Clean environment context
    clean_environment = {}
    if environment:
        for k in ["city", "temperature", "humidity", "weather"]:
            val = environment.get(k)
            if val is not None:
                clean_environment[k] = val

    # 3. Clean skin analysis context (lesion summary and severity only)
    clean_analysis = None
    if skin_analysis:
        lesions = {}
        for l_key in ["blackheads", "whiteheads", "papules", "pustules", "nodules", "dark_spots", "total_lesions"]:
            count = skin_analysis.get(l_key)
            if count is not None:
                lesions[l_key] = count
                
        clean_analysis = {
            "severity": skin_analysis.get("severity") or "Unknown",
            "severity_score": skin_analysis.get("severity_score"),
            "lesion_summary": lesions,
            "recorded_date": skin_analysis.get("created_at", "")[:10] if skin_analysis.get("created_at") else None
        }

    # 4. Clean product history context
    clean_product_history = []
    for prod in current_products_raw:
        clean_product_history.append({
            "product_name": prod.get("product_name"),
            "brand": prod.get("brand"),
            "product_type": prod.get("product_type") or prod.get("category"),
            "reaction": prod.get("reaction") or "none",
            "notes": prod.get("notes") or ""
        })

    # 5. Routine and evaluated products context from PersonalizationService
    clean_routine = {"am": [], "pm": [], "missing_steps": []}
    clean_evaluated_products = []
    clean_recommendations = []
    cross_product_interactions = []

    try:
        pers_result = personalization_service.analyze_user_personalization(user_id)
        if pers_result.get("success"):
            # AM routine slots
            am_slots = pers_result.get("am_routine") or {}
            if isinstance(am_slots, dict) and "slots" in am_slots:
                am_slots = am_slots["slots"]

            if isinstance(am_slots, dict):
                for slot_key in ["cleanser", "treatment", "moisturizer", "sunscreen"]:
                    prod = am_slots.get(slot_key)
                    if prod:
                        eval_data = prod.get("evaluation") or {}
                        clean_routine["am"].append({
                            "step": slot_key.capitalize(),
                            "product": prod.get("product_name"),
                            "brand": prod.get("brand"),
                            "decision": eval_data.get("decision", "KEEP"),
                            "reasons": eval_data.get("reasons", []),
                            "mitigations": eval_data.get("mitigations", []),
                            "status": "slotted"
                        })
                    else:
                        clean_routine["am"].append({
                            "step": slot_key.capitalize(),
                            "product": None,
                            "brand": None,
                            "decision": None,
                            "status": "missing"
                        })
            elif isinstance(am_slots, list):
                for s in am_slots:
                    prod = s.get("product") if isinstance(s, dict) else None
                    eval_data = prod.get("evaluation") or {} if prod else {}
                    clean_routine["am"].append({
                        "step": s.get("label") or s.get("step") if isinstance(s, dict) else str(s),
                        "product": prod.get("product_name") if prod else None,
                        "brand": prod.get("brand") if prod else None,
                        "decision": eval_data.get("decision") if prod else None,
                        "reasons": eval_data.get("reasons", []) if prod else [],
                        "mitigations": eval_data.get("mitigations", []) if prod else [],
                        "status": "slotted" if prod else "missing"
                    })

            # PM routine slots
            pm_slots = pers_result.get("pm_routine") or {}
            if isinstance(pm_slots, dict) and "slots" in pm_slots:
                pm_slots = pm_slots["slots"]

            if isinstance(pm_slots, dict):
                for slot_key in ["cleanser", "treatment", "moisturizer"]:
                    prod = pm_slots.get(slot_key)
                    if prod:
                        eval_data = prod.get("evaluation") or {}
                        clean_routine["pm"].append({
                            "step": slot_key.capitalize(),
                            "product": prod.get("product_name"),
                            "brand": prod.get("brand"),
                            "decision": eval_data.get("decision", "KEEP"),
                            "reasons": eval_data.get("reasons", []),
                            "mitigations": eval_data.get("mitigations", []),
                            "status": "slotted"
                        })
                    else:
                        clean_routine["pm"].append({
                            "step": slot_key.capitalize(),
                            "product": None,
                            "brand": None,
                            "decision": None,
                            "status": "missing"
                        })
            elif isinstance(pm_slots, list):
                for s in pm_slots:
                    prod = s.get("product") if isinstance(s, dict) else None
                    eval_data = prod.get("evaluation") or {} if prod else {}
                    clean_routine["pm"].append({
                        "step": s.get("label") or s.get("step") if isinstance(s, dict) else str(s),
                        "product": prod.get("product_name") if prod else None,
                        "brand": prod.get("brand") if prod else None,
                        "decision": eval_data.get("decision") if prod else None,
                        "reasons": eval_data.get("reasons", []) if prod else [],
                        "mitigations": eval_data.get("mitigations", []) if prod else [],
                        "status": "slotted" if prod else "missing"
                    })

            # Evaluated products in routine (SOURCE OF TRUTH for KEEP/CAUTION/REJECT)
            for ep in pers_result.get("evaluated_products", []):
                evaluation = ep.get("evaluation") or {}
                clean_evaluated_products.append({
                    "product_name": ep.get("product_name"),
                    "brand": ep.get("brand"),
                    "category": ep.get("category") or ep.get("product_type"),
                    "decision": evaluation.get("decision", "KEEP"),
                    "confidence": evaluation.get("confidence", "medium"),
                    "reason_codes": evaluation.get("reason_codes", []),
                    "reasons": evaluation.get("reasons", []),
                    "mitigations": evaluation.get("mitigations", [])
                })

            # Recommendations
            recs_by_cat = pers_result.get("recommendations", {})
            for cat, rec_list in recs_by_cat.items():
                for rec in rec_list:
                    rec_eval = rec.get("evaluation") or {}
                    clean_recommendations.append({
                        "category": cat,
                        "brand": rec.get("brand"),
                        "product_name": rec.get("product_name"),
                        "decision": rec_eval.get("decision", "KEEP"),
                        "reasons": rec_eval.get("reasons", [])[:2]
                    })

            # Interactions
            cross_product_interactions = pers_result.get("cross_product_interactions", [])
    except Exception as e:
        print(f"[CHAT] Error computing personalization context: {e}")

    saved_morning_routine = profile.get("morning_routine") or []
    saved_night_routine = profile.get("night_routine") or []
    user_city = profile.get("city") or environment.get("city") or ""

    # Build clear mapping for each step in user's saved profile routine
    detailed_saved_am = []
    for step_label in saved_morning_routine:
        step_str = str(step_label).strip()
        step_lower = step_str.lower()
        matched_prod = None

        # 1. First check slotted products in clean_routine["am"]
        for slot in clean_routine.get("am", []):
            slot_name = slot.get("step", "").lower()
            if slot_name in step_lower or step_lower in slot_name:
                if slot.get("product"):
                    matched_prod = {
                        "product_name": slot.get("product"),
                        "brand": slot.get("brand"),
                        "decision": slot.get("decision"),
                        "reasons": slot.get("reasons", []),
                        "mitigations": slot.get("mitigations", [])
                    }
                    break

        # 2. Check current_products history
        if not matched_prod:
            for cp in clean_product_history:
                pt = (cp.get("product_type") or "").lower()
                pn = (cp.get("product_name") or "").lower()
                if step_lower in pt or pt in step_lower or step_lower in pn:
                    ep_match = next((ep for ep in clean_evaluated_products if ep.get("product_name") == cp.get("product_name")), None)
                    matched_prod = {
                        "product_name": cp.get("product_name"),
                        "brand": cp.get("brand"),
                        "decision": ep_match.get("decision") if ep_match else None,
                        "reasons": ep_match.get("reasons", []) if ep_match else [],
                        "mitigations": ep_match.get("mitigations", []) if ep_match else []
                    }
                    break

        detailed_saved_am.append({
            "step": step_str,
            "product": matched_prod.get("product_name") if matched_prod else None,
            "brand": matched_prod.get("brand") if matched_prod else None,
            "decision": matched_prod.get("decision") if matched_prod else None,
            "reasons": matched_prod.get("reasons", []) if matched_prod else [],
            "mitigations": matched_prod.get("mitigations", []) if matched_prod else [],
            "has_product": bool(matched_prod and matched_prod.get("product_name"))
        })

    detailed_saved_pm = []
    for step_label in saved_night_routine:
        step_str = str(step_label).strip()
        step_lower = step_str.lower()
        if step_lower in ["nothing", "none"]:
            detailed_saved_pm.append({
                "step": step_str,
                "note": "User explicitly set their night routine to Nothing in their profile.",
                "has_product": False
            })
            continue

        matched_prod = None
        for slot in clean_routine.get("pm", []):
            slot_name = slot.get("step", "").lower()
            if slot_name in step_lower or step_lower in slot_name:
                if slot.get("product"):
                    matched_prod = {
                        "product_name": slot.get("product"),
                        "brand": slot.get("brand"),
                        "decision": slot.get("decision"),
                        "reasons": slot.get("reasons", []),
                        "mitigations": slot.get("mitigations", [])
                    }
                    break

        if not matched_prod:
            for cp in clean_product_history:
                pt = (cp.get("product_type") or "").lower()
                pn = (cp.get("product_name") or "").lower()
                if step_lower in pt or pt in step_lower or step_lower in pn:
                    ep_match = next((ep for ep in clean_evaluated_products if ep.get("product_name") == cp.get("product_name")), None)
                    matched_prod = {
                        "product_name": cp.get("product_name"),
                        "brand": cp.get("brand"),
                        "decision": ep_match.get("decision") if ep_match else None,
                        "reasons": ep_match.get("reasons", []) if ep_match else [],
                        "mitigations": ep_match.get("mitigations", []) if ep_match else []
                    }
                    break

        detailed_saved_pm.append({
            "step": step_str,
            "product": matched_prod.get("product_name") if matched_prod else None,
            "brand": matched_prod.get("brand") if matched_prod else None,
            "decision": matched_prod.get("decision") if matched_prod else None,
            "reasons": matched_prod.get("reasons", []) if matched_prod else [],
            "mitigations": matched_prod.get("mitigations", []) if matched_prod else [],
            "has_product": bool(matched_prod and matched_prod.get("product_name"))
        })

    return {
        "profile": clean_profile,
        "saved_profile_routine": {
            "morning_routine": saved_morning_routine,
            "detailed_saved_morning_steps": detailed_saved_am,
            "night_routine": saved_night_routine,
            "detailed_saved_night_steps": detailed_saved_pm
        },
        "user_city": user_city,
        "environment": clean_environment,
        "latest_skin_analysis": clean_analysis,
        "product_history": clean_product_history,
        "evaluated_skinwise_routine": clean_routine,
        "evaluated_routine_products": clean_evaluated_products,
        "recommendations": clean_recommendations,
        "cross_product_interactions": cross_product_interactions
    }


def _build_system_prompt(
    user_context: Dict[str, Any],
    current_product: Optional[CurrentProductContext] = None
) -> str:
    """Build grounded system prompt with strict safety instructions, product context, and clean typography."""
    context_copy = dict(user_context)
    if current_product and current_product.product_name:
        context_copy["currently_analyzed_product_on_page"] = current_product.model_dump()

    context_json = json.dumps(context_copy, indent=2)

    return f"""You are the SkinWise AI Assistant.

Your role is to help the authenticated SkinWise user understand their skin profile, current SkinWise results, skincare routine, products and ingredients.

CORE CAPABILITIES:
• Explain skincare concepts and ingredients
• Explain the user's saved profile routine and evaluated SkinWise routine
• Explain why a product is marked KEEP, CAUTION or REJECT
• Explain why a product was recommended
• Explain the user's latest facial skin analysis in simple, reassuring language

1. ACTIVE ANALYZED PRODUCT RESOLUTION (HIGHEST PRIORITY):
• When 'currently_analyzed_product_on_page' is present in context:
  The user is actively viewing this product on the Product Analysis page right now:
  Product: {current_product.product_name if current_product else 'N/A'}
  Brand: {current_product.brand if current_product else 'N/A'}
  Category: {current_product.category if current_product else 'Treatment'}
  SkinWise Decision: {current_product.decision if current_product else 'N/A'}
  Match Label: {current_product.match_label if current_product else 'N/A'}
  Reasons: {json.dumps(current_product.reasons if current_product else [])}
  Mitigations: {json.dumps(current_product.mitigations if current_product else [])}

  MANDATORY REFERENT RULES:
  1. Any user query that refers to:
     - "this product", "this", "the product", "it"
     - "why was this product marked REJECT for me?"
     - "why was this product rejected?"
     - "why was it rejected?"
     - "why was this product cautioned?"
     - "which parts of my profile contributed to this decision?"
     - "would you change this REJECT decision to KEEP?"
     - "explain the main ingredient concerns in this product"
     - "why did SkinWise recommend this product for me?"
     - "what do you think of this product?"
     MUST BE RESOLVED DIRECTLY TO THIS ACTIVE PRODUCT: '{current_product.product_name if current_product else ''}' by '{current_product.brand if current_product else ''}'!
  2. NEVER claim "no rejected product exists" or say "your routine only has KEEP/CAUTION products" when 'currently_analyzed_product_on_page' is present! The user is asking about this analyzed product.
  3. Authoritative Decision Preservation:
     - Preserve the exact decision: {current_product.decision if current_product else 'N/A'} ({current_product.match_label if current_product else 'N/A'}).
     - Connect it directly to the user's specific skin profile (e.g. skin sensitivity, skin type, barrier goals, active lesions, allergies).
     - NEVER alter, invert, or recalculate this decision.
     - If the user asks "Would you change this REJECT decision to KEEP?", answer firmly NO: explain that SkinWise maintains this safety decision because the formulation poses a severe chemical irritation or barrier damage risk for their skin profile, and safety rules are never overridden.
     - If the user asks "Why did SkinWise recommend this product for me?" when the active product is REJECT or CAUTION:
       Immediately clarify: "Actually, SkinWise did not recommend this product for you — it was evaluated as {current_product.decision if current_product else 'REJECT'} ({current_product.match_label if current_product else 'Not Recommended'})." Then explain the actual reasons.

• When 'currently_analyzed_product_on_page' is NOT present in context:
  - If the user asks "Why did SkinWise recommend this product for me?" or asks about "this product" without specifying which one, politely ask them to specify which product they are asking about.

2. DISTINGUISH TWO ROUTINE SOURCES:
• You must ALWAYS clearly distinguish between:
  A. "Your saved routine": The steps explicitly saved in the user's profile (e.g. morning_routine: Cleanser, Moisturizer, Sunscreen; or night_routine: Nothing).
  B. "Your SkinWise evaluated routine": The algorithmic routine generated by SkinWise with slotted products, suitability decisions (KEEP/CAUTION/REJECT), and missing steps.
• NEVER merge these two sources silently. Use clear explicit section headers:
  YOUR SAVED MORNING ROUTINE:
  CURRENT SKINWISE EVALUATION:
  and
  YOUR SAVED NIGHT ROUTINE:
  YOUR EVALUATED SKINWISE NIGHT ROUTINE:

3. MORNING ROUTINE EXPLANATIONS:
When the user asks:
- "What is my current morning routine?"
- "Explain my morning routine"
- "What should I do in the morning?"
- "Explain my morning routine and why each step is there"

You must explain EACH saved routine step thoroughly using the data in 'saved_profile_routine.detailed_saved_morning_steps' (or 'evaluated_skinwise_routine.am').

Structure your response with this clear format:

YOUR SAVED MORNING ROUTINE:

1. [Step Name, e.g. Cleanser]
   • Product: [Actual user product name and brand if available, e.g. Minimalist Salicylic Acid + LHA 2% Cleanser, or "No specific product added yet"]
   • Purpose: [What this step does in skincare, e.g. Cleanses away overnight sebum, sweat, and dead skin cells to prepare skin for daytime protection]
   • Why for you: [Connect directly to THIS user's profile: e.g. user's oily skin type, acne concerns, or barrier goals]

2. [Step Name, e.g. Moisturizer]
   • Product: [Actual user product if available, or "No specific product added yet"]
   • Purpose: [Hydration, barrier repair, preventing transepidermal water loss]
   • Why for you: [Connect to user's profile: e.g. strengthens the skin barrier to support acne-healing without clogging pores]

3. [Step Name, e.g. Sunscreen]
   • Product: [Actual user product if available, e.g. Watermelon Cooling Sunscreen SPF 50+]
   • Purpose: [Broad-spectrum UV protection against UVA and UVB damage]
   • Why for you: [Connect to user's profile: e.g. crucial for acne and pigmentation concerns to prevent dark marks (PIH) from darkening under sunlight]

Then, provide a dedicated section:

CURRENT SKINWISE EVALUATION:
• [Product / Step Name] → [KEEP / CAUTION / REJECT]
  - Explain the existing decision and mitigations only when an evaluated product is available (e.g. Cleanser is marked CAUTION because of active exfoliating acids on sensitive skin; recommend using alternate mornings or patch testing).
  - If a step is missing a product in the evaluated routine, note: "[Step Name]: Missing product (SkinWise recommendations are available in your Routine tab to complete this step)."

IMPORTANT: Do NOT invent product names, purposes, or suitability decisions.

4. NIGHT ROUTINE EXPLANATIONS:
When the user asks:
- "What is my current night routine?"
- "Explain my night routine"
- "What should I do at night?"

• First state the SAVED PROFILE routine clearly:
  If the profile is set to "Nothing", explicitly state:
  "Your saved night routine in your profile is currently set to Nothing."
  Do NOT call it "empty" or "unset" when the stored value is "Nothing".
• Next, if an evaluated SkinWise routine exists in 'evaluated_skinwise_routine.pm', state:
  "YOUR EVALUATED SKINWISE NIGHT ROUTINE:"
  and list the slotted products or missing steps (e.g. Cleanser: Salicylic Acid + LHA 2% Cleanser (CAUTION), Treatment: Missing, Moisturizer: Missing).
• Briefly explain why having an evening routine (such as cleansing off daytime pollution/sunscreen and moisturizing) is valuable for their skin goals (e.g. nighttime barrier repair and unclogging pores).

5. PROFILE-AWARE EXPLANATIONS FOR SPECIFIC PRODUCTS / INGREDIENTS:
• When asked "Why is sunscreen important for my skin?", explain the general UV defense AND connect it directly to the user's specific skin profile (e.g. preventing post-inflammatory hyperpigmentation / dark spots from acne, and defending against UV-induced barrier damage).
• When asked "Why is my cleanser marked CAUTION?", locate the cleanser in 'evaluated_routine_products' (or detailed steps), state the decision CAUTION, and explain the exact reasons (e.g. active chemical exfoliants salicylic acid + LHA may cause irritation or dryness on sensitive skin) and mitigations (e.g. patch test, start 2-3 times weekly).

6. FORMATTING RULES (STRICT TYPOGRAPHY - NO RAW MARKDOWN SYNTAX):
• Do NOT use raw Markdown formatting syntax. NEVER use double asterisks (**), single asterisks (*), hashtags (### or ##), backticks (`), or underscores (_).
• The client UI renders rich styled typography. If you include raw asterisks like **bold** or *italic*, it breaks the UI.
• For bulleted lists, use a standard bullet point character '• ' at the beginning of each item on a new line.
• Use plain capitalized section titles like 'YOUR SAVED MORNING ROUTINE:' or 'CURRENT SKINWISE EVALUATION:' without markdown wrappers.
• Write labels like 'Product:' or 'Why for you:' in plain text, never '*Product:*' or '**Product:**'.

7. DISCLAIMER & MEDICAL BOUNDARY RULES:
• Do NOT repeat the phrase "I am an AI assistant, not a doctor" or similar disclaimers on everyday skincare, routine, or ingredient questions. The application interface already displays a persistent educational banner.
• ONLY provide a firm medical boundary when the user asks for prescription medication, medical diagnosis, active skin infection treatment, or severe clinical dermatological issues (e.g., "What prescription medicine should I take for acne?").
• On those specific medical questions, clearly explain that SkinWise provides educational skincare analysis and cannot prescribe medications or diagnose clinical diseases, and recommend consulting a board-certified dermatologist.

8. DERMATOLOGIST SEARCH ACTIONS:
• When the user asks to find a dermatologist or doctor near them, acknowledge their location briefly and inform them that an interactive search button is provided directly below.
• CRITICAL: NEVER output any SVG tags, HTML tags, markdown links, or text like 'svgSearch' in your reply! The client UI automatically renders a real interactive Google Maps search button.

AUTHENTICATED USER CONTEXT (Grounded Truth Source):
{context_json}

RESPONSE FORMAT:
You must respond with valid JSON matching this schema:
{{
  "reply": "Your friendly, concise, evidence-aware response using plain text and bullet points (• ) without any asterisks or raw markdown syntax.",
  "suggested_actions": ["Short follow-up prompt 1", "Short follow-up prompt 2"]
}}
"""


@router.post("/chat", response_model=ChatResponse)
@router.post("/chat/", response_model=ChatResponse)
async def chat_with_assistant(
    request: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Personalized AI skincare chat assistant.
    Grounds explanations in the user's verified profile, routine, analysis, and product evaluations.
    """
    user_message = (request.message or "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="AI Assistant is temporarily unavailable (GEMINI_API_KEY is not configured)."
        )

    try:
        # 1. Retrieve sanitized user context
        user_context = _extract_sanitized_user_context(user_id)
        system_instruction = _build_system_prompt(user_context, request.current_product)

        # 2. Build conversational contents
        formatted_history = []
        for msg in (request.conversation_history or [])[-6:]:
            role = "user" if msg.role == "user" else "model"
            formatted_history.append(f"{role.capitalize()}: {msg.content}")

        full_prompt = ""
        if formatted_history:
            full_prompt += "Previous conversation:\n" + "\n".join(formatted_history) + "\n\n"

        if request.current_product and request.current_product.product_name:
            full_prompt += (
                f"[ACTIVE PRODUCT ON USER'S SCREEN: '{request.current_product.product_name}' "
                f"by '{request.current_product.brand or 'Unknown'}' | "
                f"Decision: {request.current_product.decision} ({request.current_product.match_label or 'N/A'}) | "
                f"Reasons: {', '.join(request.current_product.reasons or [])}]\n\n"
            )

        full_prompt += f"User message: {user_message}"

        candidate_models = [
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.8-flash",
        ]
        raw_text = None
        last_error = None

        # 3a. Strategy A: Call Gemini using official google-genai SDK (if available)
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=15000,
                    retry_options=types.HttpRetryOptions(attempts=2)
                )
            )

            for model_name in candidate_models:
                try:
                    gemini_response = client.models.generate_content(
                        model=model_name,
                        contents=full_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.4,
                            response_mime_type="application/json"
                        )
                    )
                    if gemini_response and gemini_response.text:
                        raw_text = gemini_response.text.strip()
                        break
                except Exception as model_err:
                    print(f"[CHAT] SDK attempt for {model_name} failed: {model_err}")
                    last_error = model_err
        except (ImportError, ModuleNotFoundError) as sdk_err:
            print(f"[CHAT] google.genai SDK not available ({sdk_err}), using direct REST API fallback...")

        # 3b. Strategy B: Direct REST API fallback using requests (always available)
        if not raw_text:
            import requests

            for model_name in candidate_models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                    payload = {
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "systemInstruction": {"parts": [{"text": system_instruction}]},
                        "generationConfig": {
                            "temperature": 0.4,
                            "responseMimeType": "application/json"
                        }
                    }
                    r = requests.post(url, json=payload, timeout=20)
                    if r.status_code == 200:
                        data = r.json()
                        candidates = data.get("candidates") or []
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts and "text" in parts[0]:
                                raw_text = parts[0]["text"].strip()
                                break
                    else:
                        print(f"[CHAT] REST attempt with {model_name} returned HTTP {r.status_code}: {r.text[:120]}")
                except Exception as rest_err:
                    print(f"[CHAT] REST attempt with {model_name} failed: {rest_err}")
                    last_error = rest_err

        if not raw_text:
            raise RuntimeError(f"All candidate models and fallback methods failed. Last error: {last_error}")

        # 4. Parse JSON structured response
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        try:
            parsed = json.loads(raw_text)
            reply = parsed.get("reply") or raw_text
            suggested_actions = parsed.get("suggested_actions") or []
        except Exception:
            reply = raw_text
            suggested_actions = ["Explain my routine", "Why is my product on caution?"]

        # Clean residual markdown symbols and any raw svg/link artifacts from reply for clean typography
        reply = re.sub(r'<svg[\s\S]*?</svg>', '', reply, flags=re.IGNORECASE)
        reply = re.sub(r'svg\s*Search[^s]*svg', '', reply, flags=re.IGNORECASE)
        reply = re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\)', r'\1', reply)
        reply = re.sub(r'<[^>]+>', '', reply)
        reply = re.sub(r'\*\*(.*?)\*\*', r'\1', reply)
        reply = re.sub(r'(?<!\w)\*([^\*]+)\*(?!\w)', r'\1', reply)
        reply = re.sub(r'#{1,6}\s*', '', reply)

        # 5. Check if user is asking to find/locate a dermatologist
        dermatologist_search_action = None
        derm_pattern = r'\b(dermatologist|dermatologists|skin\s+doctor|derm)\b'
        loc_pattern = r'\b(find|search|near|locate|recommend|consult|clinic|specialist|doctor|address|map|nearby|book|see|visit)\b'
        if re.search(derm_pattern, user_message, re.IGNORECASE) and re.search(loc_pattern, user_message, re.IGNORECASE):
            import urllib.parse
            user_city = (user_context.get("user_city") or "").strip()
            search_query = f"dermatologist near {user_city}" if user_city else "dermatologist near me"
            encoded_query = urllib.parse.quote_plus(search_query)
            maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded_query}"
            dermatologist_search_action = DermatologistSearchAction(
                type="maps",
                label=f"Search Dermatologists near {user_city}" if user_city else "Search Dermatologists Near Me",
                query=search_query,
                url=maps_url,
                maps_url=maps_url
            )

        return ChatResponse(
            reply=reply,
            suggested_actions=suggested_actions[:3],
            dermatologist_search=dermatologist_search_action
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[CHAT] Unexpected error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate assistant response. Please try again shortly."
        )
