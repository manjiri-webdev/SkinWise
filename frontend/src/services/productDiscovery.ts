import type { ProductDiscoverRequest, ProductDiscoverResponse, ProductExtractionRequest, ProductExtractionResponse, ProductAnalysisRequest, ProductAnalysisResponse } from "@/types/product";

const API_BASE_URL = process.env.NEXT_PUBLIC_INGREDIENT_SERVICE_URL ?? "http://localhost:8001";

function getErrorMessage(payload: unknown): string {
  if (typeof payload !== "object" || payload === null || !("detail" in payload)) {
    return "We couldn’t search for that product. Please try again.";
  }

  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (typeof item === "object" && item !== null && "msg" in item && typeof item.msg === "string" ? item.msg : null))
      .filter((message): message is string => message !== null);
    if (messages.length) return messages.join(" ");
  }

  return "We couldn’t search for that product. Please try again.";
}

export async function discoverProducts(
  request: ProductDiscoverRequest,
): Promise<ProductDiscoverResponse> {
  const response = await fetch(`${API_BASE_URL}/product/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getErrorMessage(payload));
  }

  return payload as ProductDiscoverResponse;
}

export async function extractProductDetails(
  request: ProductExtractionRequest,
): Promise<ProductExtractionResponse> {
  const response = await fetch(`${API_BASE_URL}/product/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getErrorMessage(payload));
  }

  return payload as ProductExtractionResponse;
}

export async function analyzeProduct(
  request: ProductAnalysisRequest,
): Promise<ProductAnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/product/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getErrorMessage(payload));
  }

  return payload as ProductAnalysisResponse;
}
