"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import Link from "next/link";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const origin = typeof window !== "undefined" ? window.location.origin : (process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000");
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${origin}/auth/reset-password`,
      });

      if (error) {
        alert(error.message);
        return;
      }

      alert("Password reset link sent! Check your email.");
    } catch (err: any) {
      alert(err?.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main
      className="relative flex min-h-screen w-full bg-gradient-to-r from-creamGradient1 to-creamGradient2 items-center justify-center fluid-bg px-4 sm:px-6 py-8 sm:py-10"
      style={{ backgroundImage: "url('/images/reusable-bg.webp')" }}
    >
      <div className="absolute inset-0 bg-pink-900/10 backdrop-blur-[1px] pointer-events-none" />

      <div className="relative z-10 w-full max-w-md flex items-center justify-center">
        <div className="auth-card">
          <div className="flex items-center gap-2 mb-6">
            <img src="/images/logo2.png" alt="SkinWise" className="w-9 h-9 object-contain" />
            <span className="text-xl font-bold text-[#DE688E]" style={{ fontFamily: "Georgia, serif" }}>
              SkinWise
            </span>
          </div>

          <h1
            className="text-2xl font-bold text-[#141414] leading-tight mb-2"
            style={{ fontFamily: "Georgia, serif" }}
          >
            Forgot Password
          </h1>

          <p className="text-xs text-[#7E7775] mb-6 leading-relaxed">
            Enter your email and we&apos;ll send you a password reset link.
          </p>

          <form onSubmit={handleReset} className="space-y-4">
            <div>
              <label htmlFor="email" className="sr-only">Email</label>
              <input
                type="email"
                id="email"
                className="w-full px-4 py-3 rounded-2xl bg-white/95 border border-white/90 text-[#2D2D2D] placeholder:text-[#9A9393] text-sm shadow-[0_2px_8px_rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-pink-300 focus:bg-white transition"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="flex justify-center pt-2">
              <button
                type="submit"
                disabled={loading}
                className="btn btn-rose w-48 py-2.5 font-bold text-sm flex items-center justify-center transition disabled:opacity-50 cursor-pointer"
              >
                <span>{loading ? "Sending link..." : "Send Reset Link"}</span>
              </button>
            </div>
          </form>

          <div className="mt-6 text-center text-xs text-[#7E7775]">
            Remember your password?{" "}
            <Link href="/auth/login" className="font-semibold text-[#E06B85] hover:underline">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}