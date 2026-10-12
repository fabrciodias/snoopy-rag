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

export interface ApiServerSentEvent {
    event: string;
    data: string;
    id?: string;
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
            const data = await response.json();

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


/**
 * Converte um quadro do protocolo SSE em um evento.
 *
 * O campo data pode conter várias linhas, conforme
 * o protocolo Server-Sent Events.
 */
function parseServerSentEvent(
    frame: string,
): ApiServerSentEvent | null {
    let event = "message";
    let id: string | undefined;

    const dataLines: string[] = [];

    for (const line of frame.split("\n")) {
        if (!line || line.startsWith(":")) {
            continue;
        }

        const separator = line.indexOf(":");

        const field =
            separator === -1
                ? line
                : line.slice(0, separator);

        let value =
            separator === -1
                ? ""
                : line.slice(separator + 1);

        if (value.startsWith(" ")) {
            value = value.slice(1);
        }

        if (field === "event") {
            event = value;
        } else if (field === "data") {
            dataLines.push(value);
        } else if (field === "id") {
            id = value;
        }
    }

    if (dataLines.length === 0) {
        return null;
    }

    const parsedEvent: ApiServerSentEvent = {
        event,
        data: dataLines.join("\n"),
    };

    if (id !== undefined) {
        parsedEvent.id = id;
    }

    return parsedEvent;
}


/**
 * Abre um fluxo SSE autenticado e fornece os eventos
 * recebidos sem tratar seu conteúdo como estado definitivo.
 *
 * O consumidor é responsável por revalidar os recursos
 * pela API após receber notificações relevantes.
 */
export async function* apiEventStream(
    path: string,
    signal: AbortSignal,
): AsyncGenerator<ApiServerSentEvent> {
    const authHeaders =
        await getAuthorizationHeader();

    const headers = new Headers(
        authHeaders,
    );

    headers.set(
        "Accept",
        "text/event-stream",
    );

    const response = await fetch(
        path,
        {
            method: "GET",
            headers,
            signal,
        },
    );

    if (!response.ok) {
        let message =
            `Erro na API (${response.status}).`;

        try {
            const data = await response.json();

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

    const contentType =
        response.headers.get("content-type") ?? "";

    if (
        !contentType.includes("text/event-stream")
    ) {
        throw new Error(
            "O backend não retornou um fluxo SSE válido.",
        );
    }

    if (!response.body) {
        throw new Error(
            "O fluxo SSE não disponibilizou um corpo de resposta.",
        );
    }

    const reader =
        response.body.getReader();

    const decoder = new TextDecoder();

    let buffer = "";
    let streamCompleted = false;

    try {
        while (true) {
            const { done, value } =
                await reader.read();

            if (done) {
                streamCompleted = true;
                break;
            }

            buffer += decoder.decode(
                value,
                {
                    stream: true,
                },
            );

            // Normaliza CRLF sem perder pares divididos
            // entre dois blocos recebidos da rede.
            buffer = buffer.replace(
                /\r\n/g,
                "\n",
            );

            let separator: number;

            while (
                (
                    separator =
                        buffer.indexOf("\n\n")
                ) !== -1
            ) {
                const frame =
                    buffer.slice(
                        0,
                        separator,
                    );

                buffer =
                    buffer.slice(
                        separator + 2,
                    );

                const event =
                    parseServerSentEvent(
                        frame,
                    );

                if (event) {
                    yield event;
                }
            }
        }

        buffer += decoder.decode();

        buffer = buffer.replace(
            /\r\n/g,
            "\n",
        );

        if (buffer.trim()) {
            const finalEvent =
                parseServerSentEvent(
                    buffer,
                );

            if (finalEvent) {
                yield finalEvent;
            }
        }
    } finally {
        if (!streamCompleted) {
            void reader.cancel().catch(
                () => undefined,
            );
        }

        reader.releaseLock();
    }
}