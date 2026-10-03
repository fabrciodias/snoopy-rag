import {
    reactive,
} from "vue";

import type {
    Session,
    User,
} from "@supabase/supabase-js";

export interface AuthState {
    initialized: boolean;
    session: Session | null;
    user: User | null;
    error: string | null;
}

export const authState = reactive<AuthState>({
    initialized: false,
    session: null,
    user: null,
    error: null,
});

export function setSession(
    session: Session | null,
): void {
    authState.session = session;
    authState.user = session?.user ?? null;
}

export function setAuthError(
    error: unknown,
): void {
    authState.error =
        error instanceof Error
            ? error.message
            : String(error);
}