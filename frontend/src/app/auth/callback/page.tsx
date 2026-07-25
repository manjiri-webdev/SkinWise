"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { redirectUser } from "@/lib/authRedirect";

export default function CallbackPage() {
  const router = useRouter();

  useEffect(() => {
    redirectUser(router);
  }, []);

  return (
    <main className="min-h-screen flex items-center justify-center bg-gradient-to-r from-creamGradient1 to-creamGradient2">
      <div className="glass p-10 rounded-3xl text-center">
        <h2 className="text-2xl font-bold">
          Signing you in...
        </h2>

        <p className="mt-3 text-textSecondary">
          Please wait while we prepare your SkinWise account.
        </p>
      </div>
    </main>
  );
}