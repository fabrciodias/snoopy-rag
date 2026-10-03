import {
    apiRequest,
} from "./client";

import type {
    TranslationResponse,
} from "../../types/translation";

export interface TranslationRequest {
    text: string;
}

export async function translate(
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