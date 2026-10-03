export class ApiError extends Error {
    status: number;

    constructor(
        message: string,
        status: number,
    ) {
        super(message);

        this.name = "ApiError";
        this.status = status;
    }
}

export async function apiRequest<T>(
    path: string,
    options: RequestInit = {},
): Promise<T> {
    const response = await fetch(path, {
        ...options,

        headers: {
            "Content-Type": "application/json",

            ...(options.headers ?? {}),
        },
    });

    if (!response.ok) {
        let message =
            `Erro na API (${response.status})`;

        try {
            const data =
                await response.json();

            if (
                typeof data?.detail === "string"
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