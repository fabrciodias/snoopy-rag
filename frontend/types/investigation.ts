import type {
    Evidence,
} from "./evidence";

export interface Investigation {
    investigation_id: string | null;

    user_id: string;
    folder_id: string;

    original_query: string;

    status:
        | "PROCESSING"
        | "COMPLETED"
        | "FAILED"
        | "CANCELLED";

    structured_response:
        | Record<string, unknown>
        | null;

    created_at: string | null;
}

export interface StructuredResponse {
    response_id: string | null;

    content: string;

    sections: Record<string, unknown>[];

    evidence_refs: string[];

    references: Record<string, unknown>[];
}

export interface InvestigationResponse {
    investigation: Investigation;

    response: StructuredResponse | null;

    evidences: Evidence[];

    message?: string;
}