from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import supabase_config
from auth_utils import get_current_user
import json
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add services directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.personalization_service import PersonalizationService

router = APIRouter()

class AddProductRequest(BaseModel):
    product_id: int
    product_name: str
    product_type: str
    category: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None

class ProfileUpdate(BaseModel):
    age_range: Optional[str] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    weather: Optional[str] = None
    sleep: Optional[str] = None
    water_intake: Optional[str] = None
    stress_level: Optional[str] = None
    diet: Optional[list] = None
    skin_type: Optional[str] = None
    skin_concerns: Optional[list] = None
    skin_sensitivity: Optional[str] = None
    morning_routine: Optional[list] = None
    night_routine: Optional[list] = None
    current_products: Optional[list] = None
    skincare_goals: Optional[list] = None
    questionnaire_completed: Optional[bool] = None
    face_analysis_completed: Optional[bool] = None
    onboarding_completed: Optional[bool] = None

@router.get("/personalization/profile")
async def get_profile(user_id: str = Depends(get_current_user)):
    """
    Get the authenticated user's profile data.
    """
    try:
        response = supabase_config.supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        
        if not response.data:
            return {
                "success": True,
                "data": None,
                "exists": False
            }
        
        # Convert to dict to ensure JSON serialization
        profile_data = dict(response.data[0])
        
        return {
            "success": True,
            "data": profile_data,
            "exists": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")

@router.post("/personalization/profile")
async def update_profile(profile_data: ProfileUpdate, user_id: str = Depends(get_current_user)):
    """
    Update or create the authenticated user's profile data.
    """
    update_data = None
    try:
        # Filter out None values to only update provided fields
        update_data = {k: v for k, v in profile_data.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")
        
        # Convert float values to int for database compatibility
        # (temperature, humidity, latitude, longitude might be sent as floats but stored as ints)
        for key in ['temperature', 'humidity']:
            if key in update_data and update_data[key] is not None:
                if isinstance(update_data[key], float):
                    update_data[key] = int(update_data[key])
        
        # Check if profile exists
        existing = supabase_config.supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        
        if existing.data:
            # Update existing profile
            response = supabase_config.supabase.table("user_profiles").update(update_data).eq("id", user_id).execute()
            
            if not response.data:
                raise HTTPException(status_code=404, detail="Profile not found or update failed")
            
            return {
                "success": True,
                "data": response.data[0]
            }
        else:
            # Create new profile with user_id
            update_data["id"] = user_id
            response = supabase_config.supabase.table("user_profiles").insert(update_data).execute()
            
            if not response.data:
                raise HTTPException(status_code=500, detail="Failed to create profile")
            
            return {
                "success": True,
                "data": response.data[0]
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

@router.post("/personalization/analyze")
async def analyze_profile(user_id: str = Depends(get_current_user)):
    """
    Analyze the user's profile for personalization.
    
    Returns:
    - Product evaluations (KEEP/CAUTION/REJECT) with reasons, confidence, and mitigations
    - AM routine with slots, conflicts, overlaps, and missing steps
    - PM routine with slots, conflicts, overlaps, and missing steps
    - Overall confidence level
    - Combined conflicts and missing steps
    """
    try:
        # Initialize personalization service
        personalization_service = PersonalizationService()
        
        # Run personalization analysis
        result = personalization_service.analyze_user_personalization(user_id)
        
        if not result.get("success"):
            return {
                "success": False,
                "error": "Personalization analysis failed",
                "message": "Could not analyze user profile"
            }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Error analyzing profile"
        }

@router.get("/personalization/latest-analysis")
async def get_latest_analysis(user_id: str = Depends(get_current_user)):
    """
    Get the latest skin analysis for the authenticated user.
    """
    try:
        response = supabase_config.supabase.table("skin_analyses").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
        
        if not response.data:
            return {
                "success": True,
                "data": None,
                "exists": False
            }
        
        analysis_data = dict(response.data[0])
        
        return {
            "success": True,
            "data": analysis_data,
            "exists": True
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": None,
            "exists": False
        }

@router.post("/personalization/add-product")
async def add_product(product_data: AddProductRequest, user_id: str = Depends(get_current_user)):
    """
    Add a product to the authenticated user's current product history.
    
    This endpoint allows users to add products to their routine from the product picker.
    It checks for existing current entries to avoid duplicates and sets status to "current".
    """
    try:
        # Check if product already exists as current for this user
        existing = supabase_config.supabase.table("user_product_history").select("*").eq("user_id", user_id).eq("product_id", product_data.product_id).eq("status", "current").execute()
        
        if existing.data:
            # Product already exists as current, return success without duplicate
            return {
                "success": True,
                "message": "Product already in current routine",
                "data": existing.data[0]
            }
        
        # Create new product history entry
        new_entry = {
            "user_id": user_id,
            "product_id": product_data.product_id,
            "product_name": product_data.product_name,
            "product_type": product_data.product_type,
            "status": "current",
            "reaction": None,
            "notes": None,
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = supabase_config.supabase.table("user_product_history").insert(new_entry).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to add product to history")
        
        return {
            "success": True,
            "message": "Product added to routine successfully",
            "data": response.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding product: {str(e)}")

@router.get("/personalization/products/{category}")
async def get_products_by_category(category: str, user_id: str = Depends(get_current_user)):
    """
    Get products by category for the product picker, evaluated for the current user.
    
    Args:
        category: Product category (cleanser, serum, moisturizer, sunscreen)
    
    Returns:
        List of products with evaluations for the current user
    """
    try:
        # Map category to database search terms
        category_map = {
            "cleanser": ["cleanser", "face wash"],
            "serum": ["serum", "toner", "treatment"],
            "moisturizer": ["moisturizer", "cream", "lotion"],
            "sunscreen": ["sunscreen", "spf"]
        }
        
        search_terms = category_map.get(category, [category])
        
        # Search products by category
        all_products = []
        for term in search_terms:
            response = supabase_config.supabase.table("products").select("*").ilike("category", f"%{term}%").limit(20).execute()
            if response.data:
                all_products.extend(response.data)
        
        # Deduplicate by product_id and filter out test/mock products
        seen_ids = set()
        unique_products = []
        for p in all_products:
            pid = p.get("product_id")
            if pid and pid not in seen_ids:
                # Filter out test/mock products server-side
                product_name = (p.get("product_name") or "").lower()
                brand = (p.get("brand") or "").lower()
                
                # Skip products with test/mock indicators in name or brand
                if any(keyword in product_name for keyword in ["test", "mock", "sample", "dummy", "service role"]):
                    continue
                if any(keyword in brand for keyword in ["test", "mock", "sample", "dummy"]):
                    continue
                
                seen_ids.add(pid)
                unique_products.append(p)
        
        # Evaluate products for current user
        personalization_service = PersonalizationService()
        user_data = personalization_service.load_user_data(user_id)
        
        evaluated_products = []
        for product in unique_products:
            # Get ingredients for evaluation
            ingredients, total_parsed = personalization_service.get_product_ingredients(product["product_id"])
            product["_resolved_ingredients"] = ingredients
            product["_total_parsed_ingredients"] = total_parsed
            
            # Evaluate product suitability
            evaluation = personalization_service.evaluate_product_suitability(
                product,
                user_data
            )
            
            # Only include non-REJECT products
            if evaluation.get("decision") != "REJECT":
                product_copy = product.copy()
                product_copy["evaluation"] = evaluation
                # Remove internal keys
                product_copy.pop("_resolved_ingredients", None)
                product_copy.pop("_total_parsed_ingredients", None)
                evaluated_products.append(product_copy)
        
        # Sort by: KEEP > CAUTION, then higher fit_score, then confidence, then product_id
        def sort_key(p):
            eval_data = p.get("evaluation", {})
            decision_order = {"KEEP": 0, "CAUTION": 1}
            decision_score = decision_order.get(eval_data.get("decision", "CAUTION"), 2)
            fit_score = -(eval_data.get("fit_score", 0))  # Higher fit_score first
            confidence_order = {"high": 0, "medium": 1, "low": 2}
            confidence_score = confidence_order.get(eval_data.get("confidence", "low"), 2)
            product_id = str(p.get("product_id", ""))
            return (decision_score, fit_score, confidence_score, product_id)
        
        evaluated_products.sort(key=sort_key)
        
        return {
            "success": True,
            "category": category,
            "products": evaluated_products
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")
