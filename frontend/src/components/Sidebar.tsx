"use client";

import Link from "next/link";
import {
  LayoutDashboard,
  Camera,
  Sparkles,
  Search,
  ShoppingBag,
  ChartSpline,
  History,
  User,
  Settings,
} from "lucide-react";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="sidebar-logo">SkinWise</h1>
      </div>

      <nav className="sidebar-nav">
        <ul>
          <li>
            <Link href="/dashboard" className="sidebar-link">
              <LayoutDashboard size={18} className="mr-2" /> Dashboard
            </Link>
          </li>
          <li>
            <Link href="/analysis" className="sidebar-link">
              <Camera size={18} className="mr-2" /> AI Skin Analysis
            </Link>
          </li>
          <li>
            <Link href="/routine" className="sidebar-link">
              <Sparkles size={18} className="mr-2" /> Personalized Routine
            </Link>
          </li>
          <li>
            <Link href="/ingredients" className="sidebar-link">
              <Search size={18} className="mr-2" /> Ingredient Checker
            </Link>
          </li>
          <li>
            <Link href="/recommendations" className="sidebar-link">
              <ShoppingBag size={18} className="mr-2" /> Product Recommendations
            </Link>
          </li>
          <li>
            <Link href="/progress" className="sidebar-link">
              <ChartSpline size={18} className="mr-2" /> Progress & Insights
            </Link>
          </li>
          <li>
            <Link href="/history" className="sidebar-link">
              <History size={18} className="mr-2" /> Analysis History
            </Link>
          </li>
        </ul>

        <hr className="sidebar-divider" />

        <ul>
          <li>
            <Link href="/profile" className="sidebar-link">
              <User size={18} className="mr-2" /> Profile
            </Link>
          </li>
          <li>
            <Link href="/settings" className="sidebar-link">
              <Settings size={18} className="mr-2" /> Settings
            </Link>
          </li>
        </ul>
      </nav>
    </aside>
  );
}
