import {
    apiRequest,
    apiEventStream,
} from "../../infrastructure/api";

import type {
    ApiServerSentEvent,
} from "../../infrastructure/api";

import type {
    Operation,
} from "./contracts";


export function getOperation(
    operationId: string,
): Promise<Operation> {
    return apiRequest<Operation>(
        `/operations/${encodeURIComponent(operationId)}`,
    );
}


export function getActiveFolderSync(
    folderId: string,
): Promise<Operation | null> {
    return apiRequest<Operation | null>(
        `/operations/active?folder_id=${encodeURIComponent(folderId)}`,
    );
}


/**
 * Escuta notificações de mudança de uma operação.
 *
 * Os eventos são notificações. O consumidor deve
 * consultar getOperation() para confirmar o estado.
 */
export function listenToOperationEvents(
    operationId: string,
    signal: AbortSignal,
): AsyncGenerator<ApiServerSentEvent> {
    return apiEventStream(
        `/operations/${encodeURIComponent(operationId)}/events`,
        signal,
    );
}