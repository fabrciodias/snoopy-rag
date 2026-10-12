<script setup lang="ts">
import {
    computed,
    nextTick,
    onMounted,
    onUnmounted,
    ref,
    watch,
} from "vue";

import {
    ArrowLeft,
    Check,
    ExternalLink,
    Languages,
    X,
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

type TranslationTab = "original" | "translation";

interface ActiveTranslation {
    key: string;
    pageNumber: number;
    sourceText: string;
}

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
 * As traduções ficam em memória durante a leitura atual.
 *
 * A chave identifica o documento, a representação,
 * a página e o bloco documental.
 */
const translations = ref<Record<string, string>>({});

const translatingBlocks = ref<Record<string, boolean>>({});

const translationErrors = ref<Record<string, string>>({});

/*
 * Estado do painel de comparação.
 *
 * No computador, original e tradução são exibidos
 * simultaneamente.
 *
 * No celular, mobileTranslationTab define qual deles
 * ocupará a área de leitura.
 */
const activeTranslation = ref<ActiveTranslation | null>(null);

const mobileTranslationTab = ref<TranslationTab>("translation");

const lastTranslationTrigger =
    ref<HTMLButtonElement | null>(null);

const closeTranslationButton =
    ref<HTMLButtonElement | null>(null);

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

const activeTranslationKey = computed(
    () => activeTranslation.value?.key ?? null,
);

const activeTranslationText = computed(() => {
    const key = activeTranslationKey.value;

    if (!key) {
        return null;
    }

    return translations.value[key] ?? null;
});

const activeTranslationLoading = computed(() => {
    const key = activeTranslationKey.value;

    return key !== null &&
        Boolean(translatingBlocks.value[key]);
});

const activeTranslationError = computed(() => {
    const key = activeTranslationKey.value;

    if (!key) {
        return null;
    }

    return translationErrors.value[key] ?? null;
});

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
    if (translatingBlocks.value[key]) {
        return "Ver tradução em andamento";
    }

    if (translations.value[key]) {
        return "Ver tradução disponível";
    }

    if (translationErrors.value[key]) {
        return "Tentar novamente a tradução";
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

function isCurrentTranslationContext(
    contextVersion: ReturnType<typeof getWorkContextVersion>,
    sourceDocumentId: string,
    sourceRepresentationId: string,
): boolean {
    return (
        contextVersion === getWorkContextVersion() &&
        sourceDocumentId === documentId.value &&
        sourceDocumentId === document.value?.document_id &&
        sourceRepresentationId === document.value?.representation_id &&
        navigationState.currentView === "reading"
    );
}

async function requestTranslation(
    key: string,
    sourceText: string,
): Promise<void> {
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
        !sourceText.trim()
    ) {
        translationErrors.value[key] =
            "Não foi possível identificar o documento para traduzir este parágrafo.";

        return;
    }

    translatingBlocks.value[key] = true;

    delete translationErrors.value[key];

    try {
        const result = await translate({
            text: sourceText,
        });

        /*
         * Uma resposta atrasada não pode atualizar uma leitura
         * que já mudou de documento, representação ou contexto.
         */
        if (
            !isCurrentTranslationContext(
                contextVersion,
                sourceDocumentId,
                sourceRepresentationId,
            )
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
    } catch (translationError) {
        if (
            !isCurrentTranslationContext(
                contextVersion,
                sourceDocumentId,
                sourceRepresentationId,
            )
        ) {
            return;
        }

        console.error(
            "[TRANSLATION] Falha ao traduzir parágrafo:",
            translationError,
        );

        translationErrors.value[key] =
            "Não foi possível traduzir este parágrafo. Verifique sua conexão e tente novamente.";
    } finally {
        translatingBlocks.value[key] = false;
    }
}

async function openTranslationPanel(
    pageNumber: number,
    block: DocumentBlock,
    event: MouseEvent,
): Promise<void> {
    const key = translationKey(pageNumber, block);

    lastTranslationTrigger.value =
        event.currentTarget as HTMLButtonElement;

    activeTranslation.value = {
        key,
        pageNumber,
        sourceText: block.text,
    };

    /*
     * No celular, abrimos diretamente a aba de tradução,
     * para que o carregamento ou resultado esteja visível.
     *
     * No computador, ambas as colunas já estarão visíveis.
     */
    mobileTranslationTab.value = "translation";

    await nextTick();

    closeTranslationButton.value?.focus();

    // O resultado já existe: basta abrir o painel.
    if (translations.value[key]) {
        return;
    }

    // A mesma requisição já está em andamento.
    if (translatingBlocks.value[key]) {
        return;
    }

    /*
     * Se houve falha anteriormente, deixamos a nova tentativa
     * a cargo do botão exibido dentro do painel.
     */
    if (translationErrors.value[key]) {
        return;
    }

    await requestTranslation(
        key,
        block.text,
    );
}

async function retryActiveTranslation(): Promise<void> {
    const currentTranslation = activeTranslation.value;

    if (
        !currentTranslation ||
        translatingBlocks.value[currentTranslation.key]
    ) {
        return;
    }

    await requestTranslation(
        currentTranslation.key,
        currentTranslation.sourceText,
    );
}

async function closeTranslationPanel(): Promise<void> {
    activeTranslation.value = null;

    await nextTick();

    /*
     * Devolve o foco ao botão que abriu o painel,
     * se ele ainda estiver disponível na interface.
     */
    if (lastTranslationTrigger.value?.isConnected) {
        lastTranslationTrigger.value.focus();
    }

    lastTranslationTrigger.value = null;
}

function handleTranslationKeydown(
    event: KeyboardEvent,
): void {
    if (
        event.key === "Escape" &&
        activeTranslation.value
    ) {
        event.preventDefault();

        void closeTranslationPanel();
    }
}

function clearTranslationState(): void {
    translations.value = {};
    translatingBlocks.value = {};
    translationErrors.value = {};

    activeTranslation.value = null;
    lastTranslationTrigger.value = null;
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

        /*
         * Uma nova evidência pode pertencer ao mesmo documento.
         * Nesse caso, preservamos as traduções em cache, mas
         * fechamos qualquer painel associado à evidência anterior.
         */
        if (
            document.value?.evidence_id &&
            document.value.evidence_id !== result.evidence_id
        ) {
            activeTranslation.value = null;
        }

        /*
         * Se o documento ou sua representação mudou, as traduções
         * antigas deixam de corresponder à leitura atual.
         */
        if (
            document.value?.document_id !== result.document_id ||
            document.value?.representation_id !== result.representation_id
        ) {
            clearTranslationState();
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

onMounted(() => {
    window.addEventListener(
        "keydown",
        handleTranslationKeydown,
    );
});

onUnmounted(() => {
    window.removeEventListener(
        "keydown",
        handleTranslationKeydown,
    );
});

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
                                    :class="{
                                        'is-translated':
                                            Boolean(
                                                translations[
                                                    translationKey(page.page_number, block)
                                                ],
                                            ),
                                        'is-translating':
                                            Boolean(
                                                translatingBlocks[
                                                    translationKey(page.page_number, block)
                                                ],
                                            ),
                                        'is-active':
                                            activeTranslationKey ===
                                            translationKey(page.page_number, block),
                                    }"
                                    type="button"
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
                                        activeTranslationKey ===
                                        translationKey(page.page_number, block)
                                    "
                                    :aria-busy="
                                        Boolean(
                                            translatingBlocks[
                                                translationKey(page.page_number, block)
                                            ],
                                        )
                                    "
                                    @click="
                                        openTranslationPanel(
                                            page.page_number,
                                            block,
                                            $event,
                                        )
                                    "
                                >
                                    <Check
                                        v-if="
                                            translations[
                                                translationKey(page.page_number, block)
                                            ]
                                        "
                                        class="icon-sm"
                                        aria-hidden="true"
                                    />

                                    <Languages
                                        v-else
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

        <!-- Janela de comparação entre o original e a tradução. -->
        <div
            v-if="activeTranslation"
            class="translation-dialog-overlay"
            role="presentation"
            @click.self="closeTranslationPanel"
        >
            <section
                class="translation-dialog"
                role="dialog"
                aria-modal="true"
                aria-labelledby="translation-dialog-title"
                @click.stop
            >
                <header class="translation-dialog-header">
                    <div class="translation-dialog-heading">
                        <h3 id="translation-dialog-title">
                            Comparar original e tradução
                        </h3>

                        <span class="translation-dialog-page">
                            Página {{ activeTranslation.pageNumber }}
                        </span>
                    </div>

                    <button
                        ref="closeTranslationButton"
                        class="btn-icon translation-dialog-close"
                        type="button"
                        title="Fechar comparação"
                        aria-label="Fechar comparação"
                        @click="closeTranslationPanel"
                    >
                        <X />
                    </button>
                </header>

                <!--
                    Estas abas são utilizadas somente em telas pequenas.
                    No computador, as duas colunas ficam visíveis.
                -->
                <div
                    class="translation-mobile-tabs"
                    role="tablist"
                    aria-label="Texto para visualizar"
                >
                    <button
                        id="translation-tab-original"
                        class="translation-mobile-tab"
                        :class="{
                            'is-active':
                                mobileTranslationTab === 'original',
                        }"
                        type="button"
                        role="tab"
                        aria-controls="translation-pane-original"
                        :aria-selected="
                            mobileTranslationTab === 'original'
                        "
                        @click="mobileTranslationTab = 'original'"
                    >
                        Original
                    </button>

                    <button
                        id="translation-tab-translation"
                        class="translation-mobile-tab"
                        :class="{
                            'is-active':
                                mobileTranslationTab === 'translation',
                        }"
                        type="button"
                        role="tab"
                        aria-controls="translation-pane-translation"
                        :aria-selected="
                            mobileTranslationTab === 'translation'
                        "
                        @click="mobileTranslationTab = 'translation'"
                    >
                        Tradução

                        <span
                            v-if="activeTranslationText"
                            class="translation-tab-check"
                            aria-label="Tradução concluída"
                        >
                            <Check class="icon-sm" />
                        </span>
                    </button>
                </div>

                <div class="translation-dialog-columns">
                    <!-- Coluna do documento original. -->
                    <section
                        id="translation-pane-original"
                        class="translation-dialog-pane translation-dialog-pane-original"
                        :class="{
                            'is-mobile-active':
                                mobileTranslationTab === 'original',
                        }"
                        role="tabpanel"
                        aria-labelledby="translation-tab-original"
                    >
                        <header class="translation-pane-header">
                            <div>
                                <h4>
                                    Trecho original
                                </h4>

                                <span>
                                    Texto do documento-fonte
                                </span>
                            </div>
                        </header>

                        <div class="translation-pane-content">
                            <p class="translation-pane-text">
                                {{ activeTranslation.sourceText }}
                            </p>
                        </div>
                    </section>

                    <!-- Coluna do resultado da tradução. -->
                    <section
                        id="translation-pane-translation"
                        class="translation-dialog-pane translation-dialog-pane-translation"
                        :class="{
                            'is-mobile-active':
                                mobileTranslationTab === 'translation',
                        }"
                        role="tabpanel"
                        aria-labelledby="translation-tab-translation"
                    >
                        <header class="translation-pane-header">
                            <div>
                                <h4>
                                    Tradução para português
                                </h4>

                                <span>
                                    {{
                                        activeTranslationLoading
                                            ? "Processando parágrafo"
                                            : activeTranslationError
                                                ? "Tradução indisponível"
                                                : activeTranslationText
                                                    ? "Tradução concluída"
                                                    : "Aguardando tradução"
                                    }}
                                </span>
                            </div>

                            <Check
                                v-if="activeTranslationText"
                                class="translation-pane-success"
                                aria-label="Tradução concluída"
                            />
                        </header>

                        <div
                            class="translation-pane-content"
                            aria-live="polite"
                        >
                            <div
                                v-if="activeTranslationLoading"
                                class="translation-dialog-state"
                                role="status"
                            >
                                <div
                                    class="spinner"
                                    aria-hidden="true"
                                ></div>

                                <div>
                                    <strong>
                                        Traduzindo para português...
                                    </strong>

                                    <p>
                                        Aguarde enquanto processamos o parágrafo.
                                    </p>
                                </div>
                            </div>

                            <div
                                v-else-if="activeTranslationError"
                                class="translation-dialog-error"
                                role="alert"
                            >
                                <p>
                                    {{ activeTranslationError }}
                                </p>

                                <button
                                    class="btn-outline translation-retry-button"
                                    type="button"
                                    @click="retryActiveTranslation"
                                >
                                    Tentar novamente
                                </button>
                            </div>

                            <p
                                v-else-if="activeTranslationText"
                                class="translation-pane-text"
                            >
                                {{ activeTranslationText }}
                            </p>

                            <p
                                v-else
                                class="translation-pane-placeholder"
                            >
                                A tradução aparecerá aqui.
                            </p>
                        </div>
                    </section>
                </div>
            </section>
        </div>
    </section>
</template>