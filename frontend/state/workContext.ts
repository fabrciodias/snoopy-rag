import {
    folderState,
} from "./folders";

import {
    clearHistory,
    clearInvestigation,
} from "./investigation";

import {
    navigationState,
    goHome,
} from "./navigation";

/**
 * Identifica a geração atual do contexto de trabalho.
 *
 * Quando o contexto é invalidado, a geração muda.
 * Operações assíncronas iniciadas em gerações anteriores
 * não devem atualizar o estado global.
 */
let workContextVersion = 0;

export function getWorkContextVersion(): number {
    return workContextVersion;
}

/**
 * Invalida operações assíncronas em andamento e limpa
 * o trabalho associado ao contexto atualmente ativo.
 *
 * Preserva a lista de acervos conectados.
 */
export function invalidateActiveWork(): void {
    workContextVersion += 1;

    clearInvestigation();
    clearHistory();

    navigationState.reading.documentId = null;
    navigationState.reading.evidenceId = null;
    navigationState.reading.location = null;

    goHome();
}

/**
 * Limpa os dados de trabalho e o contexto de acervos
 * mantidos na memória da sessão anterior.
 *
 * Não exclui dados persistidos no backend.
 */
export function clearUserWorkState(): void {
    invalidateActiveWork();

    folderState.folders = [];
    folderState.selectedFolderId = null;

    folderState.isLoading = false;
    folderState.isCreating = false;
    folderState.error = null;
}