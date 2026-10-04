import {
    createClient,
    type Session,
    type SupabaseClient,
} from "@supabase/supabase-js";

import { loadConfig } from "./config";

let supabaseClient: SupabaseClient | null = null;

export async function getSupabaseClient(): Promise<SupabaseClient> {
    if (supabaseClient) {
        return supabaseClient;
    }

    const config = await loadConfig();

    supabaseClient = createClient(
        config.url,
        config.key,
        {
            auth: {
                persistSession: true,
                autoRefreshToken: true,
                detectSessionInUrl: true,
            },
        },
    );

    return supabaseClient;
}

export async function getSession(): Promise<Session | null> {
    const client = await getSupabaseClient();

    const {
        data,
        error,
    } = await client.auth.getSession();

    if (error) {
        throw error;
    }

    return data.session;
}

export async function login(): Promise<void> {
    const client = await getSupabaseClient();

    const {
        error,
    } = await client.auth.signInWithOAuth({
        provider: "google",
        options: {
            redirectTo: `${window.location.origin}/`,
            scopes:
                "https://www.googleapis.com/auth/drive.readonly",
        },
    });

    if (error) {
        throw error;
    }
}

export async function logout(): Promise<void> {
    const client = await getSupabaseClient();

    const {
        error,
    } = await client.auth.signOut();

    if (error) {
        throw error;
    }
}

export async function onAuthStateChange(
    callback: (
        session: Session | null,
    ) => void,
): Promise<() => void> {
    const client = await getSupabaseClient();

    const {
        data,
    } = client.auth.onAuthStateChange(
        (_event, session) => {
            callback(session);
        },
    );

    return () => {
        data.subscription.unsubscribe();
    };
}