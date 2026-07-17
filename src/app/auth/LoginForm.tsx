import Link from "next/link"; 
import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

export default function LoginForm() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    const { error } = await supabase.auth.signInWithPassword({ email, password,});

    if (error) {
      alert(error.message);
      return;
    }

    alert("Login successful!");
    router.push("/questionnaire");
  };

  return (
    <form  onSubmit={handleLogin} className="space-y-4 border-t border-[#E8DAD6] font-semibold ">

      <label htmlFor="email" className="sr-only">Email</label>
      <input id="email" type="email" placeholder="Email" className="input-glass" value={email} onChange={(e) => setEmail(e.target.value)} required/>

      <label htmlFor="password" className="sr-only">Password</label>
      <input id="password" type="password" placeholder="Password" className="input-glass" value={password} onChange={(e) => setPassword(e.target.value)} required/>

      <div className="mt-4 text-sm text-end text-[#7E7775] hover:text-blue-600 ">
        <a href="/forgotPassword">Forgot Password?</a>
      </div>

      <div className="flex justify-center">
        <button className="btn w-1/2 flex font-bold justify-center bg-gradient-to-r from-pinkSoft to-pink hover:from-pinkHover hover:to-pinkSoft">
          Sign In
        </button>
      </div>
    </form>
  )
}