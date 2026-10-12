import {
    getActiveFolderSync,
    getOperation,
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


function isTerminalStatus(
    status: Operation["status"],
): boolean {
    return (
        status === "COMPLETED" ||
        status === "FAILED" ||
        status === "CANCELLED"
    );
}


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

    const timeoutMs = 5 * 60 * 1000;
    const intervalMs = 1500;
    const startedAt = Date.now();

    while (true) {
        if (!isCurrentContext()) {
            return null;
        }

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

        if (
            Date.now() - startedAt >=
            timeoutMs
        ) {
            throw new Error(
                "Não foi possível confirmar o estado " +
                "da operação dentro do tempo de espera. " +
                "Ela pode continuar em segundo plano.",
            );
        }

        await wait(intervalMs);
    }
}