import {
    getDocument,
} from "./api";

import type {
    Document,
} from "./contracts";

export async function loadDocument(
    documentId: string,
): Promise<Document> {
    return getDocument(documentId);
}