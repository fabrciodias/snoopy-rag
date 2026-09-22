import {
    openEvidencePanel,
} from "../renderer/render.js";


export function renderEvidencePanel(
    evidence,
    onRead
) {
    const container =
        document.getElementById(
            "chunks-container"
        );

    container.innerHTML =
        "";

    if (!evidence) {
        return;
    }

    const card =
        document.createElement(
            "div"
        );

    card.className =
        "chunk-card active-chunk";

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

    title.textContent =
        "Evidência";

    const button =
        document.createElement(
            "button"
        );

    button.className =
        "btn-outline";

    button.style.width =
        "fit-content";

    button.style.padding =
        "4px 10px";

    button.style.fontSize =
        "0.75rem";

    button.textContent =
        "Ler no Contexto";

    button.addEventListener(
        "click",
        () => onRead(evidence)
    );

    header.append(
        title,
        button
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

    const provenance =
        document.createElement(
            "p"
        );

    provenance.className =
        "evidence-subtitle";

    const location =
        evidence.location || {};

    const page =
        location.page ??
        location.page_number;

    provenance.textContent =
        page
            ? `Documento: ${evidence.document_id} · Página: ${page}`
            : `Documento: ${evidence.document_id}`;

    card.append(
        header,
        text,
        provenance
    );

    container.appendChild(
        card
    );

    document.getElementById(
        "chunk-abnt"
    ).textContent =
        `Proveniência: ${evidence.evidence_id}`;

    openEvidencePanel();
}