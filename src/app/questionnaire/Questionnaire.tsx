"use client";

import { useState } from "react";
import './questionnaire.css';
import {
  ageRanges, genders, countries, climates, skinTypes, sleepOptions, dietOptions, stressLevels, skinConcerns, sensitiveOptions, morningRoutineOptions, nightRoutineOptions, goals,
} from "./questions";

import {
  User, Calendar, MoonStar, HeartPulse, Sparkles, Camera, Venus, Mars, Users, Droplets, Salad, CloudSun, Globe, ShieldAlert, ShieldCheck, Target, Sun, Moon, ArrowRight, ArrowLeft, ChevronDown,
} from "lucide-react";

type QuestionnaireData = {
  ageRange: string; gender: string; country: string; climate: string; sleep: string; waterIntake: number; stress: string; diet: string; skinType: string; skinConcerns: string[]; sensitiveSkin: string; morningRoutine: string[]; nightRoutine: string[]; currentProducts: string[]; goals: string[];
};

const initialFormData: QuestionnaireData = {
  ageRange: "", gender: "", country: "", climate: "", sleep: "", waterIntake: 2, stress: "", diet: "", skinType: "", skinConcerns: [], sensitiveSkin: "", morningRoutine: [], nightRoutine: [], currentProducts: [], goals: [],
};

const stepInfo = {
  1: { icon: User, eyebrow: "Step 1", title: "Personal Information", helper: "Tell us a bit about yourself." },
  2: { icon: MoonStar, eyebrow: "Step 2", title: "Lifestyle", helper: "Your daily habits affect your skin." },
  3: { icon: HeartPulse, eyebrow: "Step 3", title: "Skin Profile", helper: "Choose your skin type and concerns." },
  4: { icon: Sparkles, eyebrow: "Step 4", title: "Routine", helper: "What products do you currently use?" },
  5: { icon: Target, eyebrow: "Step 5", title: "Goals", helper: "What do you want to improve?" },
  6: { icon: Camera, eyebrow: "Step 6", title: "AI Face Analysis", helper: "Let’s scan and finalize your profile." },
};

export default function Questionnaire() {
  const [step, setStep] = useState(1);
  const totalSteps = 6;
  const [formData, setFormData] = useState<QuestionnaireData>(initialFormData);
  const [error, setError] = useState<string | null>(null);
  const [productInput, setProductInput] = useState("");

  const nextStep = () => {
    setError(null);
    setStep((s) => Math.min(s + 1, totalSteps));
  };

  const prevStep = () => {
    setError(null);
    setStep((s) => Math.max(s - 1, 1));
  };

  const addProduct = () => {
    const trimmed = productInput.trim();
    if (!trimmed) return;
    if (formData.currentProducts.includes(trimmed)) return;
    updateField("currentProducts", [...formData.currentProducts, trimmed]);
    setProductInput("");
  };

  const removeProduct = (product: string) => {
    updateField("currentProducts", formData.currentProducts.filter((p) => p !== product));
  };

  const startAnalysis = () => {
    console.log("Questionnaire complete, profile ready:", formData);
  };

  const updateField = <K extends keyof QuestionnaireData>(key: K, value: QuestionnaireData[K]) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const toggleArrayValue = (key: keyof QuestionnaireData, value: string) => {
    setFormData((prev) => {
      const current = prev[key] as string[];
      const updated = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      return { ...prev, [key]: updated };
    });
  };

  const OptionCard = ({ children, selected, onClick }: { children: React.ReactNode; selected: boolean; onClick: () => void }) => (
    <button
      type="button"
      aria-pressed={selected}
      className={`option-card cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:border-pink-300 hover:shadow-md ${selected ? "option-card-selected" : ""}`}
      onClick={onClick}
    >
      {selected && <span className="option-check">✓</span>}
      {children}
    </button>
  );

  const OptionPill = ({ children, selected, onClick }: { children: React.ReactNode; selected: boolean; onClick: () => void }) => (
    <button
      type="button"
      aria-pressed={selected}
      className={`option-pill cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:border-pink-300 hover:shadow-md inline-flex items-center ${selected ? "option-pill-selected" : ""}`}
      onClick={onClick}
    >
      {children}
    </button>
  );

  const SelectField = ({
    icon: Icon,
    value,
    onChange,
    placeholder,
    options,
  }: {
    icon: React.ElementType;
    value: string;
    onChange: (v: string) => void;
    placeholder: string;
    options: readonly string[];
  }) => (
    <div className="relative">
      <Icon size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-pink-400 pointer-events-none" />
      <select
        className="input-glass w-full appearance-none pl-11 pr-10"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
      <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-textSecondary pointer-events-none" />
    </div>
  );

  const StepHeader = () => {
    const info = stepInfo[step as keyof typeof stepInfo];
    const Icon = info.icon;
    return (
      <div className="flex items-start gap-4 mb-8">
        <span className="icon-badge"><Icon size={22} strokeWidth={2} /></span>
        <div>
          <p className="eyebrow-label">{info.eyebrow}</p>
          <h2 className="text-xl sm:text-2xl font-semibold text-[#2D2D2D] mt-1">{info.title}</h2>
          <p className="text-sm text-textSecondary mt-1">{info.helper}</p>
        </div>
      </div>
    );
  };

  return (
    <main className="flex w-full min-h-screen items-center justify-center bg-gradient-to-r from-creamGradient1 to-creamGradient2 px-4 py-10 sm:px-6 lg:px-8">
      <div className="w-full max-w-3xl flex flex-col items-center">
        {/* Progress */}
        <div className="w-full flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl sm:text-4xl font-semibold text-[#2D2D2D]">Skin Questionnaire</h1>
            <p className="text-sm sm:text-base text-textSecondary mt-2 max-w-md">
              Help us understand your skin better. Your answers will help SkinWise personalize your skincare routine.
            </p>
          </div>
          <div className="w-full sm:w-48 shrink-0">
            <p className="text-xs font-medium text-textSecondary mb-2 sm:text-right">
              Step {step} of {totalSteps} &middot; {Math.round((step / totalSteps) * 100)}%
            </p>
            <div className="w-full h-1.5 bg-white/50 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-pink-300 to-pink-400 rounded-full transition-all duration-300" style={{ width: `${(step / totalSteps) * 100}%` }} />
            </div>
          </div>
        </div>

        {/* Form */}
        <div className="w-full h-full p-6 sm:p-8 lg:p-10 flex flex-col justify-between">
          <form className="flex flex-col gap-8 sm:gap-10 overflow-y-auto">
            <StepHeader />

            {step === 1 && (
              <>
                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Age Range</h3>
                  <SelectField
                    icon={Calendar}
                    value={formData.ageRange}
                    onChange={(v) => updateField("ageRange", v)}
                    placeholder="Select age range"
                    options={ageRanges}
                  />
                </section>

                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Gender</h3>
                  <div className="flex flex-wrap gap-3">
                    <OptionPill selected={formData.gender === "Male"} onClick={() => updateField("gender", "Male")}>
                      <Mars size={18} className="mr-2" /> Male
                    </OptionPill>
                    <OptionPill selected={formData.gender === "Female"} onClick={() => updateField("gender", "Female")}>
                      <Venus size={18} className="mr-2" /> Female
                    </OptionPill>
                    <OptionPill selected={formData.gender === "Other"} onClick={() => updateField("gender", "Other")}>
                      <Users size={18} className="mr-2" /> Other
                    </OptionPill>
                  </div>
                </section>

                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Country</h3>
                  <SelectField
                    icon={Globe}
                    value={formData.country}
                    onChange={(v) => updateField("country", v)}
                    placeholder="Select country"
                    options={countries}
                  />
                </section>

                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Climate / Region</h3>
                  <SelectField
                    icon={CloudSun}
                    value={formData.climate}
                    onChange={(v) => updateField("climate", v)}
                    placeholder="Select climate"
                    options={climates}
                  />
                </section>
              </>
            )}

            {step === 2 && (
              <>
                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Sleep Duration</h3>
                  <p className="question-description mb-4">How many hours do you usually sleep?</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {sleepOptions.map((opt) => (
                      <OptionCard
                        key={opt}
                        selected={formData.sleep === opt}
                        onClick={() => updateField("sleep", opt)}
                      >
                        <MoonStar size={18} className="mr-2 text-pink-400" /> {opt}
                      </OptionCard>
                    ))}
                  </div>
                </section>

                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D] flex items-center gap-2">
                    Water Intake <Droplets size={18} className="text-pink-400" />
                  </h3>
                  <p className="question-description mb-4">How much water do you drink daily?</p>
                  <input
                    type="range"
                    min="0"
                    max="5"
                    step="0.5"
                    className="w-full slider-track"
                    value={formData.waterIntake}
                    onChange={(e) => updateField("waterIntake", Number(e.target.value))}
                  />
                  <p className="text-xs mt-3 inline-flex items-center gap-1.5 text-textSecondary bg-white/50 px-3 py-1 rounded-full">
                    <Droplets size={12} className="text-pink-400" /> {formData.waterIntake} L / day
                  </p>
                </section>

                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Stress Level</h3>
                  <p className="question-description mb-4">Stress can affect skin recovery.</p>
                  <div className="flex flex-wrap gap-3">
                    {stressLevels.map((level) => (
                      <OptionPill
                        key={level}
                        selected={formData.stress === level}
                        onClick={() => updateField("stress", level)}
                      >
                        <HeartPulse size={18} className="mr-2 text-pink-400" /> {level}
                      </OptionPill>
                    ))}
                  </div>
                </section>

                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Diet</h3>
                  <p className="question-description mb-4">Your diet influences skin health.</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {dietOptions.map((opt) => (
                      <OptionCard
                        key={opt}
                        selected={formData.diet === opt}
                        onClick={() => updateField("diet", opt)}
                      >
                        <Salad size={18} className="mr-2 text-pink-400" /> {opt}
                      </OptionCard>
                    ))}
                  </div>
                </section>
              </>
            )}

            {step === 3 && (
              <>
                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Skin Type</h3>
                  <p className="question-description mb-4">Select the type that best describes your skin.</p>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                    {skinTypes.map((type) => (
                      <OptionCard
                        key={type}
                        selected={formData.skinType === type}
                        onClick={() => updateField("skinType", type)}
                      >
                        <Sparkles size={18} className="mr-2 text-pink-400" /> {type}
                      </OptionCard>
                    ))}
                  </div>
                </section>

                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Skin Concerns</h3>
                  <p className="question-description mb-4">Choose all concerns that apply.</p>
                  <div className="flex flex-wrap gap-2">
                    {skinConcerns.map((c) => (
                      <OptionPill
                        key={c}
                        selected={formData.skinConcerns.includes(c)}
                        onClick={() => toggleArrayValue("skinConcerns", c)}
                      >
                        <ShieldAlert size={18} className="mr-2 text-pink-400" /> {c}
                      </OptionPill>
                    ))}
                  </div>
                </section>

                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Sensitive Skin?</h3>
                  <p className="question-description mb-4">Do you often react to products?</p>
                  <div className="flex flex-wrap gap-3">
                    {sensitiveOptions.map((opt) => (
                      <OptionPill
                        key={opt}
                        selected={formData.sensitiveSkin === opt}
                        onClick={() => updateField("sensitiveSkin", opt)}
                      >
                        <ShieldAlert size={18} className="mr-2 text-pink-400" /> {opt}
                      </OptionPill>
                    ))}
                  </div>
                </section>
              </>
            )}
            {step === 4 && (
              <>
                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Morning Routine</h3>
                  <p className="question-description mb-4">Select the products you currently use in the morning.</p>
                  <div className="flex flex-wrap gap-2">
                    {morningRoutineOptions.map((item) => (
                      <OptionPill
                        key={item}
                        selected={formData.morningRoutine.includes(item)}
                        onClick={() => toggleArrayValue("morningRoutine", item)}
                      >
                        <Sun size={18} className="mr-2 text-pink-400" /> {item}
                      </OptionPill>
                    ))}
                  </div>
                </section>

                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Night Routine</h3>
                  <p className="question-description mb-4">Select the products you currently use at night.</p>
                  <div className="flex flex-wrap gap-2">
                    {nightRoutineOptions.map((item) => (
                      <OptionPill
                        key={item}
                        selected={formData.nightRoutine.includes(item)}
                        onClick={() => toggleArrayValue("nightRoutine", item)}
                      >
                        <Moon size={18} className="mr-2 text-pink-400" /> {item}
                      </OptionPill>
                    ))}
                  </div>
                </section>

                <section>
                  <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Products Currently Using</h3>
                  <p className="question-description mb-4">Add any other products you use regularly.</p>
                  <div className="flex gap-2 mb-3">
                    <input
                      type="text"
                      className="input-glass flex-1"
                      placeholder="e.g. Cleanser"
                      value={productInput}
                      onChange={(e) => setProductInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addProduct();
                        }
                      }}
                    />
                    <button
                      type="button"
                      className="btn shrink-0 rounded-full bg-pink-300 text-white hover:bg-pink-400 transition-all duration-200 hover:shadow-md px-5"
                      onClick={addProduct}
                    >
                      + Add
                    </button>
                  </div>
                  {formData.currentProducts.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {formData.currentProducts.map((product) => (
                        <span key={product} className="option-pill option-pill-selected inline-flex items-center gap-2 flex-none">
                          <Sparkles size={16} className="text-pink-400" /> {product}
                          <button type="button" aria-label={`Remove ${product}`} className="hover:text-pink-500 transition-colors" onClick={() => removeProduct(product)}>
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </section>
              </>
            )}

            {step === 5 && (
              <section>
                <h3 className="text-base sm:text-lg font-semibold mb-3 text-[#2D2D2D]">Skin Goals</h3>
                <p className="question-description mb-4">What do you want to improve?</p>
                <div className="grid grid-cols-2 gap-3">
                  {goals.map((g) => (
                    <OptionCard
                      key={g}
                      selected={formData.goals.includes(g)}
                      onClick={() => toggleArrayValue("goals", g)}
                    >
                      <Target size={18} className="mr-2 text-pink-400" /> {g}
                    </OptionCard>
                  ))}
                </div>
              </section>
            )}

            {step === 6 && (
              <section className="flex flex-col items-center text-center py-10">
                <span className="icon-badge mb-4">
                  <Camera size={26} className="text-pink-400" />
                </span>
                <h3 className="text-lg font-semibold mb-2 text-[#2D2D2D]">AI Face Analysis</h3>
                <p className="text-sm text-textSecondary mb-6 max-w-xs">
                  Your questionnaire is complete. Let’s analyze your skin.
                </p>
                <button
                  type="button"
                  className="btn rounded-full bg-pink-300 text-white hover:bg-pink-400 transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 px-10 py-3 text-base flex items-center gap-2"
                  onClick={startAnalysis}
                >
                  <Camera size={18} /> Start Analysis
                </button>
              </section>
            )}
          </form>

          {error && <p className="text-sm text-red-500 mt-4">{error}</p>}

          {/* Navigation */}
          <div className="flex justify-between items-center mt-8 pt-6 border-t border-white/40">
            <button
              type="button"
              className="btn rounded-full h-11 px-6 bg-white/50 text-[#2D2D2D] hover:bg-white/70 transition-all duration-200 flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
              onClick={prevStep}
              disabled={step === 1}
            >
              <ArrowLeft size={18} /> Previous
            </button>

            {step < totalSteps && (
              <button
                type="button"
                className="btn rounded-full h-11 px-6 bg-pink-300 text-white hover:bg-pink-400 transition-all duration-200 hover:shadow-md flex items-center gap-2"
                onClick={nextStep}
              >
                Continue <ArrowRight size={18} />
              </button>
            )}
          </div>
        </div>
        {/* Privacy Note */}
        <div className="privacy-note w-full mt-6 flex items-start gap-3">
          <span className="icon-badge" style={{ background: "rgba(167, 139, 250, 0.18)", color: "#8B5CF6" }}>
            <ShieldCheck size={18} />
          </span>
          <div>
            <p className="text-sm font-semibold text-[#2D2D2D]">Your privacy is important to us</p>
            <p className="text-xs text-textSecondary mt-1">
              All responses are securely stored and used only to personalize your skin analysis and recommendations.
            </p>
          </div>
        </div>
      </div>
    </main >
  );
}