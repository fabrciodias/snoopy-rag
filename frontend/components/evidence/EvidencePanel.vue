<script setup lang="ts">
import {
    computed,
} from "vue";

import {
    BookOpen,
    X,
} from "@lucide/vue";

import type {
    Evidence,
    DocumentReference,
} from "../../features/investigation/contracts";

const props = defineProps<{
    evidence: Evidence | null;
    reference: DocumentReference | null;
}>();

const emit = defineEmits<{
    (event: "close"): void;
    (event: "open-reading"): void;
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

const bibliographicReference =
    computed(() => {
        if (!props.reference) {
            return "Metadados indisponíveis.";
        }

        const authors =
            props.reference.authors?.trim() ||
            "AUTOR DESCONHECIDO";

        const title =
            props.reference.title?.trim() ||
            "Título não informado";

        const year =
            props.reference.publication_year ??
            "s.d.";

        return `${authors.toUpperCase()}. ${title}. ${year}.`;
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
                <X />
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
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            gap: 12px;
                            margin-bottom: 10px;
                        "
                    >
                        <div
                            style="
                                font-size: 0.8rem;
                                color: var(--text-muted);
                            "
                        >
                            Evidência
                        </div>

                        <button
                            type="button"
                            class="btn-outline"
                            style="
                                width: fit-content;
                                padding: 6px 10px;
                                font-size: 0.78rem;
                                flex-shrink: 0;
                            "
                            @click="emit('open-reading')"
                        >
                            <BookOpen class="icon-sm" />

                            Ler no Contexto
                        </button>
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
                        <strong
                            style="
                                color: var(--text-main);
                                line-height: 1.5;
                            "
                        >
                            {{ 
                                bibliographicReference
                            }}
                        </strong>

                        <span
                            v-if="locationLabel"
                        >
                            {{ locationLabel }}
                        </span>
                    </div>
                </div>
            </article>
        </template>
    </aside>
</template>