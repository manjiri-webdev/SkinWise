"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Bell,
  User,
  MapPin,
  Sun,
  Droplets,
  Pencil,
  ScanFace,
  Loader2,
  AlertCircle,
  ShieldCheck,
  ChevronRight,
  PlusCircle,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { getLatestAnalysis } from "@/services/personalization";
import "./profile.css";

interface UserProfileData {
  id: string;
  age_range?: string | null;
  gender?: string | null;
  city?: string | null;
  temperature?: number | null;
  humidity?: number | null;
  weather?: string | null;
  sleep?: string | null;
  water_intake?: string | null;
  stress_level?: string | null;
  diet?: string[] | string | null;
  skin_type?: string | null;
  skin_concerns?: string[] | null;
  skin_sensitivity?: string | null;
  skincare_goals?: string[] | null;
}

interface SkinAnalysisRecord {
  id: string;
  user_id: string;
  created_at: string;
  model_name?: string;
  model_version?: string;
  blackheads: number;
  whiteheads: number;
  papules: number;
  pustules?: number;
  nodules?: number;
  dark_spots: number;
  total_lesions: number;
  severity: string;
  severity_score: number;
}

interface ProductHistoryItem {
  id: string;
  user_id: string;
  product_id: number | null;
  product_name: string;
  product_type?: string | null;
  status?: string | null;
  reaction?: string | null;
  notes?: string | null;
  products?: {
    brand?: string | null;
    product_name?: string | null;
    category?: string | null;
    image_url?: string | null;
  } | null;
}

interface EnvironmentRecord {
  city?: string | null;
  temperature?: number | null;
  humidity?: number | null;
  weather?: string | null;
}

export default function ProfilePage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [authEmail, setAuthEmail] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string>("User");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  const [profile, setProfile] = useState<UserProfileData | null>(null);
  const [analysis, setAnalysis] = useState<SkinAnalysisRecord | null>(null);
  const [products, setProducts] = useState<ProductHistoryItem[]>([]);
  const [environment, setEnvironment] = useState<EnvironmentRecord | null>(null);

  useEffect(() => {
    loadAuthenticatedProfile();
  }, []);

  const loadAuthenticatedProfile = async () => {
    try {
      setLoading(true);

      // 1. Get currently authenticated user only
      const {
        data: { user },
        error: authError,
      } = await supabase.auth.getUser();

      if (authError || !user) {
        // Strict requirement: redirect if not authenticated, do not show another user's data
        router.push("/auth/login");
        return;
      }

      const currentUserId = user.id;
      setAuthEmail(user.email || null);

      const fullName =
        user.user_metadata?.full_name || user.user_metadata?.name;
      if (fullName) {
        setDisplayName(fullName.split(" ")[0]);
      } else if (user.email) {
        const prefix = user.email.split("@")[0];
        setDisplayName(prefix.charAt(0).toUpperCase() + prefix.slice(1));
      }

      const photo =
        user.user_metadata?.avatar_url || user.user_metadata?.picture;
      if (photo) {
        setAvatarUrl(photo);
      }

      // 2. Fetch profile strictly for currentUserId
      const { data: profileRes } = await supabase
        .from("user_profiles")
        .select("*")
        .eq("id", currentUserId)
        .maybeSingle();

      if (profileRes) {
        setProfile(profileRes);
      }

      // 3. Fetch latest skin analysis strictly for currentUserId
      let latestAnalysis: SkinAnalysisRecord | null = null;
      const { data: analysisRes } = await supabase
        .from("skin_analyses")
        .select("*")
        .eq("user_id", currentUserId)
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle();

      if (analysisRes) {
        latestAnalysis = analysisRes;
      } else {
        try {
          const apiRes = await getLatestAnalysis();
          if (apiRes && apiRes.success && apiRes.data) {
            latestAnalysis = apiRes.data as unknown as SkinAnalysisRecord;
          }
        } catch (apiErr) {
          console.warn("Could not fetch latest analysis via API:", apiErr);
        }
      }

      if (latestAnalysis) {
        setAnalysis(latestAnalysis);
      }

      // 4. Fetch product history strictly for currentUserId with resolved products
      const { data: productHistoryRes } = await supabase
        .from("user_product_history")
        .select("*, products(*)")
        .eq("user_id", currentUserId)
        .order("created_at", { ascending: false });

      if (productHistoryRes) {
        // Filter unique by product name or take current items
        const currentOrAll = (productHistoryRes as any[]).filter(
          (p) => p.status === "current" || !p.status
        );
        setProducts(currentOrAll.length > 0 ? currentOrAll : productHistoryRes);
      }

      // 5. Fetch latest environment record strictly for currentUserId
      const { data: envRes } = await supabase
        .from("user_environment_history")
        .select("*")
        .eq("user_id", currentUserId)
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle();

      if (envRes) {
        setEnvironment(envRes);
      }
    } catch (err) {
      console.error("Failed to load user profile:", err);
    } finally {
      setLoading(false);
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 17) return "Good Afternoon";
    return "Good Evening";
  };

  const formatScanDate = (isoString?: string) => {
    if (!isoString) return "";
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

  const formatReaction = (reaction?: string | null) => {
    if (!reaction || reaction.toLowerCase() === "none") {
      return { label: "No reaction", style: "bg-[#EAF5EE] text-[#48805B]" };
    }
    if (reaction.toLowerCase() === "mild") {
      return { label: "Mild reaction", style: "bg-[#FEF3C7] text-[#D97706]" };
    }
    if (reaction.toLowerCase() === "moderate" || reaction.toLowerCase() === "breakout") {
      return { label: "Moderate reaction", style: "bg-[#FFEDD5] text-[#C2410C]" };
    }
    if (reaction.toLowerCase() === "severe") {
      return { label: "Severe reaction", style: "bg-[#FEE2E2] text-[#DC2626]" };
    }
    if (reaction.toLowerCase() === "not_sure") {
      return { label: "Not sure", style: "bg-gray-100 text-gray-700" };
    }
    return { label: reaction, style: "bg-gray-100 text-gray-700" };
  };

  const formatDiet = (dietValue?: any) => {
    if (!dietValue) return "Not recorded";
    if (Array.isArray(dietValue)) {
      return dietValue.length > 0 ? dietValue.join(", ") : "Not recorded";
    }
    if (typeof dietValue === "string") {
      if (dietValue === "[]" || dietValue.trim() === "") return "Not recorded";
      try {
        const parsed = JSON.parse(dietValue);
        if (Array.isArray(parsed)) {
          return parsed.length > 0 ? parsed.join(", ") : "Not recorded";
        }
      } catch {
        return dietValue;
      }
    }
    return String(dietValue);
  };

  // Derive deterministic Skin Health metrics & percentage from skin analysis data
  const getSkinHealthMetrics = (record: SkinAnalysisRecord) => {
    const total = record.total_lesions ?? record.severity_score ?? 0;
    const rawSeverity = (record.severity || "").toLowerCase();

    // Clear case: 0 lesions or "Clear" severity -> 100% healthy, label "Clear"
    if (total === 0 || rawSeverity === "clear") {
      return {
        score: 100,
        label: "Clear",
        color: "#48805B",
        offset: 0, // 264 - (264 * 100) / 100 = 0 (100% full circle)
      };
    }

    // Mild severity: 1 - 10 lesions -> 95% down to 80%
    if (total <= 10 || rawSeverity === "mild") {
      const score = Math.max(80, Math.round(100 - total * 2));
      return {
        score,
        label: "Mild Severity",
        color: "#48805B",
        offset: 264 - (264 * score) / 100,
      };
    }

    // Moderate severity: 11 - 30 lesions -> 79% down to 50%
    if (total <= 30 || rawSeverity === "moderate") {
      const score = Math.max(50, Math.round(80 - (total - 10) * 1.5));
      return {
        score,
        label: "Moderate Severity",
        color: "#D97706",
        offset: 264 - (264 * score) / 100,
      };
    }

    // Severe severity: > 30 lesions -> maps down to 10%
    const score = Math.max(10, Math.round(50 - (total - 30) * 1.5));
    return {
      score,
      label: "Severe Severity",
      color: "#DC2626",
      offset: 264 - (264 * score) / 100,
    };
  };

  // Environment metrics
  const displayCity =
    profile?.city || environment?.city || "Location not set";
  const displayTemp =
    environment?.temperature !== undefined && environment?.temperature !== null
      ? `${environment.temperature}°C`
      : profile?.temperature !== undefined && profile?.temperature !== null
      ? `${profile.temperature}°C`
      : null;
  const displayHumidity =
    environment?.humidity !== undefined && environment?.humidity !== null
      ? `${environment.humidity}%`
      : profile?.humidity !== undefined && profile?.humidity !== null
      ? `${profile.humidity}%`
      : null;

  return (
    <div className="w-full min-h-screen p-4 sm:p-6 lg:p-10 flex flex-col gap-6 lg:gap-8 max-w-[1400px] mx-auto">
      {/* Profile Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4 sm:gap-5">
          {/* Avatar */}
          {avatarUrl ? (
            <img
              src={avatarUrl}
              alt={displayName}
              className="w-16 h-16 sm:w-18 sm:h-18 rounded-full object-cover border-2 border-pink-100 shadow-sm"
            />
          ) : (
            <div className="w-16 h-16 sm:w-18 sm:h-18 rounded-full bg-white shadow-sm border border-gray-100 text-[#A85175] flex items-center justify-center shrink-0">
              <User size={34} strokeWidth={1.8} />
            </div>
          )}

          <div>
            <h1
              className="text-2xl sm:text-3xl font-bold text-[#141414] tracking-tight"
              style={{ fontFamily: "Georgia, serif" }}
            >
              {getGreeting()}, {displayName}
            </h1>
            <p className="text-xs sm:text-sm text-[#7A7382] mt-0.5">
              your personal skincare profile &amp; journey
            </p>

            {/* User Meta Chips */}
            <div className="flex flex-wrap items-center gap-3 sm:gap-4 mt-2 text-xs font-semibold text-[#6B6375]">
              <span className="flex items-center gap-1.5 text-[#DE688E]">
                <User size={14} />
                <span>{profile?.age_range || "Age not recorded"}</span>
              </span>

              <span className="flex items-center gap-1.5">
                <MapPin size={14} className="text-[#A85175]" />
                <span>{displayCity}</span>
              </span>

              {displayTemp && (
                <span className="flex items-center gap-1.5">
                  <Sun size={14} className="text-[#DE688E]" />
                  <span>{displayTemp}</span>
                </span>
              )}

              {displayHumidity && (
                <span className="flex items-center gap-1.5">
                  <Droplets size={14} className="text-[#A85175]" />
                  <span>{displayHumidity}</span>
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 self-start md:self-center">
          <Link
            href="/questionnaire?mode=edit"
            className="btn btn-rose py-2.5 px-5 font-bold text-xs sm:text-sm rounded-full flex items-center gap-2 shadow-[0_4px_16px_rgba(222,104,142,0.3)] cursor-pointer"
          >
            <Pencil size={15} />
            <span>Edit Profile</span>
          </Link>

          <button
            type="button"
            className="w-11 h-11 rounded-full bg-white shadow-sm border border-gray-100 flex items-center justify-center text-[#2D2D2D] hover:bg-gray-50 transition cursor-pointer"
            title="Notifications"
          >
            <Bell size={19} />
          </button>
        </div>
      </header>

      {/* Loading State */}
      {loading ? (
        <div className="w-full py-20 flex flex-col items-center justify-center text-center">
          <Loader2 className="animate-spin text-[#DE688E] mb-3" size={36} />
          <p className="text-sm font-semibold text-[#6B6375]">
            Loading your profile details...
          </p>
        </div>
      ) : (
        <>
          {/* Upper Section: 2 Columns */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-stretch">
            {/* 1. My Skin Identity */}
            <div className="profile-card lg:col-span-6 p-4 sm:p-6 lg:p-7 flex flex-col justify-between">
              <div>
                <h2 className="text-lg sm:text-xl font-bold text-[#141414] mb-4">
                  My Skin Identity
                </h2>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 sm:gap-4">
                  {/* Skin Type (Mint) */}
                  <div className="pill-mint p-4 flex flex-col justify-center">
                    <span className="text-xs font-semibold text-[#5D8B6E]">
                      Skin Type
                    </span>
                    <p className="text-sm sm:text-base font-bold text-[#141414] mt-0.5">
                      {profile?.skin_type || "Not recorded"}
                    </p>
                  </div>

                  {/* Sensitivity (Lavender) */}
                  <div className="pill-lavender p-4 flex flex-col justify-center">
                    <span className="text-xs font-semibold text-[#7864A4]">
                      Sensitivity
                    </span>
                    <p className="text-sm sm:text-base font-bold text-[#141414] mt-0.5">
                      {profile?.skin_sensitivity || "Not recorded"}
                    </p>
                  </div>

                  {/* Skin Concerns (Blush Pink) */}
                  <div className="pill-blush p-4 flex flex-col justify-center">
                    <span className="text-xs font-semibold text-[#B95D79]">
                      Skin Concerns
                    </span>
                    <p className="text-sm sm:text-base font-bold text-[#141414] mt-0.5 line-clamp-2">
                      {Array.isArray(profile?.skin_concerns) && profile.skin_concerns.length > 0
                        ? profile.skin_concerns.join(", ")
                        : "No concerns recorded"}
                    </p>
                  </div>

                  {/* Primary Goals (Apricot / Peach) */}
                  <div className="pill-peach p-4 flex flex-col justify-center">
                    <span className="text-xs font-semibold text-[#B5813E]">
                      Primary Goals
                    </span>
                    <p className="text-sm sm:text-base font-bold text-[#141414] mt-0.5 line-clamp-2">
                      {Array.isArray(profile?.skincare_goals) && profile.skincare_goals.length > 0
                        ? profile.skincare_goals.join(", ")
                        : "No goals recorded"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-[#7A7382]">
                <span>Self-reported in questionnaire</span>
                <Link
                  href="/questionnaire?mode=edit"
                  className="font-bold text-[#DE688E] hover:underline"
                >
                  Update →
                </Link>
              </div>
            </div>

            {/* 2. AI Skin Health Diagnostic */}
            <div className="profile-card lg:col-span-6 p-4 sm:p-6 lg:p-7 flex flex-col justify-between">
              <div>
                <h2 className="text-lg sm:text-xl font-bold text-[#141414]">
                  AI Skin Health Diagnostic
                </h2>
                <p className="text-xs sm:text-sm text-[#7A7382] mt-0.5">
                  {analysis
                    ? `Based on your latest face scan (${formatScanDate(analysis.created_at)})`
                    : "No face scan recorded yet"}
                </p>

                {analysis ? (
                  <div className="mt-5 grid grid-cols-1 sm:grid-cols-12 gap-5 items-center">
                    {/* Gauge Circle Column */}
                    {(() => {
                      const health = getSkinHealthMetrics(analysis);
                      return (
                        <div className="sm:col-span-5 flex flex-col items-center justify-center text-center">
                          <div className="relative w-32 h-32 flex items-center justify-center">
                            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                              {/* Background Track */}
                              <circle
                                cx="50"
                                cy="50"
                                r="42"
                                fill="transparent"
                                stroke="#EFECE6"
                                strokeWidth="7"
                              />
                              {/* Progress Arc: Visual indicator of skin health derived from latest scan */}
                              <circle
                                cx="50"
                                cy="50"
                                r="42"
                                fill="transparent"
                                stroke={health.color}
                                strokeWidth="7"
                                strokeDasharray="264"
                                strokeDashoffset={health.offset}
                                strokeLinecap="round"
                                className="transition-all duration-700"
                              />
                            </svg>

                            {/* Centered Skin Health Metric */}
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                              <span className="text-2xl font-bold text-[#141414] leading-none">
                                {health.score}%
                              </span>
                              <span className="text-[10px] font-semibold text-[#7A7382] mt-0.5">
                                Skin Health
                              </span>
                            </div>
                          </div>

                          {/* Severity Level Pill */}
                          <span
                            className={`inline-block px-3 py-1 rounded-full text-xs font-bold mt-2 ${
                              health.label === "Clear" || health.label === "Mild Severity"
                                ? "bg-[#EAF5EE] text-[#48805B]"
                                : health.label === "Moderate Severity"
                                ? "bg-[#FEF3C7] text-[#D97706]"
                                : "bg-[#FEE2E2] text-[#DC2626]"
                            }`}
                          >
                            {health.label}
                          </span>
                        </div>
                      );
                    })()}

                    {/* Detected Lesions Table */}
                    <div className="sm:col-span-7 bg-[#FAF8F5] rounded-2xl p-4 border border-gray-100">
                      <h3
                        className="text-sm font-bold text-[#141414] mb-2.5"
                        style={{ fontFamily: "Georgia, serif" }}
                      >
                        Detected Lesions
                      </h3>

                      <div className="space-y-1.5 text-xs">
                        <div className="flex justify-between py-0.5 text-[#55505C]">
                          <span>Dark Spots</span>
                          <span className="font-bold text-[#141414]">
                            {analysis.dark_spots}
                          </span>
                        </div>

                        <div className="flex justify-between py-0.5 text-[#55505C]">
                          <span>Papules</span>
                          <span className="font-bold text-[#141414]">
                            {analysis.papules}
                          </span>
                        </div>

                        <div className="flex justify-between py-0.5 text-[#55505C]">
                          <span>Whiteheads</span>
                          <span className="font-bold text-[#141414]">
                            {analysis.whiteheads}
                          </span>
                        </div>

                        <div className="flex justify-between py-0.5 text-[#55505C]">
                          <span>Blackheads</span>
                          <span className="font-bold text-[#141414]">
                            {analysis.blackheads}
                          </span>
                        </div>

                        <div className="pt-1.5 mt-1 border-t border-gray-200/80 flex justify-between font-bold text-[#141414]">
                          <span>Total</span>
                          <span>{analysis.total_lesions}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="mt-6 rounded-2xl border-2 border-dashed border-gray-200/80 bg-gray-50/50 p-6 flex flex-col items-center justify-center text-center min-h-[140px]">
                    <ScanFace className="text-[#DE688E] mb-2" size={28} />
                    <p className="text-sm font-bold text-[#141414]">
                      No Face Analysis Recorded Yet
                    </p>
                    <p className="text-xs text-[#7A7382] mt-0.5 max-w-xs">
                      Complete an AI skin scan to generate clinical diagnostics for acne, spots, and texture.
                    </p>
                    <Link
                      href="/face-analysis"
                      className="mt-3 text-xs font-bold text-[#DE688E] hover:underline inline-flex items-center gap-1"
                    >
                      Start Scan →
                    </Link>
                  </div>
                )}
              </div>

              {analysis && (
                <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-[#7A7382]">
                  <span>Model: {analysis.model_name || "YOLO"} {analysis.model_version || "v1"}</span>
                  <Link
                    href="/face-analysis"
                    className="font-bold text-[#DE688E] hover:underline"
                  >
                    New Scan →
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Lower Section: 2 Columns */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-stretch">
            {/* 3. My Current Products */}
            <div className="profile-card lg:col-span-7 p-4 sm:p-6 lg:p-7 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between gap-4 mb-1">
                  <h2 className="text-lg sm:text-xl font-bold text-[#141414]">
                    My Current Products
                  </h2>
                  <Link
                    href="/routine"
                    className="text-xs sm:text-sm font-bold text-[#DE688E] hover:underline flex items-center gap-1"
                  >
                    View all →
                  </Link>
                </div>
                <p className="text-xs sm:text-sm text-[#7A7382] mb-5">
                  Products you are currently using and your skin&apos;s reaction
                </p>

                {products.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {products.slice(0, 4).map((item) => {
                      const brand = item.products?.brand || "";
                      const productName = item.products?.product_name || item.product_name;
                      const productType = item.products?.category || item.product_type || "Skincare";
                      const imageUrl = item.products?.image_url;
                      const reactionInfo = formatReaction(item.reaction);
                      const userNotes = item.notes?.trim();

                      return (
                        <div
                          key={item.id}
                          className="bg-white rounded-2xl p-4 border border-gray-100 shadow-[0_3px_12px_rgba(0,0,0,0.03)] flex flex-col justify-between"
                        >
                          <div>
                            <h3 className="text-xs sm:text-sm font-bold text-[#141414] leading-snug line-clamp-2">
                              {brand ? `${brand} ` : ""}
                              {productName}
                            </h3>

                            <div className="flex items-start gap-3 mt-3">
                              {/* Product Thumbnail */}
                              <div className="w-12 h-16 bg-gray-50 rounded-xl overflow-hidden shrink-0 flex items-center justify-center p-1 border border-gray-100">
                                {imageUrl ? (
                                  <img
                                    src={imageUrl}
                                    alt={productName}
                                    className="w-full h-full object-contain"
                                  />
                                ) : (
                                  <div className="text-[9px] text-[#A85175] font-semibold text-center leading-tight">
                                    {productType}
                                  </div>
                                )}
                              </div>

                              <div className="flex-1 min-w-0">
                                <span className="text-[11px] text-[#7A7382] font-medium block">
                                  {productType}
                                </span>

                                <span
                                  className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full mt-1.5 ${reactionInfo.style}`}
                                >
                                  {reactionInfo.label}
                                </span>

                                {userNotes && (
                                  <p className="text-[10px] text-[#6B6375] mt-1.5 leading-snug line-clamp-2 italic">
                                    &ldquo;{userNotes}&rdquo;
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="rounded-2xl border-2 border-dashed border-gray-200/80 bg-gray-50/50 p-6 flex flex-col items-center justify-center text-center min-h-[140px]">
                    <p className="text-sm font-bold text-[#141414]">
                      No Products Added Yet
                    </p>
                    <p className="text-xs text-[#7A7382] mt-0.5 max-w-xs">
                      Add the skincare products you currently use to evaluate ingredient compatibility.
                    </p>
                    <Link
                      href="/questionnaire?mode=edit"
                      className="mt-3 text-xs font-bold text-[#DE688E] hover:underline inline-flex items-center gap-1"
                    >
                      <PlusCircle size={14} /> Add Products
                    </Link>
                  </div>
                )}
              </div>

              {products.length > 0 && (
                <div className="mt-4 pt-3 border-t border-gray-100 flex justify-end">
                  <Link
                    href="/routine"
                    className="text-xs font-semibold text-[#DE688E] hover:underline inline-flex items-center gap-1"
                  >
                    Manage routine products <ChevronRight size={14} />
                  </Link>
                </div>
              )}
            </div>

            {/* 4. Lifestyle & Habits */}
            <div className="profile-card lg:col-span-5 p-4 sm:p-6 lg:p-7 flex flex-col justify-between">
              <div>
                <h2 className="text-lg sm:text-xl font-bold text-[#141414] mb-4">
                  Lifestyle &amp; Habits
                </h2>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 sm:gap-4">
                  {/* Sleep (Peach) */}
                  <div className="pill-peach p-4 flex flex-col justify-center">
                    <span className="text-xs font-semibold text-[#B5813E]">
                      Sleep
                    </span>
                    <p className="text-sm sm:text-base font-bold text-[#141414] mt-0.5">
                      {profile?.sleep || "Not recorded"}
                    </p>
                  </div>

                  {/* Water Intake (Lavender) */}
                  <div className="pill-lavender p-4 flex flex-col justify-center">
                    <span className="text-xs font-semibold text-[#7864A4]">
                      Water Intake
                    </span>
                    <p className="text-sm sm:text-base font-bold text-[#141414] mt-0.5">
                      {profile?.water_intake || "Not recorded"}
                    </p>
                  </div>

                  {/* Stress Level (Blush Pink) */}
                  <div className="pill-blush p-4 flex flex-col justify-center">
                    <span className="text-xs font-semibold text-[#B95D79]">
                      Stress Level
                    </span>
                    <p className="text-sm sm:text-base font-bold text-[#141414] mt-0.5">
                      {profile?.stress_level || "Not recorded"}
                    </p>
                  </div>

                  {/* Diet (Mint) */}
                  <div className="pill-mint p-4 flex flex-col justify-center">
                    <span className="text-xs font-semibold text-[#5D8B6E]">
                      Diet
                    </span>
                    <p className="text-sm sm:text-base font-bold text-[#141414] mt-0.5 line-clamp-2">
                      {formatDiet(profile?.diet)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-[#7A7382]">
                <span>Affects barrier recovery and hydration</span>
                <Link
                  href="/questionnaire?mode=edit"
                  className="font-bold text-[#DE688E] hover:underline"
                >
                  Edit Habits →
                </Link>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
