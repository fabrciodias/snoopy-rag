import {
    appState,
} from "../../state/application.js";

import {
    investigationState,
    startInvestigation,
    completeInvestigation,
    failInvestigation,
} from "../../state/investigation.js";

import {
    investigate,
    fetchDocument,
} from "../../infrastructure/api.js";

import {
    showInvestigation,
    showInvestigationError,
    dom,
} from "../../renderer/render.js";

import {
    renderEvidencePanel,
} from "../../components/EvidencePanel.js";


export function createInvestigationController() {
    let busy = false;


    async function execute(query) {
        const normalized =
            String(query || "").trim();

        if (!normalized) {
            return;
        }

        if (busy) {
            return;
        }

        if (!appState.isAuthLoaded) {
            throw new Error(
                "A autenticação ainda está sendo inicializada."
            );
        }

        if (!appState.userToken) {
            throw new Error(
                "Faça login para iniciar uma investigação."
            );
        }

        if (!appState.folderId) {
            throw new Error(
                "Nenhum acervo está selecionado."
            );
        }

        busy = true;

        startInvestigation(
            normalized
        );

        showInvestigation(
            normalized
        );

        try {
            const result =
                await investigate(
                    appState.folderId,
                    normalized,
                    5
                );

            await enrichEvidenceMetadata(
                result.evidences || []
            );

            completeInvestigation(
                result
            );

            renderResult(
                result
            );

            return result;

        } catch (error) {
            failInvestigation(
                error.message
            );

            showInvestigationError(
                error.message
            );

            throw error;

        } finally {
            busy = false;
        }
    }


    async function enrichEvidenceMetadata(
        evidences
    ) {
        const cache =
            new Map();

        for (
            const evidence of evidences
        ) {
            const documentId =
                evidence.document_id;

            if (!documentId) {
                continue;
            }

            if (!cache.has(documentId)) {
                try {
                    cache.set(
                        documentId,
                        await fetchDocument(
                            documentId
                        )
                    );
                } catch {
                    cache.set(
                        documentId,
                        null
                    );
                }
            }

            const document =
                cache.get(documentId);

            if (!document) {
                continue;
            }

            evidence.document_title =
                document.title ||
                "Documento";

            evidence.document =
                document;
        }

        return evidences;
    }


    function renderResult(
        result
    ) {
        dom.loadingState.classList.add(
            "hidden"
        );

        dom.answerBox.classList.remove(
            "hidden"
        );

        dom.sourcesContainer.innerHTML =
            "";

        dom.chunksContainer.innerHTML =
            "";

        const response =
            result.response;

        if (!response) {
            dom.answerText.textContent =
                "Nenhuma evidência encontrada no acervo para esta busca.";

            return;
        }

        /*
         * Mantém o texto da síntese V3.
         *
         * Não transformamos o conteúdo da resposta em
         * HTML arbitrariamente, porque ele vem do backend.
         */
        dom.answerText.textContent =
            response.content || "";

        dom.answerText.className =
            "";

        renderSources(
            response,
            result.evidences || []
        );

        renderEvidenceList(
            result.evidences || []
        );
    }


    function renderSources(
        response,
        evidences
    ) {
        dom.sourcesContainer.innerHTML =
            "";

        const evidenceMap =
            new Map();

        for (
            const evidence of evidences
        ) {
            const id =
                evidence.evidence_id ||
                evidence.id;

            if (id) {
                evidenceMap.set(
                    id,
                    evidence
                );
            }
        }

        const references =
            response.evidence_refs || [];

        if (!references.length) {
            dom.sourcesContainer.innerHTML =
                `<p class="no-sources-msg">
                    Nenhuma fonte direta indexada.
                </p>`;

            return;
        }

        for (
            const reference of references
        ) {
            const evidence =
                evidenceMap.get(
                    reference
                );

            if (!evidence) {
                continue;
            }

            const card =
                document.createElement(
                    "button"
                );

            card.type =
                "button";

            card.className =
                "source-card";

            const title =
                document.createElement(
                    "h4"
                );

            title.style.fontSize =
                "0.85rem";

            title.textContent =
                evidence.document_title ||
                "Documento";

            const meta =
                document.createElement(
                    "p"
                );

            meta.className =
                "source-meta";

            const location =
                evidence.location || {};

            const page =
                location.page ??
                location.page_number;

            meta.textContent =
                page
                    ? `Página ${page}`
                    : "Localização não informada";

            card.append(
                title,
                meta
            );

            card.addEventListener(
                "click",
                () => {
                    selectEvidence(
                        evidence
                    );
                }
            );

            dom.sourcesContainer.appendChild(
                card
            );
        }
    }


    function renderEvidenceList(
        evidences
    ) {
        dom.chunksContainer.innerHTML =
            "";

        for (
            const evidence of evidences
        ) {
            const card =
                document.createElement(
                    "div"
                );

            card.className =
                "chunk-card";

            const header =
                document.createElement(
                    "div"
                );

            header.style.display =
                "flex";

            header.style.justifyContent =
                "space-between";

            header.style.alignItems =
                "center";

            header.style.marginBottom =
                "10px";

            const title =
                document.createElement(
                    "h4"
                );

            title.style.margin =
                "0";

            title.textContent =
                "Evidência";

            const readButton =
                document.createElement(
                    "button"
                );

            readButton.type =
                "button";

            readButton.className =
                "btn-outline";

            readButton.style.width =
                "fit-content";

            readButton.style.padding =
                "4px 10px";

            readButton.style.fontSize =
                "0.75rem";

            readButton.style.minHeight =
                "unset";

            readButton.innerHTML =
                `Ler no Contexto
                 <i data-lucide="book-open"
                    class="icon-sm"
                    style="margin-left: 6px;">
                 </i>`;

            readButton.addEventListener(
                "click",
                event => {
                    event.stopPropagation();

                    selectEvidence(
                        evidence
                    );

                    onReadEvidence(
                        evidence
                    );
                }
            );

            header.append(
                title,
                readButton
            );

            const text =
                document.createElement(
                    "p"
                );

            text.textContent =
                evidence.content || "";

            text.style.whiteSpace =
                "pre-wrap";

            text.style.lineHeight =
                "1.6";

            const location =
                evidence.location || {};

            const page =
                location.page ??
                location.page_number;

            const meta =
                document.createElement(
                    "p"
                );

            meta.className =
                "source-meta";

            meta.textContent =
                page
                    ? `${evidence.document_title || "Documento"} · Página ${page}`
                    : (
                        evidence.document_title ||
                        "Documento"
                    );

            card.append(
                header,
                text,
                meta
            );

            card.addEventListener(
                "click",
                () => {
                    selectEvidence(
                        evidence
                    );
                }
            );

            dom.chunksContainer.appendChild(
                card
            );
        }

        if (window.lucide) {
            window.lucide.createIcons();
        }
    }


    function selectEvidence(
        evidence
    ) {
        investigationState.selectedEvidence =
            evidence;

        renderEvidencePanel(
            evidence,
            onReadEvidence
        );
    }


    function onReadEvidence(
        evidence
    ) {
        window.dispatchEvent(
            new CustomEvent(
                "snoopy:open-reading",
                {
                    detail:
                        evidence,
                }
            )
        );
    }


    return {
        execute,
        selectEvidence,
    };
}