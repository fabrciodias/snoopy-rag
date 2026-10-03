<script setup lang="ts">
</script>

<template>
    <section
        id="reading-view"
        class="view"
    >
        <header class="topbar reading-topbar">
            <div class="topbar-side">
                <button
                    id="btn-close-reading"
                    class="btn-icon btn-reading-action"
                    title="Voltar para a pesquisa"
                >
                    <i data-lucide="arrow-left"></i>

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
                    Título do Documento
                </h2>
            </div>

            <div class="topbar-side right">
                <a
                    id="reading-original-link"
                    href="#"
                    target="_blank"
                    class="btn-outline btn-reading-action"
                    title="Abrir PDF Original"
                >
                    <i
                        data-lucide="external-link"
                        class="icon-sm"
                    ></i>

                    <span class="hide-mobile">
                        PDF
                    </span>
                </a>
            </div>
        </header>

        <main class="reading-layout">
            <div
                id="reading-content"
                class="reading-container"
            ></div>
        </main>
    </section>
</template>