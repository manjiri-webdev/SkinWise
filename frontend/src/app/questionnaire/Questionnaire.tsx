"use client";

import { useEffect, useState, useRef } from "react";
import { getCurrentLocation } from "@/services/location";
import { fetchWeather } from "@/lib/weather";
import { supabase } from "@/lib/supabase";
import {
  updateProfile,
  getProfile,
  UserProfile,
  getProductHistory,
  processQuestionnaireProducts,
  addEnvironmentHistory,
  updateProductHistory,
} from "@/services/personalization";
import { useRouter } from "next/navigation";
import "./questionnaire.css";

import {
  ageRanges,
  genders,
  sleepOptions,
  hydrationOptions,
  stressLevels,
  eatingHabits,
  skinTypes,
  skinConcerns,
  sensitiveSkin,
  morningRoutine,
  nightRoutine,
  goals,
  currentProductTypes,
  reactionOptions,
} from "./questions";

import {
  User,
  Globe,
  Venus,
  Mars,
  Users,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
  Smile,
  ScanFace,
  Layers,
  Target,
  Camera,
  Loader2,
  ChevronDown,
  X,
  Plus,
} from "lucide-react";

type QuestionnaireData = {
  ageRanges: string;
  genders: string;
  city: string;
  sleep: string;
  hydration: string;
  stress: string;
  eatingHabits: string[];
  skinTypes: string;
  skinConcerns: string[];
  sensitiveSkin: string;
  hasRoutine: string;
  morningRoutine: string[];
  nightRoutine: string[];
  usingProducts: string;
  currentProducts: {
    type: string;
    productName: string;
    brand: string;
    reaction: string;
    notes: string;
  }[];
  goals: string[];
  latitude: number | null;
  longitude: number | null;
  temperature: number | null;
  humidity: number | null;
  weather: string;
};

const initialFormData: QuestionnaireData = {
  ageRanges: "",
  genders: "",
  city: "",
  sleep: "",
  hydration: "",
  stress: "",
  eatingHabits: [],
  skinTypes: "",
  skinConcerns: [],
  sensitiveSkin: "",
  hasRoutine: "",
  morningRoutine: [],
  nightRoutine: [],
  usingProducts: "",
  currentProducts: [],
  goals: [],
  latitude: null,
  longitude: null,
  temperature: null,
  humidity: null,
  weather: "",
};

const stepInfo = {
  1: { icon: User, status: "Step 1", title: "Personal Information", helper: "Tells us bit about yourself" },
  2: { icon: Smile, status: "Step 2", title: "Lifestyle", helper: "Your daily habits affect your skin health" },
  3: { icon: ScanFace, status: "Step 3", title: "Skin Profile", helper: "Tell us about your skin so we can personalize your recommendations" },
  4: { icon: Layers, status: "Step 4", title: "Routine", helper: "Tell us about your current skincare habits and products" },
  5: { icon: Target, status: "Step 5", title: "Skin Goals", helper: "What would you like SkinWise to help you achieve?" },
  6: { icon: Camera, status: "Step 6", title: "AI Face Analysis", helper: "Your questionnaire is complete! Let's analyze your skin using AI" },
};

function CustomSelect({
  value,
  onChange,
  options,
  placeholder = "Select an option",
  className = "",
}: {
  value: string;
  onChange: (val: string) => void;
  options: string[];
  placeholder?: string;
  className?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-3 rounded-2xl bg-white border border-white/90 text-left text-xs sm:text-sm shadow-[0_4px_14px_rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-[#C4A2FA]/60 flex items-center justify-between cursor-pointer transition active:scale-[0.99]"
      >
        <span className={value ? "text-[#141414] font-medium" : "text-[#8E8895]"}>
          {value || placeholder}
        </span>
        <ChevronDown
          size={18}
          className={`text-[#141414] transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1.5 bg-white rounded-2xl border border-white/90 shadow-[0_12px_32px_rgba(0,0,0,0.12)] p-1.5 z-50 max-h-56 overflow-y-auto ques-scrollbar">
          {options.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => {
                onChange(option);
                setIsOpen(false);
              }}
              className={`w-full text-left px-4 py-2.5 rounded-xl text-xs sm:text-sm transition cursor-pointer flex items-center justify-between ${
                value === option
                  ? "bg-[#FDE8EE] text-[#DE688E] font-bold"
                  : "text-[#2D2D2D] hover:bg-[#F3EEFA] hover:text-[#141414]"
              }`}
            >
              <span>{option}</span>
              {value === option && <span className="w-2 h-2 rounded-full bg-[#DE688E]" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Questionnaire({ searchParams }: { searchParams: any }) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<QuestionnaireData>(initialFormData);
  const [error, setError] = useState<string | null>(null);
  const [productInput, setProductInput] = useState("");
  const [brandInput, setBrandInput] = useState("");
  const [selectedType, setSelectedType] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const router = useRouter();

  const isEditMode = searchParams?.get("mode") === "edit";
  const totalSteps = isEditMode ? 5 : 6;

  // Auto-scroll refs
  const cardTopRef = useRef<HTMLDivElement>(null);
  const step4ContainerRef = useRef<HTMLDivElement>(null);
  const routineSectionRef = useRef<HTMLDivElement>(null);
  const usingProductsSectionRef = useRef<HTMLDivElement>(null);
  const productInputSectionRef = useRef<HTMLDivElement>(null);
  const productsListBottomRef = useRef<HTMLDivElement>(null);
  const [canScrollStep4Down, setCanScrollStep4Down] = useState(false);

  const handleStep4Scroll = () => {
    const el = step4ContainerRef.current;
    if (!el) return;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 30;
    setCanScrollStep4Down(!isAtBottom && el.scrollHeight > el.clientHeight + 40);
  };

  // Auto-scroll to top of card on step transition
  useEffect(() => {
    if (cardTopRef.current) {
      cardTopRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    if (step4ContainerRef.current) {
      step4ContainerRef.current.scrollTop = 0;
    }
  }, [step]);

  // Check scroll state when step 4 content changes
  useEffect(() => {
    if (step === 4) {
      const timer = setTimeout(() => {
        handleStep4Scroll();
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [step, formData.hasRoutine, formData.usingProducts, formData.currentProducts.length]);

  const checkQuestionnaireCompletion = async () => {
    try {
      const result = await getProfile();
      if (result.success && result.data) {
        const profile = result.data;
        if (profile.questionnaire_completed && profile.face_analysis_completed && profile.onboarding_completed) {
          router.push("/dashboard");
        }
      }
    } catch (err) {
      console.error("Failed to check questionnaire completion:", err);
    }
  };

  useEffect(() => {
    if (isEditMode) {
      loadExistingProfile();
    } else {
      checkQuestionnaireCompletion();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditMode]);

  const loadExistingProfile = async () => {
    try {
      setIsLoadingProfile(true);
      const result = await getProfile();
      if (result.success && result.data) {
        const profile = result.data;

        const hasMorningRoutine = profile.morning_routine && profile.morning_routine.length > 0;
        const hasNightRoutine = profile.night_routine && profile.night_routine.length > 0;
        const hasProducts = profile.current_products && profile.current_products.length > 0;

        let currentProductsWithReactions: Array<{
          type: string;
          productName: string;
          brand: string;
          reaction: string;
          notes: string;
        }> = [];

        if (hasProducts) {
          try {
            const productHistoryResult = await getProductHistory();
            if (productHistoryResult.success && productHistoryResult.data) {
              currentProductsWithReactions = (profile.current_products || []).map((product: any) => {
                const historyEntry = productHistoryResult.data.find(
                  (entry: any) =>
                    entry.status === "current" &&
                    entry.product_name.toLowerCase() === (product.productName || product.product_name || "").toLowerCase()
                );

                return {
                  type: product.type || product.product_type || "",
                  productName: product.productName || product.product_name || "",
                  brand: product.brand || "",
                  reaction: historyEntry?.reaction || "none",
                  notes: historyEntry?.notes || "",
                };
              });
            } else {
              currentProductsWithReactions = (profile.current_products || []).map((product: any) => ({
                type: product.type || product.product_type || "",
                productName: product.productName || product.product_name || "",
                brand: product.brand || "",
                reaction: product.reaction || "none",
                notes: product.notes || "",
              }));
            }
          } catch (historyError) {
            console.error("[LOAD PROFILE] Failed to load product history:", historyError);
            currentProductsWithReactions = (profile.current_products || []).map((product: any) => ({
              type: product.type || product.product_type || "",
              productName: product.productName || product.product_name || "",
              brand: product.brand || "",
              reaction: product.reaction || "none",
              notes: product.notes || "",
            }));
          }
        }

        setFormData({
          ageRanges: profile.age_range || "",
          genders: profile.gender || "",
          city: profile.city || "",
          sleep: profile.sleep || "",
          hydration: profile.water_intake || "",
          stress: profile.stress_level || "",
          eatingHabits: profile.diet || [],
          skinTypes: profile.skin_type || "",
          skinConcerns: profile.skin_concerns || [],
          sensitiveSkin: profile.skin_sensitivity || "",
          hasRoutine: hasMorningRoutine || hasNightRoutine ? "Yes" : "No",
          morningRoutine: profile.morning_routine || [],
          nightRoutine: profile.night_routine || [],
          usingProducts: hasProducts ? "Yes" : "No",
          currentProducts: currentProductsWithReactions,
          goals: profile.skincare_goals || [],
          latitude: profile.latitude || null,
          longitude: profile.longitude || null,
          temperature: profile.temperature || null,
          humidity: profile.humidity || null,
          weather: profile.weather || "",
        });
      } else if (!result.exists) {
        router.push("/questionnaire");
      }
    } catch (err) {
      console.error("Failed to load profile:", err);
      const errorMessage = err instanceof Error ? err.message : "Failed to load your profile. Please try again.";
      setError(errorMessage);
    } finally {
      setIsLoadingProfile(false);
    }
  };

  const nextStep = async () => {
    if (step < totalSteps) {
      setError(null);

      if (step === 1) {
        if (!formData.ageRanges) {
          setError("Please select your age range.");
          return;
        }
        if (!formData.genders) {
          setError("Please select your gender.");
          return;
        }
        if (!formData.city.trim()) {
          setError("Please enter your city or use current location.");
          return;
        }
      }

      if (step === 2) {
        if (!formData.sleep) {
          setError("Please select your sleep duration.");
          return;
        }
        if (!formData.hydration) {
          setError("Please select your water intake.");
          return;
        }
        if (!formData.stress) {
          setError("Please select your stress level.");
          return;
        }
        if (formData.eatingHabits.length === 0) {
          setError("Please select at least one eating habit.");
          return;
        }
      }

      if (step === 3) {
        if (!formData.skinTypes) {
          setError("Please select your skin type.");
          return;
        }
        if (formData.skinConcerns.length === 0) {
          setError("Please select at least one skin concern.");
          return;
        }
        if (!formData.sensitiveSkin) {
          setError("Please answer the sensitive skin question.");
          return;
        }
      }

      if (step === 4) {
        if (!formData.hasRoutine) {
          setError("Please tell us if you follow a skincare routine.");
          return;
        }
        if (
          formData.hasRoutine === "Yes" &&
          formData.morningRoutine.length === 0 &&
          formData.nightRoutine.length === 0
        ) {
          setError("Please select at least one morning or night routine item.");
          return;
        }
        if (!formData.usingProducts) {
          setError("Please tell us if you're currently using skincare products.");
          return;
        }
        if (formData.usingProducts === "Yes" && formData.currentProducts.length === 0) {
          setError("Please add at least one product you're currently using.");
          return;
        }
      }

      if (step === 5) {
        if (formData.goals.length === 0) {
          setError("Please select at least one skincare goal.");
          return;
        }
      }

      if (step === totalSteps - 1) {
        const success = await handleSubmit();
        if (!success) return;

        if (isEditMode) {
          router.push("/dashboard");
          return;
        }
      }
      setStep(step + 1);
      // Auto-scroll to top when moving to next step
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const prevStep = () => {
    if (step > 1) {
      setError(null);
      setStep(step - 1);
      // Auto-scroll to top when moving to previous step
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleSubmit = async (): Promise<boolean> => {
    setIsSubmitting(true);
    setError(null);

    try {
      const {
        data: { user },
        error: userError,
      } = await supabase.auth.getUser();

      if (userError || !user) {
        setError("Please log in to save your profile.");
        return false;
      }

      const profileData = {
        age_range: formData.ageRanges,
        gender: formData.genders,
        city: formData.city,
        latitude: formData.latitude,
        longitude: formData.longitude,
        temperature: formData.temperature,
        humidity: formData.humidity,
        weather: formData.weather,

        sleep: formData.sleep,
        water_intake: formData.hydration,
        stress_level: formData.stress,
        diet: Array.isArray(formData.eatingHabits) ? formData.eatingHabits : [],

        skin_type: formData.skinTypes,
        skin_concerns: formData.skinConcerns,
        skin_sensitivity: formData.sensitiveSkin,

        morning_routine: formData.morningRoutine,
        night_routine: formData.nightRoutine,
        current_products: formData.currentProducts.map((product) => ({
          type: product.type,
          productName: product.productName,
          brand: product.brand,
          reaction: product.reaction,
          notes: product.notes,
        })),

        skincare_goals: formData.goals,
        ...(isEditMode ? {} : { questionnaire_completed: true }),
      };

      const result = await updateProfile(profileData);

      if (!result.success) {
        setError("Failed to update profile. Please try again.");
        return false;
      }

      if (formData.currentProducts.length > 0) {
        getProductHistory()
          .then((existingHistory) => {
            if (existingHistory.success) {
              const resolvedProductNames = existingHistory.data
                .filter((entry) => entry.status === "current" && entry.product_id != null)
                .map((entry) => entry.product_name.toLowerCase());

              const productsToResolve = formData.currentProducts.filter(
                (product) => !resolvedProductNames.includes(product.productName.toLowerCase())
              );

              if (productsToResolve.length > 0) {
                const productsToProcess = productsToResolve.map((product) => ({
                  product_name: product.productName,
                  product_type: product.type,
                  brand: product.brand,
                  reaction: product.reaction,
                  notes: product.notes,
                }));

                processQuestionnaireProducts(productsToProcess).catch((historyError) => {
                  console.error("Background product processing failed:", historyError);
                });
              }

              const existingResolvedProducts = formData.currentProducts.filter((product) =>
                resolvedProductNames.includes(product.productName.toLowerCase())
              );

              if (existingResolvedProducts.length > 0) {
                existingResolvedProducts.forEach((product) => {
                  const existingEntry = existingHistory.data.find(
                    (entry) =>
                      entry.status === "current" &&
                      entry.product_name.toLowerCase() === product.productName.toLowerCase()
                  );

                  if (existingEntry && existingEntry.id) {
                    updateProductHistory(existingEntry.id, {
                      product_name: product.productName,
                      product_type: product.type,
                      brand: product.brand,
                      reaction: product.reaction,
                      notes: product.notes,
                      started_at: existingEntry.started_at,
                      ended_at: existingEntry.ended_at,
                    }).catch((error) => {
                      console.error(`Failed to update reaction for ${product.productName}:`, error);
                    });
                  }
                });
              }
            }
          })
          .catch((historyError) => {
            console.error("Failed to fetch product history for background processing:", historyError);
          });
      }

      if (formData.city && (formData.temperature !== null || formData.humidity !== null || formData.weather)) {
        try {
          const today = new Date().toISOString().split("T")[0];
          await addEnvironmentHistory({
            temperature: formData.temperature ?? undefined,
            humidity: formData.humidity ?? undefined,
            weather: formData.weather || undefined,
            city: formData.city || undefined,
            recorded_date: today,
          });
        } catch (envError) {
          console.error("Failed to save environment history:", envError);
        }
      }

      return true;
    } catch (err) {
      console.error(err);
      setError("An error occurred while saving. Please try again.");
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateField = (field: keyof QuestionnaireData, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const toggleArrayValue = (field: keyof QuestionnaireData, value: string) => {
    const currentArray = (formData[field] as string[]) || [];

    if (currentArray.includes(value)) {
      updateField(
        field,
        currentArray.filter((item) => item !== value)
      );
    } else {
      updateField(field, [...currentArray, value]);
    }
  };

  const addProduct = () => {
    if (!selectedType || !productInput.trim()) return;

    const newProduct = {
      type: selectedType,
      productName: productInput.trim(),
      brand: brandInput.trim(),
      reaction: "none",
      notes: "",
    };

    const alreadyExists = formData.currentProducts.some(
      (item) =>
        item.type === newProduct.type &&
        item.productName.toLowerCase() === newProduct.productName.toLowerCase() &&
        item.brand.toLowerCase() === newProduct.brand.toLowerCase()
    );

    if (alreadyExists) return;

    updateField("currentProducts", [...formData.currentProducts, newProduct]);
    setSelectedType("");
    setProductInput("");
    setBrandInput("");

    // Auto-scroll so user immediately sees the newly added product with reaction and notes fields
    setTimeout(() => {
      productsListBottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      handleStep4Scroll();
    }, 120);
  };

  const removeProduct = (index: number) => {
    updateField(
      "currentProducts",
      formData.currentProducts.filter((_, i) => i !== index)
    );
  };

  const updateProductReaction = (index: number, reaction: string) => {
    const updatedProducts = formData.currentProducts.map((product, i) =>
      i === index ? { ...product, reaction } : product
    );
    updateField("currentProducts", updatedProducts);
  };

  const updateProductNotes = (index: number, notes: string) => {
    const updatedProducts = formData.currentProducts.map((product, i) =>
      i === index ? { ...product, notes } : product
    );
    updateField("currentProducts", updatedProducts);
  };

  const handleCurrentLocation = async () => {
    try {
      const location = await getCurrentLocation();
      const latitude = location.coords.latitude;
      const longitude = location.coords.longitude;
      updateField("latitude", latitude);
      updateField("longitude", longitude);

      const weatherData = await fetchWeather(latitude, longitude);
      updateField("city", weatherData.name.normalize("NFD").replace(/[\u0300-\u036f]/g, ""));
      updateField("temperature", weatherData.main.temp);
      updateField("humidity", weatherData.main.humidity);
      updateField("weather", weatherData.weather[0].main);
    } catch (error) {
      console.error(error);
      alert("Unable to access your location. Please enter your city manually");
    }
  };

  const currentStepInfo = stepInfo[step as keyof typeof stepInfo];
  const StepIcon = currentStepInfo.icon;

  return (
    <main className="min-h-screen w-full bg-[#F7F4EF] flex items-center justify-center p-3 sm:p-6 lg:p-8">
      <div className="w-full max-w-5xl flex flex-col md:flex-row items-center md:items-stretch justify-between gap-6 lg:gap-10">
        {/* Left Column: Progress & Intro */}
        <div className="w-full md:w-64 lg:w-72 shrink-0 flex flex-col justify-between py-2">
          <div>
            {isEditMode && (
              <button
                type="button"
                onClick={() => router.push("/dashboard")}
                className="text-xs text-pink-600 hover:text-pink-700 mb-3 flex items-center gap-1 font-medium transition cursor-pointer"
              >
                <ArrowLeft size={14} /> Back to dashboard
              </button>
            )}

            {/* Progress Bar */}
            <div className="flex justify-between items-center text-xs font-semibold text-[#141414] mb-2">
              <span>Step {step} of {totalSteps}</span>
              <span className="text-[#7E7775] font-normal">{Math.round((step / totalSteps) * 100)}%</span>
            </div>
            <div className="w-full h-3 rounded-full bg-white shadow-[inset_0_1px_3px_rgba(0,0,0,0.06)] p-0.5 mb-6">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[#F6A8B8] to-[#EE8EA3] transition-all duration-300"
                style={{ width: `${(step / totalSteps) * 100}%` }}
              />
            </div>

            {/* Title */}
            <h1
              className="text-2xl sm:text-3xl lg:text-4xl font-bold text-[#141414] leading-tight mb-3"
              style={{ fontFamily: "Georgia, serif" }}
            >
              {isEditMode ? "Edit Skin Profile" : <>Skin<br className="hidden sm:inline" /> Questionnaire</>}
            </h1>
            <p className="text-xs lg:text-sm text-[#666160] leading-relaxed max-w-xs">
              {isEditMode
                ? "Update your skin profile information. Your changes will be saved immediately."
                : "Helps us understand your skin better to personalize your skincare routine."}
            </p>
          </div>

          {/* Privacy badge */}
          <div className="flex items-start gap-2.5 mt-8 pt-4">
            <ShieldCheck size={18} className="text-[#141414] shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-[#141414] text-xs">Your privacy is important to us</p>
              <p className="text-[11px] text-[#736E6D] mt-0.5 leading-relaxed">
                All responses are securely stored and used only to personalize your skin analysis and recommendations.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Lavender Glass Card */}
        {isLoadingProfile ? (
          <div className="w-full flex-1 max-w-2xl ques-card flex flex-col items-center justify-center p-8 sm:p-10 min-h-[460px]">
            <Loader2 className="animate-spin text-[#DE688E] mb-3" size={32} />
            <p className="text-sm text-[#5A5555]">Loading your profile...</p>
          </div>
        ) : (
          <div ref={cardTopRef} className="w-full flex-1 max-w-2xl ques-card flex flex-col justify-between p-4 sm:p-7 lg:p-8 min-h-[460px] scroll-mt-6">
            {/* Card Header */}
            <div className="flex items-center gap-3.5 mb-5 pb-2">
              <div className="w-10 h-10 rounded-full bg-[#141414] text-white flex items-center justify-center shrink-0 shadow-sm">
                <StepIcon size={20} strokeWidth={2.2} />
              </div>
              <div>
                <p className="text-[11px] font-medium text-[#7A7382] leading-none mb-1">
                  {currentStepInfo.status}
                </p>
                <h2
                  className="text-xl sm:text-2xl font-bold text-[#141414] leading-tight"
                  style={{ fontFamily: "Georgia, serif" }}
                >
                  {currentStepInfo.title}
                </h2>
                <p className="text-xs text-[#7A7382] mt-0.5">
                  {currentStepInfo.helper}
                </p>
              </div>
            </div>

            {/* Card Form Body */}
            <div className="flex-1 flex flex-col justify-center">
              {/* STEP 1: Personal Information */}
              {step === 1 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 sm:gap-6 items-start">
                  {/* Left Column: Age & Gender */}
                  <div className="flex flex-col justify-between h-full">
                    <div>
                      <label className="font-semibold text-xs sm:text-sm text-[#141414] mb-2 block">
                        Age
                      </label>
                      <CustomSelect
                        value={formData.ageRanges}
                        onChange={(val) => updateField("ageRanges", val)}
                        options={ageRanges}
                        placeholder="select your age range"
                      />
                    </div>

                    <div className="mt-5">
                      <label className="font-semibold text-xs sm:text-sm text-[#141414] mb-2.5 block">
                        Gender
                      </label>
                      <div className="flex flex-wrap gap-2.5">
                        {[
                          {
                            label: "Female",
                            icon: (
                              <svg className="w-3.5 h-3.5 fill-current shrink-0" viewBox="0 0 24 24">
                                <path d="M12 2C9.79 2 8 3.79 8 6s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm0 6c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm0 4c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                              </svg>
                            ),
                          },
                          {
                            label: "Male",
                            icon: (
                              <svg className="w-3.5 h-3.5 fill-current shrink-0" viewBox="0 0 24 24">
                                <path d="M12 2C9.79 2 8 3.79 8 6s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm0 6c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm0 4c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                              </svg>
                            ),
                          },
                          {
                            label: "Other",
                            icon: (
                              <svg className="w-3.5 h-3.5 stroke-current fill-none shrink-0" strokeWidth="2.2" viewBox="0 0 24 24">
                                <circle cx="12" cy="9" r="5" />
                                <path d="M12 14v8M9 19h6" />
                              </svg>
                            ),
                          },
                        ].map((item) => {
                          const isSelected = formData.genders === item.label;
                          return (
                            <button
                              key={item.label}
                              type="button"
                              onClick={() => updateField("genders", item.label)}
                              className={`rounded-full px-4 sm:px-5 py-2 sm:py-2.5 text-xs sm:text-sm font-medium flex items-center gap-1.5 transition active:scale-[0.98] cursor-pointer ${
                                isSelected
                                  ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_4px_14px_rgba(238,142,163,0.38)] border border-white/80 font-semibold"
                                  : "bg-white text-[#141414] shadow-[0_3px_10px_rgba(0,0,0,0.04)] border border-white/80 hover:bg-white/90"
                              }`}
                            >
                              {item.icon}
                              <span>{item.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Location */}
                  <div>
                    <label className="font-semibold text-xs sm:text-sm text-[#141414] mb-1 block">
                      Your Location
                    </label>
                    <p className="text-[11px] sm:text-xs text-[#7A7382] mb-3 leading-relaxed">
                      We use your location to personalize skincare recommendations based on weather, humidity and UV levels
                    </p>

                    <div className="flex flex-col gap-2.5">
                      <button
                        type="button"
                        onClick={handleCurrentLocation}
                        className="btn w-full py-3 px-4 rounded-2xl bg-gradient-to-r from-[#A88BF5] to-[#C4A2FA] hover:from-[#9D7EF2] hover:to-[#BD98F8] text-white font-bold text-xs sm:text-sm shadow-[0_8px_20px_rgba(168,139,245,0.38)] border border-white/40 active:scale-[0.99] transition flex items-center justify-center gap-2 cursor-pointer"
                      >
                        <Globe size={18} className="text-white shrink-0" />
                        <span className="text-white">Use Current Location</span>
                      </button>

                      <div className="flex items-center gap-3 my-1">
                        <div className="flex-1 h-px bg-[#C7BED8]" />
                        <span className="text-[11px] sm:text-xs font-semibold text-[#7A7382]">
                          OR
                        </span>
                        <div className="flex-1 h-px bg-[#C7BED8]" />
                      </div>

                      <input
                        type="text"
                        placeholder="Enter your city (eg. mumbai)"
                        className="w-full px-5 py-3 rounded-2xl bg-white border border-white/90 text-[#141414] placeholder:text-[#8E8895] text-xs sm:text-sm shadow-[0_4px_14px_rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-[#C4A2FA]/60 transition"
                        value={formData.city}
                        onChange={(e) => updateField("city", e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 2: Lifestyle */}
              {step === 2 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-5 items-start">
                  {/* Left Column: Sleep Duration & Water Intake */}
                  <div className="space-y-3.5">
                    <div>
                      <label className="font-semibold text-xs text-[#141414] mb-1.5 block">
                        Sleep Duration
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {sleepOptions.map((item) => {
                          const isSelected = formData.sleep === item;
                          return (
                            <button
                              key={item}
                              type="button"
                              onClick={() => updateField("sleep", item)}
                              className={`rounded-xl py-1.5 sm:py-2 px-2.5 text-[11px] sm:text-xs font-medium text-center transition active:scale-[0.98] cursor-pointer flex items-center justify-center leading-snug ${
                                isSelected
                                  ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_3px_10px_rgba(238,142,163,0.32)] border border-white/80 font-semibold"
                                  : "bg-white text-[#2D2D2D] shadow-[0_2px_6px_rgba(0,0,0,0.03)] border border-white/90 hover:bg-white/95"
                              }`}
                            >
                              <span>{item}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div>
                      <label className="font-semibold text-xs text-[#141414] mb-1.5 block">
                        Water Intake
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {hydrationOptions.map((item) => {
                          const isSelected = formData.hydration === item;
                          return (
                            <button
                              key={item}
                              type="button"
                              onClick={() => updateField("hydration", item)}
                              className={`rounded-xl py-1.5 sm:py-2 px-2.5 text-[11px] sm:text-xs font-medium text-center transition active:scale-[0.98] cursor-pointer flex items-center justify-center leading-snug ${
                                isSelected
                                  ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_3px_10px_rgba(238,142,163,0.32)] border border-white/80 font-semibold"
                                  : "bg-white text-[#2D2D2D] shadow-[0_2px_6px_rgba(0,0,0,0.03)] border border-white/90 hover:bg-white/95"
                              }`}
                            >
                              <span>{item}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Stress Level & Eating Habits */}
                  <div className="space-y-3.5">
                    <div>
                      <label className="font-semibold text-xs text-[#141414] mb-1.5 block">
                        Stress Level
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        {stressLevels.map((item) => {
                          const isSelected = formData.stress === item;
                          return (
                            <button
                              key={item}
                              type="button"
                              onClick={() => updateField("stress", item)}
                              className={`rounded-xl py-1.5 sm:py-2 px-2 text-[11px] sm:text-xs font-medium text-center transition active:scale-[0.98] cursor-pointer flex items-center justify-center ${
                                isSelected
                                  ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_3px_10px_rgba(238,142,163,0.32)] border border-white/80 font-semibold"
                                  : "bg-white text-[#2D2D2D] shadow-[0_2px_6px_rgba(0,0,0,0.03)] border border-white/90 hover:bg-white/95"
                              }`}
                            >
                              <span>{item}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <label className="font-semibold text-xs text-[#141414]">
                          Eating Habits
                        </label>
                        <span className="text-[10px] text-[#7A7382]">Select all that apply</span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 sm:gap-2">
                        {eatingHabits.map((item) => {
                          const isSelected = formData.eatingHabits.includes(item);
                          return (
                            <button
                              key={item}
                              type="button"
                              onClick={() => toggleArrayValue("eatingHabits", item)}
                              className={`rounded-xl py-1.5 px-2 text-[10.5px] sm:text-[11px] font-medium text-center transition active:scale-[0.98] cursor-pointer flex items-center justify-center leading-snug ${
                                isSelected
                                  ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_3px_10px_rgba(238,142,163,0.32)] border border-white/80 font-semibold"
                                  : "bg-white text-[#2D2D2D] shadow-[0_2px_6px_rgba(0,0,0,0.03)] border border-white/90 hover:bg-white/95"
                              }`}
                            >
                              <span>{item}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 3: Skin Profile */}
              {step === 3 && (
                <div className="space-y-4">
                  <div>
                    <label className="font-semibold text-xs sm:text-sm text-[#141414] mb-1.5 block">
                      What is your skin type?
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {skinTypes.map((item) => {
                        const isSelected = formData.skinTypes === item;
                        return (
                          <button
                            key={item}
                            type="button"
                            onClick={() => updateField("skinTypes", item)}
                            className={`rounded-full px-4 py-2 text-xs sm:text-sm font-medium transition active:scale-[0.98] cursor-pointer ${
                              isSelected
                                ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_4px_14px_rgba(238,142,163,0.38)] border border-white/80 font-semibold"
                                : "bg-white text-[#141414] shadow-[0_3px_10px_rgba(0,0,0,0.04)] border border-white/80 hover:bg-white/90"
                            }`}
                          >
                            {item}
                          </button>
                        );
                      })}
                    </div>
                    <p className="text-[11px] text-[#7A7382] mt-1.5">
                      Don&apos;t worry if you&apos;re unsure. Our AI skin analysis can estimate it later.
                    </p>
                  </div>

                  <div>
                    <label className="font-semibold text-xs sm:text-sm text-[#141414] mb-1 block">
                      What are your main skin concerns?
                    </label>
                    <p className="text-[11px] text-[#7A7382] mb-2">Select all that apply</p>
                    <div className="flex flex-wrap gap-2">
                      {skinConcerns.map((item) => {
                        const isSelected = formData.skinConcerns.includes(item);
                        return (
                          <button
                            key={item}
                            type="button"
                            onClick={() => toggleArrayValue("skinConcerns", item)}
                            className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition active:scale-[0.98] cursor-pointer ${
                              isSelected
                                ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_4px_14px_rgba(238,142,163,0.38)] border border-white/80 font-semibold"
                                : "bg-white text-[#141414] shadow-[0_3px_10px_rgba(0,0,0,0.04)] border border-white/80 hover:bg-white/90"
                            }`}
                          >
                            {item}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="font-semibold text-xs sm:text-sm text-[#141414] mb-1 block">
                      Do you have sensitive skin?
                    </label>
                    <p className="text-[11px] text-[#7A7382] mb-2">Do you often react to products?</p>
                    <div className="flex flex-wrap gap-2">
                      {sensitiveSkin.map((item) => {
                        const isSelected = formData.sensitiveSkin === item;
                        return (
                          <button
                            key={item}
                            type="button"
                            onClick={() => updateField("sensitiveSkin", item)}
                            className={`rounded-full px-4 py-2 text-xs sm:text-sm font-medium transition active:scale-[0.98] cursor-pointer ${
                              isSelected
                                ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_4px_14px_rgba(238,142,163,0.38)] border border-white/80 font-semibold"
                                : "bg-white text-[#141414] shadow-[0_3px_10px_rgba(0,0,0,0.04)] border border-white/80 hover:bg-white/90"
                            }`}
                          >
                            {item}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 4: Routine & Products */}
              {step === 4 && (
                <div
                  ref={step4ContainerRef}
                  onScroll={handleStep4Scroll}
                  className="space-y-4 max-h-[50vh] sm:max-h-[56vh] overflow-y-auto ques-scrollbar pr-1.5 scroll-smooth relative"
                >
                  <div>
                    <label className="font-semibold text-xs sm:text-sm text-[#141414] mb-2 block">
                      Do you currently follow a skincare routine?
                    </label>
                    <div className="flex gap-2.5">
                      {["Yes", "No"].map((item) => {
                        const isSelected = formData.hasRoutine === item;
                        return (
                          <button
                            key={item}
                            type="button"
                            onClick={() => {
                              updateField("hasRoutine", item);
                              if (item === "Yes") {
                                setTimeout(() => {
                                  routineSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
                                  handleStep4Scroll();
                                }, 100);
                              } else if (item === "No") {
                                setTimeout(() => {
                                  usingProductsSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
                                  handleStep4Scroll();
                                }, 100);
                              }
                            }}
                            className={`rounded-full px-5 py-2 text-xs sm:text-sm font-medium transition active:scale-[0.98] cursor-pointer ${
                              isSelected
                                ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_4px_14px_rgba(238,142,163,0.38)] border border-white/80 font-semibold"
                                : "bg-white text-[#141414] shadow-[0_3px_10px_rgba(0,0,0,0.04)] border border-white/80 hover:bg-white/90"
                            }`}
                          >
                            {item}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {formData.hasRoutine === "Yes" && (
                    <div ref={routineSectionRef} className="space-y-3.5 pt-1 scroll-mt-3">
                      <div>
                        <label className="font-semibold text-xs text-[#141414] mb-1.5 block">
                          Morning Routine
                        </label>
                        <div className="flex flex-wrap gap-1.5">
                          {morningRoutine.map((item) => {
                            const isSelected = formData.morningRoutine.includes(item);
                            return (
                              <button
                                key={item}
                                type="button"
                                onClick={() => toggleArrayValue("morningRoutine", item)}
                                className={`rounded-full px-3 py-1.5 text-xs font-medium transition active:scale-[0.98] cursor-pointer ${
                                  isSelected
                                    ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_4px_14px_rgba(238,142,163,0.38)] border border-white/80 font-semibold"
                                    : "bg-white text-[#141414] shadow-[0_3px_10px_rgba(0,0,0,0.04)] border border-white/80 hover:bg-white/90"
                                }`}
                              >
                                {item}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div>
                        <label className="font-semibold text-xs text-[#141414] mb-1.5 block">
                          Night Routine
                        </label>
                        <div className="flex flex-wrap gap-1.5">
                          {nightRoutine.map((item) => {
                            const isSelected = formData.nightRoutine.includes(item);
                            return (
                              <button
                                key={item}
                                type="button"
                                onClick={() => toggleArrayValue("nightRoutine", item)}
                                className={`rounded-full px-3 py-1.5 text-xs font-medium transition active:scale-[0.98] cursor-pointer ${
                                  isSelected
                                    ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_4px_14px_rgba(238,142,163,0.38)] border border-white/80 font-semibold"
                                    : "bg-white text-[#141414] shadow-[0_3px_10px_rgba(0,0,0,0.04)] border border-white/80 hover:bg-white/90"
                                }`}
                              >
                                {item}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  )}

                  <div ref={usingProductsSectionRef} className="pt-2 border-t border-white/60 scroll-mt-3">
                    <label className="font-semibold text-xs sm:text-sm text-[#141414] mb-2 block">
                      Are you currently using skincare products?
                    </label>
                    <div className="flex gap-2.5 mb-3">
                      {["Yes", "No"].map((item) => {
                        const isSelected = formData.usingProducts === item;
                        return (
                          <button
                            key={item}
                            type="button"
                            onClick={() => {
                              updateField("usingProducts", item);
                              if (item === "Yes") {
                                setTimeout(() => {
                                  productInputSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
                                  handleStep4Scroll();
                                }, 100);
                              }
                            }}
                            className={`rounded-full px-5 py-2 text-xs sm:text-sm font-medium transition active:scale-[0.98] cursor-pointer ${
                              isSelected
                                ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_4px_14px_rgba(238,142,163,0.38)] border border-white/80 font-semibold"
                                : "bg-white text-[#141414] shadow-[0_3px_10px_rgba(0,0,0,0.04)] border border-white/80 hover:bg-white/90"
                            }`}
                          >
                            {item}
                          </button>
                        );
                      })}
                    </div>

                    {formData.usingProducts === "Yes" && (
                      <div ref={productInputSectionRef} className="space-y-3 scroll-mt-3">
                        <div className="flex flex-col sm:flex-row gap-2">
                          <CustomSelect
                            value={selectedType}
                            onChange={setSelectedType}
                            options={currentProductTypes}
                            placeholder="Product type"
                            className="sm:w-36 shrink-0"
                          />

                          <input
                            type="text"
                            className="px-4 py-2.5 rounded-2xl bg-white border border-white/90 text-xs sm:text-sm text-[#141414] placeholder:text-[#8E8895] shadow-[0_4px_14px_rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-[#C4A2FA]/60 flex-1"
                            placeholder="Brand (e.g. Minimalist)"
                            value={brandInput}
                            onChange={(e) => setBrandInput(e.target.value)}
                          />

                          <input
                            type="text"
                            className="px-4 py-2.5 rounded-2xl bg-white border border-white/90 text-xs sm:text-sm text-[#141414] placeholder:text-[#8E8895] shadow-[0_4px_14px_rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-[#C4A2FA]/60 flex-1"
                            placeholder="Product name"
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
                            onClick={addProduct}
                            disabled={!selectedType || !productInput.trim()}
                            className="btn btn-rose rounded-full px-4 py-2 font-bold text-xs shadow-sm transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0 flex items-center gap-1 cursor-pointer"
                          >
                            <Plus size={14} /> <span>Add</span>
                          </button>
                        </div>

                        {formData.currentProducts.length > 0 && (
                          <div className="space-y-2 mt-2">
                            {formData.currentProducts.map((product, index) => (
                              <div
                                key={`${product.type}-${product.productName}-${index}`}
                                className="bg-white/90 backdrop-blur-md p-3 rounded-2xl border border-white/95 shadow-sm scroll-mt-2"
                              >
                                <div className="flex items-center justify-between">
                                  <div>
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#DE688E]">
                                      {product.type}
                                    </span>
                                    <p className="text-xs font-semibold text-[#141414]">
                                      {product.brand ? `${product.brand} - ` : ""}
                                      {product.productName}
                                    </p>
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => removeProduct(index)}
                                    className="w-6 h-6 rounded-full bg-gray-100 hover:bg-red-50 text-gray-400 hover:text-red-500 flex items-center justify-center transition cursor-pointer"
                                  >
                                    <X size={13} />
                                  </button>
                                </div>

                                <div className="mt-2 pt-2 border-t border-gray-100">
                                  <label className="text-[11px] font-semibold text-[#141414] block mb-1">
                                    Did this product cause any reaction?
                                  </label>
                                  <div className="flex flex-wrap gap-2">
                                    {reactionOptions.map((opt) => (
                                      <label
                                        key={opt.value}
                                        className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] cursor-pointer transition ${
                                          product.reaction === opt.value
                                            ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] font-semibold shadow-sm"
                                            : "bg-gray-50 text-[#5A5555] hover:bg-gray-100 border border-transparent"
                                        }`}
                                      >
                                        <input
                                          type="radio"
                                          name={`reaction-${index}`}
                                          value={opt.value}
                                          checked={product.reaction === opt.value}
                                          onChange={(e) => updateProductReaction(index, e.target.value)}
                                          className="sr-only"
                                        />
                                        <span>{opt.label}</span>
                                      </label>
                                    ))}
                                  </div>

                                  <div className="mt-2.5 pt-2 border-t border-gray-100/80">
                                    <label className="text-[11px] font-semibold text-[#141414] block mb-1">
                                      Anything you noticed while using this product? <span className="text-[10px] font-normal text-[#7A7382]">(Optional)</span>
                                    </label>
                                    <input
                                      type="text"
                                      placeholder="e.g. redness, burning, breakouts, dryness, or no issues"
                                      className="w-full px-3.5 py-2 rounded-xl bg-white border border-gray-200/70 text-xs text-[#141414] placeholder:text-[#9A9393] shadow-[0_1px_4px_rgba(0,0,0,0.03)] focus:outline-none focus:ring-2 focus:ring-[#C4A2FA]/60 transition"
                                      value={product.notes || ""}
                                      onChange={(e) => updateProductNotes(index, e.target.value)}
                                    />
                                  </div>
                                </div>
                              </div>
                            ))}
                            <div ref={productsListBottomRef} />
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Sticky Scroll Indicator when content extends below */}
                  {canScrollStep4Down && (
                    <div className="sticky bottom-0 left-0 right-0 flex justify-center pb-1 pt-2 pointer-events-none z-20">
                      <button
                        type="button"
                        onClick={() => {
                          if (step4ContainerRef.current) {
                            step4ContainerRef.current.scrollBy({ top: 160, behavior: "smooth" });
                          }
                        }}
                        className="pointer-events-auto bg-white/95 backdrop-blur-md px-3.5 py-1.5 rounded-full text-[11px] font-semibold text-[#DE688E] shadow-[0_4px_14px_rgba(222,104,142,0.25)] border border-pink-100 flex items-center gap-1.5 cursor-pointer hover:bg-white transition animate-bounce"
                      >
                        <span>Scroll down for product details</span>
                        <ChevronDown size={14} />
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* STEP 5: Skin Goals */}
              {step === 5 && (
                <div>
                  <label className="font-semibold text-xs sm:text-sm text-[#141414] mb-1.5 block">
                    What would you like SkinWise to help you achieve?
                  </label>
                  <p className="text-[11px] text-[#7A7382] mb-3">Select all that apply</p>
                  <div className="flex flex-wrap gap-2.5">
                    {goals.map((goal) => {
                      const isSelected = formData.goals.includes(goal);
                      return (
                        <button
                          key={goal}
                          type="button"
                          onClick={() => toggleArrayValue("goals", goal)}
                          className={`rounded-full px-4 py-2 text-xs sm:text-sm font-medium transition active:scale-[0.98] cursor-pointer ${
                            isSelected
                              ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] text-[#141414] shadow-[0_4px_14px_rgba(238,142,163,0.38)] border border-white/80 font-semibold"
                              : "bg-white text-[#141414] shadow-[0_3px_10px_rgba(0,0,0,0.04)] border border-white/80 hover:bg-white/90"
                          }`}
                        >
                          {goal}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* STEP 6: AI Face Analysis */}
              {step === 6 && !isEditMode && (
                <div className="flex flex-col items-center justify-center text-center py-6">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-b from-[#F9BAC8] to-[#EE8EA3] text-[#141414] flex items-center justify-center mb-4 shadow-[0_8px_24px_rgba(238,142,163,0.38)] border border-white/60">
                    <Camera size={30} strokeWidth={2} />
                  </div>

                  <h3
                    className="text-2xl font-bold text-[#141414] mb-2"
                    style={{ fontFamily: "Georgia, serif" }}
                  >
                    Ready to Scan
                  </h3>
                  <p className="text-xs sm:text-sm text-[#5A5555] max-w-sm mb-6 leading-relaxed">
                    We&apos;ll analyze your skin condition, detect visible concerns, and combine the results with your questionnaire to build your personalized skincare profile.
                  </p>

                  <button
                    type="button"
                    className="btn btn-rose rounded-full px-8 py-3 text-sm font-bold shadow-[0_8px_24px_rgba(238,142,163,0.4)] border border-white/60 flex items-center gap-2 transition cursor-pointer"
                    onClick={() => router.push("/face-analysis")}
                  >
                    <span>Start Face Analysis</span>
                    <ArrowRight size={16} strokeWidth={2.2} />
                  </button>
                </div>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <p className="text-xs text-red-600 mt-2 bg-red-50/80 px-3 py-1.5 rounded-lg border border-red-200/60 inline-block">
                {error}
              </p>
            )}

            {/* Card Footer Navigation */}
            <div className="flex justify-between items-center pt-5 mt-4 border-t border-white/70">
              <button
                type="button"
                className="btn btn-white inline-flex items-center gap-1.5 sm:gap-2 px-4 sm:px-6 py-2 sm:py-2.5 text-xs sm:text-sm font-semibold rounded-full cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                onClick={prevStep}
                disabled={step === 1}
              >
                <ArrowLeft size={16} strokeWidth={2.2} /> <span>Previous</span>
              </button>

              {step < totalSteps ? (
                <button
                  type="button"
                  className="btn btn-rose inline-flex items-center gap-1.5 sm:gap-2 px-5 sm:px-7 py-2 sm:py-2.5 text-xs sm:text-sm font-bold rounded-full cursor-pointer disabled:opacity-50"
                  onClick={nextStep}
                  disabled={isSubmitting || isLoadingProfile}
                >
                  <span>
                    {isSubmitting && step === totalSteps - 1
                      ? "Saving..."
                      : isLoadingProfile
                      ? "Loading..."
                      : isEditMode && step === totalSteps - 1
                      ? "Save Changes"
                      : "Continue"}
                  </span>
                  <ArrowRight size={16} strokeWidth={2.2} />
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn-rose inline-flex items-center gap-1.5 sm:gap-2 px-5 sm:px-7 py-2 sm:py-2.5 text-xs sm:text-sm font-bold rounded-full cursor-pointer"
                  onClick={() => router.push("/face-analysis")}
                >
                  <span>Start Face Analysis</span>
                  <ArrowRight size={16} strokeWidth={2.2} />
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}