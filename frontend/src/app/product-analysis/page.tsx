"use client";

import { useState, useEffect, useMemo, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ChevronRight,
  ChevronDown,
  Package,
  ScanFace,
  Loader2,
  AlertCircle,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Info,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { analyzeProfile } from "@/services/personalization";
import "./product-analysis.css";

type IngredientFilter =
  | "All Ingredients"
  | "Suitable"
  | "Use with Caution"
  | "Not recommended";

interface ResolvedIngredient {
  name: string;
  function?: string | null;
  benefits?: string | null;
  irritation_risk?: string | null;
  who_should_avoid?: string | null;
  allergy_sensitization?: string | null;
  status: "Suitable" | "Use with Caution" | "Not recommended" | "Unrated";
}

interface ProductRecord {
  product_id: number;
  brand?: string | null;
  product_name: string;
  category?: string | null;
  main_purpose?: string | null;
  full_ingredient_list?: string | null;
  normalized_ingredients?: string | null;
  image_url?: string | null;
  created_at?: string | null;
}

function ProductAnalysisContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const productIdParam = searchParams.get("id");
  const productNameParam = searchParams.get("name");
  const brandParam = searchParams.get("brand");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [product, setProduct] = useState<ProductRecord | null>(null);
  const [resolvedIngredients, setResolvedIngredients] = useState<ResolvedIngredient[]>([]);
  const [activeFilter, setActiveFilter] = useState<IngredientFilter>("All Ingredients");
  const [expandedIngredient, setExpandedIngredient] = useState<string | null>(null);

  // User suitability evaluation
  const [evaluation, setEvaluation] = useState<any | null>(null);
  const [isEvaluated, setIsEvaluated] = useState(false);

  useEffect(() => {
    loadProductAndIngredients();
  }, [productIdParam, productNameParam, brandParam]);

  const loadProductAndIngredients = async () => {
    try {
      setLoading(true);
      setError(null);

      let productData: ProductRecord | null = null;

      // 1. Fetch real product from Supabase products table
      if (productIdParam) {
        const { data, error: pErr } = await supabase
          .from("products")
          .select("*")
          .eq("product_id", productIdParam)
          .maybeSingle();

        if (pErr) throw pErr;
        productData = data;
      } else if (productNameParam) {
        let q = supabase.from("products").select("*");
        if (brandParam) {
          q = q.ilike("brand", `%${brandParam}%`);
        }
        q = q.ilike("product_name", `%${productNameParam}%`).limit(1);
        const { data, error: pErr } = await q;
        if (pErr) throw pErr;
        if (data && data.length > 0) {
          productData = data[0];
        }
      }

      if (!productData) {
        setError("Product not found in SkinWise catalog.");
        setLoading(false);
        return;
      }

      setProduct(productData);

      // 2. Parse ingredient names from label
      let ingredientNames: string[] = [];
      if (productData.normalized_ingredients) {
        ingredientNames = productData.normalized_ingredients
          .split("|")
          .map((s) => s.trim())
          .filter(Boolean);
      } else if (productData.full_ingredient_list) {
        ingredientNames = productData.full_ingredient_list
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      }

      // 3. Batch lookup ingredients in Supabase ingredients table
      const resolvedList: ResolvedIngredient[] = [];

      if (ingredientNames.length > 0) {
        // Query batch of ingredients
        const { data: matchedIngredients } = await supabase
          .from("ingredients")
          .select("*")
          .in("ingredient", ingredientNames);

        const matchedMap = new Map<string, any>();
        if (matchedIngredients) {
          matchedIngredients.forEach((ing) => {
            matchedMap.set(ing.ingredient.toLowerCase(), ing);
          });
        }

        // Also prepare secondary ilike lookups for key ingredients not matched exactly
        for (const name of ingredientNames) {
          const lower = name.toLowerCase();
          let ingRecord = matchedMap.get(lower);

          if (!ingRecord) {
            // Find partial match
            for (const [key, val] of matchedMap.entries()) {
              if (lower.includes(key) || key.includes(lower)) {
                ingRecord = val;
                break;
              }
            }
          }

          if (ingRecord) {
            const ir = (ingRecord.irritation_risk || "").toLowerCase();
            const whoAvoid = (ingRecord.who_should_avoid || "").toLowerCase();

            let status: ResolvedIngredient["status"] = "Suitable";

            if (
              ir.includes("high") ||
              ir.includes("very high") ||
              whoAvoid.includes("sensitive") ||
              whoAvoid.includes("allergic")
            ) {
              status = "Not recommended";
            } else if (
              ir.includes("medium") ||
              ir.includes("moderate") ||
              lower.includes("fragrance") ||
              lower.includes("parfum") ||
              lower.includes("alcohol denat")
            ) {
              status = "Use with Caution";
            } else {
              status = "Suitable";
            }

            resolvedList.push({
              name,
              function: ingRecord.function,
              benefits: ingRecord.benefits,
              irritation_risk: ingRecord.irritation_risk,
              who_should_avoid: ingRecord.who_should_avoid,
              allergy_sensitization: ingRecord.allergy_sensitization,
              status,
            });
          } else {
            // Ingredient not in database yet
            resolvedList.push({
              name,
              function: "Skin conditioning agent",
              benefits: "Formulation ingredient",
              status: "Suitable",
            });
          }
        }
      }

      setResolvedIngredients(resolvedList);

      // 4. Check if current user has an evaluation for this product
      try {
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (user) {
          const persResult = await analyzeProfile();
          if (persResult && persResult.evaluated_products) {
            const matching = persResult.evaluated_products.find(
              (p: any) =>
                p.product_id === productData?.product_id ||
                p.product_name?.toLowerCase() === productData?.product_name?.toLowerCase()
            );

            if (matching && matching.evaluation) {
              setEvaluation(matching.evaluation);
              setIsEvaluated(true);
            }
          }
        }
      } catch (persErr) {
        console.warn("Could not check user evaluation:", persErr);
      }
    } catch (err: any) {
      console.error("Failed to load product analysis:", err);
      setError(err.message || "Failed to load product details.");
    } finally {
      setLoading(false);
    }
  };

  const filteredIngredients = useMemo(() => {
    if (activeFilter === "All Ingredients") return resolvedIngredients;
    return resolvedIngredients.filter((ing) => ing.status === activeFilter);
  }, [resolvedIngredients, activeFilter]);

  const formatAnalysisDate = (isoString?: string | null) => {
    if (!isoString) {
      return new Date().toLocaleDateString("en-US", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    }
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString("en-US", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="w-full min-h-screen p-4 sm:p-6 lg:p-10 flex flex-col gap-6 max-w-[1200px] mx-auto">
      {/* Top Back Navigation */}
      <div>
        <button
          type="button"
          onClick={() => router.push("/ingredients")}
          className="inline-flex items-center gap-2 text-sm font-bold text-[#141414] hover:text-[#DE688E] transition cursor-pointer"
        >
          <ArrowLeft size={18} strokeWidth={2.4} />
          <span>Back</span>
        </button>
      </div>

      {loading ? (
        <div className="w-full py-24 flex flex-col items-center justify-center text-center">
          <Loader2 className="animate-spin text-[#DE688E] mb-3" size={36} />
          <p className="text-sm font-semibold text-[#6B6375]">
            Resolving product and ingredient safety data...
          </p>
        </div>
      ) : error || !product ? (
        <div className="w-full p-8 bg-red-50/80 border border-red-200/80 rounded-3xl text-center">
          <AlertCircle className="text-red-500 mx-auto mb-2" size={32} />
          <h2 className="text-base font-bold text-red-700">Product Analysis Unavailable</h2>
          <p className="text-xs text-red-600 mt-1 max-w-md mx-auto">
            {error || "Could not find product data in the SkinWise catalog."}
          </p>
          <button
            onClick={() => router.push("/ingredients")}
            className="mt-4 px-5 py-2 bg-white text-xs font-bold text-red-700 rounded-full border border-red-200 hover:bg-red-50 cursor-pointer"
          >
            Search another product
          </button>
        </div>
      ) : (
        <>
          {/* Card 1: Product Summary Banner */}
          <section className="analysis-card p-4 sm:p-6 lg:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
            <div className="flex items-center gap-4 sm:gap-6">
              {/* Product Image */}
              <div className="w-20 h-24 bg-gray-50 rounded-2xl overflow-hidden shrink-0 flex items-center justify-center p-2 border border-gray-100 shadow-2xs">
                {product.image_url ? (
                  <img
                    src={product.image_url}
                    alt={product.product_name}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <Package size={32} className="text-[#A85175]" />
                )}
              </div>

              <div>
                <span
                  className="text-xs sm:text-sm font-bold text-[#6B6375] block"
                  style={{ fontFamily: "Georgia, serif" }}
                >
                  {product.brand || "SkinWise Catalog"}
                </span>
                <h1 className="text-xl sm:text-2xl font-bold text-[#141414] tracking-tight leading-tight mt-0.5">
                  {product.product_name}
                </h1>
                {product.category && (
                  <p className="text-xs sm:text-sm text-[#7A7382] mt-1 font-medium">
                    {product.category}
                  </p>
                )}
              </div>
            </div>

            <div className="self-start sm:self-center shrink-0">
              <span className="inline-block bg-[#F4EFFB] text-[#6E578F] text-[11px] font-semibold px-3 py-1.5 rounded-full border border-purple-100/80">
                Analyzed · {formatAnalysisDate(product.created_at)}
              </span>
            </div>
          </section>

          {/* Card 2: Overall Compatibility Section */}
          <section className="analysis-card p-4 sm:p-6 lg:p-7 flex flex-col sm:flex-row items-center gap-6">
            {/* Circular Indicator */}
            <div className="relative w-28 h-28 shrink-0 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="transparent"
                  stroke="#EFECE6"
                  strokeWidth="7"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="transparent"
                  stroke={
                    isEvaluated
                      ? evaluation?.decision === "KEEP"
                        ? "#48805B"
                        : evaluation?.decision === "CAUTION"
                        ? "#D97706"
                        : "#DC2626"
                      : "#8C7C9E"
                  }
                  strokeWidth="7"
                  strokeDasharray="264"
                  strokeDashoffset={isEvaluated ? 264 - 264 * 0.8 : 264 - 264 * 0.4}
                  strokeLinecap="round"
                  className="transition-all duration-700"
                />
              </svg>

              <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-2">
                {isEvaluated ? (
                  <>
                    <span className="text-sm font-bold text-[#141414] leading-tight">
                      {evaluation?.decision}
                    </span>
                    <span className="text-[10px] text-[#7A7382] mt-0.5 font-medium">
                      Decision
                    </span>
                  </>
                ) : (
                  <>
                    <ShieldCheck size={20} className="text-[#8C7C9E] mb-0.5" />
                    <span className="text-[10px] font-bold text-[#6B6375] leading-tight">
                      Clinical Check
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Compatibility Copy */}
            <div className="flex-1 text-center sm:text-left">
              <h2
                className="text-lg sm:text-xl font-bold text-[#141414]"
                style={{ fontFamily: "Georgia, serif" }}
              >
                Overall compatibility
              </h2>

              {isEvaluated ? (
                <div>
                  <p className="text-xs sm:text-sm text-[#6B6375] mt-1 leading-relaxed">
                    {evaluation?.reasons?.[0] ||
                      "This product is generally safe for your skin profile, with no major concerns."}
                  </p>

                  <div className="mt-2.5 flex items-center justify-center sm:justify-start gap-2">
                    <span
                      className={`text-xs font-bold px-3 py-0.5 rounded-full ${
                        evaluation?.decision === "KEEP"
                          ? "bg-[#EAF5EE] text-[#48805B]"
                          : evaluation?.decision === "CAUTION"
                          ? "bg-[#FEF3C7] text-[#D97706]"
                          : "bg-[#FEE2E2] text-[#DC2626]"
                      }`}
                    >
                      {evaluation?.decision === "KEEP"
                        ? "Good Match"
                        : evaluation?.decision === "CAUTION"
                        ? "Caution"
                        : "Not Recommended"}
                    </span>
                    {evaluation?.confidence && (
                      <span className="text-[11px] text-[#7A7382]">
                        · {evaluation.confidence} confidence
                      </span>
                    )}
                  </div>
                </div>
              ) : (
                <div>
                  <p className="text-xs sm:text-sm text-[#7A7382] mt-1 leading-relaxed">
                    Compatibility analysis unavailable for non-routine products. Add this product to your profile routine to calculate personalized safety evaluations.
                  </p>
                  <span className="inline-block text-xs font-bold px-3 py-0.5 rounded-full mt-2.5 bg-gray-100 text-gray-700">
                    Not analyzed for your profile yet
                  </span>
                </div>
              )}
            </div>
          </section>

          {/* Card 3: Ingredient Results & Tabs */}
          <section className="analysis-card p-4 sm:p-6 lg:p-7">
            {/* Filter Tabs */}
            <div
              className="flex flex-wrap items-center gap-2 border-b border-gray-100 pb-4 mb-4"
              role="tablist"
              aria-label="Ingredient safety filters"
            >
              {(
                [
                  "All Ingredients",
                  "Suitable",
                  "Use with Caution",
                  "Not recommended",
                ] as IngredientFilter[]
              ).map((filter) => {
                const isActive = activeFilter === filter;
                return (
                  <button
                    key={filter}
                    type="button"
                    role="tab"
                    aria-selected={isActive}
                    onClick={() => setActiveFilter(filter)}
                    className={`px-3 sm:px-4 py-1.5 sm:py-2 rounded-full text-xs sm:text-sm font-bold transition-all cursor-pointer ${
                      isActive
                        ? "bg-[#FDECEF] text-[#DE688E] shadow-2xs"
                        : "text-[#6B6375] hover:text-[#141414] hover:bg-gray-50"
                    }`}
                  >
                    {filter}
                    <span className="ml-1 text-[11px] opacity-75">
                      (
                      {filter === "All Ingredients"
                        ? resolvedIngredients.length
                        : resolvedIngredients.filter((i) => i.status === filter)
                            .length}
                      )
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Ingredients Table */}
            <div className="divide-y divide-gray-100">
              {filteredIngredients.length > 0 ? (
                filteredIngredients.map((ing) => {
                  const isExpanded = expandedIngredient === ing.name;

                  return (
                    <div
                      key={ing.name}
                      onClick={() =>
                        setExpandedIngredient(isExpanded ? null : ing.name)
                      }
                      className="analysis-ingredient-row py-3 sm:py-3.5 px-2 sm:px-3 rounded-xl flex flex-col cursor-pointer transition"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 sm:gap-4">
                        <div className="flex items-center justify-between gap-2 sm:w-1/3 sm:min-w-[130px]">
                          <h3 className="text-xs sm:text-sm font-bold text-[#141414] leading-snug">
                            {ing.name}
                          </h3>
                          {/* Mobile status badge & chevron */}
                          <div className="flex items-center gap-1.5 sm:hidden shrink-0">
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                ing.status === "Suitable"
                                  ? "bg-[#EAF5EE] text-[#48805B]"
                                  : ing.status === "Use with Caution"
                                  ? "bg-[#FEF3C7] text-[#D97706]"
                                  : ing.status === "Not recommended"
                                  ? "bg-[#FEE2E2] text-[#DC2626]"
                                  : "bg-gray-100 text-gray-700"
                              }`}
                            >
                              {ing.status}
                            </span>
                            {isExpanded ? (
                              <ChevronDown size={14} className="text-gray-400" />
                            ) : (
                              <ChevronRight size={14} className="text-gray-400" />
                            )}
                          </div>
                        </div>

                        <div className="flex-1 min-w-0 sm:pr-2">
                          <p className="text-xs text-[#6B6375] leading-snug">
                            {ing.benefits || ing.function || "Skin conditioning formulation ingredient"}
                          </p>
                        </div>

                        {/* Desktop status badge & chevron */}
                        <div className="hidden sm:flex items-center gap-2 shrink-0">
                          <span
                            className={`text-[10px] sm:text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
                              ing.status === "Suitable"
                                ? "bg-[#EAF5EE] text-[#48805B]"
                                : ing.status === "Use with Caution"
                                ? "bg-[#FEF3C7] text-[#D97706]"
                                : ing.status === "Not recommended"
                                ? "bg-[#FEE2E2] text-[#DC2626]"
                                : "bg-gray-100 text-gray-700"
                            }`}
                          >
                            {ing.status}
                          </span>

                          {isExpanded ? (
                            <ChevronDown size={16} className="text-gray-400" />
                          ) : (
                            <ChevronRight size={16} className="text-gray-400" />
                          )}
                        </div>
                      </div>

                      {/* Expandable details drawer */}
                      {isExpanded && (
                        <div className="mt-3 pt-3 border-t border-gray-100/80 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-[#FBF9FD] p-3.5 rounded-xl">
                          <div>
                            <span className="font-bold text-[#6B6375] block">Function:</span>
                            <span className="text-[#141414]">
                              {ing.function || "Not specified"}
                            </span>
                          </div>

                          <div>
                            <span className="font-bold text-[#6B6375] block">Irritation Risk:</span>
                            <span className="text-[#141414]">
                              {ing.irritation_risk || "Low / None reported"}
                            </span>
                          </div>

                          <div>
                            <span className="font-bold text-[#6B6375] block">Who Should Avoid:</span>
                            <span className="text-[#141414]">
                              {ing.who_should_avoid || "None specific"}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="py-10 text-center text-xs text-[#7A7382]">
                  No ingredients found matching the &ldquo;{activeFilter}&rdquo; filter.
                </div>
              )}
            </div>
          </section>
        </>
      )}

      {/* Floating "Analyze Skin" Button (Desktop only: bottom nav handles mobile) */}
      <button
        type="button"
        onClick={() => router.push("/face-analysis")}
        className="hidden lg:flex btn-analyze-floating fixed bottom-6 right-8 z-40 px-5 py-3.5 items-center gap-3 cursor-pointer"
        title="Open AI Skin Analysis"
      >
        <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center text-white">
          <ScanFace size={20} strokeWidth={2.4} />
        </div>
        <div className="text-left leading-tight">
          <p className="text-xs font-medium text-white/90">AI Scanner</p>
          <p className="text-sm font-bold text-white tracking-wide">Analyze Skin</p>
        </div>
      </button>
    </div>
  );
}

export default function ProductAnalysisPage() {
  return (
    <Suspense
      fallback={
        <div className="w-full min-h-screen flex items-center justify-center">
          <Loader2 className="animate-spin text-[#DE688E]" size={36} />
        </div>
      }
    >
      <ProductAnalysisContent />
    </Suspense>
  );
}
