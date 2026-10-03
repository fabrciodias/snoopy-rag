import {
    apiRequest,
} from "../../infrastructure/api";

import type {
    TranslationRequest,
    TranslationResponse,
} from "./contracts";

export function translate(
    request: TranslationRequest,
): Promise<TranslationResponse> {
    return apiRequest<TranslationResponse>(
        "/translate/",
        {
            method: "POST",
            body: JSON.stringify(request),
        },
    );
}