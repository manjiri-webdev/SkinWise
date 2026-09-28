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


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    suggested_actions: Optional[List[str]] = Field(default_factory=list)


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

    return {
        "profile": clean_profile,
        "environment": clean_environment,
        "latest_skin_analysis": clean_analysis,
        "product_history": clean_product_history,
        "routine": clean_routine,
        "evaluated_routine_products": clean_evaluated_products,
        "recommendations": clean_recommendations,
        "cross_product_interactions": cross_product_interactions
    }


def _build_system_prompt(user_context: Dict[str, Any]) -> str:
    """Build grounded system prompt with strict safety instructions and user context."""
    context_json = json.dumps(user_context, indent=2)

    return f"""You are the SkinWise AI Assistant.

Your role is to help the authenticated SkinWise user understand their skin profile, current SkinWise results, skincare routine, products and ingredients.

You may:
- explain skincare concepts
- explain ingredients
- explain a user's existing SkinWise routine
- explain why SkinWise recommended a product
- explain why SkinWise marked a product KEEP, CAUTION or REJECT
- answer general skincare education questions
- provide general routine guidance based on the supplied SkinWise context
- explain the user's latest skin-analysis result in understandable language

You must:
- use the supplied user profile when relevant
- personalize explanations using the supplied context
- clearly distinguish SkinWise analysis from general educational information
- never claim to diagnose a medical condition
- never prescribe medication
- never present yourself as a dermatologist
- never invent a SkinWise suitability decision
- never override a KEEP/CAUTION/REJECT decision supplied by the existing engine
- never claim that a product is safe merely because an ingredient is generally considered safe
- recommend professional medical consultation when the question requires diagnosis or treatment

When explaining a product decision:
- use the existing SkinWise decision and reason codes as authoritative
- explain which user-specific factors contributed to the result
- do not recalculate the suitability score independently

AUTHENTICATED USER CONTEXT (Grounded Truth Source):
{context_json}

RESPONSE FORMAT:
You must respond with valid JSON matching this schema:
{{
  "reply": "Your friendly, concise, evidence-aware markdown response here.",
  "suggested_actions": ["Short follow-up question or quick prompt 1", "Short follow-up question or quick prompt 2"]
}}

Guidelines for reply content:
- Use clean Markdown formatting (bullet points, bold highlights) for readability.
- When referencing routine products, always respect the decision (KEEP, CAUTION, or REJECT) in the user context.
- Keep the tone warm, empowering, and scientifically grounded.
- If asked about a product or analysis not present in the user context, clearly state that it is not in their current record rather than inventing facts.
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

    # 1. Retrieve sanitized user context
    user_context = _extract_sanitized_user_context(user_id)
    system_instruction = _build_system_prompt(user_context)

    # 2. Build conversational contents
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=20000,
                retry_options=types.HttpRetryOptions(attempts=2)
            )
        )

        # Build message history for multi-turn context (last 6 turns max)
        formatted_history = []
        for msg in (request.conversation_history or [])[-6:]:
            role = "user" if msg.role == "user" else "model"
            formatted_history.append(f"{role.capitalize()}: {msg.content}")

        full_prompt = ""
        if formatted_history:
            full_prompt += "Previous conversation:\n" + "\n".join(formatted_history) + "\n\n"
        full_prompt += f"User message: {user_message}"

        # 3. Call Gemini using candidate models with fallback
        candidate_models = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]
        gemini_response = None
        last_error = None

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
                    break
            except Exception as model_err:
                print(f"[CHAT] Model {model_name} attempt failed: {model_err}")
                last_error = model_err

        if not gemini_response or not gemini_response.text:
            raise RuntimeError(f"All candidate models failed. Last error: {last_error}")

        # 4. Parse JSON structured response
        raw_text = gemini_response.text.strip()
        
        # Clean potential markdown fences
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
            # Fallback if raw JSON decoding fails
            reply = raw_text
            suggested_actions = ["Explain my routine", "Why is my product on caution?"]

        return ChatResponse(
            reply=reply,
            suggested_actions=suggested_actions[:3]
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[CHAT] Unexpected error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate assistant response. Please try again shortly."
        )
