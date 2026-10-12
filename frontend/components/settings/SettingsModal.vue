<script setup lang="ts">
import {
    ref,
    computed,
} from "vue";

import {
    Settings,
    X,
    Trash2,
    UploadCloud,
    LogOut,
} from "@lucide/vue";

import {
    authState,
} from "../../state/authentication";

import {
    folderState,
} from "../../state/folders";

import {
    removeFolder,
} from "../../features/folders/actions";

import {
    logout,
} from "../../infrastructure/supabase-auth";

defineProps<{
    open: boolean;
}>();

const emit = defineEmits<{
    (event: "close"): void;
}>();

const disconnectStep = ref<0 | 1 | 2>(0);
const isDisconnecting = ref(false);
const disconnectError = ref<string | null>(null);

const privateFolder = computed(
    () =>
        authState.user
            ? folderState.folders.find(
                  (folder) =>
                      folder.user_id ===
                      authState.user?.id,
              ) ?? null
            : null,
);

async function handleLogout(): Promise<void> {
    try {
        await logout();
        emit("close");
    } catch (error) {
        console.error(
            "[AUTH] Falha no logout:",
            error,
        );
    }
}

function handleRemoveFolderRequest(): void {
    disconnectError.value = null;
    disconnectStep.value = 1;
}

function handleCancelDisconnect(): void {
    disconnectStep.value = 0;
    disconnectError.value = null;
}

function handleContinueDisconnect(): void {
    disconnectError.value = null;
    disconnectStep.value = 2;
}

async function handleConfirmDisconnect(): Promise<void> {
    if (!privateFolder.value) {
        return;
    }

    isDisconnecting.value = true;
    disconnectError.value = null;

    try {
        await removeFolder(privateFolder.value.id);

        disconnectStep.value = 0;
        emit("close");
    } catch (error) {
        console.error(
            "[FOLDERS] Falha ao desconectar acervo:",
            error,
        );

        disconnectError.value =
            "Não foi possível desconectar o acervo. Tente novamente.";
    } finally {
        isDisconnecting.value = false;
    }
}

function handleClose(): void {
    disconnectStep.value = 0;
    disconnectError.value = null;
    emit("close");
}
</script>

<template>
    <div
        id="settings-modal"
        class="modal-overlay"
        :class="{
            active: open,
        }"
        @click.self="handleClose"
    >
        <div class="modal-content">
            <div class="modal-header">
                <h3
                    style="
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    "
                >
                    <Settings class="icon-sm" />

                    Configurações
                </h3>

                <button
                    id="btn-close-modal"
                    class="btn-icon"
                    title="Fechar"
                    type="button"
                    @click="handleClose"
                >
                    <X />
                </button>
            </div>

            <div class="modal-body">
                <div class="setting-group">
                    <h4>
                        Gerenciamento de Acervo
                    </h4>

                    <p class="setting-desc">
                        Gerencie a conexão com seu Google Drive.
                    </p>

                    <button
                        v-if="privateFolder && disconnectStep === 0"
                        id="btn-remove-folder"
                        class="btn-danger w-full"
                        type="button"
                        @click="handleRemoveFolderRequest"
                    >
                        <Trash2 class="icon-sm" />

                        Desconectar Acervo Privado
                    </button>

                    <div
                        v-if="disconnectStep === 1"
                        class="disconnect-warning"
                    >
                        <strong class="disconnect-warning-title">
                            Desconectar acervo privado?
                        </strong>

                        <p class="disconnect-warning-text">
                            Isso vai desvincular seu acervo privado do Google Drive.
                        </p>

                        <div class="disconnect-warning-actions">
                            <button
                                class="btn-outline"
                                style="flex: 1;"
                                type="button"
                                @click="handleCancelDisconnect"
                            >
                                Cancelar
                            </button>

                            <button
                                class="btn-danger"
                                style="flex: 1;"
                                type="button"
                                @click="handleContinueDisconnect"
                            >
                                Continuar
                            </button>
                        </div>
                    </div>

                    <div
                        v-if="disconnectStep === 2"
                        class="disconnect-warning disconnect-warning-final"
                    >
                        <strong class="disconnect-warning-title">
                            Confirme a desconexão
                        </strong>

                        <p class="disconnect-warning-text">
                            Este acervo não aparecerá mais nas suas buscas.
                            Os dados já processados continuarão salvos na nuvem.
                        </p>

                        <div class="disconnect-warning-actions">
                            <button
                                class="btn-outline"
                                style="flex: 1;"
                                type="button"
                                :disabled="isDisconnecting"
                                @click="disconnectStep = 1"
                            >
                                Voltar
                            </button>

                            <button
                                class="btn-danger"
                                style="flex: 1;"
                                type="button"
                                :disabled="isDisconnecting"
                                @click="handleConfirmDisconnect"
                            >
                                {{ 
                                    isDisconnecting
                                        ? "Desconectando..."
                                        : "Desconectar"
                                }}
                            </button>
                        </div>

                        <p
                            v-if="disconnectError"
                            style="
                                margin: 10px 0 0;
                                font-size: 0.8rem;
                                color: var(--text-muted);
                            "
                        >
                            {{ disconnectError }}
                        </p>
                    </div>

                    <button
                        class="btn-outline w-full"
                        disabled
                        title="Em breve"
                        style="
                            margin-top: 10px;
                            opacity: 0.5;
                            cursor: not-allowed;
                        "
                    >
                        <UploadCloud class="icon-sm" />

                        Upload Manual (Em breve)
                    </button>
                </div>

                <div
                    class="setting-group"
                    style="
                        margin-top: 24px;
                        border-top: 1px solid var(--border-color);
                        padding-top: 20px;
                    "
                >
                    <h4>
                        Sessão
                    </h4>

                    <button
                        id="btn-logout"
                        class="btn-outline w-full"
                        style="color: var(--text-main);"
                        @click="handleLogout"
                    >
                        <LogOut class="icon-sm" />
                        Sair da Conta
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>