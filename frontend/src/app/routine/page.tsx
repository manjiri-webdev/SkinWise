"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Bell,
  User,
  Sun,
  Moon,
  Check,
  ChevronRight,
  PlusCircle,
  AlertCircle,
  AlertTriangle,
  Loader2,
  Package,
  ScanFace,
  Sparkles,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { analyzeProfile } from "@/services/personalization";
import ProductPicker from "@/components/ProductPicker";
import "./routine.css";

interface ProductEvaluation {
  decision: "KEEP" | "CAUTION" | "REJECT";
  confidence: "high" | "medium" | "low";
  reason_codes?: string[];
  reasons?: string[];
  mitigations?: string[];
}

interface SlottedProduct {
  product_id: number;
  brand?: string | null;
  product_name: string;
  category?: string | null;
  main_purpose?: string | null;
  image_url?: string | null;
  product_type?: string | null;
  status?: string | null;
  evaluation?: ProductEvaluation;
}

interface RoutineSlot {
  id: string;
  slotKey: string;
  stepNumber: number;
  label: string;
  product: SlottedProduct | null;
  isMissing: boolean;
}

export default function RoutinePage() {
  const router = useRouter();

  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string>("there");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [amRoutineSlots, setAmRoutineSlots] = useState<RoutineSlot[]>([]);
  const [pmRoutineSlots, setPmRoutineSlots] = useState<RoutineSlot[]>([]);
  const [missingSteps, setMissingSteps] = useState<string[]>([]);
  const [hasRoutineData, setHasRoutineData] = useState(false);

  // Client-side daily completion map: { [stepId: string]: boolean }
  const [completedSteps, setCompletedSteps] = useState<Record<string, boolean>>({});

  // Active expanded reason card
  const [expandedReason, setExpandedReason] = useState<string | null>(null);

  // Product picker state
  const [isProductPickerOpen, setIsProductPickerOpen] = useState(false);
  const [pickerCategory, setPickerCategory] = useState<string>("");

  useEffect(() => {
    loadUserDataAndRoutine();
  }, []);

  const loadUserDataAndRoutine = async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. Current authenticated user only
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        router.push("/auth/login");
        return;
      }

      setCurrentUserId(user.id);

      // Derive display name
      const fullName =
        user.user_metadata?.full_name || user.user_metadata?.name;
      if (fullName) {
        setDisplayName(fullName.split(" ")[0]);
      } else if (user.email) {
        const prefix = user.email.split("@")[0];
        setDisplayName(prefix.charAt(0).toUpperCase() + prefix.slice(1));
      }

      // 2. Load client-side completion strictly scoped to current user and today's date
      const todayStr = new Date().toISOString().split("T")[0];
      const storageKey = `skinwise_routine_completion_${user.id}_${todayStr}`;
      try {
        const savedCompletion = localStorage.getItem(storageKey);
        if (savedCompletion) {
          setCompletedSteps(JSON.parse(savedCompletion));
        }
      } catch (err) {
        console.error("Failed to read routine completion from localStorage:", err);
      }

      // 3. Fetch real personalization analysis (source of truth: POST /personalization/analyze)
      const persResult = await analyzeProfile();

      if (!persResult || !persResult.success) {
        setHasRoutineData(false);
        setLoading(false);
        return;
      }

      const rawAm = persResult.am_routine || {};
      const rawPm = persResult.pm_routine || {};
      const rawMissing: string[] = persResult.missing_steps || [];
      setMissingSteps(rawMissing);

      // 4. Resolve missing product display fields from products table if necessary
      const slottedProducts: SlottedProduct[] = [
        rawAm.cleanser,
        rawAm.treatment,
        rawAm.moisturizer,
        rawAm.sunscreen,
        rawPm.cleanser,
        rawPm.treatment,
        rawPm.moisturizer,
      ].filter(Boolean);

      const idsNeedingResolution = slottedProducts
        .filter((p) => p && p.product_id && (!p.image_url || !p.brand))
        .map((p) => p.product_id);

      let productDetailsMap = new Map<number, any>();
      if (idsNeedingResolution.length > 0) {
        try {
          const { data: dbProducts } = await supabase
            .from("products")
            .select("product_id, brand, image_url, category, product_name")
            .in("product_id", idsNeedingResolution);

          if (dbProducts) {
            dbProducts.forEach((p) => productDetailsMap.set(p.product_id, p));
          }
        } catch (dbErr) {
          console.warn("Failed to resolve missing product fields from database:", dbErr);
        }
      }

      const enrichProduct = (product: any): SlottedProduct | null => {
        if (!product) return null;
        const extra = productDetailsMap.get(product.product_id);
        return {
          ...product,
          brand: product.brand || extra?.brand || null,
          image_url: product.image_url || extra?.image_url || null,
          category: product.category || extra?.category || null,
          product_name: product.product_name || extra?.product_name || "Unknown Product",
        };
      };

      const enrichedAm = {
        cleanser: enrichProduct(rawAm.cleanser),
        treatment: enrichProduct(rawAm.treatment),
        moisturizer: enrichProduct(rawAm.moisturizer),
        sunscreen: enrichProduct(rawAm.sunscreen),
      };

      const enrichedPm = {
        cleanser: enrichProduct(rawPm.cleanser),
        treatment: enrichProduct(rawPm.treatment),
        moisturizer: enrichProduct(rawPm.moisturizer),
      };

      // 5. Build AM routine slots (Cleanser, Serum, Moisturizer, Sunscreen)
      const isAmCleanserMissing = rawMissing.some(
        (m) => m.toLowerCase().includes("cleanser") && m.includes("AM")
      );
      const isAmTreatmentMissing = rawMissing.some(
        (m) => m.toLowerCase().includes("treatment") && m.includes("AM")
      );
      const isAmMoisturizerMissing = rawMissing.some(
        (m) => m.toLowerCase().includes("moisturizer") && m.includes("AM")
      );
      const isAmSunscreenMissing = rawMissing.some(
        (m) => m.toLowerCase().includes("sunscreen") && m.includes("AM")
      );

      const amSlots: RoutineSlot[] = [
        {
          id: "am_cleanser",
          slotKey: "cleanser",
          stepNumber: 1,
          label: "Cleanser",
          product: enrichedAm.cleanser,
          isMissing: !enrichedAm.cleanser && isAmCleanserMissing,
        },
        {
          id: "am_treatment",
          slotKey: "treatment",
          stepNumber: 2,
          label: "Serum",
          product: enrichedAm.treatment,
          isMissing: !enrichedAm.treatment && isAmTreatmentMissing,
        },
        {
          id: "am_moisturizer",
          slotKey: "moisturizer",
          stepNumber: 3,
          label: "Moisturizer",
          product: enrichedAm.moisturizer,
          isMissing: !enrichedAm.moisturizer && isAmMoisturizerMissing,
        },
        {
          id: "am_sunscreen",
          slotKey: "sunscreen",
          stepNumber: 4,
          label: "Sunscreen",
          product: enrichedAm.sunscreen,
          isMissing: !enrichedAm.sunscreen && isAmSunscreenMissing,
        },
      ];

      // 6. Build PM routine slots (Cleanser, Serum, Moisturizer)
      const isPmCleanserMissing = rawMissing.some(
        (m) => m.toLowerCase().includes("cleanser") && m.includes("PM")
      );
      const isPmTreatmentMissing = rawMissing.some(
        (m) => m.toLowerCase().includes("treatment") && m.includes("PM")
      );
      const isPmMoisturizerMissing = rawMissing.some(
        (m) => m.toLowerCase().includes("moisturizer") && m.includes("PM")
      );

      const pmSlots: RoutineSlot[] = [
        {
          id: "pm_cleanser",
          slotKey: "cleanser",
          stepNumber: 1,
          label: "Cleanser",
          product: enrichedPm.cleanser,
          isMissing: !enrichedPm.cleanser && isPmCleanserMissing,
        },
        {
          id: "pm_treatment",
          slotKey: "treatment",
          stepNumber: 2,
          label: "Serum",
          product: enrichedPm.treatment,
          isMissing: !enrichedPm.treatment && isPmTreatmentMissing,
        },
        {
          id: "pm_moisturizer",
          slotKey: "moisturizer",
          stepNumber: 3,
          label: "Moisturizer",
          product: enrichedPm.moisturizer,
          isMissing: !enrichedPm.moisturizer && isPmMoisturizerMissing,
        },
      ];

      setAmRoutineSlots(amSlots);
      setPmRoutineSlots(pmSlots);

      const hasAnyProduct =
        Boolean(enrichedAm.cleanser) ||
        Boolean(enrichedAm.treatment) ||
        Boolean(enrichedAm.moisturizer) ||
        Boolean(enrichedAm.sunscreen) ||
        Boolean(enrichedPm.cleanser) ||
        Boolean(enrichedPm.treatment) ||
        Boolean(enrichedPm.moisturizer) ||
        rawMissing.length > 0;

      setHasRoutineData(hasAnyProduct);
    } catch (err: any) {
      console.error("Error loading routine:", err);
      setError(err.message || "Failed to load your personalized routine.");
    } finally {
      setLoading(false);
    }
  };

  const toggleStepCompletion = (stepId: string) => {
    if (!currentUserId) return;

    setCompletedSteps((prev) => {
      const updated = { ...prev, [stepId]: !prev[stepId] };
      try {
        const todayStr = new Date().toISOString().split("T")[0];
        const storageKey = `skinwise_routine_completion_${currentUserId}_${todayStr}`;
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch (e) {
        console.error("Failed to save step completion to localStorage:", e);
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

  const handleOpenProductPicker = (slotKey: string) => {
    // Map slot keys to API categories
    const categoryMap: Record<string, string> = {
      cleanser: "cleanser",
      treatment: "serum",
      moisturizer: "moisturizer",
      sunscreen: "sunscreen",
    };
    setPickerCategory(categoryMap[slotKey] || slotKey);
    setIsProductPickerOpen(true);
  };

  const handleProductSelected = async () => {
    // Refresh personalization data after product selection
    await loadUserDataAndRoutine();
  };

  // Progress metrics calculation
  const amCompletedCount = amRoutineSlots.filter(
    (s) => s.product && completedSteps[s.id]
  ).length;
  const amTotalSteps = amRoutineSlots.length;
  const amProgressPercent =
    amTotalSteps > 0 ? (amCompletedCount / amTotalSteps) * 100 : 0;

  const pmCompletedCount = pmRoutineSlots.filter(
    (s) => s.product && completedSteps[s.id]
  ).length;
  const pmTotalSteps = pmRoutineSlots.length;
  const pmProgressPercent =
    pmTotalSteps > 0 ? (pmCompletedCount / pmTotalSteps) * 100 : 0;

  return (
    <div className="w-full min-h-screen p-4 sm:p-6 lg:p-10 flex flex-col gap-6 lg:gap-8 max-w-[1400px] mx-auto">
      {/* Top Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-sm sm:text-base font-semibold text-[#6B6375]">
            {getGreeting()}, {displayName}
          </p>
          <h1
            className="text-3xl sm:text-4xl font-bold text-[#141414] tracking-tight mt-0.5"
            style={{ fontFamily: "Georgia, serif" }}
          >
            My Routine
          </h1>
          <p className="text-xs sm:text-sm text-[#7A7382] mt-1 font-medium">
            your personalized skincare routine for healthy, glowing skin
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

      {/* Loading State */}
      {loading && (
        <div className="w-full py-28 flex flex-col items-center justify-center text-center">
          <Loader2 className="animate-spin text-[#DE688E] mb-3" size={36} />
          <p className="text-sm font-semibold text-[#6B6375]">
            Loading your personalized skincare routine...
          </p>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="w-full p-6 bg-rose-50/80 border border-rose-200 rounded-3xl text-center flex flex-col items-center gap-3">
          <AlertCircle className="text-rose-500" size={32} />
          <p className="text-sm font-semibold text-rose-800">{error}</p>
          <button
            onClick={() => loadUserDataAndRoutine()}
            className="text-xs font-bold text-[#DE688E] hover:underline"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Empty State (No routine data configured) */}
      {!loading && !error && !hasRoutineData && (
        <div className="w-full py-20 p-8 bg-white/70 backdrop-blur-md rounded-[28px] border border-[#ECE8E1] text-center flex flex-col items-center gap-4 max-w-xl mx-auto shadow-[0_8px_30px_rgba(0,0,0,0.03)]">
          <div className="w-16 h-16 rounded-2xl bg-[#FDE8EF] text-[#DE688E] flex items-center justify-center shadow-inner">
            <Package size={30} />
          </div>
          <div>
            <h2
              className="text-2xl font-bold text-[#141414] tracking-tight"
              style={{ fontFamily: "Georgia, serif" }}
            >
              No Routine Configured Yet
            </h2>
            <p className="text-sm text-[#7A7382] mt-2 max-w-md mx-auto leading-relaxed">
              We need a bit more information about your current skincare products
              and concerns before generating your personalized AM and PM routine.
            </p>
          </div>
          <Link
            href="/questionnaire"
            className="mt-2 inline-flex items-center gap-2 bg-gradient-to-r from-[#DE688E] to-[#BD426B] text-white px-6 py-3 rounded-full text-sm font-bold shadow-md shadow-pink-500/20 hover:opacity-95 transition-all"
          >
            <Sparkles size={16} /> Complete Questionnaire
          </Link>
        </div>
      )}

      {/* Main Routines Grid */}
      {!loading && !error && hasRoutineData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8 items-start">
          {/* ========================================================================= */}
          {/* MORNING ROUTINE CARD                                                      */}
          {/* ========================================================================= */}
          <section className="morning-routine-card p-4 sm:p-6 lg:p-7 flex flex-col gap-5">
            {/* Header: Title + Progress */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-amber-100/90 text-amber-600 flex items-center justify-center shrink-0 shadow-sm">
                  <Sun size={22} className="animate-spin-slow" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-[#1E293B] tracking-tight">
                    Morning Routine
                  </h2>
                  <p className="text-xs text-[#64748B] mt-0.5">
                    Start your day with care · {amTotalSteps} steps
                  </p>
                </div>
              </div>

              {/* Progress Indicator */}
              <div className="flex flex-col sm:items-end gap-1.5 shrink-0">
                <span className="text-xs font-bold text-[#4E9367]">
                  {amCompletedCount} of {amTotalSteps} completed
                </span>
                <div className="w-32 sm:w-36 bg-[#DCE8DF] rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-[#4E9367] h-full rounded-full transition-all duration-300"
                    style={{ width: `${amProgressPercent}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Steps List */}
            <div className="flex flex-col gap-3.5">
              {amRoutineSlots.map((slot) => {
                const product = slot.product;
                const isCompleted = !!completedSteps[slot.id];
                const isCaution =
                  product?.evaluation?.decision === "CAUTION";
                const isReasonExpanded = expandedReason === slot.id;

                if (!product) {
                  // Slot without product
                  return (
                    <div
                      key={slot.id}
                      className="missing-step-card p-4 flex items-center justify-between gap-3 select-none"
                    >
                      <div className="flex items-center gap-3.5 min-w-0">
                        <div className="w-6 h-6 rounded-full border border-dashed border-gray-300 text-gray-400 flex items-center justify-center text-[10px] font-bold shrink-0">
                          {slot.stepNumber}
                        </div>
                        <div className="min-w-0">
                          <span className="text-xs font-semibold text-[#8B8476] block">
                            {slot.stepNumber}. {slot.label}
                          </span>
                          <p className="text-xs text-[#9E9789] truncate">
                            {slot.isMissing
                              ? "Missing from your morning routine"
                              : "No treatment slotted (Optional)"}
                          </p>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => slot.isMissing && handleOpenProductPicker(slot.slotKey)}
                        disabled={!slot.isMissing}
                        className={`inline-flex items-center gap-1 text-xs font-bold shrink-0 px-3 py-1.5 rounded-full shadow-xs border border-[#EBE7DF] ${
                          slot.isMissing
                            ? "bg-white/90 text-[#DE688E] hover:bg-white cursor-pointer"
                            : "bg-gray-100 text-gray-400 cursor-not-allowed"
                        }`}
                      >
                        <PlusCircle size={14} /> Add Product
                      </button>
                    </div>
                  );
                }

                return (
                  <div
                    key={slot.id}
                    className={`routine-step-card p-3.5 sm:p-4 flex flex-col gap-2 transition-all ${
                      isCompleted ? "completed" : ""
                    }`}
                  >
                    <div className="flex items-center gap-3.5">
                      {/* Completion Circle Button */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleStepCompletion(slot.id);
                        }}
                        className={`completion-btn ${
                          isCompleted ? "completed" : "uncompleted"
                        }`}
                        title={
                          isCompleted
                            ? "Mark as uncompleted"
                            : "Mark as completed"
                        }
                      >
                        {isCompleted && <Check size={14} strokeWidth={3} />}
                      </button>

                      {/* Product Thumbnail */}
                      <div className="w-13 h-13 sm:w-14 sm:h-14 rounded-xl bg-white border border-gray-100 flex items-center justify-center overflow-hidden shrink-0 p-1">
                        {product.image_url ? (
                          <img
                            src={product.image_url}
                            alt={product.product_name}
                            className="w-full h-full object-contain"
                            onError={(e) => {
                              // Fallback on image load failure
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                        ) : (
                          <Package size={22} className="text-[#DE688E]" />
                        )}
                      </div>

                      {/* Product Text Content */}
                      <div className="flex-1 min-w-0">
                        <span className="text-[11px] sm:text-xs font-semibold text-[#7A7382] block">
                          {slot.stepNumber}. {slot.label}
                        </span>
                        <Link
                          href={`/product-analysis?id=${product.product_id}`}
                          className="text-sm sm:text-[14.5px] font-bold text-[#1E293B] hover:text-[#DE688E] transition-colors truncate block mt-0.5"
                          title={product.product_name}
                        >
                          {product.product_name}
                        </Link>

                        {/* Caution status tag if applicable */}
                        {isCaution && (
                          <div className="mt-1 flex items-center gap-1.5">
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                              <AlertTriangle size={10} /> Caution
                            </span>
                            {product.evaluation?.reasons &&
                              product.evaluation.reasons.length > 0 && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setExpandedReason(
                                      isReasonExpanded ? null : slot.id
                                    );
                                  }}
                                  className="text-[10px] font-semibold text-[#8B7D6B] hover:underline cursor-pointer"
                                >
                                  {isReasonExpanded ? "Hide reason" : "View reason"}
                                </button>
                              )}
                          </div>
                        )}
                      </div>

                      {/* Chevron Navigation to Product Details */}
                      <Link
                        href={`/product-analysis?id=${product.product_id}`}
                        className="text-[#94A3B8] hover:text-[#DE688E] transition p-1 shrink-0"
                        title="View ingredient analysis"
                      >
                        <ChevronRight size={20} />
                      </Link>
                    </div>

                    {/* Expandable Personalization Reason */}
                    {isCaution && isReasonExpanded && product.evaluation?.reasons && (
                      <div className="mt-1 p-2.5 rounded-xl bg-amber-50/70 border border-amber-200/80 text-xs text-amber-800 space-y-1">
                        <p className="font-bold text-[11px] text-amber-900">
                          Personalization reasons:
                        </p>
                        <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-800">
                          {product.evaluation.reasons.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* ========================================================================= */}
          {/* NIGHT ROUTINE CARD                                                        */}
          {/* ========================================================================= */}
          <section className="night-routine-card p-4 sm:p-6 lg:p-7 flex flex-col gap-5">
            {/* Header: Title + Progress */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-indigo-100/90 text-indigo-700 flex items-center justify-center shrink-0 shadow-sm">
                  <Moon size={20} />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-[#1E293B] tracking-tight">
                    Night Routine
                  </h2>
                  <p className="text-xs text-[#64748B] mt-0.5">
                    Repair and refresh · {pmTotalSteps} steps
                  </p>
                </div>
              </div>

              {/* Progress Indicator */}
              <div className="flex flex-col sm:items-end gap-1.5 shrink-0">
                <span className="text-xs font-bold text-[#6C5691]">
                  {pmCompletedCount} of {pmTotalSteps} completed
                </span>
                <div className="w-32 sm:w-36 bg-[#E3DFEB] rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-[#6C5691] h-full rounded-full transition-all duration-300"
                    style={{ width: `${pmProgressPercent}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Steps List */}
            <div className="flex flex-col gap-3.5">
              {pmRoutineSlots.map((slot) => {
                const product = slot.product;
                const isCompleted = !!completedSteps[slot.id];
                const isCaution =
                  product?.evaluation?.decision === "CAUTION";
                const isReasonExpanded = expandedReason === slot.id;

                if (!product) {
                  // Slot without product
                  return (
                    <div
                      key={slot.id}
                      className="missing-step-card p-4 flex items-center justify-between gap-3 select-none"
                    >
                      <div className="flex items-center gap-3.5 min-w-0">
                        <div className="w-6 h-6 rounded-full border border-dashed border-gray-300 text-gray-400 flex items-center justify-center text-[10px] font-bold shrink-0">
                          {slot.stepNumber}
                        </div>
                        <div className="min-w-0">
                          <span className="text-xs font-semibold text-[#8B8476] block">
                            {slot.stepNumber}. {slot.label}
                          </span>
                          <p className="text-xs text-[#9E9789] truncate">
                            {slot.isMissing
                              ? "Missing from your night routine"
                              : "No treatment slotted (Optional)"}
                          </p>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => slot.isMissing && handleOpenProductPicker(slot.slotKey)}
                        disabled={!slot.isMissing}
                        className={`inline-flex items-center gap-1 text-xs font-bold shrink-0 px-3 py-1.5 rounded-full shadow-xs border border-[#EBE7DF] ${
                          slot.isMissing
                            ? "bg-white/90 text-[#DE688E] hover:bg-white cursor-pointer"
                            : "bg-gray-100 text-gray-400 cursor-not-allowed"
                        }`}
                      >
                        <PlusCircle size={14} /> Add Product
                      </button>
                    </div>
                  );
                }

                return (
                  <div
                    key={slot.id}
                    className={`routine-step-card p-3.5 sm:p-4 flex flex-col gap-2 transition-all ${
                      isCompleted ? "completed" : ""
                    }`}
                  >
                    <div className="flex items-center gap-3.5">
                      {/* Completion Circle Button */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleStepCompletion(slot.id);
                        }}
                        className={`completion-btn ${
                          isCompleted ? "completed" : "uncompleted"
                        }`}
                        title={
                          isCompleted
                            ? "Mark as uncompleted"
                            : "Mark as completed"
                        }
                      >
                        {isCompleted && <Check size={14} strokeWidth={3} />}
                      </button>

                      {/* Product Thumbnail */}
                      <div className="w-13 h-13 sm:w-14 sm:h-14 rounded-xl bg-white border border-gray-100 flex items-center justify-center overflow-hidden shrink-0 p-1">
                        {product.image_url ? (
                          <img
                            src={product.image_url}
                            alt={product.product_name}
                            className="w-full h-full object-contain"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                        ) : (
                          <Package size={22} className="text-[#DE688E]" />
                        )}
                      </div>

                      {/* Product Text Content */}
                      <div className="flex-1 min-w-0">
                        <span className="text-[11px] sm:text-xs font-semibold text-[#7A7382] block">
                          {slot.stepNumber}. {slot.label}
                        </span>
                        <Link
                          href={`/product-analysis?id=${product.product_id}`}
                          className="text-sm sm:text-[14.5px] font-bold text-[#1E293B] hover:text-[#DE688E] transition-colors truncate block mt-0.5"
                          title={product.product_name}
                        >
                          {product.product_name}
                        </Link>

                        {/* Caution status tag if applicable */}
                        {isCaution && (
                          <div className="mt-1 flex items-center gap-1.5">
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                              <AlertTriangle size={10} /> Caution
                            </span>
                            {product.evaluation?.reasons &&
                              product.evaluation.reasons.length > 0 && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setExpandedReason(
                                      isReasonExpanded ? null : slot.id
                                    );
                                  }}
                                  className="text-[10px] font-semibold text-[#8B7D6B] hover:underline cursor-pointer"
                                >
                                  {isReasonExpanded ? "Hide reason" : "View reason"}
                                </button>
                              )}
                          </div>
                        )}
                      </div>

                      {/* Chevron Navigation to Product Details */}
                      <Link
                        href={`/product-analysis?id=${product.product_id}`}
                        className="text-[#94A3B8] hover:text-[#DE688E] transition p-1 shrink-0"
                        title="View ingredient analysis"
                      >
                        <ChevronRight size={20} />
                      </Link>
                    </div>

                    {/* Expandable Personalization Reason */}
                    {isCaution && isReasonExpanded && product.evaluation?.reasons && (
                      <div className="mt-1 p-2.5 rounded-xl bg-amber-50/70 border border-amber-200/80 text-xs text-amber-800 space-y-1">
                        <p className="font-bold text-[11px] text-amber-900">
                          Personalization reasons:
                        </p>
                        <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-800">
                          {product.evaluation.reasons.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      )}

      {/* Floating Analyze Skin Action Button (Desktop only: bottom nav handles mobile) */}
      <Link
        href="/face-analysis"
        className="hidden lg:flex btn-analyze-floating px-5 py-3 items-center gap-2.5 font-bold text-sm"
      >
        <ScanFace size={18} />
        <span>Analyze Skin</span>
      </Link>

      {/* Product Picker Modal */}
      <ProductPicker
        isOpen={isProductPickerOpen}
        onClose={() => setIsProductPickerOpen(false)}
        category={pickerCategory}
        onProductSelected={handleProductSelected}
      />
    </div>
  );
}
