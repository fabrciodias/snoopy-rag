import {
    syncDrive as syncDriveRequest,
} from "./api";

import {
    operationState,
} from "../../state/operations";

import {
    waitForOperation,
} from "../operations/actions";

import type {
    DriveSyncRequest,
    DriveSyncResponse,
} from "./contracts";

export async function syncDrive(
    request: DriveSyncRequest,
): Promise<DriveSyncResponse> {
    operationState.error = null;
    operationState.isLoading = true;

    try {
        const result =
            await syncDriveRequest(
                request,
            );

        const operation =
            await waitForOperation(
                result.operation_id,
            );

        return {
            operation_id: operation.operation_id!,
            status: operation.status,
        };
    } catch (error) {
        operationState.error =
            error instanceof Error
                ? error.message
                : String(error);

        throw error;
    } finally {
        operationState.isLoading = false;
    }
}