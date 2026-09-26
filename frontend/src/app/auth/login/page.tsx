"use client";

import LoginForm from "../LoginForm";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const handleGoogleLogin = async () => {
    const origin = typeof window !== "undefined" ? window.location.origin : (process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000");
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${origin}/auth/callback`,
      },
    });

    if (error) {
      alert(error.message);
    }
  };

  return (
    <main
      className="relative flex min-h-screen w-full bg-gradient-to-r from-creamGradient1 to-creamGradient2 items-center justify-center fluid-bg px-4 sm:px-6 py-8 sm:py-10"
      style={{ backgroundImage: "url('/images/reusable-bg.webp')" }}
    >
      <div className="absolute inset-0 bg-pink-900/10 backdrop-blur-[1px] pointer-events-none" />

      <div className="relative z-10 w-full max-w-5xl flex flex-col md:flex-row items-center justify-between gap-8 md:gap-14 px-0 sm:px-6 md:px-8">
        {/* Left side brand intro */}
        <div className="w-full md:w-1/2 flex flex-col items-start justify-center max-w-md">
          <div className="flex items-center gap-2 mb-6">
            <img src="/images/logo2.png" alt="SkinWise" className="w-10 h-10 object-contain" />
            <span className="text-2xl font-bold text-[#DE688E]" style={{ fontFamily: "Georgia, serif" }}>
              SkinWise
            </span>
          </div>
          <h1
            className="text-4xl lg:text-5xl font-bold text-[#141414] leading-tight mb-4"
            style={{ fontFamily: "Georgia, serif" }}
          >
            Welcome Back
          </h1>
          <p className="text-base lg:text-lg text-[#2D2D2D] leading-relaxed">
            Continue your personalized skincare journey powered by AI
          </p>
        </div>

        {/* Right side form card */}
        <div className="w-full md:w-1/2 flex items-center justify-center md:justify-end">
          <div className="auth-card">
            <button
              type="button"
              className="w-full py-3 px-4 rounded-2xl bg-white text-[#2D2D2D] font-medium text-sm flex items-center justify-center gap-3 shadow-[0_4px_16px_rgba(0,0,0,0.06)] border border-white/90 hover:bg-gray-50 transition active:scale-[0.99] cursor-pointer"
              onClick={handleGoogleLogin}
            >
              <img src="/images/google-icon.png" alt="Google" className="w-5 h-5 object-contain" />
              Continue with Google
            </button>

            <div className="flex items-center my-5">
              <span className="flex-grow border-t border-[#D5C2C7]" />
              <span className="px-3 text-xs text-[#7E7775]">or continue with email</span>
              <span className="flex-grow border-t border-[#D5C2C7]" />
            </div>

            <LoginForm />

            <div className="mt-6 text-center text-xs text-[#7E7775]">
              Don&apos;t have an account?{" "}
              <a href="/auth/signup" className="font-semibold text-[#E06B85] hover:underline">
                Sign Up
              </a>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
