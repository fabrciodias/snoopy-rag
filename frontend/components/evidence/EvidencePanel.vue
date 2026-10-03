<script setup lang="ts">
import {
    computed,
} from "vue";

import type {
    Evidence,
} from "../../features/investigation/contracts";

const props = defineProps<{
    evidence: Evidence | null;
}>();

const emit = defineEmits<{
    close: [];
}>();

const location =
    computed(() => {
        if (!props.evidence) {
            return null;
        }

        return props.evidence.location;
    });

const locationLabel =
    computed(() => {
        if (!location.value) {
            return "";
        }

        const parts: string[] = [];

        if (
            location.value.start_page !== null
        ) {
            if (
                location.value.end_page !== null &&
                location.value.end_page !==
                    location.value.start_page
            ) {
                parts.push(
                    `p. ${location.value.start_page}–${location.value.end_page}`,
                );
            } else {
                parts.push(
                    `p. ${location.value.start_page}`,
                );
            }
        }

        if (
            location.value.start_block !== null
        ) {
            if (
                location.value.end_block !== null &&
                location.value.end_block !==
                    location.value.start_block
            ) {
                parts.push(
                    `blocos ${location.value.start_block}–${location.value.end_block}`,
                );
            } else {
                parts.push(
                    `bloco ${location.value.start_block}`,
                );
            }
        }

        return parts.join(" · ");
    });
</script>

<template>
    <aside class="evidence-section">
        <div class="bottom-sheet-handle"></div>

        <div
            class="evidence-sticky-header"
            style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: sticky;
                top: -24px;
                background-color: var(--bg-panel);
                border-bottom: 1px solid var(--border-color);
                z-index: 10;
                padding: 24px 24px 10px 24px;
                margin: -24px -24px 15px -24px;
            "
        >
            <h3
                style="
                    font-size: 1.05rem;
                    font-weight: 600;
                    color: var(--text-main);
                    margin: 0;
                "
            >
                Trecho Original
            </h3>

            <button
                class="btn-icon"
                title="Fechar painel"
                type="button"
                style="margin-right: -8px;"
                @click="emit('close')"
            >
                <i data-lucide="x"></i>
            </button>
        </div>

        <div
            v-if="!evidence"
            style="
                color: var(--text-muted);
                font-size: 0.9rem;
                padding: 10px 0;
            "
        >
            Selecione uma evidência para
            visualizar o trecho recuperado.
        </div>

        <template v-else>
            <article
                id="chunks-container"
            >
                <div
                    style="
                        margin-bottom: 20px;
                    "
                >
                    <div
                        style="
                            font-size: 0.8rem;
                            color: var(--text-muted);
                            margin-bottom: 8px;
                        "
                    >
                        Evidência
                    </div>

                    <blockquote
                        style="
                            margin: 0;
                            padding: 16px;
                            border-left: 3px solid var(--primary);
                            background: var(--bg-hover);
                            border-radius: var(--radius-sm);
                            color: var(--text-main);
                            line-height: 1.7;
                        "
                    >
                        {{ evidence.content }}
                    </blockquote>
                </div>

                <div
                    v-if="evidence.context"
                    style="
                        margin-top: 24px;
                    "
                >
                    <div
                        style="
                            font-size: 0.8rem;
                            color: var(--text-muted);
                            margin-bottom: 8px;
                        "
                    >
                        Contexto documental
                    </div>

                    <div
                        style="
                            color: var(--text-muted);
                            line-height: 1.6;
                            white-space: pre-line;
                        "
                    >
                        {{
                            evidence.context
                        }}
                    </div>
                </div>

                <div
                    style="
                        margin-top: 28px;
                        padding-top: 18px;
                        border-top: 1px solid var(--border-color);
                    "
                >
                    <div
                        style="
                            font-size: 0.8rem;
                            color: var(--text-muted);
                            margin-bottom: 10px;
                        "
                    >
                        Proveniência
                    </div>

                    <div
                        style="
                            display: flex;
                            flex-direction: column;
                            gap: 6px;
                            font-size: 0.82rem;
                            color: var(--text-muted);
                        "
                    >
                        <span
                            v-if="locationLabel"
                        >
                            {{ locationLabel }}
                        </span>

                        <span>
                            Documento:
                            {{
                                evidence.document_id
                            }}
                        </span>

                        <span>
                            Representação:
                            {{
                                evidence
                                    .provenance
                                    .representation_id
                            }}
                        </span>
                    </div>
                </div>
            </article>

            <p
                id="chunk-abnt"
                class="evidence-subtitle"
                style="
                    font-size: 0.82rem;
                    color: var(--text-muted);
                    font-family: monospace;
                    margin-top: 15px;
                    border-top: 1px dashed var(--border-color);
                    padding-top: 15px;
                "
            >
                Evidência:
                {{
                    evidence.evidence_id ??
                    "sem identificador"
                }}
            </p>
        </template>
    </aside>
</template>