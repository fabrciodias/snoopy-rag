import {
    translateText,
} from "../../infrastructure/api.js";


export function addTranslationControl(
    chunkDiv,
    textSpan,
    originalText
) {
    if (
        !chunkDiv ||
        !textSpan ||
        !originalText?.trim()
    ) {
        return;
    }

    const btnTranslate =
        document.createElement("button");

    btnTranslate.type =
        "button";

    btnTranslate.className =
        "btn-translate-chunk";

    btnTranslate.title =
        "Traduzir este parágrafo";

    btnTranslate.innerHTML =
        `<i data-lucide="languages"
            style="width: 15px; height: 15px;">
        </i>`;

    chunkDiv.appendChild(
        btnTranslate
    );

    btnTranslate.addEventListener(
        "click",
        async event => {
            event.stopPropagation();

            if (
                chunkDiv.classList.contains(
                    "translating-pulse"
                )
            ) {
                return;
            }

            chunkDiv.classList.add(
                "translating-pulse"
            );

            btnTranslate.style.opacity =
                "0";

            try {
                const translation =
                    await translateText(
                        originalText
                    );

                const translatedClean =
                    String(
                        translation || ""
                    ).replace(
                        /\*\*(.*?)\*\*/g,
                        "<strong>$1</strong>"
                    );

                textSpan.innerHTML =
                    `<strong style="color: var(--primary);">
                        [Tradução Original]:
                    </strong>

                    ${translatedClean}`;

                textSpan.style.color =
                    "var(--text-main)";

            } catch (error) {
                console.error(
                    "[TRANSLATION]",
                    error
                );

                alert(
                    "Incapaz de obter tradução da inteligência central. Tente novamente."
                );

                btnTranslate.style.opacity =
                    "1";

            } finally {
                chunkDiv.classList.remove(
                    "translating-pulse"
                );
            }
        }
    );

    if (window.lucide) {
        window.lucide.createIcons();
    }
}