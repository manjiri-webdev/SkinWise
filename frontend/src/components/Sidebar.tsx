"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import {
  Home,
  ClipboardCheck,
  ScanFace,
  ShoppingBasket,
  User,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { supabase } from "@/lib/supabase";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [displayName, setDisplayName] = useState<string>("User");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  useEffect(() => {
    async function loadUserData() {
      try {
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (user) {
          const name =
            user.user_metadata?.full_name ||
            user.user_metadata?.name ||
            (user.email ? user.email.split("@")[0] : "User");
          setDisplayName(name);

          const photo =
            user.user_metadata?.avatar_url || user.user_metadata?.picture;
          if (photo) {
            setAvatarUrl(photo);
          }
        }
      } catch (err) {
        console.error("Failed to load user profile for sidebar:", err);
      }
    }

    loadUserData();
  }, []);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  // Handle escape key to close drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileMenuOpen(false);
    };
    if (mobileMenuOpen) {
      window.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [mobileMenuOpen]);

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      router.push("/auth/login");
    } catch (err) {
      console.error("Logout error:", err);
    }
  };

  const navigation = [
    { href: "/dashboard", label: "Home", icon: Home },
    { href: "/routine", label: "Routine", icon: ClipboardCheck },
    { href: "/face-analysis", label: "Skin Analysis", icon: ScanFace },
    { href: "/ingredients", label: "Ingredients", icon: ShoppingBasket },
  ];

  const bottomNavItems = [
    { href: "/dashboard", label: "Home", icon: Home },
    { href: "/routine", label: "Routine", icon: ClipboardCheck },
    { href: "/face-analysis", label: "Analysis", icon: ScanFace },
    { href: "/ingredients", label: "Ingredients", icon: ShoppingBasket },
    { href: "/profile", label: "Profile", icon: User },
  ];

  const isProfilePage = pathname === "/profile";

  return (
    <>
      {/* ---------------- MOBILE & TABLET TOP HEADER (< 1024px) ---------------- */}
      <header className="lg:hidden sticky top-0 z-30 w-full bg-white/90 backdrop-blur-md border-b border-gray-100 px-4 py-3 flex items-center justify-between">
        <Link href="/dashboard" className="flex items-center gap-2 group" aria-label="SkinWise Home">
          <Image
            src="/images/logo2.png"
            alt="SkinWise logo"
            width={30}
            height={30}
            className="w-7 h-7 sm:w-8 sm:h-8 object-contain"
          />
          <span
            className="text-xl sm:text-2xl font-bold text-[#DE688E] tracking-tight"
            style={{ fontFamily: "Georgia, serif" }}
          >
            SkinWise
          </span>
        </Link>

        <div className="flex items-center gap-2">
          <Link
            href="/profile"
            aria-label="View Profile"
            className="p-1.5 rounded-full hover:bg-gray-100 transition"
          >
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt={displayName}
                className="w-7 h-7 rounded-full object-cover border border-pink-200"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-[#F4EBE8] text-[#A85175] flex items-center justify-center">
                <User size={15} />
              </div>
            )}
          </Link>

          <button
            type="button"
            onClick={() => setMobileMenuOpen(true)}
            aria-label="Open navigation menu"
            className="p-2 rounded-xl text-[#55505C] hover:text-[#141414] hover:bg-gray-100 transition"
          >
            <Menu size={22} />
          </button>
        </div>
      </header>

      {/* ---------------- MOBILE SLIDE-OVER DRAWER (< 1024px) ---------------- */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />

          {/* Drawer content */}
          <div className="relative w-full max-w-[280px] bg-white h-full shadow-2xl flex flex-col justify-between p-6 z-10 animate-in slide-in-from-left duration-200">
            <div>
              <div className="flex items-center justify-between pb-6 mb-4 border-b border-gray-100">
                <Link
                  href="/dashboard"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2"
                >
                  <Image
                    src="/images/logo2.png"
                    alt="SkinWise logo"
                    width={32}
                    height={32}
                    className="w-8 h-8 object-contain"
                  />
                  <span
                    className="text-xl font-bold text-[#DE688E] tracking-tight"
                    style={{ fontFamily: "Georgia, serif" }}
                  >
                    SkinWise
                  </span>
                </Link>
                <button
                  type="button"
                  onClick={() => setMobileMenuOpen(false)}
                  aria-label="Close navigation menu"
                  className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-100 transition"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Navigation Links in Drawer */}
              <nav>
                <ul className="space-y-1.5">
                  {navigation.map(({ href, label, icon: Icon }) => {
                    const isActive = pathname === href;
                    return (
                      <li key={href}>
                        <Link
                          href={href}
                          onClick={() => setMobileMenuOpen(false)}
                          className={`flex items-center gap-3.5 px-4 py-3 rounded-2xl text-sm font-semibold transition-all duration-200 ${
                            isActive
                              ? "bg-[#FDECEF] text-[#DE688E] shadow-xs"
                              : "text-[#55505C] hover:text-[#141414] hover:bg-gray-50"
                          }`}
                        >
                          <Icon
                            size={19}
                            strokeWidth={isActive ? 2.4 : 2}
                            className={isActive ? "text-[#DE688E]" : "text-[#7A7382]"}
                          />
                          <span>{label}</span>
                        </Link>
                      </li>
                    );
                  })}
                  <li>
                    <Link
                      href="/profile"
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3.5 px-4 py-3 rounded-2xl text-sm font-semibold transition-all duration-200 ${
                        pathname === "/profile"
                          ? "bg-[#FDECEF] text-[#DE688E] shadow-xs"
                          : "text-[#55505C] hover:text-[#141414] hover:bg-gray-50"
                      }`}
                    >
                      <User
                        size={19}
                        strokeWidth={pathname === "/profile" ? 2.4 : 2}
                        className={pathname === "/profile" ? "text-[#DE688E]" : "text-[#7A7382]"}
                      />
                      <span>Profile</span>
                    </Link>
                  </li>
                </ul>
              </nav>
            </div>

            {/* Bottom logout / user info in drawer */}
            <div className="pt-4 border-t border-gray-100">
              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-3 px-3 py-2.5 rounded-2xl text-[#6B6375] hover:text-[#DE688E] hover:bg-[#FDECEF]/60 transition font-bold text-sm w-full cursor-pointer group"
              >
                <div className="w-8 h-8 rounded-lg bg-[#DE688E]/10 text-[#DE688E] flex items-center justify-center group-hover:bg-[#DE688E] group-hover:text-white transition">
                  <LogOut size={16} />
                </div>
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- MOBILE BOTTOM NAVIGATION BAR (< 1024px) ---------------- */}
      <nav
        aria-label="Mobile Navigation"
        className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-gray-200/80 px-2 py-1.5 flex items-center justify-around shadow-[0_-4px_20px_rgba(0,0,0,0.05)]"
      >
        {bottomNavItems.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || (href === "/ingredients" && pathname.startsWith("/product-analysis"));
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center justify-center min-w-[56px] py-1 px-1 rounded-xl transition-colors duration-150 ${
                isActive ? "text-[#DE688E]" : "text-[#7A7382] hover:text-[#141414]"
              }`}
            >
              <div
                className={`p-1 rounded-full transition-all ${
                  isActive ? "bg-[#FDECEF]" : ""
                }`}
              >
                <Icon size={19} strokeWidth={isActive ? 2.4 : 1.8} />
              </div>
              <span className={`text-[10px] tracking-tight mt-0.5 ${isActive ? "font-bold" : "font-medium"}`}>
                {label}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* ---------------- DESKTOP SIDEBAR (>= 1024px) ---------------- */}
      <aside className="hidden lg:flex w-64 min-h-screen bg-white/80 backdrop-blur-md border-r border-gray-100 flex-col justify-between p-6 shrink-0 sticky top-0 h-screen overflow-y-auto">
        <div>
          {/* Brand Header */}
          <div className="flex items-center gap-3 mb-8 px-2">
            <Link href="/dashboard" className="flex items-center gap-2.5 group" aria-label="SkinWise Home">
              <Image
                src="/images/logo2.png"
                alt="SkinWise logo"
                width={36}
                height={36}
                className="w-9 h-9 object-contain"
              />
              <span
                className="text-2xl font-bold text-[#DE688E] tracking-tight"
                style={{ fontFamily: "Georgia, serif" }}
              >
                SkinWise
              </span>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav>
            <ul className="space-y-2">
              {navigation.map(({ href, label, icon: Icon }) => {
                const isActive = pathname === href;
                return (
                  <li key={href}>
                    <Link
                      href={href}
                      className={`flex items-center gap-3.5 px-4 py-3 rounded-full text-sm font-semibold transition-all duration-200 ${
                        isActive
                          ? "bg-[#FDECEF] text-[#DE688E] shadow-sm"
                          : "text-[#55505C] hover:text-[#141414] hover:bg-gray-50/80"
                      }`}
                    >
                      <Icon
                        size={20}
                        strokeWidth={isActive ? 2.4 : 2}
                        className={isActive ? "text-[#DE688E]" : "text-[#7A7382]"}
                      />
                      <span>{label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </div>

        {/* Bottom Area: Logout on Profile page, Profile Card on others */}
        <div className="pt-6 border-t border-gray-100">
          {isProfilePage ? (
            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center gap-3 px-3 py-2.5 rounded-2xl text-[#6B6375] hover:text-[#DE688E] hover:bg-[#FDECEF]/60 transition font-bold text-sm w-full cursor-pointer group"
            >
              <div className="w-8 h-8 rounded-lg bg-[#DE688E]/10 text-[#DE688E] flex items-center justify-center group-hover:bg-[#DE688E] group-hover:text-white transition">
                <LogOut size={16} />
              </div>
              <span>Logout →</span>
            </button>
          ) : (
            <Link
              href="/profile"
              className="flex items-center gap-3 px-2 py-2 rounded-2xl hover:bg-gray-50/80 transition group"
            >
              {avatarUrl ? (
                <img
                  src={avatarUrl}
                  alt={displayName}
                  className="w-10 h-10 rounded-full object-cover border border-pink-100"
                />
              ) : (
                <div className="w-10 h-10 rounded-full bg-[#F4EBE8] text-[#A85175] flex items-center justify-center shrink-0">
                  <User size={20} />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-[#141414] truncate">{displayName}</p>
                <span className="text-xs text-[#7A7382] group-hover:text-[#DE688E] transition font-medium">
                  View Products →
                </span>
              </div>
            </Link>
          )}
        </div>
      </aside>
    </>
  );
}
