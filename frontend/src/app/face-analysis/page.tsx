"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { uploadFaceImage, evaluateUploadResult, convertBackendValidation, validateLiveFrame } from "@/services/faceAnalysis";
import "./face-analysis.css";

import {
  Camera,
  ShieldCheck,
  Sun,
  Glasses,
  ScanFace,
  Loader2,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Check,
  X,
  AlertTriangle,
} from "lucide-react";

type FlowStep = "instructions" | "permission" | "live" | "capturing" | "uploading" | "success" | "error";

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
  blur: ValidationCheck;
  readyForAnalysis: boolean;
}

export default function FaceAnalysis() {
  const [flowStep, setFlowStep] = useState<FlowStep>("instructions");
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [validation, setValidation] = useState<ValidationState>({
    faceDetected: { id: "faceDetected", label: "Face detected", status: "pending", message: "Waiting for face detection..." },
    singleFace: { id: "singleFace", label: "Single face", status: "pending", message: "Ensure only one face is visible" },
    brightness: { id: "brightness", label: "Lighting", status: "pending", message: "Check lighting conditions" },
    faceOrientation: { id: "faceOrientation", label: "Face position", status: "pending", message: "Face the camera directly" },
    blur: { id: "blur", label: "Image clarity", status: "pending", message: "Hold steady for clear image" },
    readyForAnalysis: false,
  });
  const [isValidating, setIsValidating] = useState(false);
  const [streamReady, setStreamReady] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const router = useRouter();

  useEffect(() => {
    // Ensure video element is properly configured
    if (videoRef.current) {
      console.log("Video element ref is available");
    }
    
    return () => {
      stopCamera();
    };
  }, []);

  // Debug: Log when video ref changes
  useEffect(() => {
    console.log("Video ref changed:", videoRef.current);
    if (videoRef.current) {
      console.log("Video element dimensions:", videoRef.current.offsetWidth, "x", videoRef.current.offsetHeight);
      console.log("Video srcObject:", videoRef.current.srcObject);
    }
  }, [flowStep]);

  // Attach stream to video element when both are ready
  useEffect(() => {
    if (streamReady && videoRef.current && streamRef.current) {
      console.log("Both stream and video ref are ready, attaching stream...");
      const video = videoRef.current;
      const stream = streamRef.current;
      
      video.srcObject = stream;
      
      video.onloadedmetadata = async () => {
        console.log("Video metadata loaded, dimensions:", video.videoWidth, "x", video.videoHeight);
        console.log("Video readyState:", video.readyState);
        
        try {
          await video.play();
          console.log("Video started playing successfully");
          console.log("Video paused:", video.paused);
          
          // Force a reflow to ensure the video is rendered
          video.style.setProperty('display', 'block');
          
        } catch (playError) {
          console.error("Video play error:", playError);
          setPermissionError("Unable to start camera. Please try again.");
        }
      };
      
      video.onerror = (error) => {
        console.error("Video element error:", error);
        setPermissionError("Camera error. Please check your device and try again.");
      };

      // Fallback: try to play immediately if metadata is already loaded
      if (video.readyState >= 2) {
        try {
          video.play();
          console.log("Video started playing immediately (metadata already loaded)");
        } catch (playError) {
          console.error("Immediate video play error:", playError);
        }
      }
    } else if (streamReady && !videoRef.current) {
      console.log("Stream is ready but video ref is null, waiting for video element to render...");
      // Retry after a short delay using setTimeout
      const retryTimer = setTimeout(() => {
        if (videoRef.current && streamRef.current) {
          console.log("Retry: Video ref is now available, attaching stream...");
          const video = videoRef.current;
          const stream = streamRef.current;
          
          video.srcObject = stream;
          
          video.onloadedmetadata = async () => {
            console.log("Video metadata loaded (retry), dimensions:", video.videoWidth, "x", video.videoHeight);
            try {
              await video.play();
              console.log("Video started playing successfully (retry)");
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

  const requestCameraAccess = async () => {
    setFlowStep("permission");
    setPermissionError(null);
    setStreamReady(false);

    try {
      console.log("Requesting camera access...");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false,
      });

      console.log("Camera access granted, stream obtained:", stream);
      streamRef.current = stream;

      // First change to live step to render the video element
      setFlowStep("live");
      
      // Wait for the video element to be rendered (React needs a render cycle)
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // Set stream ready to trigger the useEffect that attaches the stream
      setStreamReady(true);

      // Start live validation
      setIsValidating(true);

    } catch (err) {
      console.error("Camera access error:", err);
      setPermissionError(
        "Camera access was denied. Please allow camera permission in your browser settings and try again."
      );
      setFlowStep("permission");
    }
  };

  // Set up live validation interval when in live mode
  useEffect(() => {
    let validationInterval: NodeJS.Timeout | null = null;

    if (flowStep === "live" && isValidating) {
      validationInterval = setInterval(async () => {
        if (!videoRef.current || !canvasRef.current) {
          return;
        }

        try {
          const video = videoRef.current;
          const canvas = canvasRef.current;
          
          // Set canvas dimensions to match video
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          
          const ctx = canvas.getContext("2d");
          if (!ctx) return;

          // Mirror the image horizontally (CSS already mirrors, so canvas needs to match)
          ctx.translate(canvas.width, 0);
          ctx.scale(-1, 1);
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

          // Convert canvas to blob
          canvas.toBlob(async (blob) => {
            if (!blob) return;

            const file = new File([blob], "live-frame.jpg", { type: "image/jpeg" });
            
            try {
              const backendValidation = await validateLiveFrame(file);
              const frontendValidation = convertBackendValidation(backendValidation);
              
              setValidation(frontendValidation);
            } catch (error) {
              console.error("Live validation error:", error);
              // Don't clear validation on error, just log it
            }
          }, "image/jpeg", 0.5);
        } catch (error) {
          console.error("Frame capture error:", error);
        }
      }, 2000); // Validate every 2 seconds
    }

    // Cleanup interval when component unmounts or flow changes
    return () => {
      if (validationInterval) {
        clearInterval(validationInterval);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flowStep, isValidating]);

  // Stop validation when leaving live mode
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
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Mirror the image horizontally (CSS already mirrors, so canvas needs to match)
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(async (blob) => {
      if (!blob) return;

      stopCamera();
      setFlowStep("uploading");
      setUploadError(null);

      const file = new File([blob], "face-capture.jpg", { type: "image/jpeg" });

      try {
        const result = await uploadFaceImage(file);
        
        // Try to use new backend validation format first
        if ('ready_for_analysis' in result && 'validation' in result) {
          const backendValidation = result as any;
          const frontendValidation = convertBackendValidation(backendValidation);
          
          if (!frontendValidation.readyForAnalysis) {
            // Get the first failed validation message
            const failedCheck = Object.values(frontendValidation).find(
              (check): check is ValidationCheck => 
                typeof check === 'object' && check.status === 'failed'
            );
            setUploadError(failedCheck?.message || "Please adjust your position and try again.");
            setFlowStep("error");
            return;
          }
        } else {
          // Fall back to legacy validation
          const { passed, reason } = evaluateUploadResult(result);
          if (!passed) {
            setUploadError(reason);
            setFlowStep("error");
            return;
          }
        }

        await markFaceAnalysisComplete();
        setFlowStep("success");
      } catch (err) {
        console.error(err);
        setUploadError("Something went wrong while analyzing your photo. Please try again.");
        setFlowStep("error");
      }
    }, "image/jpeg", 0.5);
  };

  const markFaceAnalysisComplete = async () => {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) return;

    await supabase
      .from("user_profiles")
      .update({
        face_analysis_completed: true,
        onboarding_completed: true,
      })
      .eq("id", user.id);
  };

  const retake = async () => {
    setUploadError(null);
    // Reset validation state
    setValidation({
      faceDetected: { id: "faceDetected", label: "Face detected", status: "pending", message: "Waiting for face detection..." },
      singleFace: { id: "singleFace", label: "Single face", status: "pending", message: "Ensure only one face is visible" },
      brightness: { id: "brightness", label: "Lighting", status: "pending", message: "Check lighting conditions" },
      faceOrientation: { id: "faceOrientation", label: "Face position", status: "pending", message: "Face the camera directly" },
      blur: { id: "blur", label: "Image clarity", status: "pending", message: "Hold steady for clear image" },
      readyForAnalysis: false,
    });
    await requestCameraAccess();
  };

  const getStatusIcon = (status: ValidationStatus) => {
    switch (status) {
      case "passed":
        return <Check size={16} className="text-green-500" />;
      case "warning":
        return <AlertTriangle size={16} className="text-yellow-500" />;
      case "failed":
        return <X size={16} className="text-red-500" />;
      default:
        return <Loader2 size={16} className="text-gray-400 animate-spin" />;
    }
  };

  const getStatusColor = (status: ValidationStatus) => {
    switch (status) {
      case "passed":
        return "bg-green-500";
      case "warning":
        return "bg-yellow-500";
      case "failed":
        return "bg-red-500";
      default:
        return "bg-gray-400";
    }
  };

  const passedChecksCount = Object.values(validation).filter(
    (check): check is ValidationCheck => 
      typeof check === 'object' && check.status === 'passed'
  ).length;
  
  const totalChecks = 5;

  return (
    <main className="min-h-screen w-full bg-gradient-to-br from-lavender/20 via-pink-50/30 to-creamGradient2/20 flex justify-center items-center p-4 md:p-8">
      <div className="w-full max-w-6xl flex flex-col lg:flex-row gap-6 items-center justify-center">
        
        {/* Left Validation Panel */}
        <div className="w-full lg:w-80 order-2 lg:order-1">
          <div className="glass p-6 rounded-3xl bg-white/40 backdrop-blur-xl shadow-floaty animate-elements">
            <h2 className="text-xl font-semibold text-[#2D2D2D] mb-6 flex items-center gap-2">
              <ScanFace className="text-pink-400" size={24} />
              Camera Status
            </h2>
            
            <div className="space-y-4">
              {/* Face Detected */}
              <div className="flex items-start gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${getStatusColor(validation.faceDetected.status)}`}>
                  {getStatusIcon(validation.faceDetected.status)}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#2D2D2D]">{validation.faceDetected.label}</p>
                  <p className="text-xs text-textSecondary mt-1">{validation.faceDetected.message}</p>
                </div>
              </div>

              {/* Single Face */}
              <div className="flex items-start gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${getStatusColor(validation.singleFace.status)}`}>
                  {getStatusIcon(validation.singleFace.status)}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#2D2D2D]">{validation.singleFace.label}</p>
                  <p className="text-xs text-textSecondary mt-1">{validation.singleFace.message}</p>
                </div>
              </div>

              {/* Brightness */}
              <div className="flex items-start gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${getStatusColor(validation.brightness.status)}`}>
                  {getStatusIcon(validation.brightness.status)}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#2D2D2D]">{validation.brightness.label}</p>
                  <p className="text-xs text-textSecondary mt-1">{validation.brightness.message}</p>
                </div>
              </div>

              {/* Face Orientation */}
              <div className="flex items-start gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${getStatusColor(validation.faceOrientation.status)}`}>
                  {getStatusIcon(validation.faceOrientation.status)}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#2D2D2D]">{validation.faceOrientation.label}</p>
                  <p className="text-xs text-textSecondary mt-1">{validation.faceOrientation.message}</p>
                </div>
              </div>

              {/* Blur */}
              <div className="flex items-start gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${getStatusColor(validation.blur.status)}`}>
                  {getStatusIcon(validation.blur.status)}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#2D2D2D]">{validation.blur.label}</p>
                  <p className="text-xs text-textSecondary mt-1">{validation.blur.message}</p>
                </div>
              </div>
            </div>

            {/* Progress */}
            <div className="mt-6 pt-6 border-t border-pink-200/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-[#2D2D2D]">Progress</span>
                <span className="text-sm font-semibold text-pink-400">{passedChecksCount}/{totalChecks} checks passed</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-pink-300 to-pink-400 h-2 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${(passedChecksCount / totalChecks) * 100}%` }}
                />
              </div>
              
              {validation.readyForAnalysis && (
                <div className="mt-4 flex items-center gap-2 text-green-600 bg-green-50 px-4 py-3 rounded-xl">
                  <CheckCircle2 size={20} />
                  <span className="text-sm font-semibold">✅ Ready for Analysis</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Center Camera Area */}
        <div className="w-full lg:flex-1 order-1 lg:order-2 flex flex-col items-center">
          <div className="w-full max-w-lg">
            <div className="text-center mb-6">
              <h1 className="text-3xl md:text-4xl font-bold text-[#2D2D2D]">AI Face Analysis</h1>
              <p className="text-textSecondary mt-2 text-sm md:text-base">
                Position your face in the oval guide for optimal analysis
              </p>
            </div>

            {/* Camera Card */}
            <div className="glass rounded-3xl overflow-hidden bg-white/40 backdrop-blur-xl shadow-floaty animate-elements">
              
              {flowStep === "instructions" && (
                <div className="p-8 flex flex-col items-center text-center gap-6">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-pink-100 to-pink-200 flex items-center justify-center">
                    <ScanFace className="text-pink-400" size={36} />
                  </div>
                  <h2 className="text-2xl font-semibold text-[#2D2D2D]">Before we start</h2>

                  <div className="flex flex-col gap-4 w-full text-left">
                    <div className="flex items-start gap-3 p-3 bg-pink-50/50 rounded-xl">
                      <Sun size={20} className="text-pink-400 mt-1 shrink-0" />
                      <p className="text-sm text-textSecondary">
                        Find a well-lit spot, ideally facing a window or light source.
                      </p>
                    </div>
                    <div className="flex items-start gap-3 p-3 bg-pink-50/50 rounded-xl">
                      <Glasses size={20} className="text-pink-400 mt-1 shrink-0" />
                      <p className="text-sm text-textSecondary">
                        Remove glasses and pull back hair covering your face.
                      </p>
                    </div>
                    <div className="flex items-start gap-3 p-3 bg-pink-50/50 rounded-xl">
                      <ScanFace size={20} className="text-pink-400 mt-1 shrink-0" />
                      <p className="text-sm text-textSecondary">
                        Hold your phone at eye level and keep a neutral expression.
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="btn w-full bg-gradient-to-r from-pink-300 to-pink-400 text-white hover:from-pink-400 hover:to-pink-500 flex items-center justify-center gap-2 py-4 rounded-xl font-medium shadow-lg shadow-pink-200/50 transition-all duration-300"
                    onClick={requestCameraAccess}
                  >
                    <Camera size={20} /> Enable Camera
                  </button>
                </div>
              )}

              {flowStep === "permission" && (
                <div className="p-8 flex flex-col items-center text-center gap-6 min-h-[400px] justify-center">
                  {!permissionError ? (
                    <>
                      <Loader2 className="animate-spin text-pink-400" size={48} />
                      <p className="text-textSecondary">Requesting camera access...</p>
                    </>
                  ) : (
                    <>
                      <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center">
                        <AlertCircle className="text-red-400" size={36} />
                      </div>
                      <p className="text-sm text-textSecondary max-w-xs">{permissionError}</p>
                      <button
                        type="button"
                        className="btn bg-gradient-to-r from-pink-300 to-pink-400 text-white hover:from-pink-400 hover:to-pink-500 flex items-center gap-2 py-3 px-6 rounded-xl font-medium"
                        onClick={requestCameraAccess}
                      >
                        <RotateCcw size={18} /> Try Again
                      </button>
                    </>
                  )}
                </div>
              )}

              {(flowStep === "live" || flowStep === "capturing") && (
                <div className="relative">
                  {/* Camera Container */}
                  <div className="relative aspect-[3/4] bg-black rounded-3xl overflow-hidden">
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      className="camera-video w-full h-full object-cover"
                      style={{ 
                        transform: 'scaleX(-1)',
                        backgroundColor: '#000',
                        width: '100%',
                        height: '100%'
                      }}
                      width="1280"
                      height="720"
                    />
                    
                    {/* Face Guide Overlay */}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                      <div className="relative">
                        {/* Oval Face Guide */}
                        <div className={`w-48 h-64 md:w-56 md:h-72 border-4 border-white/80 rounded-[50%] shadow-[0_0_0_9999px_rgba(0,0,0,0.5)] transition-all duration-300 ${
                          validation.readyForAnalysis ? 'border-green-400' : 'border-white/60'
                        }`} />
                        
                        {/* Corner Guides */}
                        <div className="absolute -top-2 -left-2 w-8 h-8 border-t-4 border-l-4 border-white/60 rounded-tl-lg" />
                        <div className="absolute -top-2 -right-2 w-8 h-8 border-t-4 border-r-4 border-white/60 rounded-tr-lg" />
                        <div className="absolute -bottom-2 -left-2 w-8 h-8 border-b-4 border-l-4 border-white/60 rounded-bl-lg" />
                        <div className="absolute -bottom-2 -right-2 w-8 h-8 border-b-4 border-r-4 border-white/60 rounded-br-lg" />
                      </div>
                    </div>

                    {/* Capturing Indicator */}
                    {flowStep === "capturing" && (
                      <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                        <div className="w-16 h-16 rounded-full border-4 border-white/30 animate-ping" />
                        <div className="absolute w-16 h-16 rounded-full border-4 border-white/60" />
                      </div>
                    )}
                  </div>

                  {/* Capture Button */}
                  <div className="p-6 flex justify-center">
                    <button
                      type="button"
                      disabled={!validation.readyForAnalysis || flowStep === "capturing"}
                      onClick={captureAndUpload}
                      className={`w-20 h-20 rounded-full border-4 transition-all duration-300 ${
                        validation.readyForAnalysis 
                          ? 'bg-white border-pink-300 hover:bg-pink-50 cursor-pointer' 
                          : 'bg-gray-300 border-gray-400 cursor-not-allowed opacity-50'
                      }`}
                    >
                      {flowStep === "capturing" ? (
                        <Loader2 className="animate-spin text-pink-400 mx-auto" size={32} />
                      ) : (
                        <div className={`w-14 h-14 rounded-full mx-auto transition-all duration-300 ${
                          validation.readyForAnalysis ? 'bg-pink-400' : 'bg-gray-400'
                        }`} />
                      )}
                    </button>
                  </div>
                </div>
              )}

              {flowStep === "uploading" && (
                <div className="p-8 flex flex-col items-center text-center gap-6 min-h-[400px] justify-center">
                  <Loader2 className="animate-spin text-pink-400" size={48} />
                  <p className="text-textSecondary">Analyzing your photo...</p>
                </div>
              )}

              {flowStep === "success" && (
                <div className="p-8 flex flex-col items-center text-center gap-6 min-h-[400px] justify-center">
                  <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center">
                    <CheckCircle2 className="text-green-500" size={36} />
                  </div>
                  <h2 className="text-xl font-semibold text-[#2D2D2D]">You're all set!</h2>
                  <p className="text-sm text-textSecondary max-w-xs">
                    Your photo passed quality checks. We're putting together your personalized skincare profile.
                  </p>
                  <button
                    type="button"
                    className="btn w-full bg-gradient-to-r from-pink-300 to-pink-400 text-white hover:from-pink-400 hover:to-pink-500 py-4 rounded-xl font-medium"
                    onClick={() => router.push("/dashboard")}
                  >
                    Go to Dashboard
                  </button>
                </div>
              )}

              {flowStep === "error" && (
                <div className="p-8 flex flex-col items-center text-center gap-6 min-h-[400px] justify-center">
                  <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center">
                    <AlertCircle className="text-red-400" size={36} />
                  </div>
                  <p className="text-sm text-textSecondary max-w-xs">{uploadError}</p>
                  <button
                    type="button"
                    className="btn bg-gradient-to-r from-pink-300 to-pink-400 text-white hover:from-pink-400 hover:to-pink-500 flex items-center gap-2 py-3 px-6 rounded-xl font-medium"
                    onClick={retake}
                  >
                    <RotateCcw size={18} /> Retake Photo
                  </button>
                </div>
              )}

              <canvas ref={canvasRef} className="hidden" />
            </div>

            {/* Privacy Note */}
            <div className="mt-6 flex items-start gap-3 max-w-md mx-auto">
              <span className="icon-badge bg-pink-100 text-pink-400">
                <ShieldCheck size={18} />
              </span>
              <div>
                <p className="text-sm font-semibold text-[#2D2D2D]">Your privacy is important to us</p>
                <p className="text-xs text-textSecondary mt-1">
                  Your photo is only used to generate your skin analysis and is never shared.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}