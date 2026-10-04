<script setup lang="ts">
import {
    computed,
    ref,
} from "vue";

import EvidencePanel from "../evidence/EvidencePanel.vue";

import {
    investigationState,
} from "../../state/investigation";

import {
    goToReading
} from "../../state/navigation";

const investigation =
    computed(
        () =>
            investigationState
                .activeInvestigation,
    );

const response =
    computed(
        () =>
            investigationState.response,
    );

const evidences =
    computed(
        () =>
            investigationState.evidences,
    );

const isInvestigating =
    computed(
        () =>
            investigationState
                .isInvestigating,
    );

const error =
    computed(
        () =>
            investigationState.error,
    );

const sections =
    computed(() => {
        if (!response.value) {
            return [];
        }

        return response.value.sections;
    });

const referencedEvidences =
    computed(() => {
        if (!response.value) {
            return [];
        }

        const references =
            new Set(
                response.value
                    .evidence_refs,
            );

        return evidences.value.filter(
            (evidence) =>
                evidence.evidence_id !== null &&
                references.has(
                    evidence.evidence_id,
                ),
        );
    });

const selectedEvidenceId =
    ref<string | null>(null);

const selectedEvidence =
    computed(() => {
        if (
            !selectedEvidenceId.value
        ) {
            return null;
        }

        return (
            evidences.value.find(
                (evidence) =>
                    evidence.evidence_id ===
                    selectedEvidenceId.value,
            ) ?? null
        );
    });

function selectEvidence(
    evidenceId: string,
): void {
    selectedEvidenceId.value =
        evidenceId;
}

function openEvidenceInReading(): void {
    if (!selectedEvidence.value) return;

    goToReading(
        selectedEvidence.value.document_id,
        selectedEvidence.value.location,
    );
}

function closeEvidence(): void {
    selectedEvidenceId.value =
        null;
}
</script>

<template>
    <section
        id="result-view"
        class="view"
    >
        <header class="topbar">
            <h2
                class="sticky-query"
            >
                {{
                    investigation
                        ?.original_query ??
                    "Pesquisa"
                }}
            </h2>
        </header>

        <main class="layout-grid">
            <section class="answer-section">
                <h3
                    style="
                        font-size: 1.8rem;
                        font-weight: 600;
                        color: var(--text-main);
                        margin-bottom: 20px;
                    "
                >
                    Síntese:
                </h3>

                <div
                    v-if="isInvestigating"
                    id="loading-state"
                >
                    <div class="spinner"></div>

                    <p
                        class="live-logs"
                    >
                        Processando investigação...
                    </p>
                </div>

                <p
                    v-else-if="error"
                    class="home-error"
                >
                    {{ error }}
                </p>

                <div
                    v-else-if="response"
                    id="answer-box"
                >
                    <div id="answer-text">
                        <p>
                            {{
                                response.content
                            }}
                        </p>

                        <section
                            v-for="(
                                section,
                                index
                            ) in sections"
                            :key="index"
                            style="
                                margin-top: 24px;
                            "
                        >
                            <h4
                                v-if="
                                    typeof section.title ===
                                    'string'
                                "
                                style="
                                    font-size: 1.1rem;
                                    font-weight: 600;
                                    color: var(--text-main);
                                    margin-bottom: 10px;
                                "
                            >
                                {{
                                    section.title
                                }}
                            </h4>

                            <p
                                v-if="
                                    typeof section.content ===
                                    'string'
                                "
                            >
                                {{
                                    section.content
                                }}
                            </p>
                        </section>
                    </div>

                    <div
                        id="sources-section"
                        style="
                            margin-top: 40px;
                            padding-top: 20px;
                            border-top: 1px solid var(--border-color);
                        "
                    >
                        <h3
                            style="
                                font-size: 1.1rem;
                                color: var(--text-main);
                                font-weight: 600;
                                margin-bottom: 15px;
                            "
                        >
                            Referências do Acervo
                        </h3>

                        <div
                            id="sources-container"
                        >
                            <button
                                v-for="(
                                    evidence,
                                    index
                                ) in referencedEvidences"
                                :key="
                                    evidence.evidence_id ??
                                    evidence.unit_id
                                "
                                class="btn-outline"
                                style="
                                    width: 100%;
                                    justify-content: flex-start;
                                    margin-bottom: 8px;
                                    text-align: left;
                                "
                                type="button"
                                @click="
                                    evidence.evidence_id &&
                                    selectEvidence(
                                        evidence.evidence_id,
                                    )
                                "
                            >
                                Evidência
                                {{ index + 1 }}
                            </button>

                            <p
                                v-if="
                                    referencedEvidences.length ===
                                    0
                                "
                                style="
                                    color: var(--text-muted);
                                    font-size: 0.9rem;
                                "
                            >
                                Nenhuma evidência foi
                                associada à resposta.
                            </p>
                        </div>
                    </div>
                </div>

                <p
                    v-else
                    style="
                        color: var(--text-muted);
                    "
                >
                    Nenhuma resposta disponível.
                </p>
            </section>

            <EvidencePanel
                :evidence="selectedEvidence"
                @close="closeEvidence"
                @open-reading="openEvidenceInReading"
            />
        </main>
    </section>
</template>