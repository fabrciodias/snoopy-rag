// 1. IMPORTAÇÕES E INICIALIZAÇÃO 
import { appState, PUBLIC_FOLDER_ID, initAuth, login, logout, fetchUserFolder, linkDriveFolder, disconnectFolder } from './auth.js';
import { fetchHistory, saveHistory, streamSearch, streamSync } from './api.js';
import { dom, resetToHome, showSearchState, updateLog, showError, renderResults, renderHistoryList } from './ui.js';

lucide.createIcons();


// 2. ESTADO LOCAL DE EXECUÇÃO 
let isSearching = false;
let isUiInitialized = false;
let isSyncing = false;

// 3. CICLO DE VIDA (BOOT E AUTENTICAÇÃO) 
async function reloadHistory() {
    if (!appState.userToken) {
        dom.historyList.innerHTML = '<p class="history-empty">Faça login para ver o seu histórico.</p>';
        return;
    }
    const history = await fetchHistory();
    renderHistoryList(history, (q) => executeSearch(q));
}

initAuth(async (session) => {
    // Se for o primeiro carregamento, constrói a base do zero
    if (!isUiInitialized) {
        dom.folderContainer.classList.remove('hidden');
        dom.folderSelector.innerHTML = `<option value="${PUBLIC_FOLDER_ID}">Acervo Público</option>`;
        appState.folderId = PUBLIC_FOLDER_ID;
    }

    if (session) {
        // Estado: Logado (Atualiza dados do usuário sempre)
        appState.userToken = session.access_token;
        dom.btnLogin.classList.add('hidden');
        dom.userInfo.classList.remove('hidden');
        dom.userAvatar.src = session.user.user_metadata.avatar_url;
        dom.userName.textContent = session.user.user_metadata.full_name || 'Usuário';

        // Só busca a pasta no banco e injeta no dropdown se a UI não foi inicializada ainda
        if (!isUiInitialized) {
            const folderData = await fetchUserFolder(session.user.id);
            if (folderData) {
                const option = document.createElement('option');
                option.value = folderData.id;
                option.textContent = folderData.name;
                dom.folderSelector.appendChild(option);
                dom.folderSelector.value = folderData.id;
                appState.folderId = folderData.id;
                
                dom.btnDrive.classList.add('hidden');
                dom.btnSync.classList.remove('hidden');
                dom.btnRemoveFolder.classList.remove('hidden');
            } else {
                dom.btnDrive.classList.remove('hidden');
                dom.btnRemoveFolder.classList.add('hidden');
            }
        }
    } else {
        // Estado: Deslogado
        appState.userToken = null;
        dom.btnLogin.classList.remove('hidden');
        dom.userInfo.classList.add('hidden');
        dom.btnDrive.classList.add('hidden');
    }
    
    appState.isAuthLoaded = true;
    
    // Evita reinicialização em backgorund
    if (!isUiInitialized) {
        reloadHistory();
        isUiInitialized = true;
    }
});

// 4. CONTROLADORES CORE (Lógica Principal) 
async function executeSearch(query) {
    if (!query.trim() || isSearching) return;
    if (!appState.isAuthLoaded) return alert("Sistema a inicializar... Aguarde.");
    if (!appState.folderId) return alert("Nenhum acervo carregado.");

    isSearching = true;

    // Recolhe menus no mobile ao pesquisar
    if (window.innerWidth <= 850) {
        dom.sidebar.classList.remove('mobile-open');
        dom.mobileOverlay.classList.remove('active');
    }

    showSearchState(query);

    await streamSearch(query, {
        onLog: updateLog,
        onResult: async (data) => {
            renderResults(data);
            await saveHistory(query);
            reloadHistory();
        },
        onError: showError
    });
    
    isSearching = false;
}

// 5. EVENT LISTENERS: NAVEGAÇÃO E UI
// Ações de Reset e Navegação Principal
dom.btnNewSearch?.addEventListener('click', resetToHome);
dom.btnSidebarNew.addEventListener('click', resetToHome);
dom.logoBtn.addEventListener('click', () => {
    if (dom.sidebar.classList.contains('collapsed')) {
        dom.sidebar.classList.remove('collapsed');
    } else {
        resetToHome();
    }
});

// Comportamentos Mobile
dom.btnMobileMenu?.addEventListener('click', () => {
    dom.sidebar.classList.add('mobile-open');
    dom.mobileOverlay.classList.add('active');
});

dom.mobileOverlay?.addEventListener('click', () => {
    dom.sidebar.classList.remove('mobile-open');
    dom.layoutGrid.classList.remove('evidence-active');
    dom.mobileOverlay.classList.remove('active');
});

if (dom.btnCloseEvidence) {
    dom.btnCloseEvidence.addEventListener('click', () => {
        dom.layoutGrid.classList.remove('evidence-active');
        dom.mobileOverlay.classList.remove('active');
    });
}

// Toggle da Sidebar (Desktop vs Mobile)
dom.sidebarToggle.addEventListener('click', () => {
    if (window.innerWidth <= 850) {
        dom.sidebar.classList.remove('mobile-open');
        dom.mobileOverlay.classList.remove('active');
    } else {
        dom.sidebar.classList.toggle('collapsed');
    }
});

// Alternador de Tema (Light/Dark)
document.getElementById('btn-theme-toggle').addEventListener('click', () => {
    const isLight = document.body.classList.toggle('light-theme');
    const btn = document.getElementById('btn-theme-toggle');
    if (btn) {
        btn.innerHTML = `
            <i data-lucide="${isLight ? 'sun' : 'moon'}" class="icon-sm"></i>
            <span class="nav-title" style="font-size: 0.85rem;">Tema</span>
        `;
        lucide.createIcons();
    }
});

// Atalhos da Sidebar Colapsada
document.getElementById('btn-nav-folder').addEventListener('click', () => {
    if (dom.sidebar.classList.contains('collapsed')) dom.sidebar.classList.remove('collapsed');
    dom.folderSelector.focus(); 
});

document.getElementById('btn-nav-history').addEventListener('click', () => {
    if (dom.sidebar.classList.contains('collapsed')) dom.sidebar.classList.remove('collapsed');
});

dom.folderSelector.addEventListener('change', (e) => {
    appState.folderId = e.target.value;
    console.log("Contexto de busca alterado para:", appState.folderId);
});

// --- 6. EVENT LISTENERS: INTEGRAÇÕES E MODAIS ---
// Execução de Pesquisa
dom.homeForm.addEventListener('submit', (e) => {
    e.preventDefault();
    executeSearch(dom.inputHome.value);
});

// Autenticação
dom.btnLogin.addEventListener('click', login);

// Conexão com Google Drive (Picker)
dom.btnDrive.addEventListener('click', () => {
    if (!appState.pickerApiLoaded) return alert("A API do Google ainda está a carregar...");
    if (!appState.googleToken) return alert("Sessão expirada. Faça login novamente.");

    const view = new google.picker.DocsView()
        .setIncludeFolders(true)
        .setMimeTypes('application/vnd.google-apps.folder')
        .setSelectFolderEnabled(true)
        .setParent('root');

    const picker = new google.picker.PickerBuilder()
        .addView(view)
        .setOAuthToken(appState.googleToken)
        .setDeveloperKey(appState.googleApiKey)
        .setAppId(appState.googleAppId)
        .setCallback(async (data) => {
            if (data.action === google.picker.Action.PICKED) {
                const folder = data.docs[0];
                await linkDriveFolder(folder.name, folder.id);
            }
        }).build();
    picker.setVisible(true);
});

// Sincronização Manual do Acervo
dom.btnSync.addEventListener('click', async () => {
    if (!appState.folderId || appState.folderId === PUBLIC_FOLDER_ID) return alert("Selecione o seu Acervo Privado para sincronizar.");
    if (!appState.googleToken) return alert("Sessão do Drive expirada. Faça login novamente.");
    if (isSyncing) return;

    isSyncing = true;
    dom.btnSync.disabled = true;
    dom.btnSync.style.opacity = '0.5';
    dom.syncLogs.textContent = "A conectar ao servidor...";

    await streamSync({
        onLog: (msg) => dom.syncLogs.textContent = msg,
        onResult: (statusMsg) => dom.syncLogs.textContent = statusMsg,
        onError: (err) => dom.syncLogs.textContent = "Erro: " + err
    });

    isSyncing = false;
    dom.btnSync.disabled = false;
    dom.btnSync.style.opacity = '1';
    setTimeout(() => { dom.syncLogs.textContent = ""; }, 5000);
});

// Lógica da Modal de Configurações
dom.btnSettings?.addEventListener('click', () => {
    dom.settingsModal.classList.remove('hidden');
    // Timeout rapidinho só pro CSS ler e fazer a animação de fade
    setTimeout(() => dom.settingsModal.classList.add('active'), 10); 
});

const closeModal = () => {
    dom.settingsModal.classList.remove('active');
    setTimeout(() => dom.settingsModal.classList.add('hidden'), 250);
};

dom.btnCloseModal?.addEventListener('click', closeModal);
dom.settingsModal?.addEventListener('click', (e) => {
    if (e.target === dom.settingsModal) closeModal(); // Fecha se clicar fora da caixa
});

dom.btnLogout?.addEventListener('click', () => {
    logout();
    closeModal();
});

dom.btnRemoveFolder?.addEventListener('click', () => {
    if(confirm("Tem certeza? Isso vai desvincular seu acervo do Drive.")) {
        disconnectFolder();
    }
});

// 7. EVENT LISTENERS: MODO LEITURA
dom.btnCloseReading?.addEventListener('click', () => {
    dom.readingView.classList.remove('active');
    dom.resultView.classList.add('active');
});