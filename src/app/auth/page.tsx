"use client";

import { useState } from "react";
import LoginForm from "./LoginForm";
import SignupForm from "./SignupForm";

export default function AuthCard({ mode }: { mode: "login" | "signup" }) {
  const [isLogin, setIsLogin] = useState(mode === "login");

  return (
    <main
      className="relative flex h-screen  w-full bg-gradient-to-r from-creamGradient1 to-creamGradient2 items-center justify-center fluid-bg"
      style={{ backgroundImage: "url('/images/reusable-bg.webp')" }}
    >
      <div className="absolute inset-0 bg-pink-900/15"></div>
      <div className="hidden md:flex flex-col w-1/2 items-center justify-center p-12">

        <img src="/images/logo2.png" alt="SkinWise" className="w-20 h-20 mb-6" />

        <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-textDark text-center">
          {isLogin ? "Welcome back to SkinWise" : "Start your personalized skincare journey"}
        </h2>

        <p className="text-textSecondary font-semibold text-sm sm:text-base mt-2">
          {isLogin
            ? "Sign in to access your AI-powered skin analysis."
            : "Create an account to unlock AI-powered recommendations."}
        </p>
      </div>

      <div className="w-full md:w-1/2 flex items-center justify-center ">

        <div className="blob-wrapper animate-elements">
          <div className="blob-card bg-lavenderSoft/30 shadow-floaty">
            <div className="blob-content glass flex flex-col justify-center bg-lavenderSoft/30 shadow-floaty">

              <div className="blob-inner">
                <div className="flex justify-center gap-6 mb-6">
                  <button
                    className={`tab-btn ${isLogin ? "text-pinkHover font-bold text-[#8D8B89] " : "text-textSecondary"}`}
                    onClick={() => setIsLogin(true)} aria-pressed={isLogin}
                  >
                    Sign In
                  </button>
                  <button
                    className={`tab-btn ${!isLogin ? "text-pinkHover font-bold text-[#8D8B89] " : "text-textSecondary"}`}
                    onClick={() => setIsLogin(false)} aria-pressed={!isLogin}
                  >
                    Sign Up
                  </button>
                </div>

                <button className="btn w-full py-2 mb-4 font-semibold flex items-center justify-center gap-2">
                 <img src="/images/google-icon.png" alt="Google" className="w-5 h-5" />
                  Continue with Google
                </button>

                <div className="flex items-center my-4">
                  <span className="flex-grow border-t" />
                  <span className="px-2 text-xs text-textSecondary">or continue with email</span>
                  <span className="flex-grow border-t" />
                </div>

                {isLogin ? <LoginForm /> : <SignupForm />}

              </div>
            </div>
          </div>
        </div>
      </div>
    </main >
  );
}