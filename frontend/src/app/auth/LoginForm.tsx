"use client";

import Link from "next/link"; 
import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { redirectUser } from "@/lib/authRedirect";

export default function LoginForm() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });

      if (error) {
        alert(error.message);
        return;
      }

      await redirectUser(router);
    } catch (err: any) {
      alert(err?.message || "Failed to sign in. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleLogin} className="space-y-3.5">
      <div>
        <label htmlFor="email" className="sr-only">Email</label>
        <input 
          id="email" 
          type="email" 
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
          id="password" 
          type="password" 
          placeholder="Password" 
          className="w-full px-4 py-3 rounded-2xl bg-white/95 border border-white/90 text-[#2D2D2D] placeholder:text-[#9A9393] text-sm shadow-[0_2px_8px_rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-pink-300 focus:bg-white transition" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
          required 
        />
      </div>

      <div className="text-right pt-0.5">
        <Link href="/auth/forgot-password" className="text-xs text-[#7E7775] hover:text-[#DE688E] transition">
          Forgot Password?
        </Link>
      </div>

      <div className="flex justify-center pt-2">
        <button 
          type="submit" 
          disabled={loading} 
          className="btn btn-rose w-44 py-2.5 font-bold text-sm flex items-center justify-center transition disabled:opacity-50 cursor-pointer"
        >
          <span>{loading ? "Signing in..." : "Sign In"}</span>
        </button>
      </div>
    </form>
  );
}