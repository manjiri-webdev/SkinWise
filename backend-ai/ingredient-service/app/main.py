from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from app.products.service import find_product, get_product_ingredients
from app.ingredients.service import find_ingredient
from app.discovery.service import discover_products

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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

@app.get("/")
def root():
    return {
        "status": "online",
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

