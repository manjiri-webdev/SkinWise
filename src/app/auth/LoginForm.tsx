import Link from "next/link";

export default function LoginForm() {
  return (
    <form className="space-y-4 border-t border-[#E8DAD6] font-semibold ">
      <label htmlFor="email" className="sr-only">Email</label>
      <input id="email" type="email" placeholder="Email" className="input-glass" />
      <label htmlFor="password" className="sr-only">Password</label>
      <input id="password" type="password" placeholder="Password" className="input-glass" />

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