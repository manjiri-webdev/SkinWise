import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

export default function SignupForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      alert("Passwords do not match.");
      return;
    }

    const { error } = await supabase.auth.signUp({ email, password, });

    if (error) {
      alert(error.message);
      return;
    }

    alert("Account created successfully!");
    router.push("/auth/login");
  };

  return (
    <form onSubmit={handleSignup} className="space-y-4 font-semibold ">

      <label htmlFor="email" className="sr-only">Email</label>
      <input type="email" id="email" placeholder="Email" className="input-glass" value={email} onChange={(e) => setEmail(e.target.value)} required />

      <label htmlFor="password" className="sr-only">Password</label>
      <input type="password" id="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} className="input-glass" required />

      <label htmlFor="confirmPassword" className="sr-only">Confirm Password</label>
      <input type="password" id="confirmPassword" placeholder="Confirm Password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required className="input-glass" />

      <button className="btn w-full font-bold bg-gradient-to-r from-pinkSoft to-pink hover:from-pinkHover hover:to-pinkSoft ">
        Create Account
      </button>

      <p className="text-xs mt-2 text-center text-textSecondary"> By creating an account, you agree to our Terms & Privacy.</p>
    </form>
  )
}