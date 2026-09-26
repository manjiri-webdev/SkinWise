from app.database.supabase import supabase
from app.ingredients.service import find_ingredient

def find_product(brand: str = None, product_name: str = None):
    search_term = product_name.strip() if product_name else ""
    
    if brand:
        name_response = (
            supabase
            .table("products")
            .select("*")
            .ilike("brand", brand)
            .ilike("product_name", f"%{search_term}%")
            .execute()
        )

        category_response = (
            supabase
            .table("products")
            .select("*")
            .ilike("brand", brand)
            .ilike("category", f"%{search_term}%")
            .execute()
        )
    else:
        name_response = (
            supabase
            .table("products")
            .select("*")
            .ilike("product_name", f"%{search_term}%")
            .execute()
        )

        category_response = (
            supabase
            .table("products")
            .select("*")
            .ilike("category", f"%{search_term}%")
            .execute()
        )
    
    products = (name_response.data or []) + (category_response.data or [])

    unique_products = {
        product["product_id"]: product
        for product in products
    }

    return list(unique_products.values())

def get_product_ingredients(brand: str = None, product_name: str = None):
    products = find_product(brand, product_name)

    if not products:
        return None

    product = products[0]

    normalized = product.get("normalized_ingredients") or ""

    ingredient_names = [
        item.strip()
        for item in normalized.split("|")
        if item.strip()
    ]

    ingredient_results = []
    missing_ingredients = []

    for name in ingredient_names:
        result = find_ingredient(name)

        if result["found"]:
            ingredient_results.append({
                "searched_name": name,
                "found": True,
                "matched_by": result["matched_by"],
                "matched_name": result["matched_name"],
                "data": result["data"]
            })
        else:
            ingredient_results.append({
                "searched_name": name,
                "found": False,
                "matched_by": None,
                "matched_name": None,
                "data": None
            })
            missing_ingredients.append(name)

    return {
        "product": product,
        "ingredients": ingredient_results,
        "total_ingredients": len(ingredient_names),
        "found_ingredients": len(ingredient_names) - len(missing_ingredients),
        "missing_ingredients": missing_ingredients
    }