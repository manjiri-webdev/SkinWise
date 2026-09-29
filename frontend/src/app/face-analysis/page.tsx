"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import {
  uploadFaceImage,
  evaluateUploadResult,
  convertBackendValidation,
  validateLiveFrame,
} from "@/services/faceAnalysis";
import { updateProfile } from "@/services/personalization";
import "./face-analysis.css";

import {
  Camera,
  ShieldCheck,
  Sun,
  Glasses,
  Meh,
  ScanFace,
  Loader2,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Upload,
  ArrowLeft,
} from "lucide-react";

type FlowStep =
  | "instructions"
  | "permission"
  | "live"
  | "capturing"
  | "uploading"
  | "upload_preview"
  | "success"
  | "error";

type ValidationStatus = "passed" | "warning" | "failed" | "pending";

interface ValidationCheck {
  id: string;
  label: string;
  status: ValidationStatus;
  message: string;
}

interface ValidationState {
  faceDetected: ValidationCheck;
  singleFace: ValidationCheck;
  brightness: ValidationCheck;
  faceOrientation: ValidationCheck;
  imageClarity: ValidationCheck;
  readyForAnalysis: boolean;
  facePositionGuidance: string;
}

const initialValidationState: ValidationState = {
  faceDetected: {
    id: "faceDetected",
    label: "Face Detected",
    status: "pending",
    message: "Looking for face...",
  },
  singleFace: {
    id: "singleFace",
    label: "Single Face",
    status: "pending",
    message: "Ensure only one face is visible",
  },
  brightness: {
    id: "brightness",
    label: "Lighting",
    status: "pending",
    message: "Check lighting conditions",
  },
  faceOrientation: {
    id: "faceOrientation",
    label: "Face Position",
    status: "pending",
    message: "Look straight into camera",
  },
  imageClarity: {
    id: "imageClarity",
    label: "Image Clarity",
    status: "pending",
    message: "Checking image sharpness",
  },
  readyForAnalysis: false,
  facePositionGuidance: "Keep your face centered in the frame.",
};

export default function FaceAnalysis() {
  const [flowStep, setFlowStep] = useState<FlowStep>("instructions");
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadedFilePreview, setUploadedFilePreview] = useState<string | null>(null);
  const [validation, setValidation] = useState<ValidationState>(initialValidationState);
  const [isValidating, setIsValidating] = useState(false);
  const [streamReady, setStreamReady] = useState(false);
  const [backendWarmingUp, setBackendWarmingUp] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isValidatingRef = useRef(false);
  const consecutiveErrorsRef = useRef(0);
  const router = useRouter();

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  // Attach stream to video element when both stream and element are ready
  useEffect(() => {
    if (streamReady && videoRef.current && streamRef.current) {
      const video = videoRef.current;
      const stream = streamRef.current;
      video.srcObject = stream;

      video.onloadedmetadata = async () => {
        try {
          await video.play();
          video.style.setProperty("display", "block");
        } catch (playError) {
          console.error("Video play error:", playError);
          setPermissionError("Unable to start camera. Please try again.");
        }
      };

      video.onerror = (error) => {
        console.error("Video element error:", error);
        setPermissionError("Camera error. Please check your device and try again.");
      };

      if (video.readyState >= 2) {
        try {
          video.play();
        } catch (playError) {
          console.error("Immediate video play error:", playError);
        }
      }
    } else if (streamReady && !videoRef.current) {
      const retryTimer = setTimeout(() => {
        if (videoRef.current && streamRef.current) {
          const video = videoRef.current;
          video.srcObject = streamRef.current;
          video.onloadedmetadata = async () => {
            try {
              await video.play();
            } catch (playError) {
              console.error("Video play error (retry):", playError);
            }
          };
        }
      }, 200);

      return () => clearTimeout(retryTimer);
    }
  }, [streamReady, flowStep]);

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const stopCameraAndReturn = () => {
    stopCamera();
    setStreamReady(false);
    setIsValidating(false);
    setValidation(initialValidationState);
    setFlowStep("instructions");
  };

  const requestCameraAccess = async () => {
    setFlowStep("permission");
    setPermissionError(null);
    setStreamReady(false);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;
      setFlowStep("live");

      await new Promise((resolve) => setTimeout(resolve, 250));
      setStreamReady(true);
      setIsValidating(true);
    } catch (err) {
      console.error("Camera access error:", err);
      setPermissionError(
        "Camera access was denied. Please allow camera permission in your browser settings and try again."
      );
      setFlowStep("permission");
    }
  };

  // Live frame validation loop with chained timeout, concurrency lock, and cold-start backoff
  useEffect(() => {
    let timerId: NodeJS.Timeout | null = null;
    let isCancelled = false;

    if (flowStep !== "live" || !isValidating) {
      isValidatingRef.current = false;
      return;
    }

    const validateLoop = async () => {
      if (isCancelled) return;

      if (!videoRef.current || !canvasRef.current || isValidatingRef.current) {
        if (!isCancelled) {
          timerId = setTimeout(validateLoop, 2000);
        }
        return;
      }

      isValidatingRef.current = true;

      try {
        const video = videoRef.current;
        const canvas = canvasRef.current;

        if (!video.videoWidth || !video.videoHeight) {
          isValidatingRef.current = false;
          if (!isCancelled) {
            timerId = setTimeout(validateLoop, 1500);
          }
          return;
        }

        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;

        const ctx = canvas.getContext("2d");
        if (!ctx) {
          isValidatingRef.current = false;
          if (!isCancelled) {
            timerId = setTimeout(validateLoop, 2000);
          }
          return;
        }

        // Mirror image for canvas frame
        ctx.translate(canvas.width, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        const blob = await new Promise<Blob | null>((resolve) =>
          canvas.toBlob(resolve, "image/jpeg", 0.5)
        );

        if (!blob || isCancelled) {
          isValidatingRef.current = false;
          if (!isCancelled) {
            timerId = setTimeout(validateLoop, 2000);
          }
          return;
        }

        const file = new File([blob], "live-frame.jpg", { type: "image/jpeg" });

        try {
          const backendValidation = await validateLiveFrame(file);
          if (isCancelled) return;

          // Successful validation: reset error count and warming-up indicator
          consecutiveErrorsRef.current = 0;
          setBackendWarmingUp(false);

          const frontendValidation = convertBackendValidation(backendValidation);

          const blurCheck = (backendValidation.validation as any)?.blur;
          const imageClarityStatus: ValidationStatus = blurCheck?.status
            ? (blurCheck.status as ValidationStatus)
            : frontendValidation.brightness.status === "passed"
            ? "passed"
            : "warning";

          const imageClarityMessage =
            blurCheck?.message ||
            (imageClarityStatus === "passed"
              ? "Image is clear"
              : "Hold still for sharpest focus");

          setValidation({
            faceDetected: {
              id: "faceDetected",
              label: "Face Detected",
              status: frontendValidation.faceDetected.status,
              message:
                frontendValidation.faceDetected.status === "passed"
                  ? "Successfully detected"
                  : frontendValidation.faceDetected.message,
            },
            singleFace: {
              id: "singleFace",
              label: "Single Face",
              status: frontendValidation.singleFace.status,
              message:
                frontendValidation.singleFace.status === "passed"
                  ? "confirmed"
                  : frontendValidation.singleFace.message,
            },
            brightness: {
              id: "brightness",
              label: "Lighting",
              status: frontendValidation.brightness.status,
              message:
                frontendValidation.brightness.status === "passed"
                  ? "Good lighting"
                  : frontendValidation.brightness.message || "move to brighter place",
            },
            faceOrientation: {
              id: "faceOrientation",
              label: "Face Position",
              status: frontendValidation.faceOrientation.status,
              message:
                frontendValidation.faceOrientation.status === "passed"
                  ? "look straight into camera"
                  : frontendValidation.faceOrientation.message || "look straight into camera",
            },
            imageClarity: {
              id: "imageClarity",
              label: "Image Clarity",
              status: imageClarityStatus,
              message: imageClarityMessage,
            },
            readyForAnalysis: frontendValidation.readyForAnalysis,
            facePositionGuidance:
              frontendValidation.facePositionGuidance ||
              "Keep your face centered in the oval guide.",
          });
        } catch (validationErr) {
          consecutiveErrorsRef.current += 1;
          if (consecutiveErrorsRef.current >= 2) {
            setBackendWarmingUp(true);
          }
          if (consecutiveErrorsRef.current === 1) {
            console.warn("Live validation service is warming up or delayed:", validationErr);
          }
        }
      } catch (error) {
        console.error("Frame capture error:", error);
      } finally {
        isValidatingRef.current = false;
        if (!isCancelled) {
          const delay = consecutiveErrorsRef.current >= 2 ? 4000 : 2000;
          timerId = setTimeout(validateLoop, delay);
        }
      }
    };

    timerId = setTimeout(validateLoop, 800);

    return () => {
      isCancelled = true;
      if (timerId) {
        clearTimeout(timerId);
      }
      isValidatingRef.current = false;
    };
  }, [flowStep, isValidating]);

  useEffect(() => {
    if (flowStep !== "live") {
      setIsValidating(false);
    }
  }, [flowStep]);

  const captureAndUpload = async () => {
    if (!videoRef.current || !canvasRef.current) return;

    setFlowStep("capturing");

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      async (blob) => {
        if (!blob) return;

        stopCamera();
        setFlowStep("uploading");
        setUploadError(null);

        const file = new File([blob], "face-capture.jpg", { type: "image/jpeg" });

        try {
          const result = await uploadFaceImage(file, false);

          if ("ready_for_analysis" in result && "validation" in result) {
            const backendValidation = result as any;
            const frontendValidation = convertBackendValidation(backendValidation);

            if (!backendValidation.ready_for_analysis) {
              const val = backendValidation.validation;
              let failedMessage = "Please adjust your position and try again.";

              if (val.face_detection?.status === "failed") {
                failedMessage = val.face_detection.message;
              } else if (val.single_face?.status === "failed") {
                failedMessage = val.single_face.message;
              } else if (val.brightness?.status === "failed") {
                failedMessage = val.brightness.message;
              } else if (val.face_orientation?.status === "failed") {
                failedMessage = val.face_orientation.message;
              } else if (val.blur?.status === "failed") {
                failedMessage = val.blur.message;
              }

              setUploadError(failedMessage);
              setFlowStep("error");
              return;
            }

            setValidation((prev) => ({
              ...prev,
              ...frontendValidation,
            }));
          } else {
            const { passed, reason } = evaluateUploadResult(result);
            if (!passed) {
              setUploadError(reason);
              setFlowStep("error");
              return;
            }
          }

          await markFaceAnalysisComplete();
          setFlowStep("success");
        } catch (err: any) {
          console.error(err);
          setUploadError(err?.message || "Something went wrong while analyzing your photo. Please try again.");
          setFlowStep("error");
        }
      },
      "image/jpeg",
      0.8
    );
  };

  const markFaceAnalysisComplete = async () => {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) return;

    try {
      await updateProfile({
        face_analysis_completed: true,
        onboarding_completed: true,
      });
    } catch (error) {
      console.error("Failed to mark face analysis complete:", error);
    }
  };

  const retake = async () => {
    setUploadError(null);
    setValidation(initialValidationState);
    setUploadedFile(null);
    setUploadedFilePreview(null);
    setFlowStep("instructions");
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.match(/image\/(jpeg|jpg|png)/i)) {
      setUploadError("Please select a JPG, JPEG, or PNG image file.");
      return;
    }

    if (file.size > 8 * 1024 * 1024) {
      setUploadError("Image size must be less than 8MB.");
      return;
    }

    setUploadedFile(file);
    setUploadError(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      setUploadedFilePreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);

    stopCamera();
    setFlowStep("upload_preview");
  };

  const analyzeUploadedPhoto = async () => {
    if (!uploadedFile) return;

    setFlowStep("uploading");
    setUploadError(null);

    try {
      const result = await uploadFaceImage(uploadedFile, true);

      if ("ready_for_analysis" in result && "validation" in result) {
        const backendValidation = result as any;
        const frontendValidation = convertBackendValidation(backendValidation);

        if (!backendValidation.ready_for_analysis) {
          const val = backendValidation.validation;
          let failedMessage = "Please adjust your photo and try again.";

          if (val.face_detection?.status === "failed") {
            failedMessage = val.face_detection.message;
          } else if (val.single_face?.status === "failed") {
            failedMessage = val.single_face.message;
          } else if (val.brightness?.status === "failed") {
            failedMessage = val.brightness.message;
          } else if (val.face_orientation?.status === "failed") {
            failedMessage = val.face_orientation.message;
          } else if (val.blur?.status === "failed") {
            failedMessage = val.blur.message;
          }

          setUploadError(failedMessage);
          setFlowStep("upload_preview");
          return;
        }

        setValidation((prev) => ({
          ...prev,
          ...frontendValidation,
        }));
      } else {
        const { passed, reason } = evaluateUploadResult(result);
        if (!passed) {
          setUploadError(reason);
          setFlowStep("upload_preview");
          return;
        }
      }

      await markFaceAnalysisComplete();
      setFlowStep("success");
    } catch (err: any) {
      console.error("Upload error:", err);
      setUploadError(err?.message || "Something went wrong while analyzing your photo. Please try again.");
      setFlowStep("upload_preview");
    }
  };

  const cancelUpload = () => {
    setUploadedFile(null);
    setUploadedFilePreview(null);
    setUploadError(null);
    setFlowStep("instructions");
  };

  const isCameraActive = flowStep === "live" || flowStep === "capturing";

  const getStatusDotColor = (status: ValidationStatus) => {
    if (!isCameraActive) return "bg-[#D1D5DB]";
    switch (status) {
      case "passed":
        return "bg-[#7DBE95]";
      case "warning":
        return "bg-[#E8B058]";
      case "failed":
        return "bg-[#E07A7A]";
      default:
        return "bg-[#D1D5DB]";
    }
  };

  const validationChecksList = [
    validation.faceDetected,
    validation.singleFace,
    validation.brightness,
    validation.faceOrientation,
    validation.imageClarity,
  ];

  const passedChecksCount = isCameraActive
    ? validationChecksList.filter((check) => check.status === "passed").length
    : 0;

  const totalChecks = 5;

  return (
    <main className="min-h-screen w-full bg-[#F7F4EF] flex items-center justify-center p-3 sm:p-6 lg:p-8">
      <div className="w-full max-w-5xl flex flex-col lg:flex-row items-center lg:items-stretch justify-between gap-6 lg:gap-8">
        {/* Left Column: Heading & Camera Status Card */}
        <div className="w-full lg:w-72 shrink-0 flex flex-col justify-between py-1">
          <div>
            <div className="mb-4">
              <h1
                className="text-2xl sm:text-3xl font-bold text-[#141414] leading-tight"
                style={{ fontFamily: "Georgia, serif" }}
              >
                AI Skin Analysis
              </h1>
              <p className="text-xs sm:text-sm text-[#6B6375] mt-1.5 leading-relaxed">
                Position your face in the oval guide for optimal analysis
              </p>
            </div>

            {/* Camera Status Card */}
            <div className="camera-status-card p-5 sm:p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <ScanFace className="text-[#DE688E]" size={20} strokeWidth={2.2} />
                  <h2 className="text-sm sm:text-base font-bold text-[#141414]">
                    Camera Status
                  </h2>
                </div>

                {backendWarmingUp && (
                  <div className="mb-3.5 p-2.5 bg-amber-50/90 border border-amber-200/80 rounded-xl text-[11px] text-amber-800 leading-snug flex items-center gap-2">
                    <Loader2 size={14} className="animate-spin text-amber-600 shrink-0" />
                    <span>AI vision service is warming up... hold steady</span>
                  </div>
                )}

                <div className="space-y-3.5">
                  {validationChecksList.map((check) => (
                    <div key={check.id} className="flex items-start gap-3">
                      <span
                        className={`w-4 h-4 rounded-full shrink-0 mt-0.5 transition-colors duration-300 ${getStatusDotColor(
                          check.status
                        )}`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs sm:text-sm font-semibold text-[#141414] leading-none">
                          {check.label}
                        </p>
                        {isCameraActive && check.message && (
                          <p className="text-[11px] text-[#7A7382] mt-0.5 leading-snug truncate">
                            {check.message}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Progress Footer */}
              <div className="mt-5 pt-3.5 border-t border-gray-100">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-bold text-[#141414]">Progress</span>
                  <span className="text-[#7A7382]">
                    {isCameraActive
                      ? `${passedChecksCount} / ${totalChecks} Checks passed`
                      : `0 / ${totalChecks} Checks passed`}
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden p-0.5">
                  <div
                    className="bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] h-full rounded-full transition-all duration-300"
                    style={{
                      width: isCameraActive
                        ? `${(passedChecksCount / totalChecks) * 100}%`
                        : "0%",
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Privacy Note */}
          <div className="flex items-start gap-2.5 mt-4 pt-2">
            <ShieldCheck size={18} className="text-[#141414] shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-[#141414] text-xs">Your privacy is important to us</p>
              <p className="text-[11px] text-[#7A7382] mt-0.5 leading-relaxed">
                Your photo is only used to generate your skin analysis and is never shared.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Dynamic Analysis / Camera Viewport */}
        <div className="w-full flex-1 max-w-2xl flex flex-col items-center justify-center">
          {/* STATE 1: Instructions (Before we Start) */}
          {flowStep === "instructions" && (
            <div className="analysis-glass-card w-full p-6 sm:p-8 flex flex-col items-center justify-between text-center min-h-[440px]">
              <div>
                <div className="flex justify-center mb-2">
                  <ScanFace className="text-[#A85175]" size={36} strokeWidth={2} />
                </div>
                <h2
                  className="text-2xl sm:text-3xl font-bold text-[#141414] mb-4"
                  style={{ fontFamily: "Georgia, serif" }}
                >
                  Before we Start
                </h2>

                <div className="w-full max-w-lg space-y-3 my-4">
                  <div className="bg-white rounded-2xl p-4 shadow-[0_3px_12px_rgba(0,0,0,0.03)] border border-white/90 flex items-center gap-3.5 text-left text-xs sm:text-sm text-[#2D2D2D] font-medium">
                    <Sun size={20} className="text-[#A85175] shrink-0" />
                    <span>Find a well-lit spot, ideally facing a window or light source</span>
                  </div>

                  <div className="bg-white rounded-2xl p-4 shadow-[0_3px_12px_rgba(0,0,0,0.03)] border border-white/90 flex items-center gap-3.5 text-left text-xs sm:text-sm text-[#2D2D2D] font-medium">
                    <Glasses size={20} className="text-[#A85175] shrink-0" />
                    <span>Remove glasses and pull back hair covering your face</span>
                  </div>

                  <div className="bg-white rounded-2xl p-4 shadow-[0_3px_12px_rgba(0,0,0,0.03)] border border-white/90 flex items-center gap-3.5 text-left text-xs sm:text-sm text-[#2D2D2D] font-medium">
                    <Meh size={20} className="text-[#A85175] shrink-0" />
                    <span>Hold your phone at eye level and keep a neutral expression</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="w-full flex flex-col sm:flex-row items-center justify-center gap-3 mt-4">
                <button
                  type="button"
                  onClick={requestCameraAccess}
                  className="btn btn-rose py-3 px-9 text-sm font-bold rounded-full shadow-[0_8px_24px_rgba(238,142,163,0.4)] cursor-pointer"
                >
                  <span>Enable Camera</span>
                </button>

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="btn btn-white py-3 px-7 text-sm font-semibold rounded-full shadow-sm cursor-pointer inline-flex items-center gap-2"
                >
                  <Upload size={16} />
                  <span>Upload Photo</span>
                </button>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/jpg,image/png"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </div>

              <p className="text-[11px] text-[#7A7382] mt-3">
                Live camera capture provides real-time guidance. Upload is also available.
              </p>
            </div>
          )}

          {/* STATE 2: Requesting Permission */}
          {flowStep === "permission" && (
            <div className="analysis-glass-card w-full p-8 flex flex-col items-center justify-center text-center min-h-[420px]">
              {!permissionError ? (
                <>
                  <Loader2 className="animate-spin text-[#DE688E] mb-4" size={42} />
                  <h3
                    className="text-xl font-bold text-[#141414] mb-2"
                    style={{ fontFamily: "Georgia, serif" }}
                  >
                    Requesting Camera Access
                  </h3>
                  <p className="text-xs sm:text-sm text-[#6B6375] max-w-sm">
                    Please allow camera permission in your browser prompt so SkinWise can guide your live face analysis.
                  </p>
                </>
              ) : (
                <>
                  <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mb-4">
                    <AlertCircle className="text-red-500" size={32} />
                  </div>
                  <h3
                    className="text-xl font-bold text-[#141414] mb-2"
                    style={{ fontFamily: "Georgia, serif" }}
                  >
                    Camera Access Needed
                  </h3>
                  <p className="text-xs sm:text-sm text-[#6B6375] max-w-sm mb-6">
                    {permissionError}
                  </p>
                  <div className="flex flex-col sm:flex-row items-center gap-3">
                    <button
                      type="button"
                      className="btn btn-rose py-2.5 px-6 font-bold text-xs sm:text-sm rounded-full flex items-center gap-2 cursor-pointer"
                      onClick={requestCameraAccess}
                    >
                      <RotateCcw size={16} /> <span>Try Again</span>
                    </button>
                    <button
                      type="button"
                      className="btn btn-white py-2.5 px-6 font-semibold text-xs sm:text-sm rounded-full flex items-center gap-2 cursor-pointer"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload size={16} /> <span>Upload Photo Instead</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* STATE 3: Live Camera / Capturing State */}
          {(flowStep === "live" || flowStep === "capturing") && (
            <div className="camera-feed-card relative w-full aspect-[4/5] sm:aspect-[4/3] md:aspect-[16/11] max-h-[70vh] flex flex-col justify-between overflow-hidden">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="camera-video"
                style={{ transform: "scaleX(-1)" }}
              />

              {/* Guidance Badge Overlay */}
              <div className="relative z-20 w-full pt-4 flex justify-center pointer-events-none px-4">
                <span className="bg-black/60 backdrop-blur-md text-white text-[11px] sm:text-xs px-4 py-1.5 rounded-full border border-white/20 shadow-md">
                  {backendWarmingUp
                    ? "AI vision service is warming up. Please hold steady..."
                    : validation.facePositionGuidance}
                </span>
              </div>

              {/* Oval Face Guide Overlay */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                <div
                  className={`w-44 h-58 sm:w-60 sm:h-80 md:w-68 md:h-88 oval-face-guide ${
                    validation.readyForAnalysis ? "ready" : ""
                  }`}
                />
              </div>

              {/* Capturing feedback pulse */}
              {flowStep === "capturing" && (
                <div className="absolute inset-0 bg-black/50 z-30 flex items-center justify-center">
                  <div className="w-16 h-16 rounded-full border-4 border-white/30 animate-ping" />
                  <div className="absolute w-16 h-16 rounded-full border-4 border-[#F9BAC8]" />
                </div>
              )}

              {/* Bottom Control Bar */}
              <div className="relative z-20 w-full bg-[#A3A3A3]/75 backdrop-blur-md rounded-b-[24px] sm:rounded-b-[36px] py-2.5 sm:py-3.5 px-4 sm:px-6 flex items-center justify-between">
                <button
                  type="button"
                  onClick={stopCameraAndReturn}
                  className="w-10 h-10 rounded-full bg-white/25 hover:bg-white/35 text-white flex items-center justify-center transition cursor-pointer"
                  title="Cancel Camera"
                >
                  <ArrowLeft size={18} />
                </button>

                {/* Centered Shutter Button */}
                <button
                  type="button"
                  disabled={
                    (!validation.readyForAnalysis &&
                      validation.faceDetected.status !== "passed" &&
                      !backendWarmingUp) ||
                    flowStep === "capturing"
                  }
                  onClick={captureAndUpload}
                  className="shutter-outer-ring p-1.5 flex items-center justify-center cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  title={backendWarmingUp ? "Capture photo (AI vision is warming up)" : "Capture photo"}
                >
                  {flowStep === "capturing" ? (
                    <Loader2 className="animate-spin text-white" size={28} />
                  ) : (
                    <div
                      className={`w-12 h-12 sm:w-14 sm:h-14 rounded-full transition-transform ${
                        validation.readyForAnalysis ||
                        validation.faceDetected.status === "passed" ||
                        backendWarmingUp
                          ? "bg-gradient-to-r from-[#F9BAC8] to-[#EE8EA3] shadow-[0_4px_16px_rgba(238,142,163,0.5)]"
                          : "bg-gradient-to-r from-[#F9BAC8]/60 to-[#EE8EA3]/60"
                      }`}
                    />
                  )}
                </button>

                {/* Upload Photo Alternative in Live State */}
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="w-10 h-10 rounded-full bg-white/25 hover:bg-white/35 text-white flex items-center justify-center transition cursor-pointer"
                  title="Upload Photo Instead"
                >
                  <Upload size={18} />
                </button>
              </div>
            </div>
          )}

          {/* STATE 4: Review Uploaded Photo */}
          {flowStep === "upload_preview" && (
            <div className="analysis-glass-card w-full p-6 sm:p-8 flex flex-col items-center justify-center text-center">
              <h2
                className="text-xl sm:text-2xl font-bold text-[#141414] mb-3"
                style={{ fontFamily: "Georgia, serif" }}
              >
                Review Your Photo
              </h2>

              {uploadedFilePreview && (
                <div className="relative w-full max-w-sm max-h-[44vh] aspect-[3/4] rounded-2xl overflow-hidden shadow-md border border-white/90 bg-black/5 my-2">
                  <img
                    src={uploadedFilePreview}
                    alt="Uploaded preview"
                    className="w-full h-full object-cover"
                  />
                </div>
              )}

              {uploadError && (
                <p className="text-xs text-red-600 my-2 bg-red-50/80 px-3.5 py-1.5 rounded-xl border border-red-200/60 max-w-sm">
                  {uploadError}
                </p>
              )}

              <div className="flex flex-col sm:flex-row items-center gap-3 w-full max-w-sm mt-3">
                <button
                  type="button"
                  onClick={analyzeUploadedPhoto}
                  className="btn btn-rose w-full py-2.5 font-bold text-xs sm:text-sm rounded-full flex items-center justify-center gap-2 cursor-pointer"
                >
                  <ScanFace size={16} /> <span>Analyze Photo</span>
                </button>
                <button
                  type="button"
                  onClick={cancelUpload}
                  className="btn btn-white w-full py-2.5 font-semibold text-xs sm:text-sm rounded-full cursor-pointer"
                >
                  <span>Cancel</span>
                </button>
              </div>
            </div>
          )}

          {/* STATE 5: Analyzing in Progress */}
          {flowStep === "uploading" && (
            <div className="analysis-glass-card w-full p-8 flex flex-col items-center justify-center text-center min-h-[420px]">
              <Loader2 className="animate-spin text-[#DE688E] mb-4" size={44} />
              <h3
                className="text-xl font-bold text-[#141414] mb-2"
                style={{ fontFamily: "Georgia, serif" }}
              >
                Analyzing Your Skin...
              </h3>
              <p className="text-xs sm:text-sm text-[#6B6375] max-w-sm">
                Our AI model is evaluating visible concerns, hydration, and skin characteristics.
              </p>
            </div>
          )}

          {/* STATE 6: Success */}
          {flowStep === "success" && (
            <div className="analysis-glass-card w-full p-8 flex flex-col items-center justify-center text-center min-h-[420px]">
              <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mb-4">
                <CheckCircle2 className="text-[#7DBE95]" size={36} />
              </div>
              <h2
                className="text-2xl font-bold text-[#141414] mb-2"
                style={{ fontFamily: "Georgia, serif" }}
              >
                You&apos;re All Set!
              </h2>
              <p className="text-xs sm:text-sm text-[#6B6375] max-w-sm mb-6 leading-relaxed">
                Your skin analysis is complete! We have personalized your recommendations and morning/night routine.
              </p>
              <button
                type="button"
                className="btn btn-rose py-3 px-8 text-sm font-bold rounded-full shadow-[0_8px_24px_rgba(238,142,163,0.4)] cursor-pointer"
                onClick={() => router.push("/dashboard")}
              >
                <span>Go to Dashboard</span>
              </button>
            </div>
          )}

          {/* STATE 7: Error */}
          {flowStep === "error" && (
            <div className="analysis-glass-card w-full p-8 flex flex-col items-center justify-center text-center min-h-[420px]">
              <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mb-4">
                <AlertCircle className="text-red-500" size={36} />
              </div>
              <h3
                className="text-xl font-bold text-[#141414] mb-2"
                style={{ fontFamily: "Georgia, serif" }}
              >
                Analysis Failed
              </h3>
              <p className="text-xs sm:text-sm text-[#6B6375] max-w-sm mb-6">
                {uploadError || "We couldn't analyze your photo. Please try again with good lighting."}
              </p>
              <div className="flex flex-col sm:flex-row items-center gap-3">
                <button
                  type="button"
                  className="btn btn-rose py-2.5 px-6 font-bold text-xs sm:text-sm rounded-full flex items-center gap-2 cursor-pointer"
                  onClick={retake}
                >
                  <RotateCcw size={16} /> <span>Try Again</span>
                </button>
                <button
                  type="button"
                  className="btn btn-white py-2.5 px-6 font-semibold text-xs sm:text-sm rounded-full flex items-center gap-2 cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload size={16} /> <span>Upload Photo Instead</span>
                </button>
              </div>
            </div>
          )}

          <canvas ref={canvasRef} className="hidden" />
        </div>
      </div>
    </main>
  );
}