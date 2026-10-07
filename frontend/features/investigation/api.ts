import {
    apiRequest,
} from "../../infrastructure/api";

import type {
    HistoryEntry,
    InvestigateRequest,
    InvestigationResponse,
} from "./contracts";

export function investigate(
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

export function listHistory(): Promise<HistoryEntry[]> {
    return apiRequest<HistoryEntry[]>(
        "/history/",
    );
}

export function getInvestigation(
    investigationId: string,
): Promise<InvestigationResponse> {
    return apiRequest<InvestigationResponse>(
        `/investigations/${investigationId}`,
    );
}