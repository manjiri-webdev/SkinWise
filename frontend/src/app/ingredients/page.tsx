"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Bell,
  User,
  ArrowRight,
  ChevronRight,
  Loader2,
  Package,
  ScanFace,
  Search,
  Check,
  Sparkles,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { discoverProducts, extractProductDetails, analyzeProduct } from "@/services/productDiscovery";
import type { ProductOption } from "@/types/product";
import "./ingredients.css";

interface RecentAnalysisItem {
  id?: string | number;
  brand?: string | null;
  product_name: string;
  image_url?: string | null;
  category?: string | null;
  analyzed_at: string;
}

export default function IngredientsPage() {
  const router = useRouter();

  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string>("there");
  const [productName, setProductName] = useState("");
  const [brand, setBrand] = useState("");

  const [dbResults, setDbResults] = useState<any[]>([]);
  const [discoveryOptions, setDiscoveryOptions] = useState<ProductOption[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<ProductOption | null>(null);


  const [isLoading, setIsLoading] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [recentAnalyses, setRecentAnalyses] = useState<RecentAnalysisItem[]>([]);

  useEffect(() => {
    async function loadUserAndRecent() {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (user) {
        setCurrentUserId(user.id);
        const name =
          user.user_metadata?.full_name || user.user_metadata?.name;
        if (name) {
          setDisplayName(name.split(" ")[0]);
        } else if (user.email) {
          const prefix = user.email.split("@")[0];
          setDisplayName(prefix.charAt(0).toUpperCase() + prefix.slice(1));
        }

        // Load client-side recent analysis history strictly scoped to current user
        try {
          const storageKey = `skinwise_recent_analyses_${user.id}`;
          const saved = localStorage.getItem(storageKey);
          if (saved) {
            setRecentAnalyses(JSON.parse(saved));
          }
        } catch (e) {
          console.error("Failed to load recent analyses from localStorage:", e);
        }
      }
    }

    loadUserAndRecent();
  }, []);

  const saveRecentAnalysis = (item: RecentAnalysisItem) => {
    if (!currentUserId) return;
    try {
      const storageKey = `skinwise_recent_analyses_${currentUserId}`;
      const existing = JSON.parse(localStorage.getItem(storageKey) || "[]");
      const filtered = existing.filter(
        (p: RecentAnalysisItem) =>
          p.product_name.toLowerCase() !== item.product_name.toLowerCase()
      );
      const updated = [item, ...filtered].slice(0, 8);
      localStorage.setItem(storageKey, JSON.stringify(updated));
      setRecentAnalyses(updated);
    } catch (e) {
      console.error("Failed to save recent analysis:", e);
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 17) return "Good Afternoon";
    return "Good Evening";
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = productName.trim();
    if (!trimmedName) {
      setError("Please enter a product name to search.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setDbResults([]);
    setDiscoveryOptions([]);
    setSelectedProduct(null);
    setHasSearched(true);

    try {
      // Step 1: Check existing products in Supabase catalog
      let query = supabase.from("products").select("*");
      if (brand.trim()) {
        query = query.ilike("brand", `%${brand.trim()}%`);
      }
      query = query.ilike("product_name", `%${trimmedName}%`);

      const { data: dbProducts, error: dbError } = await query.limit(6);

      if (!dbError && dbProducts && dbProducts.length > 0) {
        setDbResults(dbProducts);
        setIsLoading(false);
        return;
      }

      // Step 2: Fallback to existing discovery pipeline on ingredient-service
      try {
        const response = await discoverProducts({
          product_name: trimmedName,
          ...(brand.trim() ? { brand: brand.trim() } : {}),
        });

        if (response && response.options) {
          setDiscoveryOptions(response.options);
        }
      } catch (discErr) {
        console.warn("Product discovery fallback error:", discErr);
      }
    } catch (err: any) {
      console.error("Search error:", err);
      setError(err.message || "Failed to search for products. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectDbProduct = (prod: any) => {
    saveRecentAnalysis({
      id: prod.product_id,
      brand: prod.brand,
      product_name: prod.product_name,
      image_url: prod.image_url,
      category: prod.category,
      analyzed_at: new Date().toISOString(),
    });
    router.push(`/product-analysis?id=${prod.product_id}`);
  };

  const handleProductSelectDiscovery = async (option: ProductOption) => {
    setSelectedProduct(option);
    setIsExtracting(true);
    setError(null);

    try {
      // Use analyzeProduct to ensure product and ingredients are extracted and inserted into catalog
      const response = await analyzeProduct({
        product_name: option.product_name,
        brand: option.brand,
        source_url: option.source_url,
      });

      if (response.success && response.product) {
        if (response.product.product_id) {
          // Save to recent analysis with the actual product_id
          saveRecentAnalysis({
            id: response.product.product_id,
            brand: response.product.brand,
            product_name: response.product.product_name,
            image_url: response.product.image_url,
            category: response.product.category || "Skincare",
            analyzed_at: new Date().toISOString(),
          });

          // Navigate using the actual product_id from the database
          router.push(`/product-analysis?id=${response.product.product_id}`);
          return;
        } else if (response.product.product_name) {
          // If product_id was not immediately returned, navigate with name and brand query params
          const brandParam = response.product.brand || option.brand || "";
          const queryParams = new URLSearchParams({
            name: response.product.product_name,
            ...(brandParam ? { brand: brandParam } : {}),
          });
          router.push(`/product-analysis?${queryParams.toString()}`);
          return;
        }
      }

      // Product analysis failed - show specific error or warning
      const errorMsg =
        response.error ||
        response.warning ||
        "Failed to analyze product. The product could not be found or inserted into the catalog.";
      setError(errorMsg);
      console.error("Product analysis failed:", response);
    } catch (extractionError: any) {
      const errorMsg = extractionError.message || "Failed to analyze product. Please try again.";
      setError(errorMsg);
      console.error("Product analysis error:", extractionError);
    } finally {
      setIsExtracting(false);
    }
  };

  return (
    <div className="w-full min-h-screen p-4 sm:p-6 lg:p-10 flex flex-col gap-6 lg:gap-8 max-w-[1400px] mx-auto">
      {/* Page Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-sm sm:text-base font-semibold text-[#6B6375]">
            {getGreeting()}, {displayName}
          </p>
          <h1
            className="text-3xl sm:text-4xl font-bold text-[#141414] tracking-tight mt-0.5"
            style={{ fontFamily: "Georgia, serif" }}
          >
            Ingredients
          </h1>
          <p className="text-xs sm:text-sm text-[#7A7382] mt-1">
            Understand what&apos;s inside your skincare and how it works for your skin
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            className="w-11 h-11 rounded-full bg-white shadow-sm border border-gray-100 flex items-center justify-center text-[#2D2D2D] hover:bg-gray-50 transition cursor-pointer"
            title="Notifications"
          >
            <Bell size={20} />
          </button>
          <Link
            href="/profile"
            className="w-11 h-11 rounded-full bg-white shadow-sm border border-gray-100 flex items-center justify-center text-[#2D2D2D] hover:bg-gray-50 transition"
            title="User Profile"
          >
            <User size={21} />
          </Link>
        </div>
      </header>

      {/* Main Grid: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
        {/* Left Column: Analyze your Product Form */}
        <div className="ingredients-glass-card lg:col-span-7 p-4 sm:p-6 lg:p-8">
          <h2
            className="text-xl sm:text-2xl font-bold text-[#141414]"
            style={{ fontFamily: "Georgia, serif" }}
          >
            Analyze your Product
          </h2>
          <p className="text-xs sm:text-sm text-[#6B6375] mt-1.5 mb-6 max-w-lg leading-relaxed">
            Enter the product name (and brand, if available) and we&apos;ll check the ingredients and their safety for your skin.
          </p>

          <form onSubmit={handleSearch} className="space-y-4 max-w-xl">
            <div>
              <label
                htmlFor="productName"
                className="block text-xs sm:text-sm font-bold text-[#252121] mb-1.5"
              >
                Product name
              </label>
              <input
                id="productName"
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="e.g. 10% Niacinamide Serum"
                disabled={isLoading}
                className="w-full px-4 py-3 rounded-2xl bg-white/95 border border-white text-sm text-[#141414] placeholder:text-[#9A9393] shadow-[0_2px_8px_rgba(0,0,0,0.03)] focus:outline-none focus:ring-2 focus:ring-pink-300 focus:bg-white transition"
              />
            </div>

            <div>
              <label
                htmlFor="brand"
                className="block text-xs sm:text-sm font-bold text-[#252121] mb-1.5"
              >
                Brand (optional)
              </label>
              <input
                id="brand"
                type="text"
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                placeholder="e.g. Minimalist"
                disabled={isLoading}
                className="w-full px-4 py-3 rounded-2xl bg-white/95 border border-white text-sm text-[#141414] placeholder:text-[#9A9393] shadow-[0_2px_8px_rgba(0,0,0,0.03)] focus:outline-none focus:ring-2 focus:ring-pink-300 focus:bg-white transition"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="btn btn-rose py-3 px-8 text-sm font-bold rounded-full shadow-[0_8px_24px_rgba(222,104,142,0.35)] flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <span>Analyze</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Search Feedback & Results */}
          {error && (
            <p className="mt-4 text-xs text-red-600 bg-red-50 p-3 rounded-xl border border-red-200">
              {error}
            </p>
          )}

          {hasSearched && !isLoading && !error && dbResults.length === 0 && discoveryOptions.length === 0 && (
            <div className="mt-6 p-4 rounded-2xl bg-white/70 border border-white text-center">
              <p className="text-xs sm:text-sm text-[#6B6375]">
                No matching products found in database. Try adjusting the product name or brand.
              </p>
            </div>
          )}

          {/* Existing Database Products Found */}
          {dbResults.length > 0 && (
            <div className="mt-6 pt-5 border-t border-purple-100/60">
              <h3 className="text-xs sm:text-sm font-bold text-[#141414] mb-3">
                Matching Products in SkinWise Catalog
              </h3>
              <div className="space-y-2.5">
                {dbResults.map((prod) => (
                  <button
                    key={prod.product_id}
                    type="button"
                    onClick={() => handleSelectDbProduct(prod)}
                    className="w-full text-left bg-white rounded-2xl p-3.5 border border-white shadow-2xs hover:shadow-md hover:border-pink-200 transition flex items-center justify-between gap-3 cursor-pointer group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-12 h-14 bg-gray-50 rounded-xl overflow-hidden shrink-0 flex items-center justify-center p-1 border border-gray-100">
                        {prod.image_url ? (
                          <img
                            src={prod.image_url}
                            alt={prod.product_name}
                            className="w-full h-full object-contain"
                          />
                        ) : (
                          <Package size={20} className="text-[#A85175]" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <span className="text-[11px] font-bold text-[#DE688E] uppercase tracking-wider block">
                          {prod.brand || "SkinWise"}
                        </span>
                        <p className="text-xs sm:text-sm font-bold text-[#141414] truncate">
                          {prod.product_name}
                        </p>
                        <span className="text-[11px] text-[#7A7382]">
                          {prod.category || "Skincare"}
                        </span>
                      </div>
                    </div>
                    <span className="text-xs font-bold text-[#DE688E] group-hover:translate-x-1 transition flex items-center gap-1 shrink-0">
                      View Details <ChevronRight size={16} />
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Discovery Fallback Options */}
          {dbResults.length === 0 && discoveryOptions.length > 0 && (
            <div className="mt-6 pt-5 border-t border-purple-100/60">
              <h3 className="text-xs sm:text-sm font-bold text-[#141414] mb-3">
                Web Discovered Products
              </h3>
              <div className="space-y-2.5">
                {discoveryOptions.map((opt) => (
                  <button
                    key={opt.source_url}
                    type="button"
                    onClick={() => handleProductSelectDiscovery(opt)}
                    className="w-full text-left bg-white rounded-2xl p-3.5 border border-white shadow-2xs hover:shadow-md transition flex items-center justify-between gap-3 cursor-pointer"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-12 h-14 bg-gray-50 rounded-xl overflow-hidden shrink-0 flex items-center justify-center p-1 border border-gray-100">
                        {opt.image_url ? (
                          <img
                            src={opt.image_url}
                            alt={opt.product_name}
                            className="w-full h-full object-contain"
                          />
                        ) : (
                          <Package size={20} className="text-[#A85175]" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <span className="text-[11px] font-bold text-[#DE688E] block">
                          {opt.brand}
                        </span>
                        <p className="text-xs sm:text-sm font-bold text-[#141414] truncate">
                          {opt.product_name}
                        </p>
                        <span className="text-[11px] text-[#7A7382]">
                          {opt.source_name}
                        </span>
                      </div>
                    </div>
                    <span className="text-xs font-bold text-[#DE688E]">
                      Select →
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Extraction in progress */}
          {isExtracting && (
            <div className="mt-4 p-4 bg-white/80 rounded-2xl text-center flex items-center justify-center gap-2 text-xs font-semibold text-[#6B6375]">
              <Loader2 size={16} className="animate-spin text-[#DE688E]" />
              <span>Analyzing product and ingredients...</span>
            </div>
          )}
        </div>

        {/* Right Column: Recently analyzed products */}
        <div className="ingredients-glass-card lg:col-span-5 p-4 sm:p-6 lg:p-8">
          <div className="flex items-center justify-between gap-2 mb-4">
            <h2
              className="text-lg sm:text-xl font-bold text-[#141414]"
              style={{ fontFamily: "Georgia, serif" }}
            >
              Recently analyzed products
            </h2>
            <Link
              href="/routine"
              className="text-xs font-bold text-[#DE688E] hover:underline flex items-center gap-1 shrink-0"
            >
              View Products →
            </Link>
          </div>

          {/* Scoped Client-Side History or Honest Empty State */}
          {recentAnalyses.length > 0 ? (
            <div className="space-y-3">
              {recentAnalyses.map((item, idx) => (
                <div
                  key={`${item.product_name}-${idx}`}
                  onClick={() => {
                    if (item.id) {
                      router.push(`/product-analysis?id=${item.id}`);
                    } else {
                      router.push(
                        `/product-analysis?name=${encodeURIComponent(
                          item.product_name
                        )}&brand=${encodeURIComponent(item.brand || "")}`
                      );
                    }
                  }}
                  className="recent-product-item p-3.5 flex items-center justify-between gap-3 cursor-pointer group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-12 h-14 bg-gray-50 rounded-xl overflow-hidden shrink-0 flex items-center justify-center p-1 border border-gray-100">
                      {item.image_url ? (
                        <img
                          src={item.image_url}
                          alt={item.product_name}
                          className="w-full h-full object-contain"
                        />
                      ) : (
                        <Package size={20} className="text-[#A85175]" />
                      )}
                    </div>

                    <div className="min-w-0">
                      <span className="text-[10px] font-bold text-[#DE688E] uppercase tracking-wider block truncate">
                        {item.brand || "Skincare"}
                      </span>
                      <p className="text-xs sm:text-sm font-bold text-[#141414] truncate">
                        {item.product_name}
                      </p>
                      <span className="inline-block text-[9px] font-bold px-2 py-0.2 rounded-full mt-1 bg-[#EAF5EE] text-[#48805B]">
                        Analyzed
                      </span>
                    </div>
                  </div>

                  <ChevronRight
                    size={18}
                    className="text-gray-400 group-hover:text-[#DE688E] group-hover:translate-x-1 transition shrink-0"
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border-2 border-dashed border-purple-200/60 bg-white/50 p-6 flex flex-col items-center justify-center text-center min-h-[220px]">
              <div className="w-10 h-10 rounded-full bg-[#F3EEFA] text-[#855CA3] flex items-center justify-center mb-2.5">
                <Search size={20} />
              </div>
              <p className="text-sm font-bold text-[#141414]">
                No recently analyzed products
              </p>
              <p className="text-xs text-[#7A7382] mt-1 max-w-xs leading-relaxed">
                Products you search and analyze will appear here for quick reference during your session.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
