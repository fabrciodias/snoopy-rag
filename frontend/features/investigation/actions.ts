import {
    investigate as investigateRequest,
    listHistory,
    getInvestigation,
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

        try {
            await loadHistory();
        } catch (error) {
            console.error(
                "[HISTORY] Falha ao atualizar histórico:",
                error,
            );
        }
    } catch (error) {
        setInvestigationError(error);

        throw error;
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

        throw error;
    }
}

export async function loadInvestigation(
    investigationId: string,
): Promise<void> {
    investigationState.isInvestigating = true;
    investigationState.error = null;

    try {
        const result =
            await getInvestigation(
                investigationId,
            );

        investigationState.activeInvestigation =
            result.investigation;

        investigationState.response =
            result.response;

        investigationState.evidences =
            result.evidences;
    } catch (error) {
        setInvestigationError(error);

        throw error;
    } finally {
        investigationState.isInvestigating = false;
    }
}