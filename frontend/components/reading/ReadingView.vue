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
    Languages,
} from "@lucide/vue";

import {
    loadContextualReading,
} from "../../features/documents/actions";

import {
    translate,
} from "../../features/translation/api";

import type {
    ContextualReading,
    DocumentBlock,
    DocumentPage,
} from "../../features/documents/contracts";

import {
    goToInvestigation,
    navigationState,
} from "../../state/navigation";

import {
    getWorkContextVersion,
} from "../../state/workContext";

const documentId = computed(
    () => navigationState.reading.documentId,
);

const evidenceId = computed(
    () => navigationState.reading.evidenceId,
);

const location = computed(
    () => navigationState.reading.location,
);

const document = ref<ContextualReading | null>(null);

const isLoading = ref(false);

const error = ref<string | null>(null);

/*
 * Estado local das traduções.
 *
 * A chave identifica o documento, sua representação,
 * a página e o bloco documental.
 *
 * Assim, parágrafos diferentes não compartilham
 * acidentalmente a mesma tradução.
 */
const translations = ref<Record<string, string>>({});

const visibleTranslations = ref<Record<string, boolean>>({});

const translatingBlocks = ref<Record<string, boolean>>({});

const translationErrors = ref<Record<string, string>>({});

const currentPage = computed(() => {
    if (
        !document.value?.representation ||
        !location.value?.start_page
    ) {
        return null;
    }

    return (
        document.value.representation.pages.find(
            (page) =>
                page.page_number === location.value?.start_page,
        ) ?? null
    );
});

const pages = computed(
    () => document.value?.representation.pages ?? [],
);

const readingContainer = ref<HTMLElement | null>(null);

function translationKey(
    pageNumber: number,
    block: DocumentBlock,
): string {
    const currentDocument = document.value;

    return [
        currentDocument?.document_id ?? "unknown-document",
        currentDocument?.representation_id ?? "unknown-representation",
        pageNumber,
        block.block_index,
    ].join(":");
}

function translationButtonLabel(
    key: string,
): string {
    if (visibleTranslations.value[key]) {
        return "Ocultar tradução";
    }

    if (translations.value[key]) {
        return "Exibir tradução";
    }

    return "Traduzir este parágrafo";
}

function blockIsInLocation(
    page: DocumentPage,
    block: DocumentBlock,
): boolean {
    const currentLocation = location.value;

    if (!currentLocation) {
        return false;
    }

    const startPage =
        currentLocation.start_page ?? page.page_number;

    const endPage =
        currentLocation.end_page ?? startPage;

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
                blockIndex >= currentLocation.start_block
            ) &&
            (
                currentLocation.end_block === null ||
                blockIndex <= currentLocation.end_block
            )
        );
    }

    // Primeira página: do bloco inicial até o fim.
    if (page.page_number === startPage) {
        return (
            currentLocation.start_block === null ||
            blockIndex >= currentLocation.start_block
        );
    }

    // Última página: do início até o bloco final.
    if (page.page_number === endPage) {
        return (
            currentLocation.end_block === null ||
            blockIndex <= currentLocation.end_block
        );
    }

    // Páginas intermediárias: todos os blocos pertencem à evidência.
    return true;
}

async function toggleTranslation(
    pageNumber: number,
    block: DocumentBlock,
): Promise<void> {
    const key = translationKey(pageNumber, block);

    // Se a tradução já estiver aberta, apenas a oculta.
    if (visibleTranslations.value[key]) {
        visibleTranslations.value[key] = false;
        return;
    }

    // Se já existir uma tradução em cache, apenas a exibe.
    if (translations.value[key]) {
        visibleTranslations.value[key] = true;
        return;
    }

    // Não permite requisições simultâneas para o mesmo bloco.
    if (translatingBlocks.value[key]) {
        return;
    }

    const sourceDocumentId = document.value?.document_id;

    const sourceRepresentationId =
        document.value?.representation_id;

    const contextVersion = getWorkContextVersion();

    if (
        !sourceDocumentId ||
        !sourceRepresentationId ||
        !block.text.trim()
    ) {
        return;
    }

    translatingBlocks.value[key] = true;

    delete translationErrors.value[key];

    try {
        const result = await translate({
            text: block.text,
        });

        /*
         * Uma resposta atrasada não deve atualizar a leitura
         * depois de uma mudança de contexto ou documento.
         */
        if (
            contextVersion !== getWorkContextVersion() ||
            sourceDocumentId !== document.value?.document_id ||
            sourceRepresentationId !== document.value?.representation_id ||
            navigationState.currentView !== "reading"
        ) {
            return;
        }

        const translatedText = result.translation.trim();

        if (!translatedText) {
            throw new Error(
                "A tradução não retornou texto.",
            );
        }

        translations.value[key] = translatedText;

        visibleTranslations.value[key] = true;
    } catch (translationError) {
        if (
            contextVersion !== getWorkContextVersion() ||
            sourceDocumentId !== document.value?.document_id ||
            sourceRepresentationId !== document.value?.representation_id ||
            navigationState.currentView !== "reading"
        ) {
            return;
        }

        console.error(
            "[TRANSLATION] Falha ao traduzir parágrafo:",
            translationError,
        );

        translationErrors.value[key] =
            "Não foi possível traduzir este parágrafo. Tente novamente.";
    } finally {
        translatingBlocks.value[key] = false;
    }
}

async function loadCurrentDocument(): Promise<void> {
    const requestedDocumentId = documentId.value;
    const requestedEvidenceId = evidenceId.value;
    const contextVersion = getWorkContextVersion();

    if (!requestedDocumentId || !requestedEvidenceId) {
        document.value = null;

        error.value =
            "Não foi possível identificar o documento e a evidência selecionados.";

        return;
    }

    isLoading.value = true;
    error.value = null;

    try {
        const result = await loadContextualReading(
            requestedDocumentId,
            requestedEvidenceId,
        );

        if (
            contextVersion !== getWorkContextVersion() ||
            requestedDocumentId !== documentId.value ||
            requestedEvidenceId !== evidenceId.value ||
            navigationState.currentView !== "reading"
        ) {
            return;
        }

        document.value = result;
    } catch (loadError) {
        if (
            contextVersion !== getWorkContextVersion() ||
            requestedDocumentId !== documentId.value ||
            requestedEvidenceId !== evidenceId.value ||
            navigationState.currentView !== "reading"
        ) {
            return;
        }

        document.value = null;

        error.value =
            loadError instanceof Error
                ? loadError.message
                : String(loadError);
    } finally {
        if (
            contextVersion === getWorkContextVersion() &&
            requestedDocumentId === documentId.value &&
            requestedEvidenceId === evidenceId.value
        ) {
            isLoading.value = false;
        }
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
    if (!documentId.value || !evidenceId.value) {
        return;
    }

    if (
        document.value?.document_id !== documentId.value ||
        document.value?.evidence_id !== evidenceId.value
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
        evidenceId,
        () => JSON.stringify(navigationState.reading.location),
    ],
    async ([view]) => {
        if (
            view !== "reading" ||
            !documentId.value ||
            !evidenceId.value
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
                    v-if="document?.drive_link"
                    id="reading-original-link"
                    :href="document.drive_link"
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
                <div id="loading-state">
                    <div class="spinner"></div>

                    <p class="live-logs">
                        Carregando documento...
                    </p>
                </div>
            </div>

            <div
                v-else-if="error"
                class="reading-container"
            >
                <p class="home-error">
                    {{ error }}
                </p>
            </div>

            <div
                v-else-if="document?.representation"
                id="reading-content"
                class="reading-container"
                ref="readingContainer"
            >
                <article
                    v-for="page in pages"
                    :key="page.page_number"
                    class="reading-page"
                    :data-page="page.page_number"
                    :class="{
                        'reading-page-current':
                            currentPage?.page_number === page.page_number,
                    }"
                >
                    <header class="reading-page-header">
                        Página
                        {{ page.page_number }}
                    </header>

                    <div class="reading-page-content">
                        <div
                            v-for="block in page.blocks"
                            :key="`${page.page_number}-${block.block_index}`"
                            class="reading-block-item"
                        >
                            <div class="reading-block-row">
                                <p
                                    class="reading-block"
                                    :class="{
                                        'reading-block-evidence':
                                            blockIsInLocation(page, block),
                                    }"
                                >
                                    {{ block.text }}
                                </p>

                                <button
                                    v-if="block.text.trim()"
                                    class="btn-translate-paragraph"
                                    type="button"
                                    :disabled="
                                        translatingBlocks[
                                            translationKey(page.page_number, block)
                                        ]
                                    "
                                    :title="
                                        translationButtonLabel(
                                            translationKey(page.page_number, block),
                                        )
                                    "
                                    :aria-label="
                                        translationButtonLabel(
                                            translationKey(page.page_number, block),
                                        )
                                    "
                                    :aria-expanded="
                                        Boolean(
                                            visibleTranslations[
                                                translationKey(page.page_number, block)
                                            ],
                                        )
                                    "
                                    @click="
                                        toggleTranslation(
                                            page.page_number,
                                            block,
                                        )
                                    "
                                >
                                    <Languages
                                        class="icon-sm"
                                        aria-hidden="true"
                                    />

                                    <span class="translation-visually-hidden">
                                        {{
                                            translationButtonLabel(
                                                translationKey(page.page_number, block),
                                            )
                                        }}
                                    </span>
                                </button>
                            </div>

                            <p
                                v-if="
                                    translatingBlocks[
                                        translationKey(page.page_number, block)
                                    ]
                                "
                                class="translation-status"
                                role="status"
                                aria-live="polite"
                            >
                                Traduzindo para português...
                            </p>

                            <p
                                v-if="
                                    translationErrors[
                                        translationKey(page.page_number, block)
                                    ]
                                "
                                class="translation-error"
                                role="alert"
                            >
                                {{
                                    translationErrors[
                                        translationKey(page.page_number, block)
                                    ]
                                }}
                            </p>

                            <section
                                v-if="
                                    visibleTranslations[
                                        translationKey(page.page_number, block)
                                    ] &&
                                    translations[
                                        translationKey(page.page_number, block)
                                    ]
                                "
                                class="translation-panel"
                                aria-label="Tradução para português"
                            >
                                <header class="translation-panel-header">
                                    <span>
                                        Tradução para português
                                    </span>

                                    <button
                                        type="button"
                                        class="translation-hide-button"
                                        @click="
                                            visibleTranslations[
                                                translationKey(page.page_number, block)
                                            ] = false
                                        "
                                    >
                                        Ocultar
                                    </button>
                                </header>

                                <p class="translation-text">
                                    {{
                                        translations[
                                            translationKey(page.page_number, block)
                                        ]
                                    }}
                                </p>
                            </section>
                        </div>
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