import {
    getSession,
} from "./supabase-auth";

export class ApiError extends Error {
    readonly status: number;

    constructor(
        message: string,
        status: number,
    ) {
        super(message);

        this.name = "ApiError";
        this.status = status;
    }
}

async function getAuthorizationHeader(): Promise<
    Record<string, string>
> {
    const session = await getSession();

    if (!session?.access_token) {
        return {};
    }

    return {
        Authorization:
            `Bearer ${session.access_token}`,
    };
}

export async function apiRequest<T>(
    path: string,
    options: RequestInit = {},
): Promise<T> {
    const authHeaders =
        await getAuthorizationHeader();

    const headers = new Headers(
        options.headers,
    );

    headers.set(
        "Content-Type",
        "application/json",
    );

    for (
        const [key, value]
        of Object.entries(authHeaders)
    ) {
        headers.set(key, value);
    }

    const response = await fetch(
        path,
        {
            ...options,
            headers,
        },
    );

    if (!response.ok) {
        let message =
            `Erro na API (${response.status}).`;

        try {
            const data =
                await response.json();

            if (
                typeof data?.detail ===
                "string"
            ) {
                message = data.detail;
            }
        } catch {
            // Mantém a mensagem HTTP padrão.
        }

        throw new ApiError(
            message,
            response.status,
        );
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return response.json() as Promise<T>;
}