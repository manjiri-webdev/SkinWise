from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

from app.products.service import find_product, get_product_ingredients
from app.ingredients.service import find_ingredient
from app.discovery.service import discover_products
from app.discovery.detailed_extraction import extract_product_from_url
from app.research_gemini.service import GeminiResearchService
from app.research_gemini.parser import parse_ingredient_list
from app.research_gemini.models import IngredientResearchRequest as GeminiResearchRequest, IngredientResearchResponse as GeminiResearchResponse
from app.product_analysis.service import ProductAnalysisService
from google import genai
from google.genai import types

app = FastAPI()

cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url.strip() not in cors_origins:
    cors_origins.append(frontend_url.strip())
cors_origins_env = os.getenv("CORS_ORIGINS")
if cors_origins_env:
    for origin in cors_origins_env.split(","):
        origin_clean = origin.strip()
        if origin_clean and origin_clean not in cors_origins:
            cors_origins.append(origin_clean)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductDiscoverRequest(BaseModel):
    product_name: str
    brand: str  # Required for better accuracy

class ProductOption(BaseModel):
    brand: str
    product_name: str
    source_name: str
    source_url: str
    image_url: Optional[str] = None
    match_reason: str

class ProductDiscoverResponse(BaseModel):
    success: bool
    query: dict
    count: int
    options: list[ProductOption]

class ProductExtractionRequest(BaseModel):
    source_url: str

class ProductAnalysisRequest(BaseModel):
    product_name: str
    brand: Optional[str] = ""
    source_url: Optional[str] = None
    category: Optional[str] = None

class GeminiDiscoveryRequest(BaseModel):
    prompt: str
    category: str

class GeminiDiscoveryResponse(BaseModel):
    success: bool
    products: list

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "SkinWise Product & Ingredient Service"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "SkinWise Product & Ingredient Service"
    }

@app.get("/product/search")
def search_product(
    product_name: str,
    brand: str = None
):
    product = find_product(brand, product_name)

    if not product:
        if brand and product_name:
            raise HTTPException(
                status_code=404,
                detail=f"Product '{product_name}' from brand '{brand}' was not found in the dataset."
            )
        elif product_name:
            raise HTTPException(
                status_code=404,
                detail=f"Product '{product_name}' was not found in the dataset."
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="No products found in the dataset."
            )

    return {
        "found": True,
        "count": len(product),
        "product": product
    }

@app.get("/ingredients/search")
def search_ingredient(ingredient: str):

    result = find_ingredient(ingredient)

    if not result["found"]:
        raise HTTPException(
            status_code=404,
            detail=f"Ingredient '{ingredient}' was not found in the dataset."
        )

    return {
        "found": True,
        "matched_by": result["matched_by"],
        "matched_name": result["matched_name"],
        "ingredient": result["data"]
    }


@app.get("/product/ingredients")
def search_product_ingredients(
    product_name: str,
    brand: str = None
):
    result = get_product_ingredients(brand, product_name)

    if not result:
        if brand and product_name:
            raise HTTPException(
                status_code=404,
                detail=f"Product '{product_name}' from brand '{brand}' was not found in the dataset."
            )
        elif product_name:
            raise HTTPException(
                status_code=404,
                detail=f"Product '{product_name}' was not found in the dataset."
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="No products found in the dataset."
            )

    return {
        "found": True,
        "product": result["product"],
        "total_ingredients": result["total_ingredients"],
        "found_ingredients": result["found_ingredients"],
        "missing_ingredients": result["missing_ingredients"],
        "ingredients": result["ingredients"]
    }

@app.post("/product/discover")
def discover_product_endpoint(request: ProductDiscoverRequest):
    """
    Discover candidate products based on product name and optional brand.
    Returns multiple possible matches for the user to choose from.
    """
    result = discover_products(request.product_name, request.brand)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Discovery failed")
        )
    
    return result

@app.post("/product/extract")
def extract_product_endpoint(request: ProductExtractionRequest):
    """
    Extract detailed product information from a source URL.
    Returns brand, product_name, category, main_purpose, full_ingredient_list, and image_url.
    """
    result = extract_product_from_url(request.source_url)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Extraction failed")
        )
    
    return result

@app.post("/ingredients/research-gemini")
def research_ingredients_gemini_endpoint(request: GeminiResearchRequest):
    """
    Research ingredient information using Gemini Flash (3.5 Flash Lite) with evidence lookup.
    
    Accepts a list of ingredient names and returns detailed research for each including:
    - ingredient_type, function, benefits
    - suitable_skin_types, skin_concerns
    - irritation_risk, irritation_notes, allergy_sensitization, who_should_avoid
    - pregnancy_safety, pregnancy_notes
    - interactions_with_other_ingredients
    - evidence_source, canonical_name, aliases
    
    This endpoint does NOT connect to Supabase or save data.
    It uses Gemini Flash with structured JSON output and evidence lookup from reliable sources.
    Ingredients are processed sequentially, one at a time.
    Note: Using Gemini 3.5 Flash Lite as API-recommended alternative to 2.5 Flash for new users.
    """
    try:
        # Initialize Gemini research service
        gemini_service = GeminiResearchService()
        
        # Parse the ingredient list if it's a single string
        if len(request.ingredient_list) == 1 and ',' in request.ingredient_list[0]:
            # Assume it's a comma-separated ingredient list
            parsed_ingredients = parse_ingredient_list(request.ingredient_list[0])
        else:
            parsed_ingredients = request.ingredient_list
        
        # Research each ingredient sequentially
        result = gemini_service.research_ingredient_list(parsed_ingredients)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail="Ingredient research failed"
            )
        
        # Return structured response with proper model conversion
        return {
            "success": result["success"],
            "total_ingredients": result["total_ingredients"],
            "successfully_researched": result["successfully_researched"],
            "failed_research": result["failed_research"],
            "ingredients": [ingredient.model_dump() if hasattr(ingredient, 'model_dump') else ingredient for ingredient in result["ingredients"]],
            "errors": result["errors"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingredient research error: {str(e)}"
        )

@app.post("/product/analyze")
def analyze_product_endpoint(request: ProductAnalysisRequest):
    """
    Product Analysis: Analyze product with intelligent database reuse.
    
    This endpoint implements the complete flow:
    1. Check Supabase for existing product (brand + product_name match)
    2. If found, use existing product data
    3. If not found, run discovery + extraction and insert new product
    4. Process ingredients sequentially:
       - Check Supabase for each ingredient
       - If found, use existing ingredient data
       - If not found, run Gemini research and insert new ingredient
    5. Return complete analysis with database reuse statistics
    
    This ensures:
    - No duplicate product/ingredient rows
    - Existing Supabase data always wins
    - New data is inserted only when the record is missing
    - Ingredient processing is sequential
    - Product Discovery, Product Extraction, and Gemini Step 3A behavior are preserved
    - Graceful fallback when extraction fails (returns partial data)
    """
    try:
        # Initialize Product Analysis service
        product_analysis_service = ProductAnalysisService()
        
        # Analyze product with database reuse
        result = product_analysis_service.analyze_product_with_reuse(
            request.product_name,
            request.brand,
            request.source_url,
            request.category
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Product analysis failed")
            )
        
        # Add warning if we used fallback data
        if result.get("warning"):
            print(f"[API] Warning in product analysis: {result.get('warning')}")
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Product analysis error: {str(e)}"
        )

@app.post("/research/discover-products")
def discover_products_gemini_endpoint(request: GeminiDiscoveryRequest):
    """
    Use Gemini to discover real candidate products for recommendation engine.
    
    Gemini ONLY returns: brand, product_name, source_url, category
    NO safety decisions, ingredient lists, or recommendations.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY not configured"
            )
        
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=request.prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "products": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "brand": {"type": "string"},
                                    "product_name": {"type": "string"},
                                    "source_url": {"type": "string"},
                                    "category": {"type": "string"}
                                },
                                "required": ["brand", "product_name", "source_url", "category"]
                            }
                        }
                    },
                    "required": ["products"]
                }
            )
        )
        
        if not response.text:
            raise HTTPException(
                status_code=500,
                detail="Gemini returned no response"
            )
        
        import json
        data = json.loads(response.text)
        
        # Validate structure
        if not isinstance(data, dict) or "products" not in data:
            raise HTTPException(
                status_code=500,
                detail="Invalid Gemini response structure"
            )
        
        products = data.get("products", [])
        if not isinstance(products, list):
            raise HTTPException(
                status_code=500,
                detail="Products must be an array"
            )
        
        # Validate each product has required fields
        for p in products:
            if not all(k in p for k in ["brand", "product_name", "source_url", "category"]):
                raise HTTPException(
                    status_code=500,
                    detail="Each product must have brand, product_name, source_url, category"
                )
        
        return {
            "success": True,
            "products": products
        }
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse Gemini response: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini discovery error: {str(e)}"
        )

