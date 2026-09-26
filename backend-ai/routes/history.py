from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel
import supabase_config
from auth_utils import get_current_user
from datetime import datetime, date
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

class ProductHistoryEntry(BaseModel):
    product_name: str
    product_type: str
    brand: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    notes: Optional[str] = None
    reaction: Optional[str] = None

class EnvironmentHistoryEntry(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    weather: Optional[str] = None
    city: Optional[str] = None
    recorded_date: Optional[str] = None

@router.get("/history/products")
async def get_product_history(user_id: str = Depends(get_current_user)):
    """
    Get the authenticated user's product history.
    """
    try:
        response = supabase_config.supabase.table("user_product_history").select("*").eq("user_id", user_id).order("started_at", desc=True).execute()
        
        return {
            "success": True,
            "data": response.data,
            "count": len(response.data)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching product history: {str(e)}")

@router.post("/history/products")
async def add_product_history(entry: ProductHistoryEntry, user_id: str = Depends(get_current_user)):
    """
    Add a new entry to the user's product history (basic version without product resolution).
    For questionnaire products with product resolution, use /history/products/process.
    """
    try:
        record = {
            "user_id": user_id,
            "product_name": entry.product_name,
            "product_type": entry.product_type,
            "started_at": entry.started_at or datetime.utcnow().isoformat(),
            "ended_at": entry.ended_at,
            "notes": entry.notes,
            "reaction": entry.reaction,
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = supabase_config.supabase.table("user_product_history").insert(record).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create product history entry")
        
        return {
            "success": True,
            "data": response.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding product history: {str(e)}")

def process_products_background(products: List[dict], user_id: str):
    """
    Background task to process questionnaire products with product resolution using ingredient-service.
    
    This function:
    - Calls ingredient-service /product/analyze for each product
    - Uses the real product_id from ingredient-service response
    - Saves to user_product_history with proper product_id
    - Runs in background without blocking the main response
    """
    try:
        print(f"[PRODUCT CONNECTOR] ============================================")
        print(f"[PRODUCT CONNECTOR] BACKGROUND Processing products for user {user_id}")
        print(f"[PRODUCT CONNECTOR] Total products to process: {len(products)}")
        print(f"[PRODUCT CONNECTOR] Products received: {products}")
        print(f"[PRODUCT CONNECTOR] ============================================")
        
        # Get ingredient-service URL from environment
        ingredient_service_url = os.getenv("INGREDIENT_SERVICE_URL", "http://localhost:8001")
        
        saved_entries = []
        
        for product in products:
            product_name = product.get("product_name")
            product_type = product.get("product_type")
            brand = product.get("brand", "")
            reaction = product.get("reaction", "")
            notes = product.get("notes", "")
            
            print(f"[PRODUCT CONNECTOR] --- Processing product: {brand} - {product_name} ({product_type}) ---")
            print(f"[PRODUCT CONNECTOR] Reaction value from questionnaire: '{reaction}'")
            print(f"[PRODUCT CONNECTOR] Notes value from questionnaire: '{notes}'")
            
            if not product_name:
                print(f"[PRODUCT CONNECTOR] Skipping: product_name is empty")
                continue
            
            # Step 1: Call ingredient-service /product/analyze
            print(f"[PRODUCT CONNECTOR] Step 1: Calling ingredient-service /product/analyze")
            
            product_id = None
            try:
                analyze_request = {
                    "product_name": product_name,
                    "brand": brand,
                    "category": product_type
                }
                
                print(f"[PRODUCT CONNECTOR] Request payload: {analyze_request}")
                
                analyze_result = None
                try:
                    response = requests.post(
                        f"{ingredient_service_url}/product/analyze",
                        json=analyze_request,
                        timeout=180  # 180 second timeout for discovery/extraction
                    )
                    response.raise_for_status()
                    analyze_result = response.json()
                except (requests.ConnectionError, requests.Timeout) as conn_err:
                    print(f"[PRODUCT CONNECTOR] HTTP call to ingredient-service failed ({conn_err}), attempting direct fallback...")
                    try:
                        import sys
                        from pathlib import Path
                        ing_service_path = Path(__file__).resolve().parent.parent / "ingredient-service"
                        if str(ing_service_path) not in sys.path:
                            sys.path.insert(0, str(ing_service_path))
                        from app.product_analysis.service import ProductAnalysisService
                        analyze_result = ProductAnalysisService().analyze_product_with_reuse(
                            product_name=product_name,
                            brand=brand or None,
                            category=product_type or None
                        )
                    except Exception as fallback_err:
                        print(f"[PRODUCT CONNECTOR] Direct fallback also failed: {fallback_err}")
                
                print(f"[PRODUCT CONNECTOR] Ingredient-service response: {analyze_result}")
                
                if not analyze_result or not analyze_result.get("success"):
                    err_msg = analyze_result.get('error') if analyze_result else 'No response'
                    print(f"[PRODUCT CONNECTOR] Ingredient-service analysis failed: {err_msg}")
                    product_id = None
                else:
                    # Extract product_id from the response
                    product_data = analyze_result.get("product", {})
                    product_id = product_data.get("product_id")
                
                if not product_id:
                    print(f"[PRODUCT CONNECTOR] No product_id in ingredient-service response")
                    # Still save the product history even if resolution failed
                    # This ensures the user's product is not silently dropped
                    print(f"[PRODUCT CONNECTOR] Will save product history with product_id = NULL")
                else:
                    print(f"[PRODUCT CONNECTOR] Got product_id from ingredient-service: {product_id}")
                if analyze_result:
                    print(f"[PRODUCT CONNECTOR] Product source: {analyze_result.get('product_source')}")
                
            except requests.Timeout:
                print(f"[PRODUCT CONNECTOR] Timeout calling ingredient-service for {product_name}")
                product_id = None
            except requests.HTTPError as e:
                print(f"[PRODUCT CONNECTOR] HTTP error calling ingredient-service: {e}")
                product_id = None
            except Exception as e:
                print(f"[PRODUCT CONNECTOR] Error calling ingredient-service: {e}")
                product_id = None
            
            # Step 2: Create or update user_product_history entry
            print(f"[PRODUCT CONNECTOR] Step 2: Saving to user_product_history (product_id={product_id})")
            try:
                # Check if entry already exists for this user and product
                existing_res = supabase_config.supabase.table("user_product_history") \
                    .select("*") \
                    .eq("user_id", user_id) \
                    .eq("status", "current") \
                    .execute()
                
                existing_entry = None
                if existing_res.data:
                    for row in existing_res.data:
                        if (row.get("product_name") or "").strip().lower() == product_name.strip().lower():
                            existing_entry = row
                            break
                
                if existing_entry:
                    entry_id = existing_entry.get("id")
                    update_data = {
                        "product_name": product_name,
                        "product_type": product_type or existing_entry.get("product_type"),
                        "reaction": reaction if reaction else existing_entry.get("reaction"),
                        "notes": notes if notes else existing_entry.get("notes")
                    }
                    if product_id is not None:
                        update_data["product_id"] = product_id
                    
                    print(f"[PRODUCT CONNECTOR] Updating existing history entry {entry_id} with data: {update_data}")
                    response = supabase_config.supabase.table("user_product_history") \
                        .update(update_data) \
                        .eq("id", entry_id) \
                        .eq("user_id", user_id) \
                        .execute()
                    
                    if response.data:
                        saved_entry = response.data[0]
                        saved_entries.append(saved_entry)
                        print(f"[PRODUCT CONNECTOR] Successfully updated history entry {entry_id}, product_id: {saved_entry.get('product_id')}")
                    else:
                        print(f"[PRODUCT CONNECTOR] History UPDATE returned no data")
                else:
                    history_data = {
                        "user_id": user_id,
                        "product_id": product_id,
                        "product_name": product_name,
                        "product_type": product_type,
                        "status": "current",
                        "started_at": None,
                        "ended_at": None,
                        "reaction": reaction if reaction else None,
                        "notes": notes if notes else None
                    }
                    print(f"[PRODUCT CONNECTOR] Inserting new history entry: {history_data}")
                    response = supabase_config.supabase.table("user_product_history").insert(history_data).execute()
                    if response.data:
                        saved_entry = response.data[0]
                        saved_entries.append(saved_entry)
                        print(f"[PRODUCT CONNECTOR] Successfully inserted history entry ID: {saved_entry.get('id')}, product_id: {saved_entry.get('product_id')}")
                    else:
                        print(f"[PRODUCT CONNECTOR] History INSERT returned no data")
                    
            except Exception as e:
                print(f"[PRODUCT CONNECTOR] Failed to save product history for {product_name}: {e}")
                print(f"[PRODUCT CONNECTOR] Exception type: {type(e).__name__}")
            
            print(f"[PRODUCT CONNECTOR] --- Finished processing {product_name} ---")
        
        print(f"[PRODUCT CONNECTOR] ============================================")
        print(f"[PRODUCT CONNECTOR] BACKGROUND Total entries saved: {len(saved_entries)}")
        print(f"[PRODUCT CONNECTOR] ============================================")
        
    except Exception as e:
        print(f"[PRODUCT CONNECTOR] ERROR in background processing: {e}")

@router.post("/history/products/process")
async def process_questionnaire_products_endpoint(products: List[dict], user_id: str = Depends(get_current_user), background_tasks: BackgroundTasks = None):
    """
    Process questionnaire products with product resolution using ingredient-service.
    
    This endpoint:
    - Adds product processing as a background task
    - Returns immediately without waiting for discovery/extraction
    - Background task calls ingredient-service /product/analyze for each product
    - Uses the real product_id from ingredient-service response
    - Saves to user_product_history with proper product_id
    """
    try:
        print(f"[PRODUCT CONNECTOR] ============================================")
        print(f"[PRODUCT CONNECTOR] Scheduling background processing for user {user_id}")
        print(f"[PRODUCT CONNECTOR] Total products to process: {len(products)}")
        print(f"[PRODUCT CONNECTOR] Products received: {products}")
        print(f"[PRODUCT CONNECTOR] ============================================")
        
        # Add background task to process products
        if background_tasks:
            background_tasks.add_task(process_products_background, products, user_id)
        
        return {
            "success": True,
            "message": "Product processing scheduled in background",
            "count": len(products)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[PRODUCT CONNECTOR] ERROR in process_questionnaire_products_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error scheduling product processing: {str(e)}")

@router.put("/history/products/{entry_id}")
async def update_product_history(entry_id: str, entry: ProductHistoryEntry, user_id: str = Depends(get_current_user)):
    """
    Update an existing product history entry.
    """
    try:
        print(f"[PRODUCT HISTORY UPDATE] Updating entry {entry_id} for user {user_id}")
        print(f"[PRODUCT HISTORY UPDATE] Update payload: {entry.model_dump()}")
        
        # Verify the entry belongs to the user
        existing = supabase_config.supabase.table("user_product_history").select("*").eq("id", entry_id).eq("user_id", user_id).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Product history entry not found")
        
        print(f"[PRODUCT HISTORY UPDATE] Existing entry: {existing.data[0]}")
        
        update_data = {
            "product_name": entry.product_name,
            "product_type": entry.product_type,
            "ended_at": entry.ended_at,
            "notes": entry.notes,
            "reaction": entry.reaction
        }
        
        # Remove None values
        # Reaction field should be saved if provided (including "none", "mild", etc.)
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        print(f"[PRODUCT HISTORY UPDATE] Final update data: {update_data}")
        print(f"[PRODUCT HISTORY UPDATE] Reaction field value: '{update_data.get('reaction')}'")
        
        response = supabase_config.supabase.table("user_product_history").update(update_data).eq("id", entry_id).eq("user_id", user_id).execute()
        
        print(f"[PRODUCT HISTORY UPDATE] Update response: {response.data}")
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update product history entry")
        
        print(f"[PRODUCT HISTORY UPDATE] Updated reaction field: '{response.data[0].get('reaction')}'")
        
        return {
            "success": True,
            "data": response.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[PRODUCT HISTORY UPDATE] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating product history: {str(e)}")

@router.delete("/history/products/{entry_id}")
async def delete_product_history(entry_id: str, user_id: str = Depends(get_current_user)):
    """
    Delete a product history entry.
    """
    try:
        # Verify the entry belongs to the user
        existing = supabase_config.supabase.table("user_product_history").select("*").eq("id", entry_id).eq("user_id", user_id).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Product history entry not found")
        
        response = supabase_config.supabase.table("user_product_history").delete().eq("id", entry_id).eq("user_id", user_id).execute()
        
        return {
            "success": True,
            "message": "Product history entry deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting product history: {str(e)}")

@router.get("/history/environment/today")
async def get_today_environment(user_id: str = Depends(get_current_user)):
    """
    Get today's environment history for the authenticated user.
    """
    try:
        today = date.today().isoformat()
        response = supabase_config.supabase.table("user_environment_history").select("*").eq("user_id", user_id).execute()
        
        if not response.data:
            return {
                "success": True,
                "data": None,
                "exists": False
            }
        
        # Get the most recent entry for today
        today_entries = [entry for entry in response.data if entry.get("created_at", "").startswith(today)]
        
        if not today_entries:
            return {
                "success": True,
                "data": None,
                "exists": False
            }
        
        return {
            "success": True,
            "data": today_entries[0],
            "exists": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching today's environment: {str(e)}")

@router.post("/history/environment")
async def add_environment_history(entry: EnvironmentHistoryEntry, user_id: str = Depends(get_current_user)):
    """
    Add or update environment history entry.
    """
    try:
        recorded_date = entry.recorded_date or date.today().isoformat()
        
        # Check if entry already exists for this user and date
        existing = supabase_config.supabase.table("user_environment_history").select("*").eq("user_id", user_id).eq("recorded_date", recorded_date).execute()
        
        record = {
            "temperature": entry.temperature,
            "humidity": entry.humidity,
            "weather": entry.weather,
            "city": entry.city
        }
        
        # Remove None values
        record = {k: v for k, v in record.items() if v is not None}
        
        if existing.data:
            # Update existing entry
            response = supabase_config.supabase.table("user_environment_history").update(record).eq("user_id", user_id).eq("recorded_date", recorded_date).execute()
            
            if not response.data:
                raise HTTPException(status_code=500, detail="Failed to update environment history")
            
            return {
                "success": True,
                "data": response.data[0],
                "action": "updated"
            }
        else:
            # Create new entry
            record["user_id"] = user_id
            record["recorded_date"] = recorded_date
            record["created_at"] = datetime.utcnow().isoformat()
            
            response = supabase_config.supabase.table("user_environment_history").insert(record).execute()
            
            if not response.data:
                raise HTTPException(status_code=500, detail="Failed to create environment history")
            
            return {
                "success": True,
                "data": response.data[0],
                "action": "created"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding environment history: {str(e)}")

@router.get("/history/environment")
async def get_environment_history(user_id: str = Depends(get_current_user)):
    """
    Get environment history for the authenticated user.
    """
    try:
        response = supabase_config.supabase.table("user_environment_history").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        
        return {
            "success": True,
            "data": response.data,
            "count": len(response.data)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching environment history: {str(e)}")
