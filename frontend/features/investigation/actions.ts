import {
    investigate as investigateRequest,
    listHistory,
    getInvestigation,
} from "./api";

import {
    investigationState,
    setInvestigationError,
} from "../../state/investigation";

import {
    getWorkContextVersion,
} from "../../state/workContext";

import type {
    InvestigateRequest,
} from "./contracts";

export async function investigate(
    request: InvestigateRequest,
): Promise<void> {
    const contextVersion =
        getWorkContextVersion();

    investigationState.isInvestigating = true;
    investigationState.error = null;

    try {
        const result =
            await investigateRequest(request);

        if (
            contextVersion !==
            getWorkContextVersion()
        ) {
            return;
        }

        investigationState.activeInvestigation =
            result.investigation;

        investigationState.response =
            result.response;

        investigationState.evidences =
            result.evidences;

        try {
            await loadHistory();

        } catch (error) {
            if (
                contextVersion !==
                getWorkContextVersion()
            ) {
                return;
            }

            console.error(
                "[HISTORY] Falha ao atualizar histórico:",
                error,
            );
        }

    } catch (error) {
        if (
            contextVersion !==
            getWorkContextVersion()
        ) {
            return;
        }

        setInvestigationError(error);

        throw error;

    } finally {
        if (
            contextVersion ===
            getWorkContextVersion()
        ) {
            investigationState.isInvestigating = false;
        }
    }
}

export async function loadHistory(): Promise<void> {
    const contextVersion =
        getWorkContextVersion();

    try {
        const history =
            await listHistory();

        if (
            contextVersion !==
            getWorkContextVersion()
        ) {
            return;
        }

        investigationState.history =
            history;

    } catch (error) {
        if (
            contextVersion !==
            getWorkContextVersion()
        ) {
            return;
        }

        setInvestigationError(error);

        throw error;
    }
}

export async function loadInvestigation(
    investigationId: string,
): Promise<void> {
    const contextVersion =
        getWorkContextVersion();

    investigationState.isInvestigating = true;
    investigationState.error = null;

    try {
        const result =
            await getInvestigation(
                investigationId,
            );

        if (
            contextVersion !==
            getWorkContextVersion()
        ) {
            return;
        }

        investigationState.activeInvestigation =
            result.investigation;

        investigationState.response =
            result.response;

        investigationState.evidences =
            result.evidences;

    } catch (error) {
        if (
            contextVersion !==
            getWorkContextVersion()
        ) {
            return;
        }

        setInvestigationError(error);

        throw error;

    } finally {
        if (
            contextVersion ===
            getWorkContextVersion()
        ) {
            investigationState.isInvestigating = false;
        }
    }
}