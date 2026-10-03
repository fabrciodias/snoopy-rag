<script setup lang="ts">
import {
    onMounted,
    onUnmounted,
    nextTick,
} from "vue";

import Sidebar from "./Sidebar.vue";

import HomeView from "../investigation/HomeView.vue";
import InvestigationView from "../investigation/InvestigationView.vue";
import ReadingView from "../reading/ReadingView.vue";
import SettingsModal from "../settings/SettingsModal.vue";

import {
    getSession,
    onAuthStateChange,
} from "../../infrastructure/supabase-auth.ts";

import {
    authState,
    setSession,
    setAuthError,
} from "../../state/authentication.ts";

let stopAuthListener:
    (() => void) | null = null;

onMounted(async () => {
    try {
        const session =
            await getSession();

        setSession(session);

        stopAuthListener =
            await onAuthStateChange(
                (newSession) => {
                    setSession(newSession);
                },
            );

        authState.initialized = true;
    } catch (error) {
        setAuthError(error);
        authState.initialized = true;
    }

    await nextTick();

    window.lucide?.createIcons();
});

onUnmounted(() => {
    stopAuthListener?.();
});
</script>

<template>
    <div class="app-container">
        <div
            id="mobile-overlay"
            class="mobile-overlay"
        ></div>

        <button
            id="btn-mobile-menu"
            class="btn-mobile-menu btn-icon"
            title="Menu"
        >
            <i data-lucide="menu"></i>
        </button>

        <Sidebar />

        <div
            id="main-content"
            class="main-area"
        >
            <HomeView />

            <InvestigationView />

            <ReadingView />
        </div>

        <SettingsModal />
    </div>
</template>