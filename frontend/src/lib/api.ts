/**
 * Centralized API URL utility for SkinWise frontend.
 * Guarantees URLs are constructed without duplicate slashes (e.g. //validate-live -> /validate-live).
 */

export function sanitizeBaseUrl(url?: string | null, fallback: string = "http://localhost:8000"): string {
  if (!url || typeof url !== "string") return fallback.replace(/\/+$/, "");
  const trimmed = url.trim();
  if (!trimmed) return fallback.replace(/\/+$/, "");
  return trimmed.replace(/\/+$/, "");
}

export const AI_BACKEND_URL = sanitizeBaseUrl(
  process.env.NEXT_PUBLIC_AI_BACKEND_URL,
  "http://localhost:8000"
);

export const INGREDIENT_SERVICE_URL = sanitizeBaseUrl(
  process.env.NEXT_PUBLIC_INGREDIENT_SERVICE_URL,
  "http://localhost:8001"
);

/**
 * Builds a clean URL joining a base URL and an endpoint path without double slashes.
 * e.g. joinApiUrl("https://skinwise-ai-backend.onrender.com/", "/validate-live")
 *      => "https://skinwise-ai-backend.onrender.com/validate-live"
 */
export function joinApiUrl(base: string, path: string): string {
  const cleanBase = sanitizeBaseUrl(base);
  const cleanPath = path.trim().replace(/^\/+/, "");
  return `${cleanBase}/${cleanPath}`;
}
