<script setup lang="ts">
import {
    onMounted,
    ref,
    watch,
} from "vue";

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
    operationState,
} from "../../state/operations";

import {
    goHome,
} from "../../state/navigation";

const props = defineProps<{
    mobileOpen: boolean;
}>();

const emit = defineEmits<{
    (event: "close-mobile"): void;
    (event: "open-settings"): void;
}>();

const isCollapsed = ref(false);
const isLightTheme = ref(
    document.body.classList.contains("light-theme"),
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

function handleThemeToggle(): void {
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

    window.lucide?.createIcons();
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

    try {
        folderState.error = null;

        const googleToken =
            getGoogleProviderToken();

        if (!googleToken) {
            throw new Error(
                "Não foi encontrado um token de acesso ao Google Drive. Faça login novamente.",
            );
        }

        const result =
            await syncDrive({
                folder_id: folderId,
                google_token: googleToken,
            });
        if (
            result.status !== "COMPLETED"
        ) {
            throw new Error(
                `A sincronização terminou com status ${result.status}.`,
            );
        }

        await loadFolders();

    } catch (error) {
        operationState.error =
            error instanceof Error
                ? error.message
                : String(error);

        console.error(
            "[SYNC] Falha ao sincronizar acervo:",
            error,
        );
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
    if (!operationState.isLoading) {
        return "Sincronizar Acervo";
    }

    return "Sincronizando...";
}

onMounted(async () => {
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

    if (!authState.user) {
        return;
    }

    try {
        await loadFolders();
    } catch {
        // O erro já foi armazenado no estado.
    }
});

watch(
    () => authState.user,
    async (user) => {
        if (!user) {
            return;
        }

        if (folderState.folders.length > 0) {
            return;
        }

        try {
            await loadFolders();
        } catch {
            // O erro já foi armazenado no estado.
        }
    },
);

</script>

<template>
    <aside class="sidebar"
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
                    <i
                        data-lucide="microscope"
                        class="icon-brand logo-default"
                    ></i>

                    <i
                        data-lucide="panel-left-open"
                        class="icon-brand logo-hover hidden"
                    ></i>

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
                    <i data-lucide="panel-left-close"></i>
                </button>
            </div>

            <button
                id="btn-sidebar-new"
                class="btn-primary-full"
            >
                <i
                    data-lucide="plus"
                    class="icon-sm"
                ></i>

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
                                operationState.isLoading ||
                                folderState.isLoading ||
                                folderState.isCreating
                            "
                            @click="handleSyncDrive"
                        >
                            <i
                                data-lucide="refresh-cw"
                                style="
                                    width: 14px;
                                    height: 14px;
                                "
                            ></i>
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
                            {{  folder.name  }}
                        </option>
                    </select>

                    <div
                        v-if="operationState.isLoading"
                        style="
                            font-size: 0.75rem;
                            color: var(--text-muted);
                            margin-top: 6px;
                            text-align: center;
                        "
                    >
                        Sincronizando acervo...
                    </div>

                    <div
                        v-else-if="operationState.error"
                        style="
                            font-size: 0.75rem;
                            color: var(--text-muted);
                            margin-top: 6px;
                            text-align: center;
                        "
                    >
                        {{  operationState.error  }}
                    </div>

                    <button
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
                        <i
                            data-lucide="folder-plus"
                            class="icon-sm"
                        ></i>

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
                        {{  folderState.error  }}
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
                    <i
                        data-lucide="folder"
                        class="icon-sm"
                    ></i>

                    <h3 class="nav-title">
                        Acervos
                    </h3>
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
                <i
                    :data-lucide="
                        isLightTheme
                            ? 'sun'
                            : 'moon'
                    "
                    class="icon-sm"
                ></i>

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
                @click="handleLogin"
            >
                <i
                    data-lucide="log-in"
                    class="icon-sm"
                ></i>

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
                        :src="authState.user?.user_metadata?.avatar_url ?? ''"
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
                    <i
                        data-lucide="settings"
                        style="width: 18px; height: 18px;"
                    ></i>
                </button>
            </div>
        </div>
    </aside>
</template>