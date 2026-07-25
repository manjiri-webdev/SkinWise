"use client";

import { Bell, User, Camera, HeartPulse, CalendarDays, AlertTriangle, Sparkles, ChartSpline, History } from "lucide-react";

export default function Dashboard() {
  return (
    <main className="flex w-full min-h-screen items-center justify-center bg-gradient-to-r from-creamGradient1 to-creamGradient2 px-4 py-10 sm:px-6 lg:px-8">
      <div className="w-full max-w-6xl flex flex-col gap-8">

        {/* Header */}
        <header className="flex justify-between items-center glass p-6 rounded-xl">
          <div>
            <h1 className="text-2xl font-semibold text-[#2D2D2D]">Good Morning, Manjiri ☀️</h1>
            <p className="text-sm text-textSecondary mt-1">Your personalized skincare companion</p>
          </div>
          <div className="flex items-center gap-4">
            <Bell size={22} className="text-[#2D2D2D]" />
            <User size={28} className="text-[#2D2D2D]" />
          </div>
        </header>

        {/* Quick Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="glass p-4 rounded-xl text-center">
            <HeartPulse size={22} className="text-pink-400 mx-auto mb-2" />
            <h3 className="text-sm font-semibold">Skin Health Score</h3>
            <p className="text-xl font-bold text-pink-400">82 / 100</p>
            <p className="text-green-600 text-sm">Healthy</p>
          </div>
          <div className="glass p-4 rounded-xl text-center">
            <CalendarDays size={22} className="text-pink-400 mx-auto mb-2" />
            <h3 className="text-sm font-semibold">Today's Routine</h3>
            <p className="text-xl font-bold text-pink-400">3 / 5 Steps</p>
            <p className="text-sm text-textSecondary">60%</p>
          </div>
          <div className="glass p-4 rounded-xl text-center">
            <AlertTriangle size={22} className="text-pink-400 mx-auto mb-2" />
            <h3 className="text-sm font-semibold">Primary Concern</h3>
            <p className="text-xl font-bold text-pink-400">Acne</p>
            <p className="text-sm text-textSecondary">Moderate</p>
          </div>
          <div className="glass p-4 rounded-xl text-center">
            <Camera size={22} className="text-pink-400 mx-auto mb-2" />
            <h3 className="text-sm font-semibold">Next Analysis</h3>
            <p className="text-xl font-bold text-pink-400">Today</p>
            <p className="text-sm text-textSecondary">Recommended</p>
          </div>
        </div>

        {/* AI Skin Analysis */}
        <div className="glass p-6 rounded-xl text-center">
          <Camera size={40} className="text-pink-400 mx-auto mb-4" />
          <h2 className="text-lg font-semibold mb-2">AI Skin Analysis</h2>
          <p className="text-sm text-textSecondary mb-4">Scan your face to detect:</p>
          <ul className="text-sm text-left max-w-sm mx-auto mb-4 space-y-1">
            <li>• Acne</li>
            <li>• Pigmentation</li>
            <li>• Hydration</li>
            <li>• Oiliness</li>
            <li>• Redness</li>
          </ul>
          <button className="btn bg-pink-300 text-white hover:bg-pink-400">Start Scan</button>
        </div>

        {/* Personalized Routine */}
        <div className="glass p-6 rounded-xl">
          <h2 className="text-lg font-semibold mb-4">Today's Personalized Routine</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-semibold mb-2">Morning</h3>
              <ul className="text-sm space-y-1">
                <li>☐ Cleanser</li>
                <li>☐ Serum</li>
                <li>☑ Moisturizer</li>
                <li>☑ Sunscreen</li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold mb-2">Night</h3>
              <ul className="text-sm space-y-1">
                <li>☑ Cleanser</li>
                <li>☐ Retinol</li>
                <li>☐ Moisturizer</li>
              </ul>
            </div>
          </div>
        </div>

        {/* AI Insights */}
        <div className="glass p-6 rounded-xl">
          <h2 className="text-lg font-semibold mb-4">Personalized AI Insights</h2>
          <ul className="text-sm space-y-1">
            <li>✓ Mild dehydration detected</li>
            <li>✓ Slight redness around cheeks</li>
            <li>✓ Oil production increased</li>
            <li>✓ Barrier looks healthy</li>
            <li>✓ UV exposure may affect pigmentation</li>
          </ul>
          <button className="btn bg-pink-300 text-white hover:bg-pink-400 mt-4">View Detailed Analysis</button>
        </div>

        {/* Progress Snapshot */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="glass p-4 rounded-xl text-center">
            <h3 className="text-sm font-semibold">Routine Streak</h3>
            <p className="text-xl font-bold text-pink-400">8 Days</p>
          </div>
          <div className="glass p-4 rounded-xl text-center">
            <h3 className="text-sm font-semibold">Skin Health</h3>
            <p className="text-xl font-bold text-pink-400">+12%</p>
            <p className="text-xs text-textSecondary">Last 30 Days</p>
          </div>
          <div className="glass p-4 rounded-xl text-center">
            <h3 className="text-sm font-semibold">Scans</h3>
            <p className="text-xl font-bold text-pink-400">14</p>
            <p className="text-xs text-textSecondary">Completed</p>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="glass p-6 rounded-xl">
          <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
          <ul className="text-sm space-y-2">
            <li>Yesterday — ✓ Face Scan Completed</li>
            <li>Today — ✓ Morning Routine Completed</li>
            <li>2 Days Ago — ✓ Ingredient Checked</li>
            <li>3 Days Ago — ✓ New Recommendation Generated</li>
          </ul>
        </div>

        {/* Daily Tip */}
        <div className="glass p-6 rounded-xl">
          <h2 className="text-lg font-semibold mb-2">Daily Skin Tip</h2>
          <p className="text-sm">💧 Drink 2L water today.</p>
          <p className="text-sm">🙌 Avoid touching your face frequently.</p>
          <p className="text-sm">☀ Wear SPF when outdoors.</p>
        </div>

      </div>
    </main>
  );
}
