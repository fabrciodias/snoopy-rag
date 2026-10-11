import {
    getContextualReading,
    getDocument,
} from "./api";

import type {
    ContextualReading,
    Document,
} from "./contracts";

export async function loadDocument(
    documentId: string,
): Promise<Document> {
    return getDocument(documentId);
}

export async function loadContextualReading(
    documentId: string,
    evidenceId: string,
): Promise<ContextualReading> {
    return getContextualReading(
        documentId,
        evidenceId,
    );
}