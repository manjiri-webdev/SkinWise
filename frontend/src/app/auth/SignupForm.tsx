"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

export default function SignupForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      alert("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const { error } = await supabase.auth.signUp({ email, password });

      if (error) {
        alert(error.message);
        return;
      }

      alert("Account created successfully! Please sign in.");
      router.push("/auth/login");
    } catch (err: any) {
      alert(err?.message || "Failed to sign up. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSignup} className="space-y-3.5">
      <div>
        <label htmlFor="email" className="sr-only">Email</label>
        <input 
          type="email" 
          id="email" 
          placeholder="Email" 
          className="w-full px-4 py-3 rounded-2xl bg-white/95 border border-white/90 text-[#2D2D2D] placeholder:text-[#9A9393] text-sm shadow-[0_2px_8px_rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-pink-300 focus:bg-white transition" 
          value={email} 
          onChange={(e) => setEmail(e.target.value)} 
          required 
        />
      </div>

      <div>
        <label htmlFor="password" className="sr-only">Password</label>
        <input 
          type="password" 
          id="password" 
          placeholder="Password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
          className="w-full px-4 py-3 rounded-2xl bg-white/95 border border-white/90 text-[#2D2D2D] placeholder:text-[#9A9393] text-sm shadow-[0_2px_8px_rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-pink-300 focus:bg-white transition" 
          required 
        />
      </div>

      <div>
        <label htmlFor="confirmPassword" className="sr-only">Confirm Password</label>
        <input 
          type="password" 
          id="confirmPassword" 
          placeholder="Confirm Password" 
          value={confirmPassword} 
          onChange={(e) => setConfirmPassword(e.target.value)} 
          required 
          className="w-full px-4 py-3 rounded-2xl bg-white/95 border border-white/90 text-[#2D2D2D] placeholder:text-[#9A9393] text-sm shadow-[0_2px_8px_rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-pink-300 focus:bg-white transition" 
        />
      </div>

      <div className="flex justify-center pt-2">
        <button 
          type="submit"
          disabled={loading}
          className="btn btn-rose w-48 py-2.5 font-bold text-sm flex items-center justify-center transition disabled:opacity-50 cursor-pointer"
        >
          <span>{loading ? "Creating account..." : "Create Account"}</span>
        </button>
      </div>

      <p className="text-[11px] text-center text-[#7E7775] pt-1">
        By creating an account, you agree to our Terms &amp; Privacy.
      </p>
    </form>
  );
}