import type {
    DocumentLocation,
} from "./document";

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