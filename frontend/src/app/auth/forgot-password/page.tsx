"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function ForgotPassword() {
    const [email, setEmail] = useState("");

    const handleReset = async (e: React.FormEvent) => {
        e.preventDefault();

        const { error } = await supabase.auth.resetPasswordForEmail(email, {
            redirectTo: "http://localhost:3000/auth/reset-password",
        });

        if (error) {
            alert(error.message);
            return;
        }

        alert("Password reset link sent! Check your email.");
    };

    return (
        <main className="relative flex h-screen w-full bg-gradient-to-r from-creamGradient1 to-creamGradient2 items-center justify-center fluid-bg"
            style={{ backgroundImage: "url('/images/reusable-bg.webp')" }}>

            <div className="glass w-full max-w-md p-10 rounded-3xl animate-elements">

                <h1 className="text-2xl font-bold mb-3">
                    Forgot Password
                </h1>

                <p className="text-textSecondary mb-6">
                    Enter your email and we'll send you a password reset link.
                </p>

                <form
                    onSubmit={handleReset}
                    className="space-y-5"
                >

                    <input
                        type="email"
                        className="input-glass"
                        placeholder="Email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />

                    <button
                        type="submit"
                        className="btn w-full bg-gradient-to-r from-pinkSoft to-pink"
                    >
                        Send Reset Link
                    </button>

                </form>

            </div>

        </main>
    );
}