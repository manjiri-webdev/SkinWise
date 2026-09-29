import { supabase } from "@/lib/supabase";
import { AI_BACKEND_URL, joinApiUrl } from "@/lib/api";

async function getAuthToken(): Promise<string> {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error("No authenticated session");
  }
  return session.access_token;
}

async function apiCall(endpoint: string, options: RequestInit = {}) {
  const token = await getAuthToken();
  const url = joinApiUrl(AI_BACKEND_URL, endpoint);
  
  let response: Response | null = null;
  const maxAttempts = 3;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      response = await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if ([502, 503, 504].includes(response.status)) {
        console.warn(`apiCall (${endpoint}) received ${response.status}. Retrying in ${attempt * 2}s...`);
        if (attempt < maxAttempts) {
          await new Promise((r) => setTimeout(r, attempt * 2000));
          continue;
        }
      }
      break;
    } catch (err: any) {
      console.warn(`apiCall (${endpoint}) network error attempt ${attempt}:`, err);
      if (attempt < maxAttempts) {
        await new Promise((r) => setTimeout(r, attempt * 2000));
      } else {
        throw new Error("Unable to connect to AI server. It may be waking up—please try again shortly.");
      }
    }
  }

  if (!response || !response.ok) {
    let errorMessage = "API request failed";
    if (response) {
      try {
        const error = await response.json();
        errorMessage = error.detail || error.message || JSON.stringify(error) || `API error ${response.status}`;
      } catch {
        errorMessage = `API error ${response.status}`;
      }
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export interface UserProfile {
  id?: string;
  age_range?: string;
  gender?: string;
  city?: string;
  latitude?: number | null;
  longitude?: number | null;
  temperature?: number | null;
  humidity?: number | null;
  weather?: string | null;
  sleep?: string;
  water_intake?: string;
  stress_level?: string;
  diet?: string[];
  skin_type?: string;
  skin_concerns?: string[];
  skin_sensitivity?: string;
  morning_routine?: string[];
  night_routine?: string[];
  current_products?: Array<{ type: string; productName: string; brand: string; reaction: string; notes: string }>;
  skincare_goals?: string[];
  questionnaire_completed?: boolean;
  face_analysis_completed?: boolean;
  onboarding_completed?: boolean;
}

export interface ProfileResponse {
  success: boolean;
  data: UserProfile | null;
  exists?: boolean;
}

export interface AnalyzeResponse {
  success: boolean;
  user_id: string;
  evaluated_products: Array<{
    id?: string | number;
    product_id?: string | number | null;
    product_name: string;
    product_type: string;
    status: string;
    evaluation: {
      decision: "KEEP" | "CAUTION" | "REJECT";
      confidence: "high" | "medium" | "low";
      reason_codes: string[];
      reasons: string[];
      mitigations: string[];
    };
  }>;
  am_routine: {
    cleanser: any;
    treatment: any;
    moisturizer: any;
    sunscreen: any;
  };
  pm_routine: {
    cleanser: any;
    treatment: any;
    moisturizer: any;
  };
  confidence: "high" | "medium" | "low";
  conflicts: string[];
  overlaps: string[];
  missing_steps: string[];
}

export interface SkinAnalysisData {
  id?: string;
  user_id: string;
  created_at: string;
  model_name: string;
  model_version: string;
  blackheads: number;
  whiteheads: number;
  papules: number;
  pustules: number;
  nodules: number;
  dark_spots: number;
  total_lesions: number;
  severity: string;
  severity_score: number;
  detections_json: any;
}

export interface LatestAnalysisResponse {
  success: boolean;
  data: SkinAnalysisData | null;
  exists: boolean;
  error?: string;
}

export async function getProfile(): Promise<ProfileResponse> {
  try {
    const { data: { user } } = await supabase.auth.getUser();
    if (user?.id) {
      const { data, error } = await supabase
        .from("user_profiles")
        .select("*")
        .eq("id", user.id)
        .maybeSingle();

      if (!error && data) {
        return {
          success: true,
          data: data as UserProfile,
          exists: true,
        };
      } else if (!error && !data) {
        return {
          success: true,
          data: null,
          exists: false,
        };
      }
    }
  } catch (supabaseErr) {
    console.warn("Direct Supabase profile fetch fallback to API:", supabaseErr);
  }
  return apiCall("/personalization/profile");
}

export async function updateProfile(profileData: Partial<UserProfile>): Promise<ProfileResponse> {
  try {
    const { data: { user } } = await supabase.auth.getUser();
    if (user?.id) {
      const { data, error } = await supabase
        .from("user_profiles")
        .update(profileData)
        .eq("id", user.id)
        .select()
        .single();
      if (!error && data) {
        return {
          success: true,
          data: data as UserProfile,
          exists: true,
        };
      }
    }
  } catch (supabaseErr) {
    console.warn("Direct Supabase profile update fallback to API:", supabaseErr);
  }

  return apiCall("/personalization/profile", {
    method: "POST",
    body: JSON.stringify(profileData),
  });
}

export async function analyzeProfile(): Promise<any> {
  return apiCall("/personalization/analyze", {
    method: "POST",
  });
}

export interface EvaluateProductPayload {
  product_id?: number | null;
  product_name?: string | null;
  brand?: string | null;
  category?: string | null;
  normalized_ingredients?: string | null;
  full_ingredient_list?: string | null;
}

export interface IngredientEvaluation {
  ingredient: string;
  status: "Suitable" | "Use with Caution" | "Not recommended";
  reason: string;
  personalized: boolean;
  risk_level?: string;
  matched_concerns?: string[];
  matched_skin_type?: boolean;
  is_contraindicated?: boolean;
  general_precaution?: string | null;
  function?: string | null;
  benefits?: string | null;
  irritation_risk?: string | null;
  who_should_avoid?: string | null;
  allergy_sensitization?: string | null;
}

export interface ProductEvaluationResponse {
  success: boolean;
  product_id?: number | null;
  product_name?: string;
  brand?: string;
  category?: string;
  evaluation: {
    decision: "KEEP" | "CAUTION" | "REJECT";
    confidence: "high" | "medium" | "low";
    reason_codes: string[];
    reasons: string[];
    mitigations: string[];
    fit_score?: number;
    risk_score?: number;
    _total_parsed_ingredients?: number;
    ingredient_evaluations?: IngredientEvaluation[];
  };
}

export async function evaluateProduct(payload: EvaluateProductPayload): Promise<ProductEvaluationResponse> {
  return apiCall("/personalization/evaluate-product", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getLatestAnalysis(): Promise<LatestAnalysisResponse> {
  return apiCall("/personalization/latest-analysis");
}

// History interfaces
export interface ProductHistoryEntry {
  id?: string;
  user_id?: string;
  product_id?: string;
  product_name: string;
  product_type: string;
  brand?: string;
  status?: string;
  started_at?: string;
  ended_at?: string;
  reaction?: string;
  notes?: string;
  created_at?: string;
}

export interface EnvironmentHistoryEntry {
  id?: string;
  user_id?: string;
  temperature?: number;
  humidity?: number;
  weather?: string;
  city?: string;
  recorded_date?: string;
  created_at?: string;
}

export interface ProductHistoryResponse {
  success: boolean;
  data: ProductHistoryEntry[];
  count: number;
}

export interface EnvironmentHistoryResponse {
  success: boolean;
  data: EnvironmentHistoryEntry | null;
  exists?: boolean;
  action?: "created" | "updated";
}

export interface EnvironmentHistoryListResponse {
  success: boolean;
  data: EnvironmentHistoryEntry[];
  count: number;
}

// Product history functions
export async function getProductHistory(): Promise<ProductHistoryResponse> {
  return apiCall("/history/products");
}

export async function addProductHistory(entry: Omit<ProductHistoryEntry, "id" | "user_id" | "created_at">): Promise<{ success: boolean; data: ProductHistoryEntry }> {
  return apiCall("/history/products", {
    method: "POST",
    body: JSON.stringify(entry),
  });
}

export async function processQuestionnaireProducts(products: Array<{ product_name: string; product_type: string; brand: string; reaction: string }>): Promise<{ success: boolean; data: ProductHistoryEntry[]; count: number }> {
  return apiCall("/history/products/process", {
    method: "POST",
    body: JSON.stringify(products),
  });
}

export async function updateProductHistory(entryId: string, entry: Omit<ProductHistoryEntry, "id" | "user_id" | "created_at">): Promise<{ success: boolean; data: ProductHistoryEntry }> {
  return apiCall(`/history/products/${entryId}`, {
    method: "PUT",
    body: JSON.stringify(entry),
  });
}

export async function deleteProductHistory(entryId: string): Promise<{ success: boolean; message: string }> {
  return apiCall(`/history/products/${entryId}`, {
    method: "DELETE",
  });
}

// Environment history functions
export async function getTodayEnvironment(): Promise<EnvironmentHistoryResponse> {
  return apiCall("/history/environment/today");
}

export async function addEnvironmentHistory(entry: Omit<EnvironmentHistoryEntry, "id" | "user_id" | "created_at">): Promise<EnvironmentHistoryResponse> {
  return apiCall("/history/environment", {
    method: "POST",
    body: JSON.stringify(entry),
  });
}

export async function getEnvironmentHistory(startDate?: string, endDate?: string): Promise<EnvironmentHistoryListResponse> {
  const params = new URLSearchParams();
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  const queryString = params.toString();
  return apiCall(`/history/environment${queryString ? `?${queryString}` : ""}`);
}
