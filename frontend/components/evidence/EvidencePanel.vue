<script setup lang="ts">
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
                id="btn-close-evidence"
                class="btn-icon"
                title="Fechar painel"
                style="margin-right: -8px;"
            >
                <i data-lucide="x"></i>
            </button>
        </div>

        <div id="chunks-container"></div>

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
            Aguardando metadados da fonte...
        </p>
    </aside>
</template>