export type OperationStatus =
    | "PENDING"
    | "PROCESSING"
    | "COMPLETED"
    | "FAILED"
    | "CANCELLED";

export type OperationTargetType =
    | "FOLDER"
    | "DOCUMENT"
    | "INVESTIGATION";

export interface OperationProgress {
    phase: string;
    message: string;

    current?: number | null;
    total?: number | null;
    unit?: string | null;

    processed?: number;
    skipped?: number;
    failed?: number;
}

export interface Operation {
    operation_id: string | null;

    operation_type: string;

    target_type: OperationTargetType | null;
    target_id: string | null;

    status: OperationStatus;

    error_log: string | null;

    progress?: OperationProgress | null;

    created_at: string | null;
    started_at: string | null;
    finished_at: string | null;
}