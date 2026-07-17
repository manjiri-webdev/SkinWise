import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function SignupForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password != confirmPassword) {
      alert("Password do not Match.");
      return;
    }

    const { data: authData, error: authError } = await supabase.auth.signUp({ email, password });

    if (authError) {
      alert(authError.message);
      return;
    }

    const user = authData.user;
    if (!user) {
      alert("Signup started! Please check your email to confirm your account.")
      navigate('/login')
      return
    }

    const { data: insertData, error: insertUserError } = await supabase.from('users').insert([
      { id: user.id, email, password }
    ])

    if (insertUserError) {
      alert(insertUserError.message)
    } else {
      alert("Signup successful! Please check your email to confirm.")
      navigate('/login')
    }
  }
  return (
    <form className="space-y-4 font-semibold ">
      <label htmlFor="email" className="sr-only">Email</label>
      <input type="email" placeholder="Email" className="input-glass" />
      <label htmlFor="password" className="sr-only">Password</label>
      <input id="password" type="password" placeholder="Password" className="input-glass" />
      <label htmlFor="confirmPassword" className="sr-only">Confirm Password</label>
      <input id="confirmPassword" type="password" placeholder="Confirm Password" className="input-glass" />

      <button className="btn w-full font-bold bg-gradient-to-r from-pinkSoft to-pink hover:from-pinkHover hover:to-pinkSoft ">
        Create Account
      </button>

      <p className="text-xs mt-2 text-center text-textSecondary"> By creating an account, you agree to our Terms & Privacy.</p>
    </form>
  )
}