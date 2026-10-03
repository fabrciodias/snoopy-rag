import {
    investigate as investigateRequest,
    listHistory,
} from "./api";

import {
    investigationState,
    setInvestigationError,
} from "../../state/investigation";

import type {
    InvestigateRequest,
} from "./contracts";

export async function investigate(
    request: InvestigateRequest,
): Promise<void> {
    investigationState.isInvestigating = true;
    investigationState.error = null;

    try {
        const result =
            await investigateRequest(request);

        investigationState.activeInvestigation =
            result.investigation;

        investigationState.response =
            result.response;

        investigationState.evidences =
            result.evidences;
    } catch (error) {
        setInvestigationError(error);
    } finally {
        investigationState.isInvestigating = false;
    }
}

export async function loadHistory(): Promise<void> {
    try {
        investigationState.history =
            await listHistory();
    } catch (error) {
        setInvestigationError(error);
    }
}