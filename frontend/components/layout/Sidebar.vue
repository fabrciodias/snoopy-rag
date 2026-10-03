<script setup lang="ts">
import {
    login,
    logout,
} from "../../infrastructure/supabase-auth";

import {
    authState,
} from "../../state/authentication";

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
</script>

<template>
    <aside class="sidebar">
        <div class="sidebar-top">
            <div class="sidebar-header">
                <div
                    id="logo-btn"
                    class="logo-area"
                    title="Página Inicial"
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
                id="auth-section"
                class="auth-box"
            >
                <div
                    id="folder-container"
                    class="folder-box hidden"
                    style="display: flex; flex-direction: column;"
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
                            style="margin-bottom: 0; line-height: 1;"
                        >
                            Acervo Atual
                        </span>

                        <button
                            id="btn-sync"
                            class="btn-icon hidden"
                            title="Sincronizar Acervo"
                            style="
                                padding: 2px;
                                transform: translateY(3px);
                            "
                        >
                            <i
                                data-lucide="refresh-cw"
                                style="width: 14px; height: 14px;"
                            ></i>
                        </button>
                    </div>

                    <select
                        id="folder-selector"
                        class="folder-dropdown"
                    >
                        <option value="f7faf7d9-ec80-46c6-9572-174865bf1e62">
                            GEPAFOR (Público)
                        </option>
                    </select>

                    <button
                        id="btn-drive"
                        class="btn-outline w-full hidden"
                        style="
                            margin-top: 10px;
                            font-size: 0.8rem;
                            padding: 6px;
                            justify-content: center;
                        "
                    >
                        <i
                            data-lucide="folder-plus"
                            class="icon-sm"
                        ></i>

                        Conectar Pasta Privada
                    </button>

                    <div
                        id="sync-logs"
                        style="
                            font-size: 0.75rem;
                            color: var(--primary);
                            margin-top: 6px;
                            text-align: center;
                            min-height: 14px;
                        "
                    ></div>

                    <div
                        id="sync-progress-container"
                        class="sync-accordion hidden"
                    >
                        <div
                            id="btn-toggle-sync"
                            class="sync-accordion-header"
                        >
                            <span
                                id="sync-global-status"
                                class="sync-status-text"
                            >
                                Processando arquivos...
                            </span>

                            <i
                                data-lucide="chevron-down"
                                class="sync-chevron icon-sm"
                            ></i>
                        </div>

                        <div
                            id="sync-jobs-list"
                            class="sync-accordion-body"
                        ></div>
                    </div>
                </div>
            </div>

            <nav class="sidebar-nav">
                <div
                    id="btn-nav-folder"
                    class="nav-title-box"
                    title="Gerenciar Acervos"
                >
                    <i
                        data-lucide="folder"
                        class="icon-sm"
                    ></i>

                    <h3 class="nav-title">
                        Acervos
                    </h3>
                </div>

                <div
                    id="btn-nav-history"
                    class="nav-title-box"
                    title="Histórico Recente"
                >
                    <i
                        data-lucide="history"
                        class="icon-sm"
                    ></i>

                    <h3 class="nav-title">
                        Histórico Recente
                    </h3>
                </div>

                <div id="history-list"></div>
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
            >
                <i
                    data-lucide="moon"
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