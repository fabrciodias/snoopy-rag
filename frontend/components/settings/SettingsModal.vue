<script setup lang="ts">
import {
    Settings,
    X,
    Trash2,
    UploadCloud,
    LogOut,
} from "@lucide/vue";

import {
    logout,
} from "../../infrastructure/supabase-auth";

defineProps<{
    open: boolean;
}>();

const emit = defineEmits<{
    (event: "close"): void;
}>();

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

function handleClose(): void {
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
                        id="btn-remove-folder"
                        class="btn-danger w-full hidden"
                    >
                        <Trash2 class="icon-sm" />

                        Desconectar Acervo Privado
                    </button>

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