import {
    getSession,
} from "./supabase-auth";

import {
    loadConfig,
} from "./config";

interface GooglePickerDocument {
    id: string;
    name: string;
}

interface GooglePickerData {
    action: string;
    docs?: GooglePickerDocument[];
}

interface GooglePickerView {
    setIncludeFolders(
        value: boolean,
    ): GooglePickerView;

    setMimeTypes(
        mimeTypes: string,
    ): GooglePickerView;

    setSelectFolderEnabled(
        value: boolean,
    ): GooglePickerView;

    setParent(
        parent: string,
    ): GooglePickerView;
}

interface GooglePickerBuilder {
    addView(
        view: GooglePickerView,
    ): GooglePickerBuilder;

    setOAuthToken(
        token: string,
    ): GooglePickerBuilder;

    setDeveloperKey(
        key: string,
    ): GooglePickerBuilder;

    setAppId(
        appId: string,
    ): GooglePickerBuilder;

    setCallback(
        callback: (
            data: GooglePickerData,
        ) => void | Promise<void>,
    ): GooglePickerBuilder;

    build(): {
        setVisible(
            visible: boolean,
        ): void;
    };
}

interface GooglePickerNamespace {
    DocsView: new () => GooglePickerView;

    PickerBuilder: new () => GooglePickerBuilder;

    Action: {
        PICKED: string;
    };
}

interface GooglePickerWindow
    extends Window {
    gapi?: {
        load(
            api: string,
            callback: () => void,
        ): void;
    };

    google?: {
        picker?: GooglePickerNamespace;
    };
}

let pickerPromise:
    Promise<void> | null = null;

function getGoogleWindow():
    GooglePickerWindow {
    return window as GooglePickerWindow;
}

function loadPickerApi():
    Promise<void> {
    if (pickerPromise) {
        return pickerPromise;
    }

    pickerPromise =
        new Promise<void>(
            (resolve, reject) => {
                const current =
                    getGoogleWindow();

                if (
                    current.google?.picker
                ) {
                    resolve();
                    return;
                }

                const existingScript =
                    document.querySelector(
                        'script[data-snoopy-google-picker]',
                    );

                if (existingScript) {
                    existingScript.addEventListener(
                        "load",
                        () => {
                            current.gapi?.load(
                                "picker",
                                () => resolve(),
                            );
                        },
                        {
                            once: true,
                        },
                    );

                    existingScript.addEventListener(
                        "error",
                        () =>
                            reject(
                                new Error(
                                    "Não foi possível carregar o Google Picker.",
                                ),
                            ),
                        {
                            once: true,
                        },
                    );

                    return;
                }

                const script =
                    document.createElement(
                        "script",
                    );

                script.src =
                    "https://apis.google.com/js/api.js";

                script.async = true;

                script.dataset.snoopyGooglePicker =
                    "true";

                script.onload = () => {
                    const gapi =
                        current.gapi;

                    if (!gapi) {
                        reject(
                            new Error(
                                "A API do Google não foi inicializada.",
                            ),
                        );

                        return;
                    }

                    gapi.load(
                        "picker",
                        () => resolve(),
                    );
                };

                script.onerror = () => {
                    reject(
                        new Error(
                            "Não foi possível carregar o Google Picker.",
                        ),
                    );
                };

                document.head.appendChild(
                    script,
                );
            },
        );

    return pickerPromise;
}

export async function pickDriveFolder(): Promise<{
    id: string;
    name: string;
} | null> {
    const session =
        await getSession();

    const googleToken =
        session?.provider_token;

    if (!googleToken) {
        throw new Error(
            "Não foi encontrado um token de acesso ao Google Drive. Faça login novamente.",
        );
    }

    const config =
        await loadConfig();

    if (
        !config.googleApiKey ||
        !config.googleAppId
    ) {
        throw new Error(
            "A configuração do Google Picker não está disponível.",
        );
    }

    await loadPickerApi();

    const google =
        getGoogleWindow().google;

    if (!google?.picker) {
        throw new Error(
            "O Google Picker não está disponível.",
        );
    }

    const pickerApi =
        google.picker;

    return new Promise(
        (resolve) => {
            const view =
                new pickerApi.DocsView()
                    .setIncludeFolders(true)
                    .setMimeTypes(
                        "application/vnd.google-apps.folder",
                    )
                    .setSelectFolderEnabled(
                        true,
                    )
                    .setParent("root");

            const picker =
                new pickerApi.PickerBuilder()
                    .addView(view)
                    .setOAuthToken(
                        googleToken,
                    )
                    .setDeveloperKey(
                        config.googleApiKey,
                    )
                    .setAppId(
                        config.googleAppId,
                    )
                    .setCallback(
                        (
                            data,
                        ) => {
                            if (
                                data.action !==
                                pickerApi
                                    .Action
                                    .PICKED
                            ) {
                                return;
                            }

                            const folder =
                                data.docs?.[0];

                            if (!folder) {
                                resolve(
                                    null,
                                );

                                return;
                            }

                            resolve({
                                id: folder.id,
                                name: folder.name,
                            });
                        },
                    )
                    .build();

            picker.setVisible(
                true,
            );
        },
    );
}