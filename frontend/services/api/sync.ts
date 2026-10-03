import {
    apiRequest,
} from "./client";

import type {
    SyncStartResponse,
} from "../../types/sync";

export interface SyncRequest {
    folder_id: string;
    google_token: string;
}

export async function startSync(
    request: SyncRequest,
): Promise<SyncStartResponse> {
    return apiRequest<SyncStartResponse>(
        "/sync-drive/",
        {
            method: "POST",

            body: JSON.stringify(request),
        },
    );
}