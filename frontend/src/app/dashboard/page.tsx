"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import {
  Bell,
  User,
  Check,
  ScanFace,
  Sparkles,
  AlertTriangle,
  AlertCircle,
  PlusCircle,
  Loader2,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";
import { analyzeProfile, getProfile, UserProfile } from "@/services/personalization";
import { supabase } from "@/lib/supabase";
import "./dashboard.css";

interface EvaluatedProduct {
  id?: string | number;
  product_id?: string | number | null;
  brand?: string;
  product_name: string;
  category?: string;
  product_type?: string;
  image_url?: string;
  status?: string;
  evaluation?: {
    decision: "KEEP" | "CAUTION" | "REJECT";
    confidence: "high" | "medium" | "low";
    reason_codes?: string[];
    reasons?: string[];
    mitigations?: string[];
  };
}

interface Recommendation {
  product_id?: string | number;
  brand?: string;
  product_name: string;
  category?: string;
  product_type?: string;
  image_url?: string;
  evaluation?: {
    decision: "KEEP" | "CAUTION" | "REJECT";
    confidence: "high" | "medium" | "low";
    reason_codes?: string[];
    reasons?: string[];
    mitigations?: string[];
  };
}

export default function Dashboard() {
  const router = useRouter();

  const [userName, setUserName] = useState<string>("there");
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [personalization, setPersonalization] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [routineType, setRoutineType] = useState<"AM" | "PM">("AM");
  const [completedSteps, setCompletedSteps] = useState<Record<string, boolean>>({});
  const [userId, setUserId] = useState<string | null>(null);

  const channelRef = useRef<any>(null);

  useEffect(() => {
    loadInitialData();
    setupRealtimeSubscriptions();

    // Load persisted completion states for today's date
    try {
      const todayKey = `skinwise_routine_${new Date().toISOString().split("T")[0]}`;
      const saved = localStorage.getItem(todayKey);
      if (saved) {
        setCompletedSteps(JSON.parse(saved));
      }
    } catch (e) {
      console.error("Failed to read routine checklist:", e);
    }

    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. Fetch current authenticated user
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (user) {
        setUserId(user.id);
        const fullName =
          user.user_metadata?.full_name || user.user_metadata?.name;
        if (fullName) {
          setUserName(fullName.split(" ")[0]);
        } else if (user.email) {
          const emailPrefix = user.email.split("@")[0];
          setUserName(emailPrefix.charAt(0).toUpperCase() + emailPrefix.slice(1));
        }
      }

      // 2. Fetch user profile
      try {
        const profileRes = await getProfile();
        if (profileRes.success && profileRes.data) {
          setUserProfile(profileRes.data);
        }
      } catch (err) {
        console.warn("Could not load user profile:", err);
      }

      // 3. Fetch real personalization analysis (evaluated products, AM/PM routine, missing steps)
      const persResult = await analyzeProfile();
      if (persResult.success) {
        setPersonalization(persResult);
      } else {
        console.warn("Personalization analysis returned unsuccessful status:", persResult);
      }
    } catch (err: any) {
      console.error("Error loading dashboard data:", err);
      setError("Failed to load dashboard data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const setupRealtimeSubscriptions = async () => {
    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return;

      const currentUserId = user.id;

      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }

      const channel = supabase
        .channel(`dashboard-live-${currentUserId}-${Date.now()}`)
        .on(
          "postgres_changes",
          { event: "*", schema: "public", table: "user_profiles", filter: `id=eq.${currentUserId}` },
          () => refreshData()
        )
        .on(
          "postgres_changes",
          { event: "*", schema: "public", table: "user_product_history", filter: `user_id=eq.${currentUserId}` },
          () => refreshData()
        )
        .on(
          "postgres_changes",
          { event: "*", schema: "public", table: "user_environment_history", filter: `user_id=eq.${currentUserId}` },
          () => refreshData()
        );

      channel.subscribe();
      channelRef.current = channel;
    } catch (err) {
      console.error("Realtime subscription setup failed:", err);
    }
  };

  const refreshData = async () => {
    try {
      const persResult = await analyzeProfile();
      if (persResult.success) {
        setPersonalization(persResult);
      }
    } catch (err) {
      console.error("Failed to refresh personalization:", err);
    }
  };

  const toggleStepCompletion = (stepId: string) => {
    setCompletedSteps((prev) => {
      const updated = { ...prev, [stepId]: !prev[stepId] };
      try {
        const todayKey = `skinwise_routine_${new Date().toISOString().split("T")[0]}`;
        localStorage.setItem(todayKey, JSON.stringify(updated));
      } catch (e) {
        console.error("Failed to persist step completion:", e);
      }
      return updated;
    });
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 17) return "Good Afternoon";
    return "Good Evening";
  };

  // Extract flagged products (CAUTION or REJECT) from actual evaluated_products
  const evaluatedProducts: EvaluatedProduct[] = personalization?.evaluated_products || [];
  const flaggedProducts = evaluatedProducts.filter(
    (p) => p.evaluation?.decision === "CAUTION" || p.evaluation?.decision === "REJECT"
  );

  // AM & PM routine slots definition mapped to real API output
  const amSteps = [
    { id: "am_cleanser", stepNumber: 1, label: "Cleanser", product: personalization?.am_routine?.cleanser },
    { id: "am_treatment", stepNumber: 2, label: "Serum", product: personalization?.am_routine?.treatment },
    { id: "am_moisturizer", stepNumber: 3, label: "Moisturizer", product: personalization?.am_routine?.moisturizer },
    { id: "am_sunscreen", stepNumber: 4, label: "Sunscreen", product: personalization?.am_routine?.sunscreen },
  ];

  const pmSteps = [
    { id: "pm_cleanser", stepNumber: 1, label: "Cleanser", product: personalization?.pm_routine?.cleanser },
    { id: "pm_treatment", stepNumber: 2, label: "Serum", product: personalization?.pm_routine?.treatment },
    { id: "pm_moisturizer", stepNumber: 3, label: "Moisturizer", product: personalization?.pm_routine?.moisturizer },
  ];

  const currentRoutineSteps = routineType === "AM" ? amSteps : pmSteps;
  const completedCount = currentRoutineSteps.filter((step) => completedSteps[step.id]).length;
  const totalStepsCount = currentRoutineSteps.length;
  const progressPercent = totalStepsCount > 0 ? (completedCount / totalStepsCount) * 100 : 0;

  return (
    <div className="w-full min-h-screen p-4 sm:p-6 lg:p-10 flex flex-col gap-6 lg:gap-8 max-w-[1400px] mx-auto">
      {/* Top Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-sm sm:text-base font-semibold text-[#6B6375]">
            {getGreeting()}, {userName}
          </p>
          <h1
            className="text-3xl sm:text-4xl font-bold text-[#141414] tracking-tight mt-0.5"
            style={{ fontFamily: "Georgia, serif" }}
          >
            Your Skin, Today
          </h1>
          <p className="text-xs sm:text-sm text-[#7A7382] mt-1">
            Here&apos;s how your skin is doing and what you can do next
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            className="w-11 h-11 rounded-full bg-white shadow-[0_2px_10px_rgba(0,0,0,0.04)] border border-gray-100 flex items-center justify-center text-[#2D2D2D] hover:bg-gray-50 transition cursor-pointer"
            title="Notifications"
          >
            <Bell size={20} />
          </button>
          <Link
            href="/profile"
            className="w-11 h-11 rounded-full bg-white shadow-[0_2px_10px_rgba(0,0,0,0.04)] border border-gray-100 flex items-center justify-center text-[#2D2D2D] hover:bg-gray-50 transition"
            title="User Profile"
          >
            <User size={21} />
          </Link>
        </div>
      </header>

      {/* Loading and Error states */}
      {loading ? (
        <div className="w-full py-20 flex flex-col items-center justify-center text-center">
          <Loader2 className="animate-spin text-[#DE688E] mb-3" size={36} />
          <p className="text-sm font-semibold text-[#6B6375]">Loading your personalized dashboard...</p>
        </div>
      ) : error ? (
        <div className="w-full p-6 bg-red-50/80 border border-red-200/60 rounded-3xl text-center">
          <AlertCircle className="text-red-500 mx-auto mb-2" size={32} />
          <p className="text-sm font-semibold text-red-700">{error}</p>
          <button
            onClick={loadInitialData}
            className="mt-3 px-5 py-2 bg-white text-xs font-bold text-red-600 rounded-full border border-red-200 hover:bg-red-50 transition cursor-pointer"
          >
            Retry
          </button>
        </div>
      ) : (
        <>
          {/* Upper Section: Product Safety Watchlist & Recommendations */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-stretch">
            {/* 1. Product Safety Watchlist */}
            <div className="watchlist-card lg:col-span-5 p-4 sm:p-6 lg:p-7 flex flex-col justify-between">
              <div>
                <h2 className="text-lg sm:text-xl font-bold text-[#141414] leading-snug">
                  Product Safety Watchlist
                </h2>
                <p className="text-xs sm:text-sm text-[#7A7382] mt-1 leading-relaxed">
                  {flaggedProducts.length === 1
                    ? "We've found 1 product that may not be ideal for your current conditions."
                    : flaggedProducts.length > 1
                    ? `We've found ${flaggedProducts.length} products that may not be ideal for your current conditions.`
                    : "No products currently flagged"}
                </p>

                {/* Flagged items list or clean empty state */}
                <div className="mt-5 space-y-3">
                  {flaggedProducts.length > 0 ? (
                    flaggedProducts.map((product, index) => {
                      const decision = product.evaluation?.decision || "CAUTION";
                      const isReject = decision === "REJECT";
                      const primaryReason =
                        product.evaluation?.reasons?.[0] ||
                        "May not be ideal for your current skin profile.";
                      const mitigation = product.evaluation?.mitigations?.[0];
                      const reasonCodes = product.evaluation?.reason_codes || [];
                      
                      // Convert reason codes to user-friendly labels
                      const reasonCodeLabels: Record<string, string> = {
                        "SKIN_TYPE_MATCH": "Skin Type Match",
                        "CONCERN_MATCH": "Targets Your Concerns",
                        "GOAL_MATCH": "Matches Your Goal",
                        "ENVIRONMENT_MISMATCH": "Climate Consideration",
                        "EVIDENCE_INCOMPLETE": "Limited Research",
                        "PRODUCT_UNRESOLVED": "Product Unverified",
                        "PREVIOUS_REACTION": "Previous Reaction",
                        "CONTRAINDICATION": "Not Recommended",
                        "IRRITATION_RISK": "Irritation Risk",
                        "SENSITIZATION_RISK": "Sensitization Risk",
                        "ACTIVE_CAUTION": "Active Ingredient Caution"
                      };

                      return (
                        <div
                          key={`flagged-${product.product_id || product.product_name || product.id || product.product_type || 'unknown'}-${index}`}
                          className="bg-white rounded-2xl p-4 shadow-[0_4px_16px_rgba(0,0,0,0.03)] border border-white flex items-start gap-3.5"
                        >
                          {/* Product Thumbnail */}
                          <div className="w-14 h-20 bg-gray-50 rounded-xl overflow-hidden shrink-0 flex items-center justify-center p-1 border border-gray-100">
                            {product.image_url ? (
                              <img
                                src={product.image_url}
                                alt={product.product_name}
                                className="w-full h-full object-contain"
                              />
                            ) : (
                              <div className="text-[10px] text-[#A85175] font-semibold text-center px-1">
                                {product.product_type || "Product"}
                              </div>
                            )}
                          </div>

                          {/* Product Details */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <h3 className="text-xs sm:text-sm font-bold text-[#141414] leading-tight line-clamp-2">
                                {product.brand ? `${product.brand} ` : ""}
                                {product.product_name}
                              </h3>
                              <span
                                className={`shrink-0 text-[10px] sm:text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
                                  isReject
                                    ? "bg-[#FEE2E2] text-[#DC2626]"
                                    : "bg-[#FEF3C7] text-[#D97706]"
                                }`}
                              >
                                {isReject ? "Reject" : "Caution"}
                              </span>
                            </div>

                            {/* Personalization Reason Badges */}
                            {reasonCodes.length > 0 && (
                              <div className="flex flex-wrap gap-1.5 mt-2">
                                {reasonCodes.slice(0, 3).map((code, idx) => {
                                  const label = reasonCodeLabels[code] || code;
                                  return (
                                    <span
                                      key={`${code}-${idx}`}
                                      className="inline-flex items-center mr-1.5 mb-1 text-[9px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200"
                                    >
                                      {label}
                                    </span>
                                  );
                                })}
                              </div>
                            )}

                            <p className="text-[11px] sm:text-xs text-[#6B6375] mt-1 leading-snug">
                              {primaryReason}
                            </p>

                            {mitigation && (
                              <p className="text-[10px] sm:text-[11px] text-[#8C827A] mt-1.5 leading-snug">
                                <strong className="text-[#6B6375]">Mitigation:</strong> {mitigation}
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="bg-white/80 rounded-2xl p-5 border border-white text-center flex flex-col items-center justify-center">
                      <div className="w-10 h-10 rounded-full bg-[#EBF5ED] text-[#48805B] flex items-center justify-center mb-2">
                        <ShieldCheck size={20} />
                      </div>
                      <p className="text-xs sm:text-sm font-semibold text-[#141414]">
                        No products currently flagged
                      </p>
                      <p className="text-[11px] text-[#7A7382] mt-0.5 max-w-xs">
                        All evaluated products in your routine are well-tolerated with no caution flags.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {flaggedProducts.length > 0 && (
                <div className="mt-4 pt-3 border-t border-orange-100/60 flex justify-end">
                  <Link
                    href="/routine"
                    className="text-xs font-semibold text-[#A85175] hover:underline inline-flex items-center gap-1"
                  >
                    Manage routine products <ChevronRight size={14} />
                  </Link>
                </div>
              )}
            </div>

            {/* 2. Recommendations */}
            <div className="recommendations-card lg:col-span-7 p-4 sm:p-6 lg:p-7 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between gap-4">
                  <h2 className="text-lg sm:text-xl font-bold text-[#141414] leading-snug">
                    Recommendations
                  </h2>
                  <Link
                    href="/ingredients"
                    className="text-xs sm:text-sm font-bold text-[#DE688E] hover:underline flex items-center gap-1 shrink-0"
                  >
                    View Products →
                  </Link>
                </div>
                <p className="text-xs sm:text-sm text-[#7A7382] mt-1 leading-relaxed">
                  Personalized recommendation for your current skin needs.
                </p>

                {/* Render recommendations or empty state */}
                {personalization?.recommendations && Object.values(personalization.recommendations).some((recs: any) => recs && recs.length > 0) ? (
                  <div className="mt-5 space-y-4">
                    {Object.entries(personalization.recommendations).map(([category, recs]) => {
                      const categoryRecommendations = recs as Recommendation[];
                      if (!categoryRecommendations || categoryRecommendations.length === 0) return null;
                      
                      // Format category name for display
                      const categoryDisplay = category.charAt(0).toUpperCase() + category.slice(1);
                      
                      return (
                        <div key={category} className="bg-white rounded-2xl p-4 shadow-[0_4px_16px_rgba(0,0,0,0.03)] border border-white">
                          <h3 className="text-sm font-bold text-[#141414] mb-3">{categoryDisplay}</h3>
                          <div className="space-y-3">
                            {categoryRecommendations.map((rec, idx) => {
                              const decision = rec.evaluation?.decision || "KEEP";
                              const isCaution = decision === "CAUTION";
                              const primaryReason = rec.evaluation?.reasons?.[0];
                              const mitigation = rec.evaluation?.mitigations?.[0];
                              const reasonCodes = rec.evaluation?.reason_codes || [];
                              const productKey = `${category}-${rec.product_id || rec.product_name || 'unknown'}-${idx}`;
                              
                              // Convert reason codes to user-friendly labels
                              const reasonCodeLabels: Record<string, string> = {
                                "SKIN_TYPE_MATCH": "Skin Type Match",
                                "CONCERN_MATCH": "Targets Your Concerns",
                                "GOAL_MATCH": "Matches Your Goal",
                                "ENVIRONMENT_MISMATCH": "Climate Consideration",
                                "EVIDENCE_INCOMPLETE": "Limited Research",
                                "PRODUCT_UNRESOLVED": "Product Unverified",
                                "PREVIOUS_REACTION": "Previous Reaction",
                                "CONTRAINDICATION": "Not Recommended",
                                "IRRITATION_RISK": "Irritation Risk",
                                "SENSITIZATION_RISK": "Sensitization Risk",
                                "ACTIVE_CAUTION": "Active Ingredient Caution"
                              };
                              
                              return (
                                <div
                                  key={productKey}
                                  className="flex items-start gap-3 p-3 rounded-xl bg-gray-50 border border-gray-100"
                                >
                                  {/* Product Thumbnail */}
                                  <div className="w-12 h-16 bg-gray-100 rounded-lg overflow-hidden shrink-0 flex items-center justify-center p-1 border border-gray-200">
                                    {rec.image_url ? (
                                      <img
                                        src={rec.image_url}
                                        alt={rec.product_name}
                                        className="w-full h-full object-contain"
                                      />
                                    ) : (
                                      <div className="text-[9px] text-[#A85175] font-semibold text-center px-1">
                                        {rec.product_type || "Product"}
                                      </div>
                                    )}
                                  </div>

                                  {/* Product Details */}
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between gap-2">
                                      <div className="flex-1 min-w-0">
                                        <h4 className="text-xs font-bold text-[#141414] leading-tight line-clamp-2">
                                          {rec.brand ? `${rec.brand} ` : ""}{rec.product_name}
                                        </h4>
                                        {isCaution && (
                                          <div className="mt-1.5 flex items-center gap-1.5">
                                            <AlertTriangle size={12} className="text-orange-500 shrink-0" />
                                            <span className="text-[10px] font-semibold text-orange-600">
                                              Use with Caution
                                            </span>
                                          </div>
                                        )}
                                        
                                        {/* Personalization Reason Badges */}
                                        {reasonCodes.length > 0 && (
                                          <div className="flex flex-wrap gap-1 mt-1.5">
                                            {reasonCodes.slice(0, 2).map((code, badgeIdx) => {
                                              const label = reasonCodeLabels[code] || code;
                                              return (
                                                <span
                                                  key={`${code}-${badgeIdx}`}
                                                  className="inline-flex items-center mr-1.5 mb-1 text-[8px] font-medium px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200"
                                                >
                                                  {label}
                                                </span>
                                              );
                                            })}
                                          </div>
                                        )}
                                      </div>
                                      {rec.product_id && (
                                        <Link
                                          href={`/product-analysis?id=${rec.product_id}`}
                                          className="text-[10px] font-bold text-[#DE688E] hover:underline shrink-0"
                                        >
                                          View Analysis
                                        </Link>
                                      )}
                                    </div>
                                    
                                    {primaryReason && (
                                      <p className="text-[10px] text-[#7A7382] mt-1.5 leading-snug line-clamp-2">
                                        {primaryReason}
                                      </p>
                                    )}
                                    
                                    {mitigation && (
                                      <p className="text-[10px] text-[#8C827A] mt-1 leading-snug">
                                        <strong className="text-[#6B6375]">Mitigation:</strong> {mitigation}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="mt-6 rounded-2xl border-2 border-dashed border-gray-200/80 bg-white/60 p-6 sm:p-8 flex flex-col items-center justify-center text-center min-h-[160px]">
                    <div className="w-12 h-12 rounded-full bg-[#FDF0F4] text-[#DE688E] flex items-center justify-center mb-3">
                      <Sparkles size={24} />
                    </div>
                    <h3 className="text-sm sm:text-base font-bold text-[#141414]">
                      No Recommendations Yet
                    </h3>
                    <p className="text-xs text-[#7A7382] max-w-md mt-1 leading-relaxed">
                      Your current routine is complete. Recommendations will appear here when missing steps are identified.
                    </p>
                  </div>
                )}
              </div>

              <div className="mt-4 pt-3 flex items-center justify-between text-xs text-[#7A7382]">
                <span>Grounded in clinical ingredient safety</span>
                {!(personalization?.recommendations && Object.keys(personalization.recommendations).length > 0) && (
                  <span className="text-[11px] font-medium bg-purple-50 text-purple-700 px-2.5 py-0.5 rounded-full">
                    AI-Powered
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Lower Section: Today's Routine */}
          <div className="routine-card p-4 sm:p-6 lg:p-7">
            {/* Header: Title, AM/PM Toggle, Progress bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div className="flex items-center gap-4">
                <h2
                  className="text-xl sm:text-2xl font-bold text-[#141414]"
                  style={{ fontFamily: "Georgia, serif" }}
                >
                  Today&apos;s Routine
                </h2>

                {/* AM / PM Toggle */}
                <div className="bg-[#EFECE6] p-1 rounded-full flex items-center gap-1 shadow-inner">
                  <button
                    type="button"
                    onClick={() => setRoutineType("AM")}
                    className={`px-3.5 py-1 text-xs font-bold rounded-full transition-all cursor-pointer ${
                      routineType === "AM"
                        ? "bg-white text-[#141414] shadow-sm"
                        : "text-[#7A7382] hover:text-[#141414]"
                    }`}
                  >
                    AM
                  </button>
                  <button
                    type="button"
                    onClick={() => setRoutineType("PM")}
                    className={`px-3.5 py-1 text-xs font-bold rounded-full transition-all cursor-pointer ${
                      routineType === "PM"
                        ? "bg-white text-[#141414] shadow-sm"
                        : "text-[#7A7382] hover:text-[#141414]"
                    }`}
                  >
                    PM
                  </button>
                </div>
              </div>

              {/* Progress counter & bar */}
              <div className="flex flex-col sm:items-end gap-1.5 w-full sm:w-auto sm:min-w-[180px]">
                <span className="text-xs font-bold text-[#6B6375]">
                  {completedCount} of {totalStepsCount} completed
                </span>
                <div className="w-full sm:max-w-[220px] bg-[#E5E7EB] rounded-full h-2.5 overflow-hidden p-0.5">
                  <div
                    className="bg-[#5B9A6F] h-full rounded-full transition-all duration-300"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Horizontal Grid of Routine Step Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {currentRoutineSteps.map((step) => {
                const product = step.product;
                const isCompleted = !!completedSteps[step.id];

                if (!product) {
                  // Step is missing from the user's routine
                  return (
                    <div
                      key={step.id}
                      className="routine-step-card p-4 border-dashed border-gray-200 bg-gray-50/50 flex flex-col justify-between min-h-[140px]"
                    >
                      <div>
                        <div className="flex items-center gap-2 mb-3">
                          <span className="w-5 h-5 rounded-full bg-gray-200 text-gray-600 text-[11px] font-bold flex items-center justify-center">
                            {step.stepNumber}
                          </span>
                          <span className="text-xs font-bold text-gray-500">
                            {step.stepNumber}. {step.label}
                          </span>
                        </div>
                        <p className="text-xs text-[#7A7382] leading-snug">
                          No {step.label.toLowerCase()} slotted in your {routineType} routine.
                        </p>
                      </div>

                      <Link
                        href="/routine"
                        className="text-[11px] font-bold text-[#DE688E] hover:underline inline-flex items-center gap-1 mt-3"
                      >
                        <PlusCircle size={14} /> Add Product
                      </Link>
                    </div>
                  );
                }

                return (
                  <div
                    key={step.id}
                    onClick={() => toggleStepCompletion(step.id)}
                    className={`routine-step-card p-4 cursor-pointer flex flex-col justify-between min-h-[140px] select-none ${
                      isCompleted ? "completed" : ""
                    }`}
                  >
                    <div>
                      {/* Step Header with Checkmark Indicator */}
                      <div className="flex items-center gap-2 mb-2.5">
                        <button
                          type="button"
                          className={`w-5 h-5 rounded-full flex items-center justify-center transition-colors ${
                            isCompleted
                              ? "bg-[#48805B] text-white"
                              : "bg-gray-200 text-gray-600"
                          }`}
                        >
                          {isCompleted ? (
                            <Check size={12} strokeWidth={3} />
                          ) : (
                            <span className="text-[11px] font-bold leading-none">
                              {step.stepNumber}
                            </span>
                          )}
                        </button>
                        <span className="text-xs font-bold text-[#141414]">
                          {step.stepNumber}. {step.label}
                        </span>
                      </div>

                      {/* Product Content: Thumbnail + Brand/Name */}
                      <div className="flex items-start gap-3 mt-2">
                        <div className="w-12 h-14 bg-white rounded-lg overflow-hidden shrink-0 flex items-center justify-center p-1 border border-gray-100 shadow-2xs">
                          {product.image_url ? (
                            <img
                              src={product.image_url}
                              alt={product.product_name}
                              className="w-full h-full object-contain"
                            />
                          ) : (
                            <div className="text-[9px] text-[#A85175] font-semibold text-center leading-tight">
                              {product.product_type || step.label}
                            </div>
                          )}
                        </div>

                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-bold text-[#141414] leading-tight line-clamp-2">
                            {product.brand ? `${product.brand} ` : ""}
                            {product.product_name}
                          </p>
                          {product.evaluation?.decision && (
                            <span
                              className={`inline-block text-[10px] font-bold px-2 py-0.2 rounded-full mt-1.5 ${
                                product.evaluation.decision === "KEEP"
                                  ? "bg-green-100/80 text-green-700"
                                  : product.evaluation.decision === "CAUTION"
                                  ? "bg-amber-100/80 text-amber-700"
                                  : "bg-red-100/80 text-red-700"
                              }`}
                            >
                              {product.evaluation.decision}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <p className="text-[10px] text-[#7A7382] mt-3">
                      {isCompleted ? "Completed today" : "Tap to complete"}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Lifestyle Insights Section */}
          {personalization?.lifestyle_insights && personalization.lifestyle_insights.length > 0 && (
            <div className="lifestyle-insights-card p-5 sm:p-6">
              <h2 className="text-base sm:text-lg font-bold text-[#141414] mb-3">
                Lifestyle Insights
              </h2>
              <div className="space-y-2">
                {personalization.lifestyle_insights.slice(0, 3).map((insight: string, index: number) => (
                  <div
                    key={`insight-${index}`}
                    className="flex items-start gap-2 text-xs sm:text-sm text-[#6B6375] leading-relaxed"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[#DE688E] mt-1.5 shrink-0" />
                    <span>{insight}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
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
