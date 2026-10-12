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

import {
    waitForOperation,
} from "../operations/actions";

import type {
    InvestigateRequest,
} from "./contracts";


export async function investigate(
    request: InvestigateRequest,
): Promise<void> {
    const contextVersion =
        getWorkContextVersion();

    const folderId =
        folderState.selectedFolderId;

    const isCurrentContext = () =>
        contextVersion ===
            getWorkContextVersion() &&
        folderId ===
            folderState.selectedFolderId;

    if (
        !folderId ||
        request.folder_id !== folderId
    ) {
        throw new Error(
            "O acervo selecionado mudou. " +
            "Selecione o acervo desejado e tente novamente.",
        );
    }

    investigationState.isInvestigating = true;

    investigationState.error = null;
    investigationState.resultMessage = null;

    investigationState.currentQuery =
        request.query;

    investigationState.activeInvestigation = null;
    investigationState.response = null;
    investigationState.evidences = [];

    investigationState.activeOperationId = null;
    investigationState.activeInvestigationId = null;

    try {
        const started =
            await investigateRequest(request);

        if (!isCurrentContext()) {
            return;
        }

        if (
            !started.operation_id ||
            !started.investigation_id
        ) {
            throw new Error(
                "O backend não retornou os identificadores " +
                "necessários para acompanhar a investigação.",
            );
        }

        investigationState.activeOperationId =
            started.operation_id;

        investigationState.activeInvestigationId =
            started.investigation_id;

        const operation =
            await waitForOperation(
                started.operation_id,
                isCurrentContext,
            );

        if (
            !operation ||
            !isCurrentContext()
        ) {
            return;
        }

        if (
            operation.status !== "COMPLETED"
        ) {
            throw new Error(
                operation.error_log ??
                (
                    operation.status === "CANCELLED"
                        ? "A investigação foi cancelada."
                        : "A investigação não foi concluída com sucesso."
                ),
            );
        }

        const result =
            await getInvestigation(
                started.investigation_id,
            );

        if (!isCurrentContext()) {
            return;
        }

        if (
            result.investigation.investigation_id !==
            started.investigation_id
        ) {
            throw new Error(
                "O backend retornou uma investigação diferente " +
                "daquela que estava sendo acompanhada.",
            );
        }

        if (
            result.investigation.folder_id !==
            folderId
        ) {
            throw new Error(
                "A investigação retornada não corresponde " +
                "ao acervo selecionado.",
            );
        }

        investigationState.activeInvestigation =
            result.investigation;

        investigationState.response =
            result.response;

        investigationState.evidences =
            result.evidences;

        investigationState.activeInvestigationId =
            result.investigation.investigation_id;

        investigationState.currentQuery =
            result.investigation.original_query;

        investigationState.resultMessage =
            result.response
                ? null
                : (
                    result.message ??
                    "Nenhuma evidência foi encontrada " +
                    "no acervo para esta consulta."
                );

        try {
            await loadHistory(folderId);
        } catch (error) {
            if (!isCurrentContext()) {
                return;
            }

            console.error(
                "[HISTORY] Falha ao atualizar histórico:",
                error,
            );
        }

    } catch (error) {
        if (!isCurrentContext()) {
            return;
        }

        setInvestigationError(error);

        throw error;

    } finally {
        if (isCurrentContext()) {
            investigationState.isInvestigating = false;
        }
    }
}


export async function loadHistory(
    folderId: string | null =
        folderState.selectedFolderId,
): Promise<void> {
    const contextVersion =
        getWorkContextVersion();

    if (
        !folderId ||
        folderId !==
            folderState.selectedFolderId
    ) {
        investigationState.history = [];
        return;
    }

    try {
        const history =
            await listHistory(folderId);

        if (
            contextVersion !==
                getWorkContextVersion() ||
            folderId !==
                folderState.selectedFolderId
        ) {
            return;
        }

        investigationState.history = history;

    } catch (error) {
        if (
            contextVersion !==
                getWorkContextVersion() ||
            folderId !==
                folderState.selectedFolderId
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

    const folderId =
        folderState.selectedFolderId;

    const isCurrentContext = () =>
        contextVersion ===
            getWorkContextVersion() &&
        folderId ===
            folderState.selectedFolderId;

    if (!folderId) {
        throw new Error(
            "Selecione um acervo antes de restaurar uma investigação.",
        );
    }

    investigationState.isInvestigating = true;

    investigationState.error = null;
    investigationState.resultMessage = null;

    investigationState.activeOperationId = null;
    investigationState.activeInvestigationId =
        investigationId;

    try {
        const result =
            await getInvestigation(
                investigationId,
            );

        if (!isCurrentContext()) {
            return;
        }

        if (
            result.investigation.investigation_id !==
            investigationId
        ) {
            throw new Error(
                "A investigação retornada não corresponde " +
                "ao identificador solicitado.",
            );
        }

        if (
            result.investigation.folder_id !==
            folderId
        ) {
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

        investigationState.currentQuery =
            result.investigation.original_query;

        investigationState.resultMessage =
            result.response
                ? null
                : "Esta investigação não possui uma síntese disponível.";

    } catch (error) {
        if (!isCurrentContext()) {
            return;
        }

        setInvestigationError(error);

        throw error;

    } finally {
        if (isCurrentContext()) {
            investigationState.isInvestigating = false;
        }
    }
}