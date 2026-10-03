import type {
    OperationStatus,
} from "../operations/contracts";

export interface DriveSyncRequest {
    folder_id: string;
    google_token: string;
}

export interface DriveSyncResponse {
    operation_id: string;
    status: OperationStatus;
}