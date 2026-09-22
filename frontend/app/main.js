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
        folders;

    const selectedExists =
        folders.some(
            folder =>
                folder.id ===
                appState.folderId
        );

    if (
        !selectedExists
    ) {
        appState.folderId =
            PUBLIC_FOLDER_ID;
    }

    const selected =
        folders.find(
            folder =>
                folder.id ===
                appState.folderId
        );

    appState.folderName =
        selected?.name ||
        "Acervo Público";

    renderFolders(
        folders,
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

    dom.btnDrive?.classList.remove(
        "hidden"
    );

    if (isPublic) {
        dom.btnSync?.classList.add(
            "hidden"
        );

        dom.btnRemoveFolder?.classList.add(
            "hidden"
        );
    } else {
        dom.btnSync?.classList.remove(
            "hidden"
        );

        dom.btnRemoveFolder?.classList.remove(
            "hidden"
        );
    }
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
            )

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
                        /*
                        * A API devolve exatamente o acervo criado.
                        * Não procuramos pelo nome.
                        */
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
                            setSyncOperationState,
                    }
                );

            setSyncState(
                "Sincronização concluída."
            );

            setSyncOperationState(
                finished
            );
        } catch (error) {
            setSyncState(
                "Falha na sincronização."
            );

            alert(
                error.message
            );
        } finally {
            syncBusy =
                false;

            dom.btnSync.disabled =
                false;

            setTimeout(
                () => {
                    dom.syncLogs.textContent =
                        "";
                },
                5000
            );
        }
    }
);


/* ============================================================
   Investigação
   ============================================================ */

async function executeSearch(
    query
) {
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
            query
        );
    } catch {
        // O controller já renderizou o erro.
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

    const history =
        await fetchHistory();

    renderHistory(
        history,
        executeSearch
    );
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

        /*
         * O endpoint /folders/ é protegido.
         * Não tente chamá-lo sem sessão.
         *
         * O acervo público já é conhecido pelo ID.
         */
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
        } catch (error) {
            alert(
                error.message
            );
        }
    }
);


/* ============================================================
   Nova pesquisa / home
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

        pageTitle.style.margin =
            "32px 0 16px";

        pageElement.appendChild(
            pageTitle
        );

        for (
            const block of
            page.blocks || []
        ) {
            const paragraph =
                document.createElement(
                    "p"
                );

            paragraph.className =
                "reading-chunk";

            paragraph.textContent =
                block.text || "";

            paragraph.style.whiteSpace =
                "pre-wrap";

            paragraph.style.lineHeight =
                "1.7";

            const evidenceText =
                (evidence.content ||
                    "")
                    .replace(
                        /\s+/g,
                        " "
                    )
                    .trim();

            const blockText =
                (block.text ||
                    "")
                    .replace(
                        /\s+/g,
                        " "
                    )
                    .trim();

            if (
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
            ) {
                paragraph.style.borderLeft =
                    "4px solid var(--primary)";

                paragraph.style.paddingLeft =
                    "16px";

                target =
                    paragraph;
            }

            pageElement.appendChild(
                paragraph
            );
        }

        dom.readingContent.appendChild(
            pageElement
        );
    }

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
        await initAuth(handleSession);

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