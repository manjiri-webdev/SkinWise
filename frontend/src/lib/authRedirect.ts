import { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { supabase } from "./supabase";

export async function redirectUser(router: AppRouterInstance) {
    const {
        data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
        router.replace("/auth/login");
        return;
    }

    const { data: profile, error } = await supabase
        .from("user_profiles")
        .select("questionnaire_completed, face_analysis_completed, onboarding_completed")
        .eq("id", user.id)
        .single();

    if (error && error.code !== "PGRST116") {
        console.error("Database error:", error);
        router.replace("/auth/login");
        return;
    }

    if (!profile) {
        const { error: insertError } = await supabase
            .from("user_profiles")
            .insert({
                id: user.id,
                questionnaire_completed: false,
                face_analysis_completed: false,
                onboarding_completed: false,
            });

        if (insertError) {
            console.error("Insert error:", insertError);
            router.replace("/auth/login");
            return;
        }

        router.replace("/questionnaire");
        return;
    }

    if (!profile.questionnaire_completed) {
        router.replace("/questionnaire");
        return;
    }
    if (!profile.face_analysis_completed) {
        router.replace("/face-analysis");
        return;
    }

    router.replace("/dashboard");
}