import {
    createClient,
    type Session,
    type SupabaseClient,
} from "@supabase/supabase-js";

import { loadConfig } from "./config";

let supabaseClient: SupabaseClient | null = null;

const GOOGLE_PROVIDER_TOKEN_KEY =
    "snoopy_g_token";

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

function persistGoogleProviderToken(
    session: Session | null,
): void {
    if (session?.provider_token) {
        localStorage.setItem(
            GOOGLE_PROVIDER_TOKEN_KEY,
            session.provider_token,
        );

        return;
    }

    if (!session) {
        localStorage.removeItem(
            GOOGLE_PROVIDER_TOKEN_KEY,
        );
    }
}

export function getGoogleProviderToken(): string | null {
    return localStorage.getItem(
        GOOGLE_PROVIDER_TOKEN_KEY,
    );
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

    persistGoogleProviderToken(
        data.session,
    );

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

    localStorage.removeItem(
        GOOGLE_PROVIDER_TOKEN_KEY,
    );
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
            persistGoogleProviderToken(
                session,
            );

            callback(session);
        },
    );

    return () => {
        data.subscription.unsubscribe();
    };
}