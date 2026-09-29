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
import { evaluateProduct } from "@/services/personalization";
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
  reason?: string | null;
  personalized?: boolean;
  general_precaution?: string | null;
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

  useEffect(() => {
    if (product && evaluation) {
      try {
        const evalObj = evaluation as any;
        const currentProductSnapshot = {
          product_name: product.product_name,
          brand: product.brand,
          category: product.category,
          decision: evaluation.decision,
          match_label:
            evalObj.match_label ||
            (evaluation.decision === "KEEP"
              ? "Good Match"
              : evaluation.decision === "CAUTION"
              ? "Use with Caution"
              : "Not Recommended"),
          confidence: evaluation.confidence,
          reasons: evaluation.reasons || [],
          mitigations: evaluation.mitigations || [],
          reason_codes: evaluation.reason_codes || [],
          suitable_count: evalObj.suitable_count,
          caution_count: evalObj.caution_count,
          not_recommended_count: evalObj.not_recommended_count,
        };
        sessionStorage.setItem("skinwise_current_product_analysis", JSON.stringify(currentProductSnapshot));
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("skinwise_product_evaluated", { detail: currentProductSnapshot }));
        }
      } catch (err) {
        console.warn("Could not sync product snapshot to sessionStorage:", err);
      }
    }
  }, [product, evaluation]);

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
            const als = (ingRecord.allergy_sensitization || "").toLowerCase();

            let status: ResolvedIngredient["status"] = "Suitable";
            let reason = "Low irritation risk formulation ingredient; well tolerated";

            // Baseline toxicology classification prior to personalization
            if (ir.includes("very high")) {
              status = "Use with Caution";
              reason = "Elevated irritation risk (Very High); patch testing strongly recommended";
            } else if (ir.includes("high")) {
              status = "Use with Caution";
              reason = "Elevated irritation risk (High); patch testing recommended before regular use";
            } else if (
              ir.includes("medium") ||
              ir.includes("moderate") ||
              lower.includes("fragrance") ||
              lower.includes("parfum") ||
              lower.includes("alcohol denat") ||
              als.includes("sensitizer") ||
              als.includes("allergen")
            ) {
              status = "Use with Caution";
              reason = "Moderate irritation potential or recognized contact sensitizer; introduce gradually";
            } else {
              status = "Suitable";
              if (whoAvoid) {
                reason = "Low irritation risk formulation ingredient (general precautions apply to specific allergies)";
              } else {
                reason = "Low irritation risk formulation ingredient; well tolerated";
              }
            }

            resolvedList.push({
              name,
              function: ingRecord.function,
              benefits: ingRecord.benefits,
              irritation_risk: ingRecord.irritation_risk,
              who_should_avoid: ingRecord.who_should_avoid,
              allergy_sensitization: ingRecord.allergy_sensitization,
              status,
              reason,
              personalized: false,
              general_precaution: ingRecord.who_should_avoid || null,
            });
          } else {
            // Ingredient not in database yet
            resolvedList.push({
              name,
              function: "Skin conditioning agent",
              benefits: "Formulation ingredient",
              status: "Suitable",
              reason: "Standard formulation ingredient; low irritation baseline",
              personalized: false,
            });
          }
        }
      }

      setResolvedIngredients(resolvedList);

      // 4. Evaluate product against logged-in user profile using existing personalization engine
      try {
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (user && productData) {
          const evalResult = await evaluateProduct({
            product_id: productData.product_id,
            product_name: productData.product_name,
            brand: productData.brand,
            category: productData.category,
            normalized_ingredients: productData.normalized_ingredients,
            full_ingredient_list: productData.full_ingredient_list,
          });

          if (evalResult && evalResult.evaluation) {
            setEvaluation(evalResult.evaluation);
            setIsEvaluated(true);

            // Store current product evaluation snapshot in sessionStorage for Assistant context
            try {
              const evalObj = evalResult.evaluation as any;
              const currentProductSnapshot = {
                product_name: productData.product_name,
                brand: productData.brand,
                category: productData.category,
                decision: evalResult.evaluation.decision,
                match_label:
                  evalObj.match_label ||
                  (evalResult.evaluation.decision === "KEEP"
                    ? "Good Match"
                    : evalResult.evaluation.decision === "CAUTION"
                    ? "Use with Caution"
                    : "Not Recommended"),
                confidence: evalResult.evaluation.confidence,
                reasons: evalResult.evaluation.reasons || [],
                mitigations: evalResult.evaluation.mitigations || [],
                reason_codes: evalResult.evaluation.reason_codes || [],
                suitable_count: evalObj.suitable_count,
                caution_count: evalObj.caution_count,
                not_recommended_count: evalObj.not_recommended_count,
              };
              sessionStorage.setItem("skinwise_current_product_analysis", JSON.stringify(currentProductSnapshot));
              if (typeof window !== "undefined") {
                window.dispatchEvent(new CustomEvent("skinwise_product_evaluated", { detail: currentProductSnapshot }));
              }
            } catch (storageErr) {
              console.warn("Could not save product snapshot to sessionStorage:", storageErr);
            }

            // Merge personalized ingredient evaluations from the personalization engine
            if (evalResult.evaluation.ingredient_evaluations?.length) {
              const evalMap = new Map<string, any>();
              for (const ie of evalResult.evaluation.ingredient_evaluations) {
                evalMap.set((ie.ingredient || "").toLowerCase(), ie);
              }

              setResolvedIngredients((prev) =>
                prev.map((ing) => {
                  const lower = ing.name.toLowerCase();
                  let match = evalMap.get(lower);
                  if (!match) {
                    for (const [key, val] of evalMap.entries()) {
                      if (lower.includes(key) || key.includes(lower)) {
                        match = val;
                        break;
                      }
                    }
                  }
                  if (match) {
                    return {
                      ...ing,
                      status: match.status,
                      reason: match.reason,
                      personalized: match.personalized,
                      general_precaution: match.general_precaution || ing.general_precaution,
                    };
                  }
                  return ing;
                })
              );
            }
          }
        }
      } catch (persErr) {
        console.warn("Could not evaluate product for user profile:", persErr);
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
          <section className="analysis-card p-4 sm:p-6 lg:p-7 flex flex-col sm:flex-row items-start sm:items-center gap-6">
            {/* Circular Indicator */}
            <div className="relative w-28 h-28 shrink-0 flex items-center justify-center self-center sm:self-start">
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
                    <span
                      className={`text-sm font-bold leading-tight ${
                        evaluation?.decision === "KEEP"
                          ? "text-[#48805B]"
                          : evaluation?.decision === "CAUTION"
                          ? "text-[#D97706]"
                          : "text-[#DC2626]"
                      }`}
                    >
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
            <div className="flex-1 w-full text-center sm:text-left">
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2.5">
                <h2
                  className="text-lg sm:text-xl font-bold text-[#141414]"
                  style={{ fontFamily: "Georgia, serif" }}
                >
                  Overall compatibility
                </h2>
                {isEvaluated && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-[#F4EFFB] text-[#6E578F] border border-purple-100/80">
                    <CheckCircle2 size={12} className="text-[#8C7C9E]" />
                    Analyzed for your profile
                  </span>
                )}
              </div>

              {isEvaluated ? (
                <div className="mt-2 flex flex-col gap-2.5">
                  <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
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
                      <span className="text-[11px] text-[#7A7382] font-medium capitalize">
                        · {evaluation.confidence} confidence
                      </span>
                    )}
                  </div>

                  {/* Primary Reasons / Compatibility Notes */}
                  {evaluation?.reasons && evaluation.reasons.length > 0 && (
                    <div className="flex flex-col gap-1.5 mt-1 text-left">
                      {evaluation.reasons.map((reason: string, idx: number) => (
                        <div key={idx} className="flex items-start gap-2 text-xs sm:text-sm text-[#4A4553]">
                          <span className="text-[#DE688E] mt-0.5 font-bold shrink-0">•</span>
                          <span className="leading-relaxed">{reason}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Mitigations & Safety Instructions */}
                  {evaluation?.mitigations && evaluation.mitigations.length > 0 && (
                    <div className="mt-2 p-3 bg-[#FFF9F2] border border-[#FDE6D2] rounded-xl text-left">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-[#C05621] mb-1">
                        <AlertTriangle size={14} />
                        <span>Recommended Usage & Mitigations</span>
                      </div>
                      <div className="flex flex-col gap-1 text-xs text-[#7B341E]">
                        {evaluation.mitigations.map((mitigation: string, idx: number) => (
                          <p key={idx} className="leading-relaxed">
                            {mitigation}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="mt-2">
                  <p className="text-xs sm:text-sm text-[#7A7382] leading-relaxed">
                    Sign in to your SkinWise account to view personalized compatibility analysis based on your skin type, sensitivity, concerns, and routine history.
                  </p>
                  <div className="mt-3 flex items-center justify-center sm:justify-start gap-3">
                    <button
                      onClick={() => router.push("/auth/login")}
                      className="text-xs font-bold text-[#DE688E] hover:underline cursor-pointer"
                    >
                      Sign In
                    </button>
                    <span className="text-gray-300">·</span>
                    <button
                      onClick={() => router.push("/questionnaire")}
                      className="text-xs font-bold text-[#6B6375] hover:underline cursor-pointer"
                    >
                      Complete Skin Questionnaire
                    </button>
                  </div>
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
                          {ing.reason && (
                            <p className="text-[11px] font-medium mt-1 flex items-center gap-1.5 flex-wrap">
                              {ing.status === "Suitable" && (
                                <span className="inline-flex items-center gap-1 text-[#48805B]">
                                  <CheckCircle2 size={12} className="shrink-0" />
                                  <span>{ing.reason}</span>
                                </span>
                              )}
                              {ing.status === "Use with Caution" && (
                                <span className="inline-flex items-center gap-1 text-[#D97706]">
                                  <AlertTriangle size={12} className="shrink-0" />
                                  <span>{ing.reason}</span>
                                </span>
                              )}
                              {ing.status === "Not recommended" && (
                                <span className="inline-flex items-center gap-1 text-[#DC2626]">
                                  <AlertCircle size={12} className="shrink-0" />
                                  <span>{ing.reason}</span>
                                </span>
                              )}
                            </p>
                          )}
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
                            <span className="font-bold text-[#6B6375] block">General Caution / Who Should Avoid:</span>
                            <span className="text-[#141414]">
                              {ing.who_should_avoid || "None specific"}
                            </span>
                          </div>

                          {ing.reason && (
                            <div className="sm:col-span-3 pt-2 mt-1 border-t border-gray-200/60">
                              <span className="font-bold text-[#6B6375] block">
                                {ing.personalized ? "Personalized Profile Compatibility & Why:" : "Safety & Evaluation Note:"}
                              </span>
                              <span className="text-[#141414] font-medium leading-relaxed">
                                {ing.reason}
                              </span>
                            </div>
                          )}
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
