<script setup lang="ts">
import {
    computed,
    nextTick,
    ref,
    watch,
} from "vue";

import {
    ArrowLeft,
    ExternalLink,
} from "@lucide/vue";

import {
    loadDocument,
} from "../../features/documents/actions";

import type {
    Document,
    DocumentBlock,
    DocumentPage,
} from "../../features/documents/contracts";

import {
    goToInvestigation,
    navigationState,
} from "../../state/navigation";

const documentId =
    computed(
        () =>
            navigationState.reading
                .documentId,
    );

const location =
    computed(
        () =>
            navigationState.reading
                .location,
    );

const document =
    ref<Document | null>(null);

const isLoading =
    ref(false);

const error =
    ref<string | null>(null);

const currentPage =
    computed(() => {
        if (
            !document.value?.current_representation ||
            !location.value?.start_page
        ) {
            return null;
        }

        return (
            document.value
                .current_representation
                .pages.find(
                    (page) =>
                        page.page_number ===
                        location.value
                            ?.start_page,
                ) ?? null
        );
    });

const pages =
    computed(
        () =>
            document.value
                ?.current_representation
                ?.pages ?? [],
    );

const readingContainer =
    ref<HTMLElement | null>(null);

function blockIsInLocation(
    page: DocumentPage,
    block: DocumentBlock,
): boolean {
    const currentLocation = location.value;

    if (!currentLocation) {
        return false;
    }

    const startPage =
        currentLocation.start_page ??
        page.page_number;

    const endPage =
        currentLocation.end_page ??
        startPage;

    if (
        page.page_number < startPage ||
        page.page_number > endPage
    ) {
        return false;
    }

    const blockIndex = block.block_index;

    // Evidência inteira na mesma página.
    if (startPage === endPage) {
        return (
            (
                currentLocation.start_block === null ||
                blockIndex >=
                    currentLocation.start_block
            ) &&
            (
                currentLocation.end_block === null ||
                blockIndex <=
                    currentLocation.end_block
            )
        );
    }

    // Primeira página: do bloco inicial até o fim.
    if (page.page_number === startPage) {
        return (
            currentLocation.start_block === null ||
            blockIndex >=
                currentLocation.start_block
        );
    }

    // Última página: do início até o bloco final.
    if (page.page_number === endPage) {
        return (
            currentLocation.end_block === null ||
            blockIndex <=
                currentLocation.end_block
        );
    }

    // Páginas intermediárias: todos os blocos pertencem à evidência.
    return true;
}

async function loadCurrentDocument(): Promise<void> {
    if (!documentId.value) {
        error.value =
            "Nenhum documento foi selecionado.";
        return;
    }

    isLoading.value = true;
    error.value = null;

    try {
        document.value =
            await loadDocument(
                documentId.value,
            );
    } catch (loadError) {
        error.value =
            loadError instanceof Error
                ? loadError.message
                : String(loadError);
    } finally {
        isLoading.value = false;
    }
}

async function scrollToEvidence(): Promise<void> {
    await nextTick();

    const target =
        readingContainer.value?.querySelector(
            ".reading-block-evidence",
        );

    if (!target) {
        return;
    }

    target.scrollIntoView({
        behavior: "smooth",
        block: "center",
    });
}

async function ensureReadingDocument(): Promise<void> {
    if (!documentId.value) {
        return;
    }

    if (
        document.value?.id !==
        documentId.value
    ) {
        await loadCurrentDocument();
    }

    await scrollToEvidence();
}

function handleBack(): void {
    goToInvestigation();
}

watch(
    [
        () => navigationState.currentView,
        documentId,
        () =>
            JSON.stringify(
                navigationState.reading.location,
            ),
    ],
    async ([view]) => {
        if (
            view !== "reading" ||
            !documentId.value
        ) {
            return;
        }

        await ensureReadingDocument();
    },
    {
        immediate: true,
    },
);
</script>

<template>
    <section
        id="reading-view"
        class="view"
    >
        <header
            class="topbar reading-topbar"
        >
            <div class="topbar-side">
                <button
                    id="btn-close-reading"
                    class="btn-icon btn-reading-action"
                    title="Voltar para a pesquisa"
                    type="button"
                    @click="handleBack"
                >
                    <ArrowLeft />

                    <span class="hide-mobile">
                        Voltar
                    </span>
                </button>
            </div>

            <div class="topbar-center">
                <h2
                    id="reading-title"
                    class="sticky-query"
                >
                    {{
                        document?.title ??
                        "Leitura do documento"
                    }}
                </h2>
            </div>

            <div
                class="topbar-side right"
            >
                <a
                    v-if="
                        document?.drive_link
                    "
                    id="reading-original-link"
                    :href="
                        document.drive_link
                    "
                    target="_blank"
                    rel="noopener noreferrer"
                    class="btn-outline btn-reading-action"
                    title="Abrir PDF Original"
                >
                    <ExternalLink class="icon-sm" />

                    <span class="hide-mobile">
                        PDF
                    </span>
                </a>
            </div>
        </header>

        <main
            class="reading-layout"
        >
            <div
                v-if="isLoading"
                class="reading-container"
            >
                <div
                    id="loading-state"
                >
                    <div
                        class="spinner"
                    ></div>

                    <p
                        class="live-logs"
                    >
                        Carregando documento...
                    </p>
                </div>
            </div>

            <div
                v-else-if="error"
                class="reading-container"
            >
                <p
                    class="home-error"
                >
                    {{ error }}
                </p>
            </div>

            <div
                v-else-if="
                    document?.current_representation
                "
                id="reading-content"
                class="reading-container"
                ref="readingContainer"
            >
                <article
                    v-for="page in pages"
                    :key="
                        page.page_number
                    "
                    class="reading-page"
                    :data-page="
                        page.page_number
                    "
                    :class="{
                        'reading-page-current':
                            currentPage
                                ?.page_number ===
                            page.page_number,
                    }"
                >
                    <header
                        class="reading-page-header"
                    >
                        Página
                        {{
                            page.page_number
                        }}
                    </header>

                    <div
                        class="reading-page-content"
                    >
                        <p
                            v-for="block in page.blocks"
                            :key="
                                `${page.page_number}-${block.block_index}`
                            "
                            class="reading-block"
                            :class="{
                                'reading-block-evidence':
                                    blockIsInLocation(
                                        page,
                                        block,
                                    ),
                            }"
                        >
                            {{
                                block.text
                            }}
                        </p>
                    </div>
                </article>
            </div>

            <div
                v-else
                class="reading-container"
            >
                <p>
                    Este documento ainda não
                    possui uma representação
                    publicada para leitura.
                </p>
            </div>
        </main>
    </section>
</template>