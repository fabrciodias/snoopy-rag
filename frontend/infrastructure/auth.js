import {
    appState,
} from "../state/application.js";

let pickerLoadPromise = null;

function storeProviderToken(session) {
    if (session?.provider_token) {
        localStorage.setItem(
            "snoopy_g_token",
            session.provider_token
        );
    }

    appState.googleToken =
        localStorage.getItem(
            "snoopy_g_token"
        );
}

function clearProviderToken() {
    localStorage.removeItem(
        "snoopy_g_token"
    );

    appState.googleToken = null;
}

export async function initAuth(
    onSessionUpdate
) {
    const response = await fetch(
        "/config"
    );

    if (!response.ok) {
        throw new Error(
            "Falha ao carregar a configuração da aplicação."
        );
    }

    const config =
        await response.json();

    appState.supabaseClient =
        window.supabase.createClient(
            config.url,
            config.key,
            {
                auth: {
                    storage: window.localStorage,
                    autoRefreshToken: true,
                    persistSession: true,
                    detectSessionInUrl: true,
                },
            }
        );

    appState.googleApiKey =
        config.googleApiKey;

    appState.googleAppId =
        config.googleAppId;

    /*
     * Registra o listener imediatamente após
     * a criação do cliente.
     *
     * Não fazemos chamadas assíncronas diretamente
     * dentro do callback do Supabase.
     */
    appState.supabaseClient.auth
        .onAuthStateChange(
            (event, session) => {
                if (session?.provider_token) {
                    storeProviderToken(
                        session
                    );
                }

                if (
                    event ===
                    "SIGNED_OUT"
                ) {
                    clearProviderToken();
                }

                setTimeout(() => {
                    onSessionUpdate(
                        session,
                        event
                    );
                }, 0);
            }
        );

    const {
        data,
        error,
    } =
        await appState.supabaseClient.auth
            .getSession();

    if (error) {
        throw error;
    }

    const session =
        data.session;

    if (session) {
        storeProviderToken(
            session
        );
    }

    appState.session = session;
    appState.user =
        session?.user || null;
    appState.userToken =
        session?.access_token || null;

    appState.isAuthLoaded = true;

    await onSessionUpdate(
        session,
        "INITIAL_SESSION"
    );
}

export async function login() {
    if (
        !appState.supabaseClient
    ) {
        throw new Error(
            "Autenticação ainda não foi inicializada."
        );
    }

    const {
        error,
    } =
        await appState.supabaseClient.auth
            .signInWithOAuth({
                provider: "google",
                options: {
                    scopes:
                        "https://www.googleapis.com/auth/drive.readonly",
                },
            });

    if (error) {
        throw error;
    }
}

export async function logout() {
    clearProviderToken();

    if (
        appState.supabaseClient
    ) {
        await appState.supabaseClient.auth
            .signOut();
    }
}

export function loadGooglePicker() {
    if (
        pickerLoadPromise
    ) {
        return pickerLoadPromise;
    }

    pickerLoadPromise =
        new Promise(
            (resolve, reject) => {
                if (
                    window.gapi
                ) {
                    window.gapi.load(
                        "picker",
                        () => {
                            appState.pickerApiLoaded =
                                true;

                            resolve();
                        }
                    );

                    return;
                }

                const script =
                    document.createElement(
                        "script"
                    );

                script.src =
                    "https://apis.google.com/js/api.js";

                script.async = true;

                script.onload = () => {
                    window.gapi.load(
                        "picker",
                        () => {
                            appState.pickerApiLoaded =
                                true;

                            resolve();
                        }
                    );
                };

                script.onerror =
                    () => {
                        reject(
                            new Error(
                                "Não foi possível carregar o Google Picker."
                            )
                        );
                    };

                document.body.appendChild(
                    script
                );
            }
        );

    return pickerLoadPromise;
}