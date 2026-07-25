"use client"; 

import React from "react";

export default function QuestionnaireLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <section className="min-h-screen flex items-center justify-center bg-gradient-to-r from-creamGradient1 to-creamGradient2">
      {children}
    </section>
  );
}
