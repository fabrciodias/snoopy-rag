import type {
    InvestigationResponse,
} from "../types/investigation";

import type {
    Evidence,
} from "../types/evidence";

export type InvestigationStatus =
    | "IDLE"
    | "PROCESSING"
    | "COMPLETED"
    | "FAILED";

export interface InvestigationState {
    status: InvestigationStatus;

    query: string;

    investigation:
        InvestigationResponse["investigation"] | null;

    response:
        InvestigationResponse["response"];

    evidences: Evidence[];

    selectedEvidenceId: string | null;

    error: string | null;
}

export const investigationState: InvestigationState = {
    status: "IDLE",

    query: "",

    investigation: null,

    response: null,

    evidences: [],

    selectedEvidenceId: null,

    error: null,
};

export function resetInvestigation(): void {
    investigationState.status = "IDLE";

    investigationState.query = "";

    investigationState.investigation = null;

    investigationState.response = null;

    investigationState.evidences = [];

    investigationState.selectedEvidenceId = null;

    investigationState.error = null;
}


export function startInvestigation(
    query: string,
): void {
    investigationState.status = "PROCESSING";

    investigationState.query = query;

    investigationState.investigation = null;

    investigationState.response = null;

    investigationState.evidences = [];

    investigationState.selectedEvidenceId = null;

    investigationState.error = null;
}


export function completeInvestigation(
    data: InvestigationResponse,
): void {
    investigationState.status = "COMPLETED";

    investigationState.investigation =
        data.investigation;

    investigationState.response =
        data.response;

    investigationState.evidences =
        data.evidences;

    investigationState.error = null;
}


export function failInvestigation(
    error: unknown,
): void {
    investigationState.status = "FAILED";

    investigationState.error =
        error instanceof Error
            ? error.message
            : String(error);
}


export function selectEvidence(
    evidenceId: string | null,
): void {
    investigationState.selectedEvidenceId =
        evidenceId;
}