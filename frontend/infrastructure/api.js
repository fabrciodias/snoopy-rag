import {
    appState,
} from "../state/application.js";


async function getFreshAccessToken() {
    if (
        !appState.supabaseClient
    ) {
        return null;
    }

    const {
        data,
    } =
        await appState.supabaseClient.auth
            .getSession();

    const session =
        data?.session || null;

    if (session) {
        appState.session =
            session;

        appState.user =
            session.user;

        appState.userToken =
            session.access_token;

        if (
            session.provider_token
        ) {
            localStorage.setItem(
                "snoopy_g_token",
                session.provider_token
            );

            appState.googleToken =
                session.provider_token;
        }
    }

    return session?.access_token || null;
}


async function request(
    path,
    options = {},
    retry = true
) {
    let token =
        appState.userToken ||
        await getFreshAccessToken();

    const headers = {
        ...(options.headers || {}),
    };

    if (
        options.body &&
        !headers["Content-Type"]
    ) {
        headers["Content-Type"] =
            "application/json";
    }

    if (token) {
        headers.Authorization =
            `Bearer ${token}`;
    }

    let response;

    try {
        response =
            await fetch(
                path,
                {
                    ...options,
                    headers,
                }
            );
    } catch (error) {
        throw new Error(
            "Não foi possível comunicar com o servidor."
        );
    }

    if (
        response.status === 401 &&
        retry &&
        appState.supabaseClient
    ) {
        const freshToken =
            await getFreshAccessToken();

        if (
            freshToken &&
            freshToken !== token
        ) {
            appState.userToken =
                freshToken;

            return request(
                path,
                options,
                false
            );
        }
    }

    const raw =
        await response.text();

    let payload = null;

    if (raw) {
        try {
            payload =
                JSON.parse(raw);
        } catch {
            payload = {
                detail: raw,
            };
        }
    }

    if (!response.ok) {
        throw new Error(
            payload?.detail ||
            `Servidor retornou HTTP ${response.status}.`
        );
    }

    return payload;
}


/* ============================================================
   Acervos
   ============================================================ */

export async function fetchFolders() {
    const result =
        await request(
            "/folders/"
        );

    return Array.isArray(result)
        ? result
        : (result?.folders || []);
}


export async function createFolder(
    name,
    driveId
) {
    return request(
        "/folders/",
        {
            method: "POST",
            body: JSON.stringify({
                name,
                drive_id: driveId,
            }),
        }
    );
}


export async function disconnectFolder(
    folderId
) {
    return request(
        `/folders/${encodeURIComponent(folderId)}`,
        {
            method: "DELETE",
        }
    );
}


/* ============================================================
   Investigação
   ============================================================ */

export async function investigate(
    folderId,
    query,
    limit = 5
) {
    return request(
        "/investigate/",
        {
            method: "POST",
            body: JSON.stringify({
                folder_id: folderId,
                query,
                limit,
            }),
        }
    );
}


/* ============================================================
   Sincronização
   ============================================================ */

export async function startSync(
    folderId,
    googleToken
) {
    return request(
        "/sync-drive/",
        {
            method: "POST",
            body: JSON.stringify({
                folder_id: folderId,
                google_token: googleToken,
            }),
        }
    );
}


export async function getOperation(
    operationId
) {
    return request(
        `/operations/${encodeURIComponent(operationId)}`
    );
}


function sleep(ms) {
    return new Promise(
        resolve =>
            setTimeout(
                resolve,
                ms
            )
    );
}


export async function waitForOperation(
    operationId,
    {
        onUpdate,
        interval = 1500,
        maxAttempts = 600,
    } = {}
) {
    let communicationFailures = 0;

    for (
        let attempt = 0;
        attempt < maxAttempts;
        attempt++
    ) {
        let operation;

        try {
            operation =
                await getOperation(
                    operationId
                );

            communicationFailures = 0;

        } catch (error) {
            communicationFailures += 1;

            if (
                communicationFailures >= 5
            ) {
                throw new Error(
                    "A conexão com o servidor foi perdida durante o acompanhamento da operação."
                );
            }

            await sleep(interval);
            continue;
        }

        if (onUpdate) {
            onUpdate(operation);
        }

        const status =
            String(
                operation.status || ""
            ).toUpperCase();

        /*
         * Estados terminais são tratados fora do
         * bloco de comunicação.
         *
         * Uma operação FAILED não é uma falha
         * de comunicação.
         */
        if (
            status === "COMPLETED"
        ) {
            return operation;
        }

        if (
            status === "FAILED"
        ) {
            throw new Error(
                operation.error_log ||
                "A operação falhou."
            );
        }

        if (
            status === "CANCELLED"
        ) {
            throw new Error(
                operation.error_log ||
                "A operação foi cancelada."
            );
        }

        await sleep(interval);
    }

    throw new Error(
        "A operação demorou mais do que o esperado. O estado pode ser consultado novamente."
    );
}


/* ============================================================
   Documentos / Reading
   ============================================================ */

export async function fetchDocument(
    documentId
) {
    return request(
        `/documents/${encodeURIComponent(documentId)}`
    );
}


/* ============================================================
   Histórico
   ============================================================ */

export async function fetchHistory() {
    if (!appState.user) {
        return [];
    }

    const result = await request(
        "/history/"
    );

    if (!Array.isArray(result)) {
        return [];
    }

    return result
        .map(item => {
            if (typeof item === "string") {
                return item;
            }

            return item?.query || "";
        })
        .filter(Boolean);
}
