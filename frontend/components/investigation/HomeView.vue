<script setup lang="ts">
import {
    computed,
    onMounted,
    ref,
} from "vue";

import {
    investigate,
} from "../../features/investigation/actions";

import {
    loadFolders,
} from "../../features/folders/actions";

import {
    folderState,
} from "../../state/folders";

import {
    investigationState,
} from "../../state/investigation";

const query = ref("");

const selectedFolderId = computed(
    () => folderState.selectedFolderId,
);

const isLoading = computed(
    () => investigationState.isInvestigating,
);

const error = computed(
    () =>
        investigationState.error ??
        folderState.error,
);

async function submitInvestigation(): Promise<void> {
    const normalizedQuery =
        query.value.trim();

    if (
        !normalizedQuery ||
        !selectedFolderId.value
    ) {
        return;
    }

    await investigate({
        folder_id:
            selectedFolderId.value,
        query: normalizedQuery,
        limit: 5,
    });
}

function handleSubmit(): void {
    void submitInvestigation();
}

onMounted(() => {
    if (folderState.folders.length === 0) {
        void loadFolders();
    }
});
</script>

<template>
    <section
        id="home-view"
        class="view active"
    >
        <div class="hero">
            <h1 class="logo">
                LPP-Acervo
            </h1>

            <p class="subtitle">
                Memória Institucional e Recuperação Semântica Documental
            </p>

            <form
                id="search-home"
                class="search-box"
                @submit.prevent="handleSubmit"
            >
                <input
                    id="input-home"
                    v-model="query"
                    type="text"
                    placeholder="Pesquisar"
                    required
                    autocomplete="off"
                    :disabled="isLoading"
                >

                <button
                    type="submit"
                    :disabled="
                        isLoading ||
                        !query.trim() ||
                        !selectedFolderId
                    "
                >
                    →
                </button>
            </form>

            <p
                v-if="error"
                class="home-error"
            >
                {{ error }}
            </p>
        </div>
    </section>
</template>