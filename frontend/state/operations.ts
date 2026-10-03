import {
    reactive,
} from "vue";

import type {
    Operation,
} from "../features/operations/contracts";

export interface OperationState {
    operations: Operation[];

    isLoading: boolean;
    error: string | null;
}

export const operationState =
    reactive<OperationState>({
        operations: [],

        isLoading: false,
        error: null,
    });

export function setOperationError(
    error: unknown,
): void {
    operationState.error =
        error instanceof Error
            ? error.message
            : String(error);
}