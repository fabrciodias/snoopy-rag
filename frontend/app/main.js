import {
    appState,
    PUBLIC_FOLDER_ID,
} from "../state/application.js";

import {
    initAuth,
    login,
    logout,
    loadGooglePicker,
} from "../infrastructure/auth.js";

import {
    fetchFolders,
    createFolder,
    disconnectFolder,
    startSync,
    waitForOperation,
    fetchDocument,
    fetchHistory,
} from "../infrastructure/api.js";

import {
    dom,
    showHome,
    closeEvidencePanel,
    closeReading,
    renderHistory,
    renderFolders,
    setSyncState,
    setSyncOperationState,
} from "../renderer/render.js";

import {
    createInvestigationController,
} from "../features/investigation/controller.js";

import {
    renderEvidencePanel,
} from "../components/EvidencePanel.js";

import {
    addTranslationControl,
} from "../features/reading/translation.js";


const investigation =
    createInvestigationController();


/* ============================================================
   Lucide
   ============================================================ */

if (window.lucide) {
    lucide.createIcons();
}

/* ============================================================
   Tema
   ============================================================ */

const savedTheme =
    localStorage.getItem(
        "snoopy_theme"
    );

if (
    savedTheme === "light"
) {
    document.body.classList.add(
        "light-theme"
    );
}


function updateThemeButton() {
    if (!dom.themeToggle) {
        return;
    }

    const isLight =
        document.body.classList.contains(
            "light-theme"
        );

    dom.themeToggle.innerHTML = `
        <i data-lucide="${
            isLight
                ? "sun"
                : "moon"
        }" class="icon-sm"></i>
        <span class="nav-title" style="font-size: 0.85rem;">
            Tema
        </span>
    `;

    if (window.lucide) {
        lucide.createIcons();
    }
}


dom.themeToggle?.addEventListener(
    "click",
    () => {
        const light =
            document.body.classList.toggle(
                "light-theme"
            );

        localStorage.setItem(
            "snoopy_theme",
            light
                ? "light"
                : "dark"
        );

        updateThemeButton();
    }
);

updateThemeButton();

/* ============================================================
   Acervos
   ============================================================ */

async function loadFolders() {
    const folders =
        await fetchFolders();

    appState.folders =
        Array.isArray(folders)
            ? folders
            : [];

    const selectedExists =
        appState.folders.some(
            folder =>
                folder.id ===
                appState.folderId
        );

    /*
     * Ao restaurar uma sessão, o estado inicial da V3
     * aponta para o acervo público.
     *
     * Se o usuário possui um acervo privado ativo,
     * /folders/ já o devolveu do Supabase.
     *
     * Restauramos esse acervo automaticamente,
     * reproduzindo o comportamento da V2.
     */
    if (
        appState.folderId ===
            PUBLIC_FOLDER_ID &&
        !selectedExists
    ) {
        const privateFolder =
            appState.folders.find(
                folder =>
                    folder.id !==
                    PUBLIC_FOLDER_ID
            );

        if (privateFolder) {
            appState.folderId =
                privateFolder.id;
        }
    }

    const selected =
        appState.folders.find(
            folder =>
                folder.id ===
                appState.folderId
        );

    if (!selected) {
        appState.folderId =
            PUBLIC_FOLDER_ID;
    }

    const finalSelected =
        appState.folders.find(
            folder =>
                folder.id ===
                appState.folderId
        );

    appState.folderName =
        finalSelected?.name ||
        "Acervo Público";

    renderFolders(
        appState.folders,
        appState.folderId
    );

    updateFolderControls();
}


function updateFolderControls() {
    const isPublic =
        appState.folderId ===
        PUBLIC_FOLDER_ID;

    const loggedIn =
        Boolean(
            appState.user
        );

    if (!loggedIn) {
        dom.btnDrive?.classList.add(
            "hidden"
        );

        dom.btnSync?.classList.add(
            "hidden"
        );

        dom.btnRemoveFolder?.classList.add(
            "hidden"
        );

        return;
    }

    /*
     * Acervo público:
     *
     * - pode conectar uma pasta privada;
     * - não pode sincronizar;
     * - não pode desconectar o público.
     *
     * O botão de desconectar permanece dentro
     * das Configurações.
     */
    if (isPublic) {
        dom.btnDrive?.classList.remove(
            "hidden"
        );

        dom.btnSync?.classList.add(
            "hidden"
        );

        dom.btnRemoveFolder?.classList.add(
            "hidden"
        );

        return;
    }

    /*
     * Acervo privado:
     *
     * - "Conectar Pasta Privada" desaparece;
     * - sincronização aparece;
     * - desconectar permanece disponível
     *   dentro das Configurações.
     */
    dom.btnDrive?.classList.add(
        "hidden"
    );

    dom.btnSync?.classList.remove(
        "hidden"
    );

    dom.btnRemoveFolder?.classList.remove(
        "hidden"
    );
}


dom.folderSelector?.addEventListener(
    "change",
    event => {
        appState.folderId =
            event.target.value;

        const selected =
            appState.folders.find(
                folder =>
                    folder.id ===
                    appState.folderId
            );

        appState.folderName =
            selected?.name ||
            "Acervo";

        updateFolderControls();
    }
);

/* ============================================================
   Google Picker
   ============================================================ */

async function openDrivePicker() {
    if (
        !appState.googleToken
    ) {
        alert(
            "A sessão do Google Drive expirou. Faça login novamente."
        );

        return;
    }

    if (
        !appState.pickerApiLoaded
    ) {
        await loadGooglePicker();
    }

    const view =
        new google.picker.DocsView()
            .setIncludeFolders(true)
            .setMimeTypes(
                "application/vnd.google-apps.folder"
            )
            .setSelectFolderEnabled(
                true
            );

    const picker =
        new google.picker.PickerBuilder()
            .addView(view)
            .setOAuthToken(
                appState.googleToken
            )
            .setDeveloperKey(
                appState.googleApiKey
            )
            .setAppId(
                appState.googleAppId
            )
            .setOrigin(
                window.location.origin
            )
            .setCallback(
                async data => {
                    if (
                        data.action !==
                        google.picker.Action.PICKED
                    ) {
                        return;
                    }

                    const folder =
                        data.docs?.[0];

                    if (!folder) {
                        return;
                    }

                    try {
                        const created =
                            await createFolder(
                                folder.name,
                                folder.id
                            );

                        await loadFolders();

                        if (created?.id) {
                            appState.folderId =
                                created.id;

                            appState.folderName =
                                created.name ||
                                folder.name;

                            renderFolders(
                                appState.folders,
                                created.id
                            );
                        }

                        updateFolderControls();

                    } catch (error) {
                        console.error(
                            "[PICKER]",
                            error
                        );

                        alert(
                            `Não foi possível vincular o acervo: ${error.message}`
                        );
                    }
                }
            )
            .build();

    picker.setVisible(
        true
    );
}


dom.btnDrive?.addEventListener(
    "click",
    openDrivePicker
);

/* ============================================================
   Sincronização
   ============================================================ */

let syncBusy =
    false;

let syncHideTimer =
    null;


function showSyncProgress() {
    if (
        syncHideTimer
    ) {
        clearTimeout(
            syncHideTimer
        );

        syncHideTimer =
            null;
    }

    dom.syncProgressContainer.classList.remove(
        "hidden"
    );

    dom.syncProgressContainer.classList.add(
        "expanded"
    );
}


function hideSyncProgress(
    delay = 5000
) {
    if (
        syncHideTimer
    ) {
        clearTimeout(
            syncHideTimer
        );
    }

    syncHideTimer =
        setTimeout(
            () => {
                dom.syncLogs.textContent =
                    "";

                dom.syncProgressContainer.classList.remove(
                    "expanded"
                );

                dom.syncProgressContainer.classList.add(
                    "hidden"
                );

                syncHideTimer =
                    null;
            },
            delay
        );
}


dom.btnSync?.addEventListener(
    "click",
    async () => {
        if (syncBusy) {
            return;
        }

        if (
            appState.folderId ===
            PUBLIC_FOLDER_ID
        ) {
            return;
        }

        if (
            !appState.googleToken
        ) {
            alert(
                "A sessão do Google Drive expirou. Faça login novamente."
            );

            return;
        }

        syncBusy =
            true;

        dom.btnSync.disabled =
            true;

        try {
            setSyncState(
                "Iniciando sincronização..."
            );

            showSyncProgress();

            const operation =
                await startSync(
                    appState.folderId,
                    appState.googleToken
                );

            setSyncOperationState(
                operation
            );

            const finished =
                await waitForOperation(
                    operation.operation_id,
                    {
                        onUpdate:
                            operation => {
                                setSyncOperationState(
                                    operation
                                );
                            },
                    }
                );

            setSyncState(
                "Sincronização concluída."
            );

            setSyncOperationState(
                finished
            );

            await loadFolders();

            hideSyncProgress(
                5000
            );

        } catch (error) {
            setSyncState(
                "Falha na sincronização."
            );

            showSyncProgress();

            alert(
                error.message
            );

        } finally {
            syncBusy =
                false;

            dom.btnSync.disabled =
                false;
        }
    }
);

/* ============================================================
   Investigação
   ============================================================ */

async function executeSearch(
    query
) {
    const normalizedQuery =
        String(
            query || ""
        ).trim();

    if (!normalizedQuery) {
        return;
    }

    if (
        window.innerWidth <=
        850
    ) {
        dom.sidebar.classList.remove(
            "mobile-open"
        );

        dom.mobileOverlay.classList.remove(
            "active"
        );
    }

    try {
        await investigation.execute(
            normalizedQuery
        );
    } catch {
        /*
         * O controller já renderizou o erro.
         */
    }
}


dom.homeForm?.addEventListener(
    "submit",
    event => {
        event.preventDefault();

        executeSearch(
            dom.inputHome.value
        );
    }
);

/* ============================================================
   Histórico
   ============================================================ */

async function reloadHistory() {
    if (!appState.user) {
        renderHistory(
            [],
            executeSearch
        );

        dom.historyList.innerHTML =
            "<p class=\"history-empty\">Faça login para ver o seu histórico.</p>";

        return;
    }

    try {
        const history =
            await fetchHistory();

        renderHistory(
            history,
            executeSearch
        );

    } catch (error) {
        console.error(
            "[HISTORY]",
            error
        );

        dom.historyList.innerHTML =
            "<p class=\"history-empty\">Não foi possível carregar o histórico.</p>";
    }
}

/* ============================================================
   Autenticação
   ============================================================ */

async function handleSession(
    session
) {
    appState.session =
        session;

    appState.user =
        session?.user || null;

    appState.userToken =
        session?.access_token ||
        null;

    if (session?.provider_token) {
        appState.googleToken =
            session.provider_token;

        localStorage.setItem(
            "snoopy_g_token",
            session.provider_token
        );
    } else {
        appState.googleToken =
            localStorage.getItem(
                "snoopy_g_token"
            );
    }

    if (!session) {
        closeSettings();
    }

    if (session) {
        dom.btnLogin?.classList.add(
            "hidden"
        );

        dom.userInfo?.classList.remove(
            "hidden"
        );

        const metadata =
            session.user
                ?.user_metadata ||
            {};

        dom.userName.textContent =
            metadata.full_name ||
            metadata.name ||
            session.user.email ||
            "Usuário";

        dom.userAvatar.src =
            metadata.avatar_url ||
            "";

        await loadFolders();

        await reloadHistory();

    } else {
        dom.btnLogin?.classList.remove(
            "hidden"
        );

        dom.userInfo?.classList.add(
            "hidden"
        );

        dom.btnDrive?.classList.add(
            "hidden"
        );

        dom.btnSync?.classList.add(
            "hidden"
        );

        dom.btnRemoveFolder?.classList.add(
            "hidden"
        );

        appState.folderId =
            PUBLIC_FOLDER_ID;

        appState.folders = [
            {
                id:
                    PUBLIC_FOLDER_ID,
                name:
                    "Acervo Público",
            },
        ];

        renderFolders(
            appState.folders,
            PUBLIC_FOLDER_ID
        );

        renderHistory(
            [],
            executeSearch
        );

        dom.historyList.innerHTML =
            "<p class=\"history-empty\">Faça login para ver o seu histórico.</p>";
    }
}


dom.btnLogin?.addEventListener(
    "click",
    async () => {
        try {
            await login();
        } catch (error) {
            alert(
                error.message
            );
        }
    }
);


dom.btnLogout?.addEventListener(
    "click",
    async () => {
        closeSettings();

        await logout();
    }
);

/* ============================================================
   Desconectar acervo
   ============================================================ */

dom.btnRemoveFolder?.addEventListener(
    "click",
    async () => {
        if (
            appState.folderId ===
            PUBLIC_FOLDER_ID
        ) {
            return;
        }

        const confirmed =
            window.confirm(
                "Deseja desconectar este acervo? Os documentos processados continuarão salvos."
            );

        if (!confirmed) {
            return;
        }

        try {
            await disconnectFolder(
                appState.folderId
            );

            appState.folderId =
                PUBLIC_FOLDER_ID;

            await loadFolders();

            closeSettings();

        } catch (error) {
            alert(
                error.message
            );
        }
    }
);

/* ============================================================
   Nova pesquisa / Home
   ============================================================ */

dom.btnSidebarNew?.addEventListener(
    "click",
    () => {
        showHome();
    }
);


dom.logoBtn?.addEventListener(
    "click",
    () => {
        if (
            dom.sidebar.classList.contains(
                "collapsed"
            )
        ) {
            dom.sidebar.classList.remove(
                "collapsed"
            );
        } else {
            showHome();
        }
    }
);

/* ============================================================
   Sidebar
   ============================================================ */

dom.sidebarToggle?.addEventListener(
    "click",
    () => {
        if (
            window.innerWidth <=
            850
        ) {
            dom.sidebar.classList.remove(
                "mobile-open"
            );

            dom.mobileOverlay.classList.remove(
                "active"
            );
        } else {
            dom.sidebar.classList.toggle(
                "collapsed"
            );
        }
    }
);


dom.btnMobileMenu?.addEventListener(
    "click",
    () => {
        dom.sidebar.classList.remove(
            "collapsed"
        );

        dom.sidebar.classList.add(
            "mobile-open"
        );

        dom.mobileOverlay.classList.add(
            "active"
        );
    }
);


dom.mobileOverlay?.addEventListener(
    "click",
    () => {
        dom.sidebar.classList.remove(
            "mobile-open"
        );

        closeEvidencePanel();

        dom.mobileOverlay.classList.remove(
            "active"
        );
    }
);

/* ============================================================
   Painel de sincronização
   ============================================================ */

dom.btnToggleSync?.addEventListener(
    "click",
    () => {
        dom.syncProgressContainer.classList.toggle(
            "expanded"
        );
    }
);

/* ============================================================
   Evidência
   ============================================================ */

dom.btnCloseEvidence?.addEventListener(
    "click",
    () => {
        closeEvidencePanel();
    }
);

/* ============================================================
   Reading
   ============================================================ */

function normalizeReadingText(
    text
) {
    return String(
        text || ""
    )
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
}


async function openReading(
    evidence
) {
    closeEvidencePanel();

    dom.resultView.classList.remove(
        "active"
    );

    dom.readingView.classList.add(
        "active"
    );

    dom.readingTitle.textContent =
        "Carregando documento...";

    dom.readingOriginalLink.classList.add(
        "hidden"
    );

    dom.readingContent.innerHTML =
        "";

    const loading =
        document.createElement(
            "p"
        );

    loading.textContent =
        "Recuperando a representação do documento...";

    loading.style.textAlign =
        "center";

    loading.style.marginTop =
        "60px";

    dom.readingContent.appendChild(
        loading
    );

    try {
        const documentData =
            await fetchDocument(
                evidence.document_id
            );

        dom.readingTitle.textContent =
            documentData.title ||
            "Documento";

        if (
            documentData.drive_link
        ) {
            dom.readingOriginalLink.href =
                documentData.drive_link;

            dom.readingOriginalLink.classList.remove(
                "hidden"
            );
        }

        renderDocumentRepresentation(
            documentData,
            evidence
        );

    } catch (error) {
        dom.readingContent.innerHTML =
            "";

        const message =
            document.createElement(
                "p"
            );

        message.textContent =
            `Não foi possível abrir o documento: ${error.message}`;

        message.style.textAlign =
            "center";

        message.style.marginTop =
            "60px";

        dom.readingContent.appendChild(
            message
        );
    }
}


function renderDocumentRepresentation(
    documentData,
    evidence
) {
    const representation =
        documentData.representation;

    dom.readingContent.innerHTML =
        "";

    if (
        !representation ||
        !representation.pages?.length
    ) {
        const empty =
            document.createElement(
                "p"
            );

        empty.textContent =
            "A representação canônica deste documento ainda não está disponível.";

        empty.style.textAlign =
            "center";

        empty.style.marginTop =
            "60px";

        dom.readingContent.appendChild(
            empty
        );

        return;
    }

    let target =
        null;

    const evidenceText =
        normalizeReadingText(
            evidence?.content
        );

    let lastSection =
        null;

    for (
        const page of
        representation.pages
    ) {
        const pageElement =
            document.createElement(
                "section"
            );

        pageElement.className =
            "reading-page";

        const pageTitle =
            document.createElement(
                "h4"
            );

        pageTitle.textContent =
            `Página ${page.page_number}`;

        pageTitle.className =
            "reading-page-title";

        pageElement.appendChild(
            pageTitle
        );

        for (
            const block of
            page.blocks || []
        ) {
            const chunkDiv =
                document.createElement(
                    "div"
                );

            chunkDiv.className =
                "reading-chunk";

            /*
             * A representação pode trazer a seção
             * no próprio bloco ou na página.
             *
             * Não assumimos que ela exista:
             * se não existir, o Reading continua
             * exatamente como antes.
             */
            const section =
                block.section ||
                page.section ||
                null;

            if (
                section &&
                section !== lastSection
            ) {
                const sectionElement =
                    document.createElement(
                        "span"
                    );

                sectionElement.className =
                    "reading-chunk-section";

                sectionElement.textContent =
                    section;

                chunkDiv.appendChild(
                    sectionElement
                );

                lastSection =
                    section;
            }

            const originalText =
                block.text || "";

            const textSpan =
                document.createElement(
                    "span"
                );

            textSpan.className =
                "chunk-text-content";

            textSpan.textContent =
                originalText;

            textSpan.style.whiteSpace =
                "pre-wrap";

            chunkDiv.appendChild(
                textSpan
            );

            /*
             * Localização da evidência.
             *
             * Primeiro tenta o casamento completo,
             * como na V2.
             */
            const blockText =
                normalizeReadingText(
                    originalText
                );

            const matchesEvidence =
                Boolean(
                    evidenceText &&
                    blockText &&
                    (
                        blockText.includes(
                            evidenceText
                        ) ||
                        evidenceText.includes(
                            blockText
                        )
                    )
                );

            if (
                matchesEvidence
            ) {
                chunkDiv.style.borderLeft =
                    "4px solid var(--primary)";

                chunkDiv.style.paddingLeft =
                    "16px";

                chunkDiv.classList.add(
                    "reading-evidence-target"
                );

                target =
                    chunkDiv;
            }

            /*
             * A tradução continua totalmente
             * encapsulada em translation.js.
             */
            addTranslationControl(
                chunkDiv,
                textSpan,
                originalText
            );

            pageElement.appendChild(
                chunkDiv
            );
        }

        dom.readingContent.appendChild(
            pageElement
        );
    }

    if (window.lucide) {
        lucide.createIcons();
    }

    /*
     * Leva o usuário diretamente para a
     * evidência que originou a leitura.
     */
    if (target) {
        setTimeout(
            () => {
                target.scrollIntoView({
                    behavior:
                        "smooth",
                    block:
                        "center",
                });
            },
            150
        );
    }
}


/* ============================================================
   Reading — comportamento da topbar
   ============================================================ */

let lastReadingScrollTop =
    0;

dom.readingView?.addEventListener(
    "scroll",
    () => {
        const currentScroll =
            dom.readingView.scrollTop;

        const readingTopbar =
            dom.readingView.querySelector(
                ".reading-topbar"
            );

        if (!readingTopbar) {
            return;
        }

        if (
            currentScroll <= 60
        ) {
            readingTopbar.classList.remove(
                "hidden-on-scroll"
            );

            dom.btnMobileMenu?.classList.remove(
                "menu-hidden"
            );

            lastReadingScrollTop =
                currentScroll;

            return;
        }

        if (
            currentScroll >
            lastReadingScrollTop
        ) {
            /*
             * Descendo:
             * esconde a barra para liberar
             * espaço de leitura.
             */
            readingTopbar.classList.add(
                "hidden-on-scroll"
            );

            dom.btnMobileMenu?.classList.add(
                "menu-hidden"
            );
        } else {
            /*
             * Subindo:
             * mostra novamente.
             */
            readingTopbar.classList.remove(
                "hidden-on-scroll"
            );

            dom.btnMobileMenu?.classList.remove(
                "menu-hidden"
            );
        }

        lastReadingScrollTop =
            currentScroll;
    }
);


dom.btnCloseReading?.addEventListener(
    "click",
    () => {
        closeReading();
    }
);


window.addEventListener(
    "snoopy:open-reading",
    event => {
        openReading(
            event.detail
        );
    }
);

/* ============================================================
   Settings
   ============================================================ */

dom.btnSettings?.addEventListener(
    "click",
    () => {
        dom.settingsModal.classList.remove(
            "hidden"
        );

        setTimeout(
            () => {
                dom.settingsModal.classList.add(
                    "active"
                );
            },
            10
        );
    }
);


function closeSettings() {
    dom.settingsModal.classList.remove(
        "active"
    );

    setTimeout(
        () => {
            dom.settingsModal.classList.add(
                "hidden"
            );
        },
        250
    );
}


dom.btnCloseModal?.addEventListener(
    "click",
    closeSettings
);


dom.settingsModal?.addEventListener(
    "click",
    event => {
        if (
            event.target ===
            dom.settingsModal
        ) {
            closeSettings();
        }
    }
);

/* ============================================================
   Google Picker bootstrap
   ============================================================ */

loadGooglePicker().catch(
    error => {
        console.warn(
            "[PICKER]",
            error.message
        );
    }
);

/* ============================================================
   BOOT
   ============================================================ */

async function boot() {
    try {
        /*
         * A autenticação precisa terminar antes de qualquer
         * chamada à API protegida.
         */
        await initAuth(
            handleSession
        );

        /*
         * O Picker é auxiliar da interface.
         * Não deve bloquear o boot nem a autenticação.
         */
        loadGooglePicker().catch(
            error => {
                console.warn(
                    "[PICKER]",
                    error.message
                );
            }
        );

    } catch (error) {
        console.error(
            "[BOOT]",
            error
        );

        if (dom.liveLogs) {
            dom.liveLogs.textContent =
                error.message;
        }
    }
}


boot();