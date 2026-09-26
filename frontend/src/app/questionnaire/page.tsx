"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Questionnaire from "./Questionnaire";

function QuestionnairePageContent() {
  const searchParams = useSearchParams();
  return <Questionnaire searchParams={searchParams} />;
}

export default function QuestionnairePage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
      <QuestionnairePageContent />
    </Suspense>
  );
}
