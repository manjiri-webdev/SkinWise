"use client";

import { useEffect, useState } from "react";
import { getCurrentLocation } from "@/services/location";
import { fetchWeather } from "@/lib/weather";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import './questionnaire.css';

import {
  ageRanges, genders, sleepOptions, hydrationOptions, stressLevels, eatingHabits, skinTypes, skinConcerns, sensitiveSkin, morningRoutine, nightRoutine, goals, currentProductTypes,
} from "./questions";

import {
  User, Globe, Venus, Mars, Users, ArrowRight, ArrowLeft, ShieldCheck, Smile, ScanFace, Layers, Target, Camera
} from "lucide-react";

type QuestionnaireData = {
  ageRanges: string; genders: string; city: string;
  sleep: string; hydration: string; stress: string; eatingHabits: string[];
  skinTypes: string; skinConcerns: string[]; sensitiveSkin: string; hasRoutine: string; morningRoutine: string[]; nightRoutine: string[]; usingProducts: string; currentProducts: {
    type: string;
    productName: string;
  }[];
  goals: string[];
  latitude: number | null;
  longitude: number | null; temperature: number | null; humidity: number | null; weather: string;
}

const initalFromData: QuestionnaireData = {
  ageRanges: "", genders: "", city: "", sleep: "", hydration: "", stress: "", eatingHabits: [], skinTypes: "", skinConcerns: [], sensitiveSkin: "", hasRoutine: "", morningRoutine: [], nightRoutine: [], usingProducts: "", currentProducts: [], goals: [], latitude: null, longitude: null, temperature: null, humidity: null, weather: "",
}

const stepInfo = {
  1: { icon: User, status: "Step 1", title: "Personal Information", helper: "Tell us a bit about yourself." },
  2: { icon: Smile, status: "Step 2", title: "Lifestyle", helper: "Your daily habits affect your skin." },
  3: { icon: ScanFace, status: "Step 3", title: "Skin Profile", helper: "Tell us about your skin so we can personalize your recommendations." },
  4: { icon: Layers, status: "Step 4", title: "Routine", helper: "Tell us about your current skincare habits." },
  5: { icon: Target, status: "Step 5", title: "Skin Goals", helper: "What would you like SkinWise to help you achieve?" },
  6: { icon: Camera, status: "Step 6", title: "AI Face Analysis", helper: "Your questionnaire is complete! Let's analyze your skin using AI." },
};

export default function Questionnaire() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<QuestionnaireData>(initalFromData);
  const [error, setError] = useState<string | null>(null);
  const totalSteps = 6;
  const [productInput, setProductInput] = useState("");
  const [selectedType, setSelectedType] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();

  useEffect(() => {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }, [step]);

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
      }
      setStep(step + 1);
    }
  };
  const prevStep = () => {
    if (step > 1) {
      setError(null);
      setStep(step - 1);
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

      const { error: updateError } = await supabase
        .from("user_profiles")
        .update({
          // id: user.id,

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
          diet: formData.eatingHabits,

          skin_type: formData.skinTypes,
          skin_concerns: formData.skinConcerns,
          skin_sensitivity: formData.sensitiveSkin,

          morning_routine: formData.morningRoutine,
          night_routine: formData.nightRoutine,
          current_products: formData.currentProducts,

          skincare_goals: formData.goals,

          questionnaire_completed: true,
        }).eq("id", user.id);

      if (updateError) {
        console.error(updateError);
        setError(updateError.message);
        return false;
      }

      return true;
    } catch (err) {
      console.error(err);
      setError("Something went wrong while saving your profile. Please try again.");
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateField = <K extends keyof QuestionnaireData>(key: K, value: QuestionnaireData[K]) => {
    setFormData((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const toggleArrayValue = (
    key: keyof QuestionnaireData,
    value: string
  ) => {
    setFormData((prev) => {
      const current = prev[key] as string[];

      return {
        ...prev,
        [key]: current.includes(value)
          ? current.filter((item) => item !== value)
          : [...current, value],
      };
    });
  };

  const addProduct = () => {
    if (!selectedType || !productInput.trim()) return;

    const newProduct = {
      type: selectedType,
      productName: productInput.trim(),
    };

    const alreadyExists = formData.currentProducts.some(
      (item) =>
        item.type === newProduct.type &&
        item.productName.toLowerCase() === newProduct.productName.toLowerCase()
    );

    if (alreadyExists) return;

    updateField("currentProducts", [
      ...formData.currentProducts,
      newProduct,
    ]);

    setSelectedType("");
    setProductInput("");
  };

  const removeProduct = (index: number) => {
    updateField(
      "currentProducts",
      formData.currentProducts.filter((_, i) => i !== index)
    );
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
  }
  const StepHeader = () => {
    const info = stepInfo[step as keyof typeof stepInfo];
    const Icon = info.icon;
    return (
      <div className="flex items-center gap-4 mb-10">
        <div className="w-12 h-12 rounded-full bg-pink-100 flex justify-center items-center">
          <Icon className="text-pink-400" />
        </div>
        <div>
          <p className="text-sm text-textSecondary">{info.status}</p>
          <h2 className="text-2xl font-semibold">{info.title}</h2>
          <p className="text-sm text-textSecondary">{info.helper}</p>
        </div>
      </div>
    );
  };

  return (
    <main className="min-h-screen w-full bg-lavender/20  flex justify-center items-center p-8">

      <div className="w-full max-w-4xl">
        <div className="mb-8  flex flex-col items-center">
          <h1 className="text-4xl font-bold text-[#2D2D2D]"> Skin Questionnaire </h1>
          <p className="text-textSecondary mt-2"> Help us understand your skin better. Your answers will help SkinWise personalize your skincare routine.
          </p>
        </div>

        <div className="mb-8">
          <div className="flex justify-between text-sm mb-2">
            <span>Step {step} of {totalSteps}</span>
            <span>{Math.round((step / totalSteps) * 100)}%</span>
          </div>

          <div className="w-full h-2 rounded-full bg-white">
            <div className="h-full rounded-full bg-pink-300 transition-all duration-300"
              style={{ width: `${(step / totalSteps) * 100}%`, }}
            ></div>
          </div>
        </div>

        {/* container starts here */}
        <div className="glass ques-card p-10 w-full h-full sm:p-8 lg:p-10 flex flex-col justify-between animate-elements bg-creamGradient1">
          <form className="flex flex-col gap-8 mb-10 p-5 overflow-y-auto">
            <StepHeader />
            {step === 1 && (
              <>
                {/* age */}
                <section className="mb-8">
                  <label className="font-semibold mb-2 block"> Age Range </label>
                  <select
                    value={formData.ageRanges}
                    onChange={(e) => updateField("ageRanges", e.target.value)}
                    className="input-glass"
                  >
                    <option value="">Select age range</option>
                    {ageRanges.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </section>

                {/* gender */}
                <section className="mb-8">
                  <label className="font-semibold block mb-3"> Gender </label>
                  <div className="flex gap-4">
                    {genders.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => updateField("genders", item)}
                        className={`btn ${formData.genders === item
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}
                      >
                        {item === "Male" && <Mars size={18} />}
                        {item === "Female" && <Venus size={18} />}
                        {item === "Other" && <Users size={18} />}
                        {item}
                      </button>
                    ))}
                  </div>
                </section>

                {/* location */}
                <section className="mb-8">
                  <h3 className="text-sm font-semibold mb-3">Your Location</h3>
                  <p className="mb-4"> We use your location to personalize skincare recommendations based on
                    weather, humidity and UV levels.</p>
                  <div className="flex flex-col gap-4">

                    <button
                      type="button"
                      onClick={handleCurrentLocation}
                      className="btn bg-pink-300 text-white hover:bg-pink-400 flex items-center justify-center gap-2"
                    >
                      <Globe size={18} /> Use Current Location
                    </button>

                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-px bg-gray-300"></div>
                      <span className="text-xs text-textSecondary">
                        OR
                      </span>
                      <div className="flex-1 h-px bg-gray-300"></div>
                    </div>

                    <input
                      type="text"
                      placeholder="Enter your city (e.g. Mumbai)"
                      className="input-glass"
                      value={formData.city}
                      onChange={(e) => updateField("city", e.target.value)}
                    //  readOnly={formData.city !== ""}
                    />
                  </div>
                </section>
              </>
            )}

            {step === 2 && (
              <>
                {/* sleep */}
                <section className="mb-8">
                  <label className="font-semibold mb-2 block"> How many hours do you usually sleep?</label>

                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3 ">

                    {sleepOptions.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => updateField("sleep", item)}
                        className={`btn ${formData.sleep === item
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </section>

                {/* hydration */}
                <section className="mb-8">
                  <label className="font-semibold mb-2 block"> How well do you stay hydrated?</label>

                  <div className="flex gap-3">
                    {hydrationOptions.map((item) => (

                      <button
                        key={item}
                        type="button"
                        onClick={() => updateField("hydration", item)}
                        className={`btn ${formData.hydration === item
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}>
                        {item}
                      </button>
                    ))}
                  </div>
                </section>

                {/* stress */}
                <section className="mb-8">
                  <label className="font-semibold mb-2 block"> Current Stress Level</label>

                  <div className="flex gap-3">
                    {stressLevels.map((item) => (

                      <button
                        key={item}
                        type="button"
                        onClick={() => updateField("stress", item)}
                        className={`btn ${formData.stress === item
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}>
                        {item}
                      </button>
                    ))}
                  </div>
                </section>

                {/* diet */}
                <section className="mb-8">
                  <label className="font-semibold mb-2 block"> Eating Habits</label>
                  <p className="text-sm text-textSecondary mb-4">
                    Select all that apply.
                  </p>

                  <div className="flex gap-3">
                    {eatingHabits.map((item) => (

                      <button
                        key={item}
                        type="button"
                        onClick={() =>
                          toggleArrayValue("eatingHabits", item)
                        }
                        className={`btn ${formData.eatingHabits.includes(item)
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </section>

              </>
            )}

            {step === 3 && (
              <>
                {/* skin type */}
                <section className="mb-8">
                  <label className="font-semibold mb-2 block"> What is your skin type?</label>

                  <div className="flex gap-3">
                    {skinTypes.map((item) => (

                      <button
                        key={item}
                        type="button"
                        onClick={() => updateField("skinTypes", item)}
                        className={`btn ${formData.skinTypes === item
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}>
                        {item}
                      </button>
                    ))}
                  </div>
                  <p className="text-xs text-textSecondary mt-3">
                    Don't worry if you're unsure. Our AI skin analysis can estimate it later.
                  </p>
                </section>

                {/* skin concerns */}
                <section className="mb-8">
                  <label className="font-semibold mb-2 block"> What is your main skin concerns?</label>
                  <p className="text-sm text-textSecondary mb-4">
                    Select all that apply.
                  </p>

                  <div className="flex flex-wrap gap-3">
                    {skinConcerns.map((item) => (

                      <button
                        key={item}
                        type="button"
                        onClick={() => toggleArrayValue("skinConcerns", item)}
                        className={`btn ${formData.skinConcerns.includes(item)
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}>
                        {item}
                      </button>
                    ))}
                  </div>
                </section>

                {/* sensitive skin*/}
                <section className="mb-8">
                  <label className="font-semibold mb-2 block"> Do you have sensitive skin?</label>
                  <p className="text-sm text-textSecondary mb-4">Do you often react to products?</p>

                  <div className="flex gap-3">
                    {sensitiveSkin.map((item) => (

                      <button
                        key={item}
                        type="button"
                        onClick={() => updateField("sensitiveSkin", item)}
                        className={`btn ${formData.sensitiveSkin === item
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}>
                        {item}
                      </button>
                    ))}
                  </div>
                </section>
              </>
            )}

            {step === 4 && (
              <>
                <div>
                  <label className="font-semibold block mb-4">
                    Do you currently follow a skincare routine?
                  </label>

                  <div className="flex gap-4">
                    {["Yes", "No"].map((item) => (

                      <button
                        key={item}
                        type="button"
                        onClick={() => updateField("hasRoutine", item)}
                        className={`btn ${formData.hasRoutine === item
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Morning & Night */}
                {formData.hasRoutine === "Yes" && (
                  <>

                    <div>
                      <label className="font-semibold block mb-3">
                        Morning Routine
                      </label>

                      <div className="flex flex-wrap gap-3">
                        {morningRoutine.map((item) => (

                          <button
                            key={item}
                            type="button"
                            onClick={() => toggleArrayValue("morningRoutine", item)}
                            className={`btn ${formData.morningRoutine.includes(item)
                              ? "bg-pink-300 text-white"
                              : "bg-white"
                              }`}
                          >
                            {item}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>

                      <label className="font-semibold block mb-3">
                        Night Routine
                      </label>

                      <div className="flex flex-wrap gap-3">
                        {nightRoutine.map((item) => (

                          <button
                            key={item}
                            type="button"
                            onClick={() => toggleArrayValue("nightRoutine", item)}
                            className={`btn ${formData.nightRoutine.includes(item)
                              ? "bg-pink-300 text-white"
                              : "bg-white"
                              }`}
                          >
                            {item}
                          </button>
                        ))}
                      </div>
                    </div>
                  </>
                )}

                {/* products */}
                <div>
                  <label className="font-semibold block mb-4">
                    Are you currently using skincare products?
                  </label>

                  <div className="flex gap-4 mb-6">
                    {["Yes", "No"].map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => updateField("usingProducts", item)}
                        className={`btn ${formData.usingProducts === item
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}
                      >
                        {item}
                      </button>
                    ))}
                  </div>

                  {formData.usingProducts === "Yes" && (
                    <div className="flex flex-col gap-4">
                      <div className="flex flex-col sm:flex-row gap-3">
                        <select
                          className="input-glass sm:w-48"
                          value={selectedType}
                          onChange={(e) => setSelectedType(e.target.value)}
                        >
                          <option value="">Product type</option>
                          {currentProductTypes.map((type) => (
                            <option key={type} value={type}>{type}</option>
                          ))}
                        </select>

                        <input
                          type="text"
                          className="input-glass flex-1"
                          placeholder="Enter product name"
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
                          className="btn bg-pink-300 text-white disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                        >
                          + Add
                        </button>
                      </div>

                      {formData.currentProducts.length === 0 ? (
                        <p className="text-xs text-textSecondary">No products added yet.</p>
                      ) : (
                        <div className="flex flex-wrap gap-3">
                          {formData.currentProducts.map((product, index) => (
                            <div
                              key={`${product.type}-${product.productName}-${index}`}
                              className="bg-pink-100 px-4 py-2 rounded-xl flex items-center gap-3"
                            >
                              <div>
                                <p className="font-semibold text-sm">{product.type}</p>
                                <p className="text-sm text-textSecondary">{product.productName}</p>
                              </div>
                              <button
                                type="button"
                                onClick={() => removeProduct(index)}
                                aria-label={`Remove ${product.productName}`}
                              >
                                ✕
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </>
            )}

            {step === 5 && (
              <>
                <div>
                  <label className="font-semibold block mb-4">
                    Select all that apply
                  </label>

                  <div className="flex flex-wrap gap-3">
                    {goals.map((goal) => (

                      <button
                        key={goal}
                        type="button"
                        onClick={() => toggleArrayValue("goals", goal)}
                        className={`btn ${formData.goals.includes(goal)
                          ? "bg-pink-300 text-white"
                          : "bg-white"
                          }`}
                      >
                        {goal}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {step === 6 && (
              <>
                <div className="flex flex-col items-center justify-center text-center py-12">

                  <Camera
                    size={70}
                    className="text-pink-400 mb-6"
                  />

                  <h3 className="text-xl font-semibold mb-3">
                    Ready to Scan
                  </h3>
                  <p className="text-textSecondary max-w-md mb-8">
                    We'll analyze your skin condition, detect visible concerns,
                    and combine the results with your questionnaire to build
                    your personalized skincare profile.
                  </p>

                  <button
                    type="button"
                    className="btn bg-pink-300 text-white px-8 py-3"
                    onClick={() => router.push("/face-analysis")}
                  >
                    Start Face Analysis
                  </button>
                </div>
              </>
            )}

          </form>

          {error && <p className="text-sm text-red-500 mt-4">{error}</p>}
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
                disabled={isSubmitting}
              >
                {isSubmitting && step === totalSteps - 1 ? "Saving..." : "Continue"} <ArrowRight size={18} />
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
    </main>
  );
}