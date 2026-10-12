import {
    syncDrive as syncDriveRequest,
} from "./api";

import {
    operationState,
    setOperationError,
} from "../../state/operations";

import {
    folderState,
} from "../../state/folders";

import {
    getWorkContextVersion,
} from "../../state/workContext";

import {
    waitForOperation,
} from "../operations/actions";

import type {
    DriveSyncRequest,
    DriveSyncResponse,
} from "./contracts";

type ContextCheck = () => boolean;

export async function syncDrive(
    request: DriveSyncRequest,
    contextCheck?: ContextCheck,
): Promise<DriveSyncResponse | null> {
    const contextVersion =
        getWorkContextVersion();

    const isCurrentContext = () =>
        contextVersion ===
            getWorkContextVersion() &&
        folderState.selectedFolderId ===
            request.folder_id &&
        (!contextCheck || contextCheck());

    if (!isCurrentContext()) {
        return null;
    }

    operationState.error = null;

    try {
        const result =
            await syncDriveRequest(
                request,
            );

        if (!isCurrentContext()) {
            return null;
        }

        const operation =
            await waitForOperation(
                result.operation_id,
                isCurrentContext,
            );

        if (
            !operation ||
            !isCurrentContext()
        ) {
            return null;
        }

        if (!operation.operation_id) {
            throw new Error(
                "O backend não retornou um identificador válido " +
                "para a operação de sincronização.",
            );
        }

        return {
            operation_id:
                operation.operation_id,
            status: operation.status,
        };
    } catch (error) {
        if (!isCurrentContext()) {
            return null;
        }

        setOperationError(error);

        throw error;
    }
}