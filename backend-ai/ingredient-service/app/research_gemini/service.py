import os
import json
from typing import Dict, List, Optional

from google import genai
from google.genai import types

from app.research_gemini.models import IngredientResearchResult
from app.research_gemini.evidence_lookup import EvidenceLookupService


class GeminiResearchService:
    """
    Research cosmetic ingredients using source-backed evidence
    and Gemini structured output.
    """

    ALLOWED_INGREDIENT_TYPES = [
        "active",
        "emollient",
        "humectant",
        "surfactant",
        "preservative",
        "fragrance",
        "solvent",
        "thickener",
        "antioxidant",
        "sunscreen",
        "colorant",
        "buffering_agent",
        "chelating_agent",
        "other",
    ]

    ALLOWED_SKIN_TYPES = [
        "oily",
        "dry",
        "combination",
        "sensitive",
        "normal",
        "acne-prone",
    ]

    ALLOWED_IRRITATION_RISK = [
        "low",
        "moderate",
        "high",
        "unknown",
    ]

    ALLOWED_PREGNANCY_SAFETY = [
        "safe",
        "caution",
        "avoid",
        "unknown",
    ]

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(api_key=api_key)
        self.evidence_service = EvidenceLookupService()

    # ------------------------------------------------------------------
    # SINGLE INGREDIENT
    # ------------------------------------------------------------------

    def research_ingredient(
        self,
        ingredient: str
    ) -> IngredientResearchResult:

        if not ingredient or not ingredient.strip():
            return self._create_empty_result(
                ingredient,
                "Empty ingredient name"
            )

        # Preserve the original requested ingredient - this must never change
        requested_ingredient = ingredient.strip()

        try:
            evidence = self.evidence_service.lookup_evidence(
                requested_ingredient
            )

            return self._analyze_with_gemini(
                requested_ingredient,
                evidence
            )

        except Exception as exc:
            print(
                f"Ingredient research failed for "
                f"'{requested_ingredient}': {exc}"
            )

            return self._create_empty_result(
                requested_ingredient,
                str(exc)
            )

    # ------------------------------------------------------------------
    # GEMINI
    # ------------------------------------------------------------------

    def _analyze_with_gemini(
        self,
        ingredient: str,
        evidence: Optional[List[Dict]]
    ) -> IngredientResearchResult:

        if evidence:
            evidence_text = self._format_evidence_for_gemini(
                evidence
            )

            prompt = f"""
You are a cosmetic ingredient research and normalization system.

Your task is to convert ONLY the supplied source evidence into the
16-field SkinWise ingredient record.

TARGET_INGREDIENT (application-controlled, must be preserved exactly):
{ingredient}

SOURCE EVIDENCE:
{evidence_text}

CRITICAL IDENTITY RULE:
TARGET_INGREDIENT is application-controlled and must be returned exactly
in the "ingredient" field. Never replace, expand, concatenate, summarize,
or derive the ingredient name from evidence text or article content.

IMPORTANT:
The source evidence is authoritative. Do not use your own outside
knowledge to fill missing information.

==================================================
FIELD RULES
==================================================

1. ingredient
MUST return exactly:
"{ingredient}"

This is application-controlled and must never be changed based on
evidence text, article content, or model interpretation.

2. ingredient_type
Must be exactly one of:
{", ".join(self.ALLOWED_INGREDIENT_TYPES)}

Choose the cosmetic/formulation role supported by the evidence.
Prefer the role most relevant to topical cosmetics.

3. function
State the primary cosmetic/formulation function supported by evidence.
Do not include unrelated pharmaceutical, oral-care, industrial, or
non-cosmetic functions unless the source specifically establishes them
as relevant to cosmetic use.

4. benefits
Include evidence-supported skin benefits only.
Do not copy marketing language unnecessarily.
Do not convert a study population or experimental outcome into a
general claim without appropriate support.

5. suitable_skin_types
Allowed values ONLY:
{", ".join(self.ALLOWED_SKIN_TYPES)}

Rules:
- Include a skin type only when the evidence explicitly supports
  suitability or compatibility with that skin type.
- Do NOT infer a skin type from a benefit.
- Do NOT infer "oily" because an ingredient is used for acne.
- Do NOT infer "dry" merely because an ingredient is hydrating.
- If the evidence explicitly says "suitable for all skin types",
  return all six allowed skin types.
- Otherwise return only explicitly supported types.
- If there is not enough evidence, return null.

6. skin_concerns
Include only concerns explicitly supported by the evidence.
Examples:
acne, dryness, dehydration, hyperpigmentation, wrinkles,
redness, sensitivity, barrier damage, etc.

Do not turn a study population, disease name, or unrelated medical
condition into a general skincare concern unless the evidence supports
that interpretation.

7. irritation_risk
Must be one of:
low, moderate, high, unknown

Use cosmetic/dermatological irritation evidence.
Do NOT convert generic chemical, occupational, ingestion, eye-contact,
or GHS hazard information into cosmetic irritation risk.

8. irritation_notes
Include only cosmetic/dermatological irritation information.

9. allergy_sensitization
Include only evidence related to allergic reaction, contact allergy,
sensitization, allergenicity, or hypersensitivity relevant to topical
cosmetic use.

Do not infer allergy risk from generic toxicity.

10. who_should_avoid
Include only clearly supported groups or situations.
Examples:
- people with known allergy to the ingredient
- people with a specific documented sensitivity
- specific populations where a source explicitly recommends avoidance

Do not invent contraindications.

11. pregnancy_safety
Must be one of:
safe, caution, avoid, unknown

Rules:
- Use safe/caution/avoid ONLY when appropriate pregnancy-specific or
  authoritative safety evidence supports it.
- Do not infer pregnancy safety from "generally safe", "non-toxic",
  natural occurrence, or general cosmetic use.
- Otherwise use unknown.

12. pregnancy_notes
Only evidence-supported pregnancy information.

13. interactions_with_other_ingredients

This field is STRICT.

Include an ingredient ONLY when the evidence explicitly describes:
- incompatibility
- conflict
- destabilization
- documented problematic combination
- clinically relevant combination concern
- a specific interaction in cosmetic/formulation use

DO NOT include an ingredient merely because:
- they were used together in a study
- they were present in the same formulation
- the source says they work well together
- the ingredient appears in a treatment containing the ingredient

If no true interaction is documented, return null.

14. evidence_source
List the actual sources that materially support the returned fields.

15. canonical_name
Use the authoritative identity evidence.
Prefer cosmetic/chemical identity sources.

16. aliases
Use authoritative synonym/identity evidence.
Do not include arbitrary product names, brand names, PMID values,
CAS numbers, or unrelated trade names as aliases unless they are
actually useful chemical/cosmetic aliases.

==================================================
GENERAL EVIDENCE RULES
==================================================

- ONLY use information supported by the supplied evidence.
- Never use external memory or general model knowledge.
- Never guess.
- Never infer missing safety information.
- Never fill a field merely because it "sounds likely".
- null is preferable to unsupported information.
- TARGET_INGREDIENT must be preserved exactly in the ingredient field.
- Keep the output concise and normalized.
- Return ONLY the requested JSON structure.
"""

        else:
            prompt = f"""
Create a SkinWise ingredient record for:

TARGET_INGREDIENT (application-controlled, must be preserved exactly):
{ingredient}

No reliable source evidence was found.

STRICT RULE:
Return TARGET_INGREDIENT exactly in the "ingredient" field and set every
other field to null.

Do not use outside knowledge.
Do not guess.
Do not infer.
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "ingredient": {
                                "type": "string"
                            },

                            "ingredient_type": {
                                "anyOf": [
                                    {
                                        "type": "string",
                                        "enum": self.ALLOWED_INGREDIENT_TYPES
                                    },
                                    {
                                        "type": "null"
                                    }
                                ]
                            },

                            "function": {
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "null"}
                                ]
                            },

                            "benefits": {
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "null"}
                                ]
                            },

                            "suitable_skin_types": {
                                "anyOf": [
                                    {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                            "enum": self.ALLOWED_SKIN_TYPES
                                        }
                                    },
                                    {
                                        "type": "null"
                                    }
                                ]
                            },

                            "skin_concerns": {
                                "anyOf": [
                                    {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        }
                                    },
                                    {
                                        "type": "null"
                                    }
                                ]
                            },

                            "irritation_risk": {
                                "anyOf": [
                                    {
                                        "type": "string",
                                        "enum": self.ALLOWED_IRRITATION_RISK
                                    },
                                    {
                                        "type": "null"
                                    }
                                ]
                            },

                            "irritation_notes": {
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "null"}
                                ]
                            },

                            "allergy_sensitization": {
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "null"}
                                ]
                            },

                            "who_should_avoid": {
                                "anyOf": [
                                    {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        }
                                    },
                                    {
                                        "type": "null"
                                    }
                                ]
                            },

                            "pregnancy_safety": {
                                "anyOf": [
                                    {
                                        "type": "string",
                                        "enum": self.ALLOWED_PREGNANCY_SAFETY
                                    },
                                    {
                                        "type": "null"
                                    }
                                ]
                            },

                            "pregnancy_notes": {
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "null"}
                                ]
                            },

                            "interactions_with_other_ingredients": {
                                "anyOf": [
                                    {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        }
                                    },
                                    {
                                        "type": "null"
                                    }
                                ]
                            },

                            "evidence_source": {
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "null"}
                                ]
                            },

                            "canonical_name": {
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "null"}
                                ]
                            },

                            "aliases": {
                                "anyOf": [
                                    {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        }
                                    },
                                    {
                                        "type": "null"
                                    }
                                ]
                            }
                        }
                    }
                )
            )

            result_data = json.loads(response.text)

            # CRITICAL: Enforce that ingredient field always equals the requested ingredient
            # This prevents evidence/article text from becoming the ingredient name
            result_data["ingredient"] = ingredient

            # Final defensive cleanup.
            result_data = self._normalize_result(result_data)

            return IngredientResearchResult(**result_data)

        except Exception as exc:
            print(
                f"Gemini analysis failed for "
                f"'{ingredient}': {exc}"
            )

            return self._create_empty_result(
                ingredient,
                str(exc)
            )

    # ------------------------------------------------------------------
    # NORMALIZATION
    # ------------------------------------------------------------------

    def _normalize_result(
        self,
        data: Dict
    ) -> Dict:

        # Ensure exact ingredient name.
        if "ingredient" not in data:
            data["ingredient"] = ""

        # Skin type validation.
        skin_types = data.get("suitable_skin_types")

        if isinstance(skin_types, list):
            cleaned = []

            for value in skin_types:
                if not isinstance(value, str):
                    continue

                value = value.strip().lower()

                if value in self.ALLOWED_SKIN_TYPES:
                    if value not in cleaned:
                        cleaned.append(value)

            data["suitable_skin_types"] = (
                cleaned if cleaned else None
            )

        # Normalize empty arrays to null.
        for field in [
            "suitable_skin_types",
            "skin_concerns",
            "who_should_avoid",
            "interactions_with_other_ingredients",
            "aliases",
        ]:
            value = data.get(field)

            if isinstance(value, list):
                cleaned = []

                for item in value:
                    if isinstance(item, str) and item.strip():
                        item = item.strip()

                        if item not in cleaned:
                            cleaned.append(item)

                data[field] = cleaned if cleaned else None

        # Clean empty strings.
        for field in [
            "ingredient_type",
            "function",
            "benefits",
            "irritation_notes",
            "allergy_sensitization",
            "pregnancy_notes",
            "evidence_source",
            "canonical_name",
        ]:
            value = data.get(field)

            if isinstance(value, str):
                value = value.strip()

                data[field] = value if value else None

        return data

    # ------------------------------------------------------------------
    # MULTIPLE INGREDIENTS
    # ------------------------------------------------------------------

    def research_ingredient_list(
        self,
        ingredient_list: List[str]
    ) -> Dict:

        results = []
        errors = []

        successful_count = 0
        failed_count = 0

        # Deliberately sequential.
        for ingredient in ingredient_list:

            try:
                result = self.research_ingredient(
                    ingredient
                )

                results.append(result)

                if self._has_research_success(result):
                    successful_count += 1
                else:
                    failed_count += 1

            except Exception as exc:

                errors.append({
                    "ingredient": ingredient,
                    "error": str(exc)
                })

                failed_count += 1

                results.append(
                    self._create_empty_result(
                        ingredient,
                        str(exc)
                    )
                )

        return {
            "success": failed_count == 0,
            "total_ingredients": len(results),
            "successfully_researched": successful_count,
            "failed_research": failed_count,
            "ingredients": results,
            "errors": errors if errors else None
        }

    # ------------------------------------------------------------------
    # SUCCESS CHECK
    # ------------------------------------------------------------------

    def _has_research_success(
        self,
        result: IngredientResearchResult
    ) -> bool:

        # A successful ingredient research should contain at least
        # the basic cosmetic profile, rather than merely one field.
        core_fields = [
            result.ingredient_type,
            result.function,
            result.benefits,
        ]

        populated = sum(
            1 for value in core_fields
            if value
        )

        return populated >= 1

    # ------------------------------------------------------------------
    # EMPTY RESULT
    # ------------------------------------------------------------------

    def _create_empty_result(
        self,
        ingredient: str,
        error: str
    ) -> IngredientResearchResult:

        return IngredientResearchResult(
            ingredient=ingredient,
            ingredient_type=None,
            function=None,
            benefits=None,
            suitable_skin_types=None,
            skin_concerns=None,
            irritation_risk=None,
            irritation_notes=None,
            allergy_sensitization=None,
            who_should_avoid=None,
            pregnancy_safety=None,
            pregnancy_notes=None,
            interactions_with_other_ingredients=None,
            evidence_source=f"Error: {error}",
            canonical_name=None,
            aliases=None
        )

    # ------------------------------------------------------------------
    # EVIDENCE FORMATTER
    # ------------------------------------------------------------------

    def _format_evidence_for_gemini(
        self,
        evidence: List[Dict]
    ) -> str:

        sections = []

        for item in evidence:

            source_name = item.get(
                "source_name",
                "Unknown source"
            )

            source_type = item.get(
                "source_type",
                "unknown"
            )

            source_url = item.get(
                "source_url",
                ""
            )

            evidence_text = item.get(
                "evidence_text",
                ""
            )

            sections.append(
                f"""
--- SOURCE ---
Name: {source_name}
Type: {source_type}
URL: {source_url}

Evidence:
{evidence_text}
"""
            )

        return "\n".join(sections)