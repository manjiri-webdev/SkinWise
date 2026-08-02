// Talks to the FastAPI backend's /upload endpoint.
// NEXT_PUBLIC_AI_BACKEND_URL should point at your backend, e.g. http://localhost:8000
// Add it to .env.local: NEXT_PUBLIC_AI_BACKEND_URL=http://localhost:8000

const AI_BACKEND_URL = process.env.NEXT_PUBLIC_AI_BACKEND_URL;

export type ValidationStatus = "passed" | "warning" | "failed" | "pending";

export type ValidationCheck = {
  id: string;
  label: string;
  status: ValidationStatus;
  message: string;
};

export type BackendValidationResponse = {
  ready_for_analysis: boolean;
  validation: {
    brightness: ValidationCheck;
    face_orientation: ValidationCheck;
    blur?: ValidationCheck;
    face_detection?: ValidationCheck;
    single_face?: ValidationCheck;
  };
};

export type UploadValidationResponse = {
  filename: string;
  image_info: unknown;
  blur_results: unknown;
  brightness_result: unknown;
  detected_face: unknown;
  face_orientation?: unknown;
  summary?: unknown;
  severity?: unknown;
  acne_detections?: unknown;
};

export async function uploadFaceImage(file: File): Promise<UploadValidationResponse> {
  if (!AI_BACKEND_URL) {
    throw new Error("AI backend URL is not configured. Set NEXT_PUBLIC_AI_BACKEND_URL in .env.local");
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${AI_BACKEND_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed with status ${response.status}`);
  }

  return response.json();
}

// Convert backend validation response to frontend validation state
export function convertBackendValidation(backendResponse: BackendValidationResponse): {
  faceDetected: { id: string; label: string; status: ValidationStatus; message: string };
  singleFace: { id: string; label: string; status: ValidationStatus; message: string };
  brightness: { id: string; label: string; status: ValidationStatus; message: string };
  faceOrientation: { id: string; label: string; status: ValidationStatus; message: string };
  blur: { id: string; label: string; status: ValidationStatus; message: string };
  readyForAnalysis: boolean;
} {
  const { validation, ready_for_analysis } = backendResponse;

  return {
    faceDetected: validation.face_detection ? {
      id: "faceDetected",
      label: "Face detected",
      status: validation.face_detection.status,
      message: validation.face_detection.message
    } : {
      id: "faceDetected",
      label: "Face detected",
      status: "passed",
      message: "Face detected successfully"
    },
    singleFace: validation.single_face ? {
      id: "singleFace",
      label: "Single face",
      status: validation.single_face.status,
      message: validation.single_face.message
    } : {
      id: "singleFace",
      label: "Single face",
      status: "passed",
      message: "Single face confirmed"
    },
    brightness: validation.brightness ? {
      id: "brightness",
      label: "Lighting",
      status: validation.brightness.status,
      message: validation.brightness.message
    } : {
      id: "brightness",
      label: "Lighting",
      status: "passed",
      message: "Lighting is good"
    },
    faceOrientation: validation.face_orientation ? {
      id: "faceOrientation",
      label: "Face position",
      status: validation.face_orientation.status,
      message: validation.face_orientation.message
    } : {
      id: "faceOrientation",
      label: "Face position",
      status: "passed",
      message: "Face position is good"
    },
    blur: validation.blur ? {
      id: "blur",
      label: "Image clarity",
      status: validation.blur.status,
      message: validation.blur.message
    } : {
      id: "blur",
      label: "Image clarity",
      status: "passed",
      message: "Image clarity is good"
    },
    readyForAnalysis: ready_for_analysis
  };
}

// Legacy evaluation function for current backend response format
// TODO: This will be replaced with convertBackendValidation once backend is updated
export function evaluateUploadResult(result: UploadValidationResponse): {
  passed: boolean;
  reason: string | null;
} {
  const blur = result.blur_results as { status?: string; message?: string } | undefined;
  const brightness = result.brightness_result as { status?: string; message?: string } | undefined;
  const face = result.detected_face as { status?: string; message?: string } | undefined;

  if (face?.status === "failed") {
    return { passed: false, reason: face.message || "Face detection failed" };
  }
  if (blur?.status === "failed") {
    return { passed: false, reason: blur.message || "The photo looks blurry" };
  }
  if (brightness?.status === "failed") {
    return { passed: false, reason: brightness.message || "Lighting conditions are not suitable" };
  }

  return { passed: true, reason: null };
}

// Validate live camera frame for real-time feedback
export async function validateLiveFrame(file: File): Promise<BackendValidationResponse> {
  if (!AI_BACKEND_URL) {
    throw new Error("AI backend URL is not configured. Set NEXT_PUBLIC_AI_BACKEND_URL in .env.local");
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${AI_BACKEND_URL}/validate-live`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Live validation failed with status ${response.status}`);
  }

  return response.json();
}