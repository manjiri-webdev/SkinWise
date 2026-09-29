"use client";

import { useEffect } from "react";
import { AI_BACKEND_URL, INGREDIENT_SERVICE_URL, joinApiUrl } from "@/lib/api";

/**
 * Fires non-blocking background health check pings to wake up sleeping Render backend instances
 * when any user visits the site.
 */
export function ServerWarmup() {
  useEffect(() => {
    // Only run in client browser
    if (typeof window === "undefined") return;

    const warmUp = async () => {
      try {
        if (AI_BACKEND_URL) {
          fetch(joinApiUrl(AI_BACKEND_URL, "/health"), {
            method: "GET",
            mode: "cors",
            cache: "no-store",
          }).catch(() => {});
        }
      } catch {}

      try {
        if (INGREDIENT_SERVICE_URL) {
          fetch(joinApiUrl(INGREDIENT_SERVICE_URL, "/health"), {
            method: "GET",
            mode: "cors",
            cache: "no-store",
          }).catch(() => {});
        }
      } catch {}
    };

    // Warm up immediately upon application load
    warmUp();
  }, []);

  return null;
}
