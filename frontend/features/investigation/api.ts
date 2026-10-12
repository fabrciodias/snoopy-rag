import {
    apiRequest,
} from "../../infrastructure/api";

import type {
    HistoryEntry,
    InvestigateRequest,
    InvestigationResponse,
    InvestigationStartResponse,
} from "./contracts";


export function investigate(
    request: InvestigateRequest,
): Promise<InvestigationStartResponse> {
    return apiRequest<InvestigationStartResponse>(
        "/investigate/",
        {
            method: "POST",
            body: JSON.stringify(request),
        },
    );
}


export function listHistory(
    folderId: string,
): Promise<HistoryEntry[]> {
    const params = new URLSearchParams({
        folder_id: folderId,
    });

    return apiRequest<HistoryEntry[]>(
        `/history/?${params.toString()}`,
    );
}


export function getInvestigation(
    investigationId: string,
): Promise<InvestigationResponse> {
    return apiRequest<InvestigationResponse>(
        `/investigations/${encodeURIComponent(investigationId)}`,
    );
}