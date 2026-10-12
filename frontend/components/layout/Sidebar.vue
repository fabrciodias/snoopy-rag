<script setup lang="ts">
import {
    computed,
    onMounted,
    onUnmounted,
    ref,
    watch,
} from "vue";

import {
    Settings,
    Sun,
    Moon,
    Microscope,
    PanelLeftOpen,
    PanelLeftClose,
    Plus,
    RefreshCw,
    FolderPlus,
    Folder,
    History,
    LogIn,
} from "@lucide/vue";

import {
    getGoogleProviderToken,
    login,
    logout,
} from "../../infrastructure/supabase-auth";

import {
    pickDriveFolder,
} from "../../infrastructure/google-picker";

import {
    authState,
} from "../../state/authentication";

import {
    folderState,
} from "../../state/folders";

import {
    addFolder,
    loadFolders,
    selectFolder,
} from "../../features/folders/actions";

import {
    syncDrive,
} from "../../features/synchronization/actions";

import {
    loadActiveFolderSync,
    waitForOperation,
} from "../../features/operations/actions";

import {
    operationState,
} from "../../state/operations";

import {
    loadHistory,
    loadInvestigation,
} from "../../features/investigation/actions";

import {
    investigationState,
    clearHistory,
} from "../../state/investigation";

import {
    goHome,
    goToInvestigation,
} from "../../state/navigation";

const props = defineProps<{
    mobileOpen: boolean;
}>();

const emit = defineEmits<{
    (event: "close-mobile"): void;
    (event: "open-settings"): void;
}>();

const isCollapsed = ref(false);

const isSyncing = ref(false);

let syncAttemptVersion = 0;

const isLightTheme = ref(
    document.body.classList.contains("light-theme"),
);

const hasPrivateFolder = computed(
    () =>
        !!authState.user &&
        folderState.folders.some(
            (folder) =>
                folder.user_id ===
                authState.user?.id,
        ),
);

const latestFolderSyncOperation = computed(() => {
    const folderId =
        folderState.selectedFolderId;

    if (!folderId) {
        return null;
    }

    const matchingOperations =
        operationState.operations.filter(
            (operation) =>
                operation.operation_type === "DRIVE_SYNC" &&
                operation.target_type === "FOLDER" &&
                operation.target_id === folderId,
        );

    return (
        matchingOperations[
            matchingOperations.length - 1
        ] ?? null
    );
});


const activeFolderSyncOperation = computed(() => {
    const folderId =
        folderState.selectedFolderId;

    if (!folderId) {
        return null;
    }

    return (
        [...operationState.operations]
            .reverse()
            .find(
                (operation) =>
                    operation.operation_type === "DRIVE_SYNC" &&
                    operation.target_type === "FOLDER" &&
                    operation.target_id === folderId &&
                    (
                        operation.status === "PENDING" ||
                        operation.status === "PROCESSING"
                    ),
            ) ?? null
    );
});


const syncProgress = computed(() => {
    if (isSyncing.value) {
        return (
            activeFolderSyncOperation.value?.progress ??
            null
        );
    }

    return (
        latestFolderSyncOperation.value?.progress ??
        null
    );
});


const showSyncFileProgress = computed(() => {
    const progress = syncProgress.value;

    return (
        progress?.unit === "files" &&
        progress.total != null &&
        progress.total > 0
    );
});


const syncProgressPercent = computed(() => {
    const progress = syncProgress.value;

    if (
        !progress ||
        progress.total == null ||
        progress.total <= 0
    ) {
        return 0;
    }

    const current =
        progress.current ?? 0;

    return Math.max(
        0,
        Math.min(
            100,
            Math.round(
                (current / progress.total) * 100,
            ),
        ),
    );
});


const currentFolderSyncOperation = computed(
    () =>
        activeFolderSyncOperation.value ??
        latestFolderSyncOperation.value,
);

// ============================================================
// Exibição temporária da mensagem de conclusão
// ============================================================

const syncCompletionVisible = ref(false);

let syncCompletionTimeout: ReturnType<
    typeof setTimeout
> | null = null;


function clearSyncCompletionTimeout(): void {
    if (syncCompletionTimeout !== null) {
        clearTimeout(syncCompletionTimeout);
        syncCompletionTimeout = null;
    }
}

watch(
    [
        () =>
            currentFolderSyncOperation.value?.operation_id ??
            null,

        () =>
            currentFolderSyncOperation.value?.status ??
            null,

        () => isSyncing.value,
    ],

    ([
        operationId,
        status,
        currentlySyncing,
    ], [
        previousOperationId,
        previousStatus,
        wasSyncing,
    ]) => {
        const justCompleted =
            operationId !== null &&
            status === "COMPLETED" &&
            !currentlySyncing &&
            (
                (
                    operationId === previousOperationId &&
                    (
                        previousStatus === "PROCESSING" ||
                        previousStatus === "PENDING"
                    )
                ) ||
                wasSyncing
            );

        if (justCompleted) {
            clearSyncCompletionTimeout();

            syncCompletionVisible.value = true;

            syncCompletionTimeout = setTimeout(
                () => {
                    syncCompletionVisible.value = false;
                    syncCompletionTimeout = null;
                },
                6000,
            );

            return;
        }

        /*
         * Uma troca de operação, uma nova sincronização
         * ou qualquer estado que não seja conclusão
         * invalida a mensagem temporária anterior.
         */
        if (
            operationId !== previousOperationId ||
            status !== "COMPLETED" ||
            currentlySyncing
        ) {
            clearSyncCompletionTimeout();
            syncCompletionVisible.value = false;
        }
    },
);

onUnmounted(() => {
    clearSyncCompletionTimeout();
});

watch(
    () => [
        authState.user?.id ?? null,
        folderState.selectedFolderId,
    ] as const,
    () => {
        syncAttemptVersion += 1;

        isSyncing.value = false;

        operationState.error = null;
    },
    {
        flush: "sync",
    },
);

function handleSidebarToggle(): void {
    if (window.innerWidth <= 850) {
        emit("close-mobile");
        return;
    }

    isCollapsed.value =
        !isCollapsed.value;
}

function handleLogoClick(): void {
    if (isCollapsed.value) {
        isCollapsed.value = false;
        return;
    }

    handleNewInvestigation();
}

async function handleThemeToggle(): Promise<void> {
    isLightTheme.value =
        !isLightTheme.value;

    document.body.classList.toggle(
        "light-theme",
        isLightTheme.value,
    );

    localStorage.setItem(
        "snoopy_theme",
        isLightTheme.value
            ? "light"
            : "dark",
    );

}

function handleOpenSettings(): void {
    emit("open-settings");
}

function focusFolderSelector(): void {
    if (!isCollapsed.value) {
        return;
    }

    isCollapsed.value = false;

    requestAnimationFrame(() => {
        document
            .getElementById("folder-selector")
            ?.focus();
    });
}

async function handleHistoryClick(
    investigationId: string | null,
): Promise<void> {
    if (!investigationId) {
        return;
    }

    try {
        await loadInvestigation(
            investigationId,
        );

        goToInvestigation();
        emit("close-mobile");
    } catch (error) {
        console.error(
            "[HISTORY] Falha ao restaurar investigação:",
            error,
        );
    }
}

function handleNewInvestigation(): void {
    goHome();
}

async function handleLogin(): Promise<void> {
    try {
        await login();
    } catch (error) {
        console.error(
            "[AUTH] Falha no login:",
            error,
        );
    }
}

async function handleLogout(): Promise<void> {
    try {
        await logout();
    } catch (error) {
        console.error(
            "[AUTH] Falha no logout:",
            error,
        );
    }
}

async function handleConnectDrive():
    Promise<void> {
    try {
        folderState.error = null;

        const folder =
            await pickDriveFolder();

        if (!folder) {
            return;
        }

        await addFolder({
            name: folder.name,
            drive_id: folder.id,
        });
    } catch (error) {
        folderState.error =
            error instanceof Error
                ? error.message
                : String(error);

        console.error(
            "[FOLDERS] Falha ao conectar acervo:",
            error,
        );
    }
}

async function handleSyncDrive():
    Promise<void> {
    const folderId =
        folderState.selectedFolderId;

    if (!folderId) {
        folderState.error =
            "Selecione um acervo antes de sincronizar.";

        return;
    }

    if (isSyncing.value) {
        return;
    }

    const attemptVersion =
        ++syncAttemptVersion;

    const userId =
        authState.user?.id ?? null;

    const isCurrentAttempt = () =>
        attemptVersion ===
            syncAttemptVersion &&
        (authState.user?.id ?? null) ===
            userId &&
        folderState.selectedFolderId ===
            folderId;

    isSyncing.value = true;

    try {
        folderState.error = null;

        operationState.error = null;

        const googleToken =
            getGoogleProviderToken();

        if (!googleToken) {
            throw new Error(
                "Não foi encontrado um token de acesso ao " +
                "Google Drive. Faça login novamente.",
            );
        }

        const result =
            await syncDrive(
                {
                    folder_id: folderId,
                    google_token: googleToken,
                },
                isCurrentAttempt,
            );

        if (
            !isCurrentAttempt() ||
            !result
        ) {
            return;
        }

        if (
            result.status !== "COMPLETED"
        ) {
            throw new Error(
                `A sincronização terminou com status ${result.status}.`,
            );
        }
    } catch (error) {
        if (!isCurrentAttempt()) {
            return;
        }

        operationState.error =
            error instanceof Error
                ? error.message
                : String(error);

        console.error(
            "[SYNC] Falha ao sincronizar acervo:",
            error,
        );
    } finally {
        if (isCurrentAttempt()) {
            isSyncing.value = false;
        }
    }
}

function handleFolderChange(
    event: Event,
): void {
    const target =
        event.target as HTMLSelectElement;

    selectFolder(
        target.value,
    );
}

function getSyncLabel(): string {
    if (!isSyncing.value) {
        return "Sincronizar Acervo";
    }

    return "Sincronizando...";
}

onMounted(() => {
    const savedTheme =
        localStorage.getItem(
            "snoopy_theme",
        );

    if (savedTheme === "light") {
        isLightTheme.value = true;

        document.body.classList.add(
            "light-theme",
        );
    } else if (savedTheme === "dark") {
        isLightTheme.value = false;

        document.body.classList.remove(
            "light-theme",
        );
    }
});


// ============================================================
// Carregamento dos acervos por identidade autenticada
// ============================================================

watch(
    () => authState.user?.id ?? null,
    async (userId) => {
        if (!userId) {
            clearHistory();
            return;
        }

        // A lista já foi carregada para esta sessão.
        if (folderState.folders.length > 0) {
            return;
        }

        try {
            await loadFolders();
        } catch {
            // O erro já foi armazenado no estado.
        }
    },
    {
        immediate: true,
    },
);

// ============================================================
// Recuperação do acompanhamento de sincronização
// ============================================================

watch(
    () => [
        authState.user?.id ?? null,
        folderState.selectedFolderId,
    ] as const,

    async ([userId, folderId]) => {
        // Cada mudança de contexto invalida tentativas anteriores.
        const attemptVersion =
            ++syncAttemptVersion;

        if (!userId || !folderId) {
            return;
        }

        const isCurrentAttempt = () =>
            attemptVersion ===
                syncAttemptVersion &&
            (authState.user?.id ?? null) ===
                userId &&
            folderState.selectedFolderId ===
                folderId;

        try {
            // Consulta a API para descobrir se o acervo
            // já possui uma sincronização em andamento.
            const activeOperation =
                await loadActiveFolderSync(
                    folderId,
                    isCurrentAttempt,
                );

            if (
                !activeOperation ||
                !isCurrentAttempt()
            ) {
                return;
            }

            const operationId =
                activeOperation.operation_id;

            if (!operationId) {
                throw new Error(
                    "A operação de sincronização não possui " +
                    "um identificador válido.",
                );
            }

            // A partir daqui, a interface retoma o acompanhamento.
            isSyncing.value = true;

            const completedOperation =
                await waitForOperation(
                    operationId,
                    isCurrentAttempt,
                );

            if (
                !completedOperation ||
                !isCurrentAttempt()
            ) {
                return;
            }

            if (
                completedOperation.status !==
                "COMPLETED"
            ) {
                operationState.error =
                    `A sincronização terminou com status ` +
                    `${completedOperation.status}.`;
            }
        } catch (error) {
            if (!isCurrentAttempt()) {
                return;
            }

            operationState.error =
                error instanceof Error
                    ? error.message
                    : String(error);

            console.error(
                "[SYNC] Falha ao recuperar o acompanhamento:",
                error,
            );
        } finally {
            if (isCurrentAttempt()) {
                isSyncing.value = false;
            }
        }
    },

    {
        immediate: true,
    },
);


// ============================================================
// Carregamento do histórico por acervo ativo
// ============================================================

watch(
    () => [
        authState.user?.id ?? null,
        folderState.selectedFolderId,
    ] as const,
    async ([userId, folderId]) => {
        if (!userId || !folderId) {
            clearHistory();
            return;
        }

        try {
            await loadHistory(folderId);
        } catch {
            // O erro já foi armazenado no estado.
        }
    },
    {
        immediate: true,
    },
);

</script>

<template>
    <aside
        class="sidebar"
        :class="{
            collapsed: isCollapsed,
            'mobile-open': props.mobileOpen,
        }"
    >
        <div class="sidebar-top">
            <div class="sidebar-header">
                <div
                    id="logo-btn"
                    class="logo-area"
                    title="Página Inicial"
                    type="button"
                    @click="handleLogoClick"
                >
                    <Microscope
                        class="icon-brand logo-default"
                    />

                    <PanelLeftOpen
                        class="icon-brand logo-hover hidden"
                    />

                    <h2 class="logo-small">
                        LPP-Acervo
                    </h2>
                </div>

                <button
                    id="btn-sidebar-toggle"
                    class="btn-icon"
                    title="Recolher menu"
                    type="button"
                    @click="handleSidebarToggle"
                >
                    <PanelLeftClose />
                </button>
            </div>

            <button
                id="btn-sidebar-new"
                class="btn-primary-full"
                type="button"
                @click="handleNewInvestigation"
            >
                <Plus class="icon-sm" />

                <span>Nova Pesquisa</span>
            </button>
        </div>

        <div class="sidebar-middle">
            <div
                v-if="authState.user"
                id="auth-section"
                class="auth-box"
            >
                <div
                    id="folder-container"
                    class="folder-box"
                    style="
                        display: flex;
                        flex-direction: column;
                    "
                >
                    <div
                        style="
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            margin-bottom: 6px;
                        "
                    >
                        <span
                            class="folder-label"
                            style="
                                margin-bottom: 0;
                                line-height: 1;
                            "
                        >
                            Acervo Atual
                        </span>

                        <button
                            id="btn-sync"
                            class="btn-icon"
                            title="Sincronizar Acervo"
                            style="
                                padding: 2px;
                                transform: translateY(3px);
                            "
                            type="button"
                            :disabled="
                                isSyncing ||
                                folderState.isLoading ||
                                folderState.isCreating
                            "
                            @click="handleSyncDrive"
                        >
                            <RefreshCw
                                style="
                                    width: 14px;
                                    height: 14px;
                                "
                            />
                        </button>
                    </div>

                    <select
                        id="folder-selector"
                        class="folder-dropdown"
                        :value="
                            folderState.selectedFolderId ??
                            undefined
                        "
                        :disabled="
                            folderState.isLoading ||
                            folderState.isCreating
                        "
                        @change="handleFolderChange"
                    >
                        <option
                            v-if="folderState.isLoading"
                            disabled
                            value=""
                        >
                            Carregando acervos...
                        </option>

                        <option
                            v-for="folder in folderState.folders"
                            :key="folder.id"
                            :value="folder.id"
                        >
                            {{ folder.name }}
                        </option>
                    </select>

                    <div
                        v-if="isSyncing"
                        class="sync-progress-summary"
                        role="status"
                        aria-live="polite"
                    >
                        <p class="sync-progress-message">
                            {{ 
                                syncProgress?.message ??
                                "Preparando sincronização..."    
                            }}
                        </p>

                        <template
                            v-if="showSyncFileProgress"
                        >
                            <div class="sync-progress-meta">
                                <span>
                                    {{  syncProgress?.current ?? 0  }}
                                    de
                                    {{  syncProgress?.total  }}
                                    arquivos concluídos
                                </span>
                            </div>

                            <div
                                class="sync-progress-track"
                                role="progressbar"
                                aria-label="Progresso da sincronização de arquivos"
                                :aria-valuemin="0"
                                :aria-valuemax="syncProgress?.total ?? 0"
                                :aria-valuenow="syncProgress?.current ?? 0"
                            >
                                <div
                                    class="sync-progress-fill"
                                    :style="{
                                        width: `${syncProgressPercent}%`,
                                    }"
                                ></div>
                            </div>

                            <p class="sync-progress-counts">
                                {{  syncProgress?.processed ?? 0  }} processados
                                ·
                                {{  syncProgress?.skipped ?? 0  }} ignorados
                                ·
                                {{  syncProgress?.failed ?? 0  }} falharam
                            </p>
                        </template>
                    </div>

                    <div
                        v-else-if="
                            currentFolderSyncOperation?.status === 'FAILED' ||
                            currentFolderSyncOperation?.status === 'CANCELLED'
                        "
                        class="sync-progress-terminal-error"
                    >
                        {{ 
                            currentFolderSyncOperation.progress?.message ??
                            "A sincronização não foi concluída."
                        }}
                    </div>

                    <div
                        v-else-if="operationState.error"
                        class="sync-progress-terminal-error"
                    >
                        {{ operationState.error }}
                    </div>

                    <div
                        v-else-if="
                            currentFolderSyncOperation?.status === 'COMPLETED'
                        "
                        class="sync-progress-complete"
                    >
                        {{ 
                            currentFolderSyncOperation.progress?.message ??
                            "Acervo sincronizado."
                        }}
                    </div>

                    <button
                        v-if="!hasPrivateFolder"
                        id="btn-drive"
                        class="btn-outline w-full"
                        style="
                            margin-top: 10px;
                            font-size: 0.8rem;
                            padding: 6px;
                            justify-content: center;
                        "
                        type="button"
                        :disabled="
                            folderState.isCreating
                        "
                        @click="handleConnectDrive"
                    >
                        <FolderPlus class="icon-sm" />

                        {{
                            folderState.isCreating
                                ? "Conectando..."
                                : "Conectar Pasta Privada"
                        }}
                    </button>

                    <div
                        v-if="folderState.error"
                        style="
                            font-size: 0.75rem;
                            color: var(--text-muted);
                            margin-top: 6px;
                            text-align: center;
                        "
                    >
                        {{ folderState.error }}
                    </div>
                </div>
            </div>

            <nav class="sidebar-nav">
                <div
                    id="btn-nav-folder"
                    class="nav-title-box"
                    title="Gerenciar Acervos"
                    @click="focusFolderSelector"
                >
                    <Folder class="icon-sm" />

                    <h3 class="nav-title">
                        Acervos
                    </h3>
                </div>

                <div
                    v-if="authState.user"
                    id="btn-nav-history"
                    class="nav-title-box"
                    title="Histórico Recente"
                >
                    <History class="icon-sm" />

                    <h3 class="nav-title">
                        Histórico Recente
                    </h3>
                </div>

                <div
                    v-if="authState.user"
                    id="history-list"
                >
                    <p
                        v-if="
                            investigationState.history.length === 0
                        "
                        class="history-empty"
                    >
                        Nenhuma pesquisa recente.
                    </p>

                    <button
                        v-for="entry in investigationState.history"
                        :key="
                            entry.investigation_id ??
                            `${entry.query}-${entry.created_at}`
                        "
                        class="history-item"
                        :class="{
                            'history-item-disabled':
                                !entry.investigation_id,
                        }"
                        type="button"
                        :disabled="!entry.investigation_id"
                        :title="
                            entry.investigation_id
                                ? 'Restaurar investigação'
                                : 'Esta pesquisa não possui investigação persistida'
                        "
                        @click="
                            handleHistoryClick(
                                entry.investigation_id,
                            )
                        "
                    >
                        <History class="icon-sm" />

                        <span>
                            {{  entry.query  }}
                        </span>
                    </button>
                </div>
            </nav>
        </div>

        <div class="sidebar-bottom">
            <button
                id="btn-theme-toggle"
                class="btn-icon"
                style="
                    margin-bottom: 8px;
                    width: 100%;
                    justify-content: flex-start;
                "
                title="Alternar Tema"
                type="button"
                @click="handleThemeToggle"
            >
                <Sun
                    v-if="isLightTheme"
                    class="icon-sm theme-icon theme-icon-light"
                />

                <Moon  
                    v-else
                    class="icon-sm theme-icon theme-icon-dark"
                />

                <span
                    class="nav-title"
                    style="font-size: 0.85rem;"
                >
                    Tema
                </span>
            </button>

            <button
                id="btn-login"
                class="btn-primary-full"
                :class="{ hidden: authState.user }"
                style="
                    padding: 10px 12px;
                    margin-top: 4px;
                    min-height: 44px;
                "
                type="button"
                @click="handleLogin"
            >
                <LogIn class="icon-sm" />

                <span
                    style="
                        font-size: 0.85rem;
                        font-weight: 500;
                    "
                >
                    Entrar
                </span>
            </button>

            <div
                id="user-info"
                class="user-profile"
                :class="{ hidden: !authState.user }"
                style="
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    background-color: var(--bg-app);
                    padding: 8px 12px;
                    border-radius: var(--radius-md);
                    border: 1px solid var(--border-color);
                "
            >
                <div
                    style="
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        overflow: hidden;
                    "
                >
                    <img
                        id="user-avatar"
                        :src="
                            authState.user?.user_metadata?.avatar_url ??
                            ''
                        "
                        alt="Avatar"
                        class="avatar-img"
                    >

                    <span
                        class="user-name"
                        style="
                            font-size: 0.85rem;
                            font-weight: 500;
                            white-space: nowrap;
                            overflow: hidden;
                            text-overflow: ellipsis;
                        "
                    >
                        {{ authState.user?.email ?? "Usuário" }}
                    </span>
                </div>

                <button
                    id="btn-settings"
                    class="btn-icon"
                    title="Configurações"
                    type="button"
                    @click="handleOpenSettings"
                >
                    <Settings
                        style="
                            width: 18px;
                            height: 18px;
                        "
                    />
                </button>
            </div>
        </div>
    </aside>
</template>