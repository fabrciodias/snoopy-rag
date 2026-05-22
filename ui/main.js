import { appState, PUBLIC_FOLDER_ID, initAuth, login, logout, fetchUserFolder, linkDriveFolder, disconnectFolder } from './auth.js';
import { fetchHistory, saveHistory, streamSearch, streamSync } from './api.js';
import { dom, resetToHome, showSearchState, updateLog, showError, renderResults, renderHistoryList } from './ui.js';
lucide.createIcons();

let isSearching = false;
let isSyncing = false;

dom.btnLogin.addEventListener('click', login);
dom.btnNewSearch?.addEventListener('click', resetToHome);
dom.btnSidebarNew.addEventListener('click', resetToHome);

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
        dom.mobileOverlay.classList.remove('active'); // Adiciona isso
    });
}

dom.logoBtn.addEventListener('click', () => {
    if (dom.sidebar.classList.contains('collapsed')) {
        dom.sidebar.classList.remove('collapsed');
    } else {
        resetToHome();
    }
});

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

document.getElementById('btn-nav-folder').addEventListener('click', () => {
    if (dom.sidebar.classList.contains('collapsed')) {
        dom.sidebar.classList.remove('collapsed');
    }
    dom.folderSelector.focus(); 
});

document.getElementById('btn-nav-history').addEventListener('click', () => {
    if (dom.sidebar.classList.contains('collapsed')) {
        dom.sidebar.classList.remove('collapsed');
    }
});

dom.folderSelector.addEventListener('change', (e) => {
    appState.folderId = e.target.value;
    console.log("Contexto de busca alterado para:", appState.folderId);
});

async function reloadHistory() {
    if (!appState.userToken) {
        dom.historyList.innerHTML = '<p class="history-empty">Faça login para ver seu histórico.</p>';
        return;
    }
    const history = await fetchHistory();
    renderHistoryList(history, (q) => executeSearch(q));
}

initAuth(async (session) => {
    dom.folderContainer.classList.remove('hidden');
    dom.folderSelector.innerHTML = `<option value="${PUBLIC_FOLDER_ID}">Acervo Público</option>`;
    appState.folderId = PUBLIC_FOLDER_ID;

    if (session) {
        appState.userToken = session.access_token;
        dom.btnLogin.classList.add('hidden');
        dom.userInfo.classList.remove('hidden');
        dom.userAvatar.src = session.user.user_metadata.avatar_url;
        dom.userName.textContent = session.user.user_metadata.full_name || 'Usuário';

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
        } else {
            dom.btnDrive.classList.remove('hidden');
        }
    } else {
        appState.userToken = null;
        dom.btnLogin.classList.remove('hidden');
        dom.userInfo.classList.add('hidden');
        dom.btnDrive.classList.add('hidden');
    }
    appState.isAuthLoaded = true;
    reloadHistory();
});

async function executeSearch(query) {
    if (!query.trim() || isSearching) return;
    if (!appState.isAuthLoaded) return alert("Sistema inicializando... Aguarde.");
    if (!appState.folderId) return alert("Nenhum acervo carregado.");

    isSearching = true;

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
dom.homeForm.addEventListener('submit', (e) => {
    e.preventDefault();
    executeSearch(dom.inputHome.value);
});

dom.btnDrive.addEventListener('click', () => {
    if (!appState.pickerApiLoaded) return alert("A API do Google ainda está carregando...");
    if (!appState.googleToken) return alert("Token expirado. Faça login novamente.");

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

dom.btnSync.addEventListener('click', async () => {
    if (!appState.folderId || appState.folderId === PUBLIC_FOLDER_ID) return alert("Selecione seu Acervo Privado para sincronizar.");
    if (!appState.googleToken) return alert("Sessão do Drive expirada. Faça login novamente.");
    if (isSyncing) return;

    isSyncing = true;
    dom.btnSync.disabled = true;
    dom.btnSync.style.opacity = '0.5';
    dom.syncLogs.textContent = "Conectando ao servidor...";

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

dom.sidebarToggle.addEventListener('click', () => {
    if (window.innerWidth <= 850) {
        dom.sidebar.classList.remove('mobile-open');
        dom.mobileOverlay.classList.remove('active');
    } else {
        dom.sidebar.classList.toggle('collapsed');
    }
});

/*

const btnRemove = document.createElement('button');
btnRemove.id = 'btn-remove-folder';
btnRemove.className = 'btn-outline';
btnRemove.style.color = '#dc3545';  
btnRemove.style.borderColor = '#dc3545';
btnRemove.style.padding = '0 10px';
btnRemove.title = "Desconectar Acervo";
btnRemove.textContent = "✖";
btnRemove.onclick = disconnectFolder;
dom.btnSync.parentNode.insertBefore(btnRemove, dom.btnSync.nextSibling);

*/
