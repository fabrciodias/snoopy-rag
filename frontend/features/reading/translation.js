import {
    translateText,
} from "../../infrastructure/api.js";


const translatedBlocks =
    new WeakMap();


function createButton(
    text
) {
    const button =
        document.createElement(
            "button"
        );

    button.type =
        "button";

    button.className =
        "btn-outline reading-translation-button";

    button.textContent =
        text;

    button.style.width =
        "fit-content";

    button.style.padding =
        "4px 10px";

    button.style.fontSize =
        "0.75rem";

    button.style.marginTop =
        "8px";

    return button;
}


function addTranslationControl(
    paragraph
) {
    if (
        !paragraph ||
        paragraph.dataset.translationReady ===
            "true"
    ) {
        return;
    }

    const originalText =
        paragraph.textContent?.trim();

    if (!originalText) {
        return;
    }

    paragraph.dataset.translationReady =
        "true";

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "reading-translation-controls";

    wrapper.style.display =
        "flex";

    wrapper.style.gap =
        "8px";

    wrapper.style.alignItems =
        "center";

    const translateButton =
        createButton(
            "Traduzir"
        );

    const status =
        document.createElement(
            "span"
        );

    status.className =
        "evidence-subtitle";

    status.textContent =
        "";

    wrapper.append(
        translateButton,
        status
    );

    paragraph.insertAdjacentElement(
        "afterend",
        wrapper
    );

    translatedBlocks.set(
        paragraph,
        {
            original:
                originalText,
            translated:
                null,
            showingTranslation:
                false,
        }
    );

    translateButton.addEventListener(
        "click",
        async () => {
            const state =
                translatedBlocks.get(
                    paragraph
                );

            if (!state) {
                return;
            }

            if (
                state.showingTranslation
            ) {
                paragraph.textContent =
                    state.original;

                state.showingTranslation =
                    false;

                translateButton.textContent =
                    "Traduzir";

                status.textContent =
                    "";

                return;
            }

            if (
                state.translated
            ) {
                paragraph.textContent =
                    state.translated;

                state.showingTranslation =
                    true;

                translateButton.textContent =
                    "Ver original";

                status.textContent =
                    "Tradução";

                return;
            }

            translateButton.disabled =
                true;

            status.textContent =
                "Traduzindo...";

            try {
                const translation =
                    await translateText(
                        state.original
                    );

                state.translated =
                    translation;

                state.showingTranslation =
                    true;

                paragraph.textContent =
                    translation;

                translateButton.textContent =
                    "Ver original";

                status.textContent =
                    "Tradução";

            } catch (error) {
                console.error(
                    "[TRANSLATION]",
                    error
                );

                status.textContent =
                    `Erro: ${error.message}`;

            } finally {
                translateButton.disabled =
                    false;
            }
        }
    );
}


function scanReadingBlocks() {
    const readingContent =
        document.getElementById(
            "reading-content"
        );

    if (!readingContent) {
        return;
    }

    const paragraphs =
        readingContent.querySelectorAll(
            ".reading-chunk"
        );

    paragraphs.forEach(
        addTranslationControl
    );
}


function initializeTranslationObserver() {
    scanReadingBlocks();

    const readingContent =
        document.getElementById(
            "reading-content"
        );

    if (!readingContent) {
        return;
    }

    const observer =
        new MutationObserver(
            () => {
                scanReadingBlocks();
            }
        );

    observer.observe(
        readingContent,
        {
            childList:
                true,
            subtree:
                true,
        }
    );
}


if (
    document.readyState ===
    "loading"
) {
    document.addEventListener(
        "DOMContentLoaded",
        initializeTranslationObserver,
        {
            once:
                true,
        }
    );
} else {
    initializeTranslationObserver();
}