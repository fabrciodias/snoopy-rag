export const dom = {
    layoutGrid:
        document.querySelector(
            ".layout-grid"
        ),

    mobileOverlay:
        document.getElementById(
            "mobile-overlay"
        ),

    sidebar:
        document.querySelector(
            ".sidebar"
        ),

    sidebarToggle:
        document.getElementById(
            "btn-sidebar-toggle"
        ),

    logoBtn:
        document.getElementById(
            "logo-btn"
        ),

    btnSidebarNew:
        document.getElementById(
            "btn-sidebar-new"
        ),

    btnMobileMenu:
        document.getElementById(
            "btn-mobile-menu"
        ),

    btnLogin:
        document.getElementById(
            "btn-login"
        ),

    userInfo:
        document.getElementById(
            "user-info"
        ),

    userName:
        document.querySelector(
            ".user-name"
        ),

    userAvatar:
        document.getElementById(
            "user-avatar"
        ),

    folderContainer:
        document.getElementById(
            "folder-container"
        ),

    folderSelector:
        document.getElementById(
            "folder-selector"
        ),

    btnDrive:
        document.getElementById(
            "btn-drive"
        ),

    btnSync:
        document.getElementById(
            "btn-sync"
        ),

    syncLogs:
        document.getElementById(
            "sync-logs"
        ),

    syncProgressContainer:
        document.getElementById(
            "sync-progress-container"
        ),

    syncGlobalStatus:
        document.getElementById(
            "sync-global-status"
        ),

    syncJobsList:
        document.getElementById(
            "sync-jobs-list"
        ),

    btnToggleSync:
        document.getElementById(
            "btn-toggle-sync"
        ),

    historyList:
        document.getElementById(
            "history-list"
        ),

    homeView:
        document.getElementById(
            "home-view"
        ),

    homeForm:
        document.getElementById(
            "search-home"
        ),

    inputHome:
        document.getElementById(
            "input-home"
        ),

    resultView:
        document.getElementById(
            "result-view"
        ),

    queryDisplay:
        document.getElementById(
            "query-title"
        ),

    loadingState:
        document.getElementById(
            "loading-state"
        ),

    liveLogs:
        document.getElementById(
            "live-logs"
        ),

    answerBox:
        document.getElementById(
            "answer-box"
        ),

    answerText:
        document.getElementById(
            "answer-text"
        ),

    sourcesContainer:
        document.getElementById(
            "sources-container"
        ),

    chunksContainer:
        document.getElementById(
            "chunks-container"
        ),

    chunkAbnt:
        document.getElementById(
            "chunk-abnt"
        ),

    btnCloseEvidence:
        document.getElementById(
            "btn-close-evidence"
        ),

    readingView:
        document.getElementById(
            "reading-view"
        ),

    btnCloseReading:
        document.getElementById(
            "btn-close-reading"
        ),

    readingTitle:
        document.getElementById(
            "reading-title"
        ),

    readingOriginalLink:
        document.getElementById(
            "reading-original-link"
        ),

    readingContent:
        document.getElementById(
            "reading-content"
        ),

    settingsModal:
        document.getElementById(
            "settings-modal"
        ),

    btnSettings:
        document.getElementById(
            "btn-settings"
        ),

    btnCloseModal:
        document.getElementById(
            "btn-close-modal"
        ),

    btnLogout:
        document.getElementById(
            "btn-logout"
        ),

    btnRemoveFolder:
        document.getElementById(
            "btn-remove-folder"
        ),

    themeToggle:
        document.getElementById(
            "btn-theme-toggle"
        ),
};


/* ============================================================
   Navegação
   ============================================================ */

export function showHome() {
    dom.homeView.classList.add(
        "active"
    );

    dom.resultView.classList.remove(
        "active"
    );

    dom.readingView.classList.remove(
        "active"
    );

    dom.layoutGrid.classList.remove(
        "evidence-active"
    );

    dom.mobileOverlay.classList.remove(
        "active"
    );
}


export function showInvestigation(
    query
) {
    dom.homeView.classList.remove(
        "active"
    );

    dom.readingView.classList.remove(
        "active"
    );

    dom.resultView.classList.add(
        "active"
    );

    dom.layoutGrid.classList.remove(
        "evidence-active"
    );

    dom.mobileOverlay.classList.remove(
        "active"
    );

    dom.queryDisplay.textContent =
        query;

    /*
     * Limpa completamente a investigação anterior
     * antes de iniciar uma nova.
     */
    dom.answerText.textContent =
        "";

    dom.answerText.className =
        "";

    dom.sourcesContainer.innerHTML =
        "";

    dom.chunksContainer.innerHTML =
        "";

    dom.answerBox.classList.add(
        "hidden"
    );

    dom.loadingState.classList.remove(
        "hidden"
    );

    dom.liveLogs.textContent =
        "Investigando o acervo...";
}


export function showInvestigationError(
    message
) {
    dom.loadingState.classList.add(
        "hidden"
    );

    dom.sourcesContainer.innerHTML =
        "";

    dom.chunksContainer.innerHTML =
        "";

    dom.answerBox.classList.remove(
        "hidden"
    );

    dom.answerText.textContent =
        `Erro: ${message}`;

    dom.answerText.className =
        "error-text";
}


export function openEvidencePanel() {
    dom.sidebar.classList.add(
        "collapsed"
    );

    dom.layoutGrid.classList.add(
        "evidence-active"
    );

    dom.mobileOverlay.classList.add(
        "active"
    );
}


export function closeEvidencePanel() {
    dom.layoutGrid.classList.remove(
        "evidence-active"
    );

    dom.mobileOverlay.classList.remove(
        "active"
    );
}


export function openReading() {
    dom.resultView.classList.remove(
        "active"
    );

    dom.readingView.classList.add(
        "active"
    );
}


export function closeReading() {
    dom.readingView.classList.remove(
        "active"
    );

    dom.resultView.classList.add(
        "active"
    );
}


/* ============================================================
   Histórico
   ============================================================ */

export function renderHistory(
    history,
    onSelect
) {
    dom.historyList.innerHTML =
        "";

    if (!history.length) {
        const empty =
            document.createElement(
                "p"
            );

        empty.className =
            "history-empty";

        empty.textContent =
            "Nenhuma pesquisa recente.";

        dom.historyList.appendChild(
            empty
        );

        return;
    }

    history.forEach(
        entry => {
            /*
             * O backend V3 retorna objetos:
             *
             * {
             *   query,
             *   created_at
             * }
             *
             * O renderer também aceita strings para
             * manter compatibilidade com respostas antigas.
             */
            const query =
                typeof entry === "string"
                    ? entry
                    : entry?.query || "";

            if (!query) {
                return;
            }

            const item =
                document.createElement(
                    "div"
                );

            item.className =
                "history-item";

            const icon =
                document.createElement(
                    "span"
                );

            icon.className =
                "history-icon";

            icon.textContent =
                "◷";

            const text =
                document.createTextNode(
                    ` ${query}`
                );

            item.append(
                icon,
                text
            );

            item.addEventListener(
                "click",
                () => onSelect(query)
            );

            dom.historyList.appendChild(
                item
            );
        }
    );
}


/* ============================================================
   Acervos
   ============================================================ */

export function renderFolders(
    folders,
    selectedId
) {
    dom.folderSelector.innerHTML =
        "";

    for (
        const folder of folders
    ) {
        const option =
            document.createElement(
                "option"
            );

        option.value =
            folder.id;

        option.textContent =
            folder.name;

        if (
            folder.id ===
            selectedId
        ) {
            option.selected =
                true;
        }

        dom.folderSelector.appendChild(
            option
        );
    }

    dom.folderContainer.classList.remove(
        "hidden"
    );
}


/* ============================================================
   Sincronização
   ============================================================ */

export function setSyncState(
    message
) {
    dom.syncLogs.textContent =
        message;
}


export function setSyncOperationState(
    operation
) {
    dom.syncProgressContainer.classList.remove(
        "hidden"
    );

    const status =
        String(
            operation?.status || ""
        ).toUpperCase();

    if (
        status === "PROCESSING"
    ) {
        dom.syncGlobalStatus.textContent =
            "Sincronizando acervo...";
    } else if (
        status === "PENDING"
    ) {
        dom.syncGlobalStatus.textContent =
            "Sincronização aguardando execução...";
    } else if (
        status === "COMPLETED"
    ) {
        dom.syncGlobalStatus.textContent =
            "Sincronização concluída.";
    } else if (
        status === "FAILED"
    ) {
        dom.syncGlobalStatus.textContent =
            "Falha na sincronização.";
    } else if (
        status === "CANCELLED"
    ) {
        dom.syncGlobalStatus.textContent =
            "Sincronização cancelada.";
    } else {
        dom.syncGlobalStatus.textContent =
            "Atualizando sincronização...";
    }

    dom.syncJobsList.innerHTML =
        "";

    const item =
        document.createElement(
            "div"
        );

    item.className =
        "sync-job-item";

    const info =
        document.createElement(
            "div"
        );

    info.className =
        "sync-job-info";

    const label =
        document.createElement(
            "span"
        );

    label.className =
        "sync-job-filename";

    label.textContent =
        "Sincronização do acervo";

    const state =
        document.createElement(
            "span"
        );

    state.className =
        "sync-job-percentage";

    state.textContent =
        status;

    info.append(
        label,
        state
    );

    item.appendChild(
        info
    );

    dom.syncJobsList.appendChild(
        item
    );
}