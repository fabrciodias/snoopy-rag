import type {
    DocumentLocation,
} from "../investigation/contracts";

export type DocumentStatus =
    | "PENDING"
    | "PROCESSING"
    | "ACTIVE"
    | "FAILED"
    | "REJECTED"
    | "REMOVED";

export interface DocumentBlock {
    block_index: number;
    text: string;
    block_type: string;

    x0: number | null;
    y0: number | null;
    x1: number | null;
    y1: number | null;
}

export interface DocumentPage {
    page_number: number;
    width: number | null;
    height: number | null;
    blocks: DocumentBlock[];
}

export interface DocumentRepresentation {
    representation_id: string;
    document_id: string;
    pages: DocumentPage[];
    metadata: Record<string, unknown>;
}

export interface Document {
    id: string;
    folder_id: string;

    title: string;
    authors: string | null;
    publication_year: number | null;

    drive_file_id: string | null;
    drive_link: string | null;

    status: DocumentStatus;

    representation: DocumentRepresentation | null;
}