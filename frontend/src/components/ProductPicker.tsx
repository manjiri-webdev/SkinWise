"use client";

import { useState, useEffect } from "react";
import { X, Package, AlertTriangle, ShieldCheck, Plus } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { AI_BACKEND_URL, joinApiUrl } from "@/lib/api";

interface ProductEvaluation {
  decision: "KEEP" | "CAUTION" | "REJECT";
  confidence: "high" | "medium" | "low";
  fit_score?: number;
  reason_codes?: string[];
  reasons?: string[];
  mitigations?: string[];
}

interface Product {
  product_id: number;
  brand?: string | null;
  product_name: string;
  category?: string | null;
  product_type?: string | null;
  image_url?: string | null;
  evaluation?: ProductEvaluation;
}

interface ProductPickerProps {
  isOpen: boolean;
  onClose: () => void;
  category: string;
  onProductSelected: (product: Product) => void;
}

export default function ProductPicker({
  isOpen,
  onClose,
  category,
  onProductSelected,
}: ProductPickerProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addingProductId, setAddingProductId] = useState<number | null>(null);

  useEffect(() => {
    if (isOpen && category) {
      loadProducts();
    }
  }, [isOpen, category]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      setError(null);

      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(
        joinApiUrl(AI_BACKEND_URL, `/personalization/products/${category}`),
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Failed to load products");
      }

      const data = await response.json();
      if (data.success) {
        setProducts(data.products || []);
      } else {
        throw new Error(data.error || "Failed to load products");
      }
    } catch (err: any) {
      setError(err.message || "Failed to load products");
    } finally {
      setLoading(false);
    }
  };

  const handleAddProduct = async (product: Product) => {
    try {
      setAddingProductId(product.product_id);

      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(
        joinApiUrl(AI_BACKEND_URL, "/personalization/add-product"),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            product_id: product.product_id,
            product_name: product.product_name,
            product_type: product.product_type || category,
            category: product.category,
            brand: product.brand,
            image_url: product.image_url,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to add product");
      }

      const data = await response.json();
      if (data.success) {
        onProductSelected(product);
        onClose();
      } else {
        throw new Error(data.error || "Failed to add product");
      }
    } catch (err: any) {
      setError(err.message || "Failed to add product");
    } finally {
      setAddingProductId(null);
    }
  };

  if (!isOpen) return null;

  const categoryDisplay = category.charAt(0).toUpperCase() + category.slice(1);

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center z-50 p-3 sm:p-4">
      <div className="bg-white rounded-2xl sm:rounded-3xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-gray-100">
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-[#141414]">
              Add {categoryDisplay}
            </h2>
            <p className="text-xs sm:text-sm text-[#7A7382] mt-0.5 sm:mt-1">
              Choose a product evaluated for your skin profile
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 hover:bg-gray-200 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-3.5 sm:p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-12 h-12 border-4 border-[#DE688E] border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-sm font-semibold text-[#6B6375]">
                Loading products...
              </p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertTriangle className="text-red-500 mb-3" size={32} />
              <p className="text-sm font-semibold text-red-700">{error}</p>
              <button
                type="button"
                onClick={loadProducts}
                className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded-full text-sm font-semibold hover:bg-red-200 transition"
              >
                Retry
              </button>
            </div>
          ) : products.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Package className="text-[#A85175] mb-3" size={32} />
              <p className="text-sm font-semibold text-[#141414]">
                No products available
              </p>
              <p className="text-xs text-[#7A7382] mt-1">
                No {categoryDisplay.toLowerCase()} products found in our catalog
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {products.map((product) => {
                const evaluation = product.evaluation;
                const decision = evaluation?.decision || "KEEP";
                const isCaution = decision === "CAUTION";
                const primaryReason = evaluation?.reasons?.[0];

                return (
                  <div
                    key={product.product_id}
                    className="flex items-start gap-4 p-4 rounded-2xl border border-gray-100 bg-white hover:shadow-md transition"
                  >
                    {/* Product Thumbnail */}
                    <div className="w-16 h-20 bg-gray-50 rounded-xl overflow-hidden shrink-0 flex items-center justify-center p-1 border border-gray-100">
                      {product.image_url ? (
                        <img
                          src={product.image_url}
                          alt={product.product_name}
                          className="w-full h-full object-contain"
                        />
                      ) : (
                        <Package className="text-[#A85175]" size={24} />
                      )}
                    </div>

                    {/* Product Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-bold text-[#141414] leading-tight line-clamp-2">
                            {product.brand ? `${product.brand} ` : ""}
                            {product.product_name}
                          </h3>
                          <div className="mt-2 flex items-center gap-2">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                                isCaution
                                  ? "bg-amber-100/80 text-amber-700"
                                  : "bg-green-100/80 text-green-700"
                              }`}
                            >
                              {isCaution ? (
                                <AlertTriangle size={12} />
                              ) : (
                                <ShieldCheck size={12} />
                              )}
                              {decision}
                            </span>
                            {evaluation?.fit_score !== undefined && (
                              <span className="text-[10px] text-[#7A7382]">
                                Fit: {evaluation.fit_score}
                              </span>
                            )}
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleAddProduct(product)}
                          disabled={addingProductId === product.product_id}
                          className="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 bg-[#DE688E] text-white rounded-full text-xs font-bold hover:bg-[#BD426B] transition disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {addingProductId === product.product_id ? (
                            "Adding..."
                          ) : (
                            <>
                              <Plus size={14} /> Add
                            </>
                          )}
                        </button>
                      </div>

                      {primaryReason && (
                        <p className="text-xs text-[#7A7382] mt-2 line-clamp-2">
                          {primaryReason}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}