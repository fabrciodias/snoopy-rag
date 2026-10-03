import {
    apiRequest,
} from "./client";

import type {
    InvestigationResponse,
} from "../../types/investigation";

export interface InvestigateRequest {
    query: string;
    folder_id: string;
}

export async function investigate(
    request: InvestigateRequest,
): Promise<InvestigationResponse> {
    return apiRequest<InvestigationResponse>(
        "/investigate/",
        {
            method: "POST",

            body: JSON.stringify(request),
        },
    );
}