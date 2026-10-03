import {
    apiRequest,
} from "./client";

import type {
    Document,
} from "../../types/document";

export async function getDocument(
    documentId: string,
): Promise<Document> {
    return apiRequest<Document>(
        `/documents/${documentId}`,
    );
}