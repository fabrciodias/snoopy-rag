<script setup lang="ts">
import {
    onMounted,
    onUnmounted,
} from "vue";

import {
    Menu,
} from "@lucide/vue";

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

import {
    computed,
    ref,
} from "vue";

import {
    navigationState,
} from "../../state/navigation";

let stopAuthListener:
    (() => void) | null = null;

const mobileSidebarOpen =
    ref(false);

const settingsOpen =
    ref(false);

function openMobileSidebar(): void {
    mobileSidebarOpen.value = true;
}

function closeMobileSidebar(): void {
    mobileSidebarOpen.value = false;
}

function openSettings(): void {
    settingsOpen.value = true;
}

function closeSettings(): void {
    settingsOpen.value = false;
}

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
});

onUnmounted(() => {
    stopAuthListener?.();
});

const currentView =
    computed(
        () =>
            navigationState.currentView,
    );
</script>

<template>
    <div class="app-container">
        <div
            id="mobile-overlay"
            class="mobile-overlay"
            :class="{
                active: mobileSidebarOpen,
            }"
            @click="closeMobileSidebar"
        ></div>

        <button
            id="btn-mobile-menu"
            class="btn-mobile-menu btn-icon"
            title="Menu"
            type="button"
            @click="openMobileSidebar"
        >
            <Menu />
        </button>

        <Sidebar 
            :mobile-open="mobileSidebarOpen"
            @close-mobile="closeMobileSidebar"
            @open-settings="openSettings"
        />

        <div
            id="main-content"
            class="main-area"
        >
            <HomeView 
                v-if="currentView === 'home'"    
            />

            <InvestigationView 
                v-else-if="
                    currentView ===
                    'investigation'
                "
            />

            <ReadingView 
                v-else-if="
                    currentView ===
                    'reading'
                "
            />
        </div>

        <SettingsModal 
            :open="settingsOpen"
            @close="closeSettings"
        />
    </div>
</template>