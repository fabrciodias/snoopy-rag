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
    saveHistory,
} from "../../infrastructure/api.js";

import {
    showInvestigation,
    showInvestigationError,
    dom,
} from "../../components/ResultList.js";

import {
    renderEvidencePanel,
} from "../../components/EvidencePanel.js";


export function createInvestigationController() {
    let busy = false;


    async function execute(query) {
        const normalized = query.trim();

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

        startInvestigation(normalized);

        showInvestigation(normalized);

        try {
            const result = await investigate(
                appState.folderId,
                normalized,
                5
            );

            completeInvestigation(result);

            renderResult(result);

            if (result.response) {
                try {
                    await saveHistory(normalized);
                } catch (historyError) {
                    console.warn(
                        "[INVESTIGATION] Falha ao salvar histórico:",
                        historyError
                    );
                }
            }

            return result;

        } catch (error) {
            failInvestigation(error.message);

            showInvestigationError(
                error.message
            );

            throw error;

        } finally {
            busy = false;
        }
    }


    function renderResult(result) {
        dom.loadingState.classList.add(
            "hidden"
        );

        if (!result.response) {
            dom.answerBox.classList.remove(
                "hidden"
            );

            dom.answerText.textContent =
                "Nenhuma resposta foi produzida.";

            return;
        }

        dom.answerBox.classList.remove(
            "hidden"
        );

        dom.answerText.className =
            "";

        dom.answerText.textContent =
            result.response.content || "";

        renderSources(
            result.response,
            result.evidences || []
        );

        renderChunks(
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
            new Map(
                evidences.map(
                    evidence => [
                        evidence.evidence_id ||
                        evidence.id,
                        evidence
                    ]
                )
            );

        const references =
            response.evidence_refs || [];

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

            const button =
                document.createElement(
                    "button"
                );

            button.type =
                "button";

            button.className =
                "source-card";

            button.textContent =
                `Evidência ${reference}`;

            button.addEventListener(
                "click",
                () =>
                    selectEvidence(
                        evidence
                    )
            );

            dom.sourcesContainer.appendChild(
                button
            );
        }
    }


    function renderChunks(
        evidences
    ) {
        dom.chunksContainer.innerHTML =
            "";

        for (
            const evidence of evidences
        ) {
            const card =
                document.createElement(
                    "article"
                );

            card.className =
                "chunk-card";

            const content =
                document.createElement(
                    "p"
                );

            content.textContent =
                evidence.content || "";

            card.appendChild(
                content
            );

            const location =
                evidence.provenance?.location;

            if (location) {
                const meta =
                    document.createElement(
                        "small"
                    );

                meta.textContent =
                    `Localização: ${location}`;

                card.appendChild(
                    meta
                );
            }

            card.addEventListener(
                "click",
                () =>
                    selectEvidence(
                        evidence
                    )
            );

            dom.chunksContainer.appendChild(
                card
            );
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
                    detail: evidence,
                }
            )
        );
    }


    return {
        execute,
        selectEvidence,
    };
}