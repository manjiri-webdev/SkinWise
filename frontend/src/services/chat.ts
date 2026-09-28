import { supabase } from "@/lib/supabase";

const API_BASE_URL = process.env.NEXT_PUBLIC_AI_BACKEND_URL || "http://localhost:8000";

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  suggested_actions?: string[];
  timestamp?: string;
}

export interface ChatRequest {
  message: string;
  conversation_history?: Array<{
    role: "user" | "assistant";
    content: string;
  }>;
}

export interface ChatResponse {
  reply: string;
  suggested_actions?: string[];
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
  history: ChatMessage[] = []
): Promise<ChatResponse> {
  const token = await getAuthToken();

  const formattedHistory = history.map((msg) => ({
    role: msg.role,
    content: msg.content,
  }));

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: message.trim(),
      conversation_history: formattedHistory,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMsg =
      errorData.detail || errorData.message || "Failed to get response from assistant. Please try again.";
    throw new Error(errorMsg);
  }

  return response.json();
}
