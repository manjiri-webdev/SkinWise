"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

export default function ForgotPassword() {
    const router = useRouter();
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    const handleReset = async (e: React.FormEvent) => {
        e.preventDefault();

        if (password !== confirmPassword) {
            alert("Passwords do not match.");
            return;
        }

        const { error } = await supabase.auth.updateUser({
            password,
        });

        if (error) {
            alert(error.message);
            return;
        }

        alert("Password updated successfully!");
        router.push("/auth/login");
    };

    return (
        <main className="relative flex h-screen w-full bg-gradient-to-r from-creamGradient1 to-creamGradient2 items-center justify-center fluid-bg"
            style={{ backgroundImage: "url('/images/reusable-bg.webp')" }}>

            <div className="glass w-full max-w-md p-10 rounded-3xl animate-elements">

                <h1 className="text-2xl font-bold mb-3">
                    Reset Password
                </h1>

                <p className="text-textSecondary mb-6">
                    Create a new password for your SkinWise account.
                </p>

                <form
                    onSubmit={handleReset}
                    className="space-y-5"
                >

                    <label htmlFor="password" className="sr-only">Password</label>
                    <input id="password" type="password" placeholder="Password" className="input-glass" value={password} onChange={(e) => setPassword(e.target.value)} required />

                    <label htmlFor="confirmPassword" className="sr-only">Confirm Password</label>
                    <input type="password" id="confirmPassword" placeholder="Confirm Password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required className="input-glass" />

                    <button
                        type="submit"
                        className="btn w-full bg-gradient-to-r from-pinkSoft to-pink"
                    >
                        Save New Password
                    </button>

                </form>

            </div>

        </main>
    );
}