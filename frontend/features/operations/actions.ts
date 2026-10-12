import {
    getActiveFolderSync,
    getOperation,
    listenToOperationEvents,
} from "./api";

import {
    operationState,
    setOperationError,
} from "../../state/operations";

import {
    getWorkContextVersion,
} from "../../state/workContext";

import type {
    Operation,
} from "./contracts";


type ContextCheck = () => boolean;


const POLL_INTERVAL_MS = 1500;

const OPERATION_TIMEOUT_MS =
    5 * 60 * 1000;


function storeOperation(
    operation: Operation,
): void {
    const index =
        operationState.operations.findIndex(
            (current) =>
                current.operation_id ===
                operation.operation_id,
        );

    if (index === -1) {
        operationState.operations.push(
            operation,
        );

        return;
    }

    operationState.operations[index] =
        operation;
}


function isTerminalStatus(
    status: Operation["status"],
): boolean {
    return (
        status === "COMPLETED" ||
        status === "FAILED" ||
        status === "CANCELLED"
    );
}


function wait(
    milliseconds: number,
): Promise<void> {
    return new Promise(
        (resolve) =>
            setTimeout(
                resolve,
                milliseconds,
            ),
    );
}


function operationTimeoutError(): Error {
    return new Error(
        "Não foi possível confirmar o estado " +
        "da operação dentro do tempo de espera. " +
        "Ela pode continuar em segundo plano.",
    );
}


export async function loadOperation(
    operationId: string,
): Promise<Operation | null> {
    const contextVersion =
        getWorkContextVersion();

    const isCurrentContext = () =>
        contextVersion ===
        getWorkContextVersion();

    operationState.error = null;

    try {
        const operation =
            await getOperation(
                operationId,
            );

        if (!isCurrentContext()) {
            return null;
        }

        storeOperation(operation);

        return operation;
    } catch (error) {
        if (!isCurrentContext()) {
            return null;
        }

        setOperationError(error);

        throw error;
    }
}


/**
 * Procura uma sincronização ativa para um acervo.
 *
 * A API continua sendo a fonte autoritativa do estado.
 * O frontend apenas recupera a operação para acompanhá-la.
 */
export async function loadActiveFolderSync(
    folderId: string,
    contextCheck?: ContextCheck,
): Promise<Operation | null> {
    const contextVersion =
        getWorkContextVersion();

    const isCurrentContext = () =>
        contextVersion ===
            getWorkContextVersion() &&
        (!contextCheck || contextCheck());

    try {
        const operation =
            await getActiveFolderSync(
                folderId,
            );

        if (!isCurrentContext()) {
            return null;
        }

        if (!operation) {
            return null;
        }

        if (!operation.operation_id) {
            throw new Error(
                "A operação de sincronização não possui " +
                "um identificador válido.",
            );
        }

        storeOperation(operation);

        return operation;
    } catch (error) {
        if (!isCurrentContext()) {
            return null;
        }

        setOperationError(error);

        throw error;
    }
}


export async function refreshOperation(
    operationId: string,
    contextCheck?: ContextCheck,
): Promise<Operation | null> {
    const contextVersion =
        getWorkContextVersion();

    const isCurrentContext =
        contextCheck ??
        (() =>
            contextVersion ===
            getWorkContextVersion());

    try {
        const operation =
            await getOperation(
                operationId,
            );

        if (!isCurrentContext()) {
            return null;
        }

        storeOperation(operation);

        return operation;
    } catch (error) {
        if (!isCurrentContext()) {
            return null;
        }

        setOperationError(error);

        throw error;
    }
}


/**
 * Aguarda uma operação usando SSE.
 *
 * A cada evento operation_changed, consulta novamente
 * a API para obter o estado confirmado.
 *
 * Se o fluxo SSE falhar, o acompanhamento continua
 * por polling. A falha do canal não significa que a
 * operação tenha falhado.
 */
export async function waitForOperation(
    operationId: string,
    contextCheck?: ContextCheck,
): Promise<Operation | null> {
    const contextVersion =
        getWorkContextVersion();

    const isCurrentContext =
        contextCheck ??
        (() =>
            contextVersion ===
            getWorkContextVersion());

    const startedAt = Date.now();

    let pollingFallback = false;

    while (true) {
        if (!isCurrentContext()) {
            return null;
        }

        // Sempre consultamos a fonte autoritativa.
        const operation =
            await refreshOperation(
                operationId,
                isCurrentContext,
            );

        if (
            !operation ||
            !isCurrentContext()
        ) {
            return null;
        }

        if (
            isTerminalStatus(
                operation.status,
            )
        ) {
            return operation;
        }

        const elapsed =
            Date.now() - startedAt;

        if (
            elapsed >=
            OPERATION_TIMEOUT_MS
        ) {
            throw operationTimeoutError();
        }

        /*
         * Se o SSE não estiver disponível, mantemos
         * o acompanhamento pela API.
         */
        if (pollingFallback) {
            await wait(
                POLL_INTERVAL_MS,
            );

            continue;
        }

        const controller =
            new AbortController();

        const remainingTime =
            OPERATION_TIMEOUT_MS - elapsed;

        const timeoutHandle =
            setTimeout(
                () => controller.abort(),
                remainingTime,
            );

        let streamEndedNormally = false;

        try {
            for await (
                const event
                of listenToOperationEvents(
                    operationId,
                    controller.signal,
                )
            ) {
                if (!isCurrentContext()) {
                    controller.abort();

                    return null;
                }

                /*
                 * Heartbeat mantém a conexão ativa e permite
                 * verificar se o contexto de trabalho mudou.
                 * Não exige nova consulta da operação.
                 */
                if (
                    event.event === "heartbeat"
                ) {
                    continue;
                }

                if (
                    event.event !==
                    "operation_changed"
                ) {
                    continue;
                }

                let payload: {
                    operation_id?: unknown;
                };

                try {
                    payload = JSON.parse(
                        event.data,
                    ) as {
                        operation_id?: unknown;
                    };
                } catch {
                    // Evento inválido não modifica o estado.
                    continue;
                }

                if (
                    payload.operation_id !==
                    operationId
                ) {
                    continue;
                }

                /*
                 * O evento apenas solicita uma revalidação.
                 * O payload não é utilizado como estado definitivo.
                 */
                const confirmedOperation =
                    await refreshOperation(
                        operationId,
                        isCurrentContext,
                    );

                if (
                    !confirmedOperation ||
                    !isCurrentContext()
                ) {
                    controller.abort();

                    return null;
                }

                if (
                    isTerminalStatus(
                        confirmedOperation.status,
                    )
                ) {
                    controller.abort();

                    return confirmedOperation;
                }
            }

            streamEndedNormally = true;
        } catch (streamError) {
            if (!isCurrentContext()) {
                return null;
            }

            if (
                Date.now() - startedAt >=
                OPERATION_TIMEOUT_MS
            ) {
                throw operationTimeoutError();
            }

            /*
             * O estado da operação continua sendo consultado
             * pela API. Apenas desativamos o uso do SSE para
             * esta espera e seguimos com polling.
             */
            pollingFallback = true;

            console.warn(
                "[OPERATIONS] Fluxo SSE indisponível. " +
                "Continuando acompanhamento pela API.",
                streamError,
            );
        } finally {
            clearTimeout(timeoutHandle);

            controller.abort();
        }

        if (
            streamEndedNormally &&
            !pollingFallback
        ) {
            /*
             * Se a conexão terminou sem confirmar um estado
             * terminal, aguardamos brevemente e voltamos a
             * consultar a API antes de reconectar.
             */
            await wait(
                POLL_INTERVAL_MS,
            );
        }
    }
}