export const investigationState = {
    status: "IDLE",

    query: "",

    investigation: null,

    response: null,

    evidences: [],

    selectedEvidenceId: null,

    error: null,
};


export function resetInvestigation() {
    investigationState.status =
        "IDLE";

    investigationState.query =
        "";

    investigationState.investigation =
        null;

    investigationState.response =
        null;

    investigationState.evidences =
        [];

    investigationState.selectedEvidenceId =
        null;

    investigationState.error =
        null;
}


export function startInvestigation(
    query
) {
    investigationState.status =
        "PROCESSING";

    investigationState.query =
        query;

    investigationState.investigation =
        null;

    investigationState.response =
        null;

    investigationState.evidences =
        [];

    investigationState.selectedEvidenceId =
        null;

    investigationState.error =
        null;
}


export function completeInvestigation(
    data
) {
    investigationState.status =
        "COMPLETED";

    investigationState.investigation =
        data.investigation;

    investigationState.response =
        data.response;

    investigationState.evidences =
        data.evidences || [];

    investigationState.error =
        null;
}


export function failInvestigation(
    error
) {
    investigationState.status =
        "FAILED";

    investigationState.error =
        error;
}


export function selectEvidence(
    evidenceId
) {
    investigationState.selectedEvidenceId =
        evidenceId;
}