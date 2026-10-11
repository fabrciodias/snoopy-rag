import {
    reactive,
} from "vue";

import type {
    Session,
    User,
} from "@supabase/supabase-js";

import {
    clearUserWorkState,
} from "./workContext";

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
    const previousUserId =
        authState.user?.id ?? null;

    const nextUserId =
        session?.user?.id ?? null;

    const identityChanged =
        previousUserId !== nextUserId;

    if (identityChanged) {
        clearUserWorkState();
    }

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