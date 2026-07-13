export default function SignupForm() {
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

      <p className="text-xs mt-2 text-center text-textSecondary">
        Already have an account? <a className="text-[#DF7F8D] font-medium hover:text-[#C96A79]" href="/Login">Sign In</a>
      </p>
    </form>
  )
}