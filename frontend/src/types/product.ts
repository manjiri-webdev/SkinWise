export type ProductDiscoverRequest = {
  product_name: string;
  brand?: string;
};

export type ProductOption = {
  brand: string;
  product_name: string;
  source_name: string;
  source_url: string;
  image_url?: string | null;
  match_score?: number;
  match_reason?: string;
};

export type ProductDiscoverResponse = {
  success: boolean;
  query: ProductDiscoverRequest;
  count: number;
  options: ProductOption[];
};

export type ProductExtractionRequest = {
  source_url: string;
};

export type ProductExtractionData = {
  brand: string | null;
  product_name: string | null;
  category: string | null;
  main_purpose: string | null;
  full_ingredient_list: string | null;
  image_url: string | null;
};

export type ProductExtractionResponse = {
  success: boolean;
  source_url: string;
  data: ProductExtractionData;
};

export type ProductAnalysisRequest = {
  product_name: string;
  brand?: string;
  source_url?: string;
  category?: string;
};

export type ProductAnalysisResponse = {
  success: boolean;
  error?: string;
  warning?: string;
  product?: {
    product_id?: number | null;
    brand: string | null;
    product_name: string;
    category: string | null;
    main_purpose: string | null;
    full_ingredient_list: string | null;
    normalized_ingredients: string | null;
    image_url: string | null;
    created_at?: string | null;
  };
  product_source?: string;
  total_ingredients?: number;
  ingredients?: any[];
  database_reuse_stats?: {
    products_reused: number;
    products_created: number;
    ingredients_reused: number;
    ingredients_researched: number;
    ingredients_created: number;
    ingredient_insert_failures: number;
  };
};
