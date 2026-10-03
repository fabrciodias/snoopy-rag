import {
    apiRequest,
} from "./client";

import type {
    SyncStartResponse,
} from "../../types/sync";

export interface SyncRequest {
    folder_id: string;
}

export async function startSync(
    request: SyncRequest,
): Promise<SyncStartResponse> {
    return apiRequest<SyncStartResponse>(
        "/api/v3/sync-drive",
        {
            method: "POST",

            body: JSON.stringify(request),
        },
    );
}