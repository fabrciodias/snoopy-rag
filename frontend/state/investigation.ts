import {
    reactive,
} from "vue";

import type {
    Evidence,
    HistoryEntry,
    Investigation,
    StructuredResponse,
} from "../features/investigation/contracts";

export interface InvestigationState {
    activeInvestigation: Investigation | null;
    response: StructuredResponse | null;
    evidences: Evidence[];

    history: HistoryEntry[];

    currentQuery: string | null;

    isInvestigating: boolean;
    error: string | null;

    activeOperationId: string | null;
    activeInvestigationId: string | null;

    resultMessage: string | null;
}

export const investigationState =
    reactive<InvestigationState>({
        activeOperationId: null,
        activeInvestigationId: null,

        resultMessage: null,

        activeInvestigation: null,
        response: null,
        evidences: [],

        history: [],

        currentQuery: null,

        isInvestigating: false,
        error: null,
    });

export function clearInvestigation(): void {
    investigationState.activeOperationId = null;
    investigationState.activeInvestigationId = null;

    investigationState.resultMessage = null;

    investigationState.activeInvestigation = null;
    investigationState.response = null;
    investigationState.evidences = [];

    investigationState.currentQuery = null;

    investigationState.isInvestigating = false;
    investigationState.error = null;
}

export function clearHistory(): void {
    investigationState.history = [];
}

export function setInvestigationError(
    error: unknown,
): void {
    investigationState.error =
        error instanceof Error
            ? error.message
            : String(error);
}