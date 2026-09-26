"use client";

import { ArrowRight, ShieldPlus } from "lucide-react";
import { useRouter } from "next/navigation";

export default function SplashPage() {
  const router = useRouter();

  return (
    <main className="relative min-h-screen w-full flex items-center fluid-bg"
      style={{ backgroundImage: "url('/images/splash-bg.webp')" }} >

      <div className="relative z-10 flex flex-col justify-center h-full items-start px-4 sm:px-8 py-8 sm:py-12 space-y-6 sm:space-y-10 md:space-y-12 max-w-2xl w-full">

        <div className="flex flex-col items-center animate-elements">
          <img src="/images/logo2.png" alt="SkinWise Ai"
            className="w-14 h-14 sm:w-20 sm:h-20 md:w-20 md:h-16 object-contain"
          />
        </div>

        <div className="text-luxury w-full">
          <h1 className="text-2xl sm:text-3xl md:text-5xl font-display font-bold leading-tight animate-elements">
            <span className="text-textDark">Smarter skincare,</span>
            <br />
            <span className="text-green">powered by AI</span>
            <span className="text-textDark"> and science.</span>
          </h1><br />

          <p className="text-textSecondary text-sm sm:text-base md:text-lg">
            Discover your skin profile, evaluate cosmetic ingredients, and receive AI-powered recommendations tailored to your unique needs.
          </p>
        </div>

        <button 
        className="btn w-fit inline-flex items-center gap-3 sm:gap-4 pl-5 sm:pl-6 pr-1.5 py-1.5 bg-gradient-to-r from-lavenderSoft to-lavender hover:from-lavenderHover hover:to-lavenderSoft animate-elements"
        onClick={() => router.push("/auth/login")}
        >
          <span className="text-sm sm:text-base font-medium text-black">Start Assessment</span>
          <span className="btn-icon">
            <ArrowRight className="h-4 w-4 sm:h-5 sm:w-5" />
          </span>
        </button>

        <div className="flex flex-wrap gap-2 sm:gap-3">
          <span className="px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm text-textSecondary bg-white/30 rounded-full backdrop-blur-xs"> AI Skin Analysis </span>
          <span className="px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm text-textSecondary bg-white/30 rounded-full backdrop-blur-xs"> Ingredient Safety </span>
          <span className="px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm text-textSecondary bg-white/30 rounded-full backdrop-blur-xs"> Personalized Care </span>
        </div>
      </div>
    </main>
  );
}
