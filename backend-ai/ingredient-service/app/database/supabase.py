import os

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is not configured.")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_SECRET_KEY is not configured.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def insert_product(product_data: dict) -> dict:
    """
    Insert a new product into the products table.
    
    Args:
        product_data: Dictionary containing product fields matching the table schema
        
    Returns:
        The inserted product record or error information
    """
    try:
        response = supabase.table("products").insert(product_data).execute()
        return {
            "success": True,
            "data": response.data[0] if response.data else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def insert_ingredient(ingredient_data: dict) -> dict:
    """
    Insert a new ingredient into the ingredients table.
    
    Args:
        ingredient_data: Dictionary containing ingredient fields matching the table schema
        
    Returns:
        The inserted ingredient record or error information
    """
    try:
        # Log that we're writing to public.ingredients (no secrets)
        print(f"[INSERT] Writing to public.ingredients table")
        
        # Perform the insert
        response = supabase.table("ingredients").insert(ingredient_data).execute()
        
        # Log inserted row details
        if response.data and len(response.data) > 0:
            inserted_row = response.data[0]
            print(f"[INSERT] Insert successful - Row ID: {inserted_row.get('id')}")
            print(f"[INSERT] Inserted ingredient name: {inserted_row.get('ingredient')}")
            
            # Immediate read-after-insert verification
            ingredient_name = ingredient_data.get("ingredient")
            print(f"[INSERT] Performing immediate SELECT verification for: {ingredient_name}")
            
            try:
                # Select the same ingredient immediately
                select_response = supabase.table("ingredients").select("*").eq("ingredient", ingredient_name).execute()
                
                # Log SELECT results
                print(f"[INSERT] SELECT verification - Row count: {len(select_response.data) if select_response.data else 0}")
                
                if select_response.data and len(select_response.data) > 0:
                    latest_row = select_response.data[0]
                    print(f"[INSERT] SELECT verification - Latest row ID: {latest_row.get('id')}")
                    print(f"[INSERT] SELECT verification - Latest ingredient name: {latest_row.get('ingredient')}")
                    print(f"[INSERT] SELECT verification - Match: {latest_row.get('id') == inserted_row.get('id')}")
                else:
                    print(f"[INSERT] SELECT verification - WARNING: No rows found after insert!")
                    
            except Exception as select_error:
                print(f"[INSERT] SELECT verification failed: {str(select_error)}")
        else:
            print(f"[INSERT] Insert successful but no data returned in response")
        
        return {
            "success": True,
            "data": response.data[0] if response.data else None
        }
    except Exception as e:
        print(f"[INSERT] Insert failed with error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
