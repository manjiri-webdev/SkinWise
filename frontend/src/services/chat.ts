import { supabase } from "@/lib/supabase";

const API_BASE_URL = process.env.NEXT_PUBLIC_AI_BACKEND_URL || "http://localhost:8000";

export interface CurrentProductContext {
  product_name?: string;
  brand?: string;
  category?: string;
  decision?: "KEEP" | "CAUTION" | "REJECT" | string;
  match_label?: string;
  confidence?: string;
  reasons?: string[];
  mitigations?: string[];
  reason_codes?: string[];
  suitable_count?: number;
  caution_count?: number;
  not_recommended_count?: number;
}

export interface DermatologistSearchAction {
  type?: string;
  label: string;
  query: string;
  maps_url: string;
  url?: string;
}

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  suggested_actions?: string[];
  dermatologist_search?: DermatologistSearchAction | null;
  timestamp?: string;
}

export interface ChatRequest {
  message: string;
  conversation_history?: Array<{
    role: "user" | "assistant";
    content: string;
  }>;
  current_product?: CurrentProductContext;
}

export interface ChatResponse {
  reply: string;
  suggested_actions?: string[];
  dermatologist_search?: DermatologistSearchAction | null;
}

async function getAuthToken(): Promise<string> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error("No authenticated session. Please sign in to chat with SkinWise Assistant.");
  }
  return session.access_token;
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[] = [],
  currentProduct?: CurrentProductContext | null
): Promise<ChatResponse> {
  const token = await getAuthToken();

  const formattedHistory = history.map((msg) => ({
    role: msg.role,
    content: msg.content,
  }));

  const payload: Record<string, any> = {
    message: message.trim(),
    conversation_history: formattedHistory,
  };

  if (currentProduct) {
    payload.current_product = currentProduct;
  }

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMsg =
      errorData.detail || errorData.message || "Failed to get response from assistant. Please try again.";
    throw new Error(errorMsg);
  }

  return response.json();
}
