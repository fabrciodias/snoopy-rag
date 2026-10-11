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
    folderState,
} from "../../state/folders";

import {
    getWorkContextVersion,
} from "../../state/workContext";

import type {
    InvestigateRequest,
} from "./contracts";

export async function investigate(
    request: InvestigateRequest,
): Promise<void> {
    const contextVersion = getWorkContextVersion();
    const folderId = folderState.selectedFolderId;

    if (!folderId || request.folder_id !== folderId) {
        throw new Error(
            "O acervo selecionado mudou. Selecione o acervo desejado e tente novamente.",
        );
    }

    investigationState.isInvestigating = true;
    investigationState.error = null;

    try {
        const result = await investigateRequest(request);

        if (
            contextVersion !== getWorkContextVersion() ||
            folderId !== folderState.selectedFolderId
        ) {
            return;
        }

        if (result.investigation.folder_id !== folderId) {
            throw new Error(
                "A investigação retornada não corresponde ao acervo selecionado.",
            );
        }

        investigationState.activeInvestigation =
            result.investigation;

        investigationState.response =
            result.response;

        investigationState.evidences =
            result.evidences;

        try {
            await loadHistory(folderId);
        } catch (error) {
            if (
                contextVersion !== getWorkContextVersion() ||
                folderId !== folderState.selectedFolderId
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
            contextVersion !== getWorkContextVersion() ||
            folderId !== folderState.selectedFolderId
        ) {
            return;
        }

        setInvestigationError(error);
        throw error;
    } finally {
        if (
            contextVersion === getWorkContextVersion() &&
            folderId === folderState.selectedFolderId
        ) {
            investigationState.isInvestigating = false;
        }
    }
}

export async function loadHistory(
    folderId: string | null = folderState.selectedFolderId,
): Promise<void> {
    const contextVersion = getWorkContextVersion();

    if (
        !folderId ||
        folderId !== folderState.selectedFolderId
    ) {
        investigationState.history = [];
        return;
    }

    try {
        const history = await listHistory(folderId);

        if (
            contextVersion !== getWorkContextVersion() ||
            folderId !== folderState.selectedFolderId
        ) {
            return;
        }

        investigationState.history = history;
    } catch (error) {
        if (
            contextVersion !== getWorkContextVersion() ||
            folderId !== folderState.selectedFolderId
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
    const contextVersion = getWorkContextVersion();
    const folderId = folderState.selectedFolderId;

    if (!folderId) {
        throw new Error(
            "Selecione um acervo antes de restaurar uma investigação.",
        );
    }

    investigationState.isInvestigating = true;
    investigationState.error = null;

    try {
        const result = await getInvestigation(investigationId);

        if (
            contextVersion !== getWorkContextVersion() ||
            folderId !== folderState.selectedFolderId
        ) {
            return;
        }

        if (result.investigation.folder_id !== folderId) {
            throw new Error(
                "A investigação não pertence ao acervo selecionado.",
            );
        }

        investigationState.activeInvestigation =
            result.investigation;

        investigationState.response =
            result.response;

        investigationState.evidences =
            result.evidences;
    } catch (error) {
        if (
            contextVersion !== getWorkContextVersion() ||
            folderId !== folderState.selectedFolderId
        ) {
            return;
        }

        setInvestigationError(error);
        throw error;
    } finally {
        if (
            contextVersion === getWorkContextVersion() &&
            folderId === folderState.selectedFolderId
        ) {
            investigationState.isInvestigating = false;
        }
    }
}