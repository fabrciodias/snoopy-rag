import {
    apiRequest,
} from "../../infrastructure/api";

import type {
    DriveSyncRequest,
    DriveSyncResponse,
} from "./contracts";

export function syncDrive(
    request: DriveSyncRequest,
): Promise<DriveSyncResponse> {
    return apiRequest<DriveSyncResponse>(
        "/sync-drive/",
        {
            method: "POST",
            body: JSON.stringify(request),
        },
    );
}