import {
    reactive,
} from "vue";

import type {
    Operation,
} from "../features/operations/contracts";

export interface OperationState {
    operations: Operation[];

    error: string | null;
}

export const operationState =
    reactive<OperationState>({
        operations: [],

        error: null,
    });

export function clearOperationError(): void {
    operationState.error = null;
}

export function clearOperationState(): void {
    operationState.operations = [];
    operationState.error = null;
}

export function setOperationError(
    error: unknown,
): void {
    operationState.error =
        error instanceof Error
            ? error.message
            : String(error);
}