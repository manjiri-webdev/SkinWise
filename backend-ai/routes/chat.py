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
    label: str
    query: str
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
            "product_type": prod.get("product_type"),
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
            # AM routine
            am_steps = pers_result.get("am_routine", {}).get("steps", [])
            for s in am_steps:
                prod = s.get("product")
                clean_routine["am"].append({
                    "step": s.get("label"),
                    "product": prod.get("product_name") if prod else None,
                    "brand": prod.get("brand") if prod else None,
                    "status": "slotted" if prod else "missing"
                })

            # PM routine
            pm_steps = pers_result.get("pm_routine", {}).get("steps", [])
            for s in pm_steps:
                prod = s.get("product")
                clean_routine["pm"].append({
                    "step": s.get("label"),
                    "product": prod.get("product_name") if prod else None,
                    "brand": prod.get("brand") if prod else None,
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

    return {
        "profile": clean_profile,
        "saved_profile_routine": {
            "morning_routine": saved_morning_routine,
            "night_routine": saved_night_routine
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

ROUTINE CONTEXT RULES (GROUND TRUTH):
• When the user asks "What is my morning / AM routine?" or "What is my night / PM routine?":
  - First consult 'saved_profile_routine'.
  - If 'morning_routine' or 'night_routine' has steps (e.g. ["Moisturizer", "Sunscreen"] or ["Nothing"]), clearly state:
    "Your saved morning routine includes: Moisturizer and Sunscreen." (or "In your profile, your night routine is set to Nothing.")
  - If 'evaluated_skinwise_routine' has slotted products or missing steps, explain them as your evaluated SkinWise routine:
    "In your evaluated SkinWise routine: [list slotted products and decisions]."
  - NEVER claim the user's routine is empty when 'saved_profile_routine' contains items!

CURRENTLY ANALYZED PRODUCT CONTEXT:
• If 'currently_analyzed_product_on_page' is present in the context:
  When asked "Why was this product rejected/cautioned/recommended for me?" or questions about "this product":
  - Use the authoritative decision (KEEP, CAUTION, or REJECT), match_label, reasons, and mitigations in 'currently_analyzed_product_on_page'.
  - Connect this decision directly to the user's specific skin profile (e.g. skin type, sensitivity level, barrier goals).
  - NEVER alter, recalculate, or invent a different decision.
• If 'currently_analyzed_product_on_page' is not present in context:
  - Check the user's evaluated routine products, or politely invite the user to specify which product they would like to discuss.

FORMATTING RULES (STRICT TYPOGRAPHY - NO RAW MARKDOWN SYNTAX):
• Do NOT use raw Markdown formatting syntax. NEVER use double asterisks (**), single asterisks (*), hashtags (### or ##), backticks (`), or underscores (_).
• The client UI renders rich styled typography. If you include raw asterisks like **bold** or *italic*, it breaks the UI.
• For bulleted lists, use a standard bullet point character '• ' at the beginning of each item on a new line.
• Use plain capitalized section titles like 'SAVED PROFILE ROUTINE:' or 'WHY THIS DECISION:' without markdown wrappers.
• Write labels like 'Why:' or 'Mitigation:' in plain text, never '*Why:*'.

DISCLAIMER & MEDICAL BOUNDARY RULES:
• Do NOT repeat the phrase "I am an AI assistant, not a doctor" or similar disclaimers on everyday skincare, routine, or ingredient questions. The application interface already displays a persistent educational banner.
• ONLY provide a firm medical boundary when the user asks for prescription medication, medical diagnosis, active skin infection treatment, or severe clinical dermatological issues (e.g., "What prescription medicine should I take for acne?").
• On those specific medical questions, clearly explain that SkinWise provides educational skincare analysis and cannot prescribe medications or diagnose clinical diseases, and recommend consulting a board-certified dermatologist.

DERMATOLOGIST SEARCH ACTIONS:
• When the user asks to find a dermatologist or doctor near them, acknowledge their location and inform them that an interactive Google Maps search button is provided directly below.

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

        # Clean residual markdown symbols from reply for clean typography
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
            dermatologist_search_action = DermatologistSearchAction(
                label=f"Search Dermatologists near {user_city}" if user_city else "Search Dermatologists Near Me",
                query=search_query,
                maps_url=f"https://www.google.com/maps/search/?api=1&query={encoded_query}"
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
