<script setup lang="ts">
import EvidencePanel from "../evidence/EvidencePanel.vue";
</script>

<template>
    <section
        id="result-view"
        class="view"
    >
        <header class="topbar">
            <h2
                id="query-title"
                class="sticky-query"
            ></h2>
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
                    id="loading-state"
                    class="hidden"
                >
                    <div class="spinner"></div>

                    <p
                        id="live-logs"
                        class="live-logs"
                    >
                        Iniciando motor...
                    </p>
                </div>

                <div
                    id="answer-box"
                    class="hidden"
                >
                    <div id="answer-text"></div>

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

                        <div id="sources-container"></div>
                    </div>
                </div>
            </section>

            <EvidencePanel />
        </main>
    </section>
</template>