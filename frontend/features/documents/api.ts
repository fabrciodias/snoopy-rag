import {
    apiRequest,
} from "../../infrastructure/api";

import type {
    Document,
} from "./contracts";

export function getDocument(
    documentId: string,
): Promise<Document> {
    return apiRequest<Document>(
        `/documents/${documentId}`,
    );
}