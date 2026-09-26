import { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { supabase } from "./supabase";
import { getProfile, updateProfile } from "@/services/personalization";

export async function redirectUser(router: AppRouterInstance) {
    const {
        data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
        router.replace("/auth/login");
        return;
    }

    try {
        const result = await getProfile();
        
        if (!result.exists || !result.data) {
            // Create initial profile if it doesn't exist
            await updateProfile({
                questionnaire_completed: false,
                face_analysis_completed: false,
                onboarding_completed: false,
            });
            router.replace("/questionnaire");
            return;
        }

        const profile = result.data;

        if (!profile.questionnaire_completed) {
            router.replace("/questionnaire");
            return;
        }
        if (!profile.face_analysis_completed) {
            router.replace("/face-analysis");
            return;
        }

        router.replace("/dashboard");
    } catch (error) {
        console.error("Error fetching profile:", error);
        // Don't redirect to login for transient errors - user is already authenticated
        // Default to dashboard for authenticated users
        router.replace("/dashboard");
    }
}