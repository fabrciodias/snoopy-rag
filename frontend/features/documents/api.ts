import {
    apiRequest,
} from "../../infrastructure/api";

import type {
    ContextualReading,
    Document,
} from "./contracts";

export function getDocument(
    documentId: string,
): Promise<Document> {
    return apiRequest<Document>(
        `/documents/${documentId}`,
    );
}

export function getContextualReading(
    documentId: string,
    evidenceId: string,
): Promise<ContextualReading> {
    const params = new URLSearchParams({
        evidence_id: evidenceId,
    });

    return apiRequest<ContextualReading>(
        `/documents/${encodeURIComponent(documentId)}/reading?${params.toString()}`,
    );
}