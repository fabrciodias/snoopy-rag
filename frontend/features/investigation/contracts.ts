export type InvestigationStatus =
    | "PROCESSING"
    | "COMPLETED"
    | "FAILED"
    | "CANCELLED";

export interface Investigation {
    investigation_id: string | null;
    user_id: string;
    folder_id: string;
    original_query: string;
    status: InvestigationStatus;
    structured_response: Record<string, unknown> | null;
    created_at: string | null;
}

export interface DocumentReference {
    document_id: string;
    title: string | null;
    authors: string | null;
    publication_year: number | null;
    drive_link: string | null;
}

export interface DocumentLocation {
    start_page: number | null;
    end_page: number | null;

    start_block: number | null;
    end_block: number | null;

    start_x0: number | null;
    start_y0: number | null;
    start_x1: number | null;
    start_y1: number | null;

    end_x0: number | null;
    end_y0: number | null;
    end_x1: number | null;
    end_y1: number | null;
}

export interface EvidenceProvenance {
    investigation_id: string;
    result_id: string;
    unit_id: number;
    document_id: string;
    representation_id: string;
    location: DocumentLocation;
}

export interface Evidence {
    evidence_id: string | null;
    investigation_id: string;
    unit_id: number;
    document_id: string;
    location: DocumentLocation;
    content: string;
    context: string;
    provenance: EvidenceProvenance;
}

export interface StructuredResponse {
    response_id: string | null;
    content: string;
    sections: Record<string, unknown>[];
    evidence_refs: string[];
    references: DocumentReference[];
}

export interface InvestigateRequest {
    folder_id: string;
    query: string;
    limit?: number;
}

export interface InvestigationResponse {
    message?: string;
    investigation: Investigation;
    response: StructuredResponse | null;
    evidences: Evidence[];
}

export interface HistoryEntry {
    query: string;
    created_at: string | null;
    investigation_id: string | null;
}