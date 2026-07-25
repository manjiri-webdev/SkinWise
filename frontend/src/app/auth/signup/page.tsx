"use client";

import SignupForm from "../SignupForm";
import { supabase } from "@/lib/supabase";

export default function SignupPage() {

    const handleGoogleSignup = async() =>{
        const { error } = await supabase.auth.signInWithOAuth({
          provider: "google",
          options:{
            redirectTo: "http://localhost:3000/auth/callback",
          },
        });
    
        if(error){
          alert(error.message);
        }
      }
      
    return (
        <main
            className="relative flex h-screen w-full bg-gradient-to-r from-creamGradient1 to-creamGradient2 items-center justify-center fluid-bg"
            style={{ backgroundImage: "url('/images/reusable-bg.webp')" }}
        >
            <div className="absolute inset-0 bg-pink-900/15"></div>

            <div className="hidden md:flex flex-col w-1/2 items-center justify-center p-12">
                <img src="/images/logo2.png" alt="SkinWise" className="w-20 h-20 mb-6" />
                <h2 className="text-4xl font-bold text-textDark text-center leading-tight">
                    Join SkinWise
                </h2>
                <p className="text-textSecondary text-center mt-4 max-w-md">
                    Create your account to receive personalized skincare insights, ingredient analysis, and AI-powered recommendations.
                </p>
            </div>

            <div className="w-full md:w-1/2 flex items-center justify-center">
                <div className="blob-wrapper animate-elements">
                    <div className="blob-card bg-lavenderSoft/30 shadow-floaty">
                        <div className="blob-content glass flex flex-col justify-center bg-lavenderSoft/30 shadow-floaty">
                            <div className="blob-inner">
                                <button className="btn w-full py-2 mb-4 font-semibold flex items-center justify-center gap-2"
                                onClick={handleGoogleSignup}>
                                    <img src="/images/google-icon.png" alt="Google" className="w-5 h-5" />
                                    Continue with Google
                                </button>

                                <div className="flex items-center my-4">
                                    <span className="flex-grow border-t" />
                                    <span className="px-2 text-xs text-textSecondary">or continue with email</span>
                                    <span className="flex-grow border-t" />
                                </div>

                                <SignupForm />

                                <div className="mt-6 text-center text-sm">
                                    <span className="text-textSecondary">Already have an account?</span>
                                    <a href="/auth/login" className="ml-1 font-semibold text-pinkHover hover:underline">
                                        Sign In
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}
