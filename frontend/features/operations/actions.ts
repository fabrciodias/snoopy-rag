import {
    getOperation,
} from "./api";

import {
    operationState,
    setOperationError,
} from "../../state/operations";

import type {
    Operation,
} from "./contracts";

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
): Promise<Operation> {
    operationState.error = null;
    operationState.isLoading = true;

    try {
        const operation =
            await getOperation(
                operationId,
            );

        storeOperation(operation);

        return operation;
    } catch (error) {
        setOperationError(error);
        throw error;
    } finally {
        operationState.isLoading =
            false;
    }
}

export async function refreshOperation(
    operationId: string,
): Promise<Operation> {
    try {
        const operation =
            await getOperation(
                operationId,
            );

        storeOperation(operation);

        return operation;
    } catch (error) {
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
): Promise<Operation> {
    const timeoutMs = 5 * 60 * 1000;
    const intervalMs = 1500;
    const startedAt = Date.now();

    while (true) {
        const operation =
            await refreshOperation(
                operationId,
            );

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
                "O acompanhamento da operação excedeu o tempo limite.",
            );
        }

        await wait(intervalMs);
    }
}