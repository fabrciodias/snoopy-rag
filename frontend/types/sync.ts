import type {
    OperationStatus,
} from "./operation";

export interface SyncStartResponse {
    operation_id: string;
    status: OperationStatus;
}