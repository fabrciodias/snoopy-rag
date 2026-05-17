/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

const homeView = document.getElementById('home-view');
const resultView = document.getElementById('result-view');
const homeForm = document.getElementById('search-home');
const navForm = document.getElementById('search-nav');
const queryDisplay = document.getElementById('query-title');
const loadingState = document.getElementById('loading-state');
const answerBox = document.getElementById('answer-box');
const answerText = document.getElementById('answer-text');
const sourcesContainer = document.getElementById('sources-container');
const liveLogs = document.getElementById('live-logs');

const PUBLIC_FOLDER_ID = "f7faf7d9-ec80-46c6-9572-174865bf1e62";


let supabaseClient;
let userToken = null;
let folderId = null;
let isAuthLoaded = false;
let isSearching = false;
let isSyncing = false;

let googleToken = null;
let googleApiKey = null;
let googleAppId = null;
let pickerApiLoaded = false;

const gScript = document.createElement('script');
gScript.src = 'https://apis.google.com/js/api.js';
gScript.onload = () => gapi.load('picker', () => { pickerApiLoaded = true; });
document.body.appendChild(gScript);

async function initAuth() {
    try {
        const res = await fetch('/api/config');
        const config = await res.json();

        supabaseClient = window.supabase.createClient(config.url, config.key);
        googleApiKey = config.googleApiKey;
        googleAppId = config.googleAppId;

        const { data: { session }, error } = await supabaseClient.auth.getSession();
        if (session?.provider_token) localStorage.setItem('snoopy_g_token', session.provider_token);
        googleToken = localStorage.getItem('snoopy_g_token');
        await processSession(session);

        supabaseClient.auth.onAuthStateChange(async (event, newSession) => {
            if (event === 'SIGNED_IN') {
                if (newSession?.provider_token) localStorage.setItem('snoopy_g_token', newSession.provider_token);
                googleToken = localStorage.getItem('snoopy_g_token');
            }
            if (event === 'SIGNED_IN' || event === 'SIGNED_OUT') {
                await processSession(newSession);
            }
        });

        document.getElementById('btn-login').addEventListener('click', async () => {
            await supabaseClient.auth.signInWithOAuth({
                provider: 'google',
                options: { scopes: 'https://www.googleapis.com/auth/drive.readonly' }
            });
        });

        document.getElementById('btn-logout').addEventListener('click', async (e) => {
            e.preventDefault(); 
            console.log("Sinal de Logout enviado ao Supabase...");
            localStorage.removeItem('snoopy_g_token');
            try { await supabaseClient.auth.signOut(); } catch(err) { console.error(err); }
            window.location.reload(); 
        });

        const btnDrive = document.getElementById('btn-drive');
        if (btnDrive) {
            btnDrive.addEventListener('click', () => {
                if (!pickerApiLoaded) return alert("A API do Google ainda está carregando...");
                if (!googleToken) return alert("Token do Drive expirado. Por favor, clique em Sair e faça login novamente.");

                const view = new google.picker.DocsView()
                    .setIncludeFolders(true)
                    .setMimeTypes('application/vnd.google-apps.folder')
                    .setSelectFolderEnabled(true)
                    .setParent('root');

                const picker = new google.picker.PickerBuilder()
                    .addView(view)
                    .setOAuthToken(googleToken)
                    .setDeveloperKey(googleApiKey)
                    .setAppId(googleAppId)
                    .setCallback(async (data) => {
                        if (data.action === google.picker.Action.PICKED) {
                            const folder = data.docs[0];
                            console.log("Drive Selecionado:", folder.name, folder.id);
                            await linkDriveFolder(folder.name, folder.id);
                        }
                    })
                    .build();
                picker.setVisible(true);
            });
        }
        
    } catch (error) {
        console.error("Erro Crítico na inicialização do app:", error);
    }
}

async function processSession(session) {
    const folderContainer = document.getElementById('folder-container');
    const folderSelector = document.getElementById('folder-selector');
    const btnDrive = document.getElementById('btn-drive');

    folderContainer.classList.remove('hidden')
    folderSelector.innerHTML =`<option value="${PUBLIC_FOLDER_ID}">Acervo Público</option>`;
    folderId = PUBLIC_FOLDER_ID;

    if (session) {
        userToken = session.access_token;
        document.getElementById('btn-login').classList.add('hidden');
        document.getElementById('user-info').classList.remove('hidden');
        document.getElementById('user-avatar').src = session.user.user_metadata.avatar_url;

        await fetchUserFolder(session.user.id, folderSelector, btnDrive);
        renderHistory();
    } else {
        userToken = null;

        document.getElementById('btn-login').classList.remove('hidden');
        document.getElementById('user-info').classList.add('hidden');

        if (btnDrive) btnDrive.classList.add('hidden');
        isAuthLoaded = true; 
        console.log("Modo Anônimo Ativado. Pasta:", folderId);
    }
    folderSelector.addEventListener('change', (e) => {
        folderId = e.target.value;
        console.log("Contexto de busca alterado para:", folderId);
    });
    renderHistory();
}

async function fetchUserFolder(userId, folderSelector, btnDrive) {
    try {
        const { data, error } = await supabaseClient
            .from('folders')
            .select('id, name')
            .eq('user_id', userId)
            .eq('is_active', true)
            .limit(1)
            .maybeSingle();

        if (data) {
            const option = document.createElement('option');
            option.value = data.id;
            option.textContent = data.name;
            folderSelector.appendChild(option);

            folderSelector.value = data.id;
            folderId = data.id;

            btnDrive.classList.add('hidden')
            console.log("Acervo Privado ativado:", folderId);
            document.getElementById('btn-sync').classList.remove('hidden');
        } else {
            console.log("Usuário sem acervo privado. Exibindo botão de conexão.");
            btnDrive.classList.remove('hidden')
        }
    } catch (err) {
        console.error("Erro ao verificar acervo:", err);
    } finally {
        isAuthLoaded = true;  
    }
}

async function linkDriveFolder(folderName, driveFolderId) {
    try {
        const { data: { user } } = await supabaseClient.auth.getUser();
        
        const { data: existingFolder } = await supabaseClient
            .from('folders')
            .select('id')
            .eq('user_id', user.id)
            .eq('drive_id', driveFolderId)
            .maybeSingle();

        let targetFolderData;

        if (existingFolder) {
            const { data, error } = await supabaseClient
                .from('folders')
                .update({ is_active: true, name: folderName }) 
                .eq('id', existingFolder.id)
                .select()
                .single();
            
            if (error) throw error;
            targetFolderData = data;
            console.log("Acervo reativado! Recuperando memória existente...");
        } else {
            const { data, error } = await supabaseClient
                .from('folders')
                .insert([{
                    user_id: user.id,
                    name: folderName,
                    drive_id: driveFolderId,
                    is_active: true
                }])
                .select()
                .single();
            
            if (error) throw error;
            targetFolderData = data;
            console.log("Novo Acervo vinculado com sucesso.");
        }

        const folderSelector = document.getElementById('folder-selector');
        
        let option = Array.from(folderSelector.options).find(opt => opt.value === targetFolderData.id);
        if (!option) {
            option = document.createElement('option');
            option.value = targetFolderData.id;
            option.textContent = targetFolderData.name;
            folderSelector.appendChild(option);
        }

        folderSelector.value = targetFolderData.id;
        folderId = targetFolderData.id;

        window.location.reload();

    } catch (error) {
        console.error("Erro ao vincular pasta no banco:", error);
        alert("Erro ao vincular a pasta no Drive");
    }
}
function resetToHome() {
    resultView.classList.remove('active');
    homeView.classList.add('active');
    document.getElementById('input-home').value = '';
    document.getElementById('input-nav').value = '';
    queryDisplay.textContent = '';
    answerBox.classList.add('hidden');
    sourcesContainer.innerHTML = '';
    loadingState.classList.add('hidden');
    liveLogs.textContent = '';
}
window.resetToHome = resetToHome;

async function performSearch(query) {
    if (!query.trim() || isSearching) return;

    if (!isAuthLoaded) {
        alert("Sistema inicializando... Aguarde um instante e tente novamente.");
        return;
    }

    if (!folderId) {
        alert("Erro de Sessão: Nenhum acervo carregado.");
        return;
    }
    isSearching = true;

    homeView.classList.remove('active');
    resultView.classList.add('active');
    
    document.getElementById('input-nav').value = query;
    queryDisplay.textContent = query;
    answerBox.classList.add('hidden');
    sourcesContainer.innerHTML = '';
    loadingState.classList.remove('hidden');
    liveLogs.textContent = 'Iniciando motor semântico...';

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (userToken) {
            headers['Authorization'] = `Bearer ${userToken}`;
        }

        const response = await fetch('/api/search', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ query, folder_id: folderId })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let done = false;
        let buffer = "";

        while (!done) {
            const { value, done: readerDone } = await reader.read();
            done = readerDone;

            if (value) {
                buffer += decoder.decode(value, { stream: true });
                const messages = buffer.split('\n\n');

                buffer = messages.pop();

                for (const msg of messages) {
                    if (msg.startsWith('data: ')) {
                        const jsonStr = msg.replace('data: ', '');
                        if(!jsonStr.trim()) continue;

                        try {
                            const payload = JSON.parse(jsonStr);
                            if (payload.type === 'log') {
                                liveLogs.textContent = payload.message;
                            } else if (payload.type === 'result') {
                                renderResults(payload.data);
                                saveHistory(query);
                            } else if (payload.type === 'error') {
                                throw new Error(payload.message);
                            }
                        } catch (e) {
                            console.error("Erro no parser do stream:", e, jsonStr);
                        }
                    }
                }
            }
        }
    } catch (error) {
        loadingState.classList.add('hidden');
        answerBox.classList.remove('hidden');
        answerText.innerHTML = `<span class="error-text">Erro: ${error.message}</span>`;
    } finally {
        isSearching = false;
    }
}

function renderResults(data) {
    loadingState.classList.add('hidden');
    answerBox.classList.remove('hidden');

    let formattedAnswer = data.answer.replace(/\[(TRECHOS?[^\]]+)\]/gi, '<span class="trecho-highlight">[$1]</span>');
    formattedAnswer = formattedAnswer.replace(/\n\n/g, '<br><br>');
    
    answerText.innerHTML = formattedAnswer;

    if (data.sources && data.sources.length > 0) {
        data.sources.forEach((source, index) => {
            const card = document.createElement('div');
            card.className = 'source-card';
            
            const driveBtn = source.link !== 'Link indisponível' 
                ? `<a href="${source.link}" target="_blank" class="drive-link">Abrir no Drive ↗</a>` 
                : `<span class="drive-link link-disabled">Link indisponível</span>`;

                const trechoStr = source.trechos ? source.trechos.join(', ') : 'N/A';

            card.innerHTML = `
                <div class="badge-secao">Trechos Refrenciados: ${trechoStr}</div>
                <h4>${source.titulo}</h4>
                <p class="source-meta">Arq: ${source.arquivo}</p>
                ${driveBtn}
            `;
            sourcesContainer.appendChild(card);
        });
    } else {
        sourcesContainer.innerHTML = '<p class="no-sources-msg">Nenhuma fonte direta indexada para esta resposta.</p>';
    }
}

homeForm.addEventListener('submit', (e) => {
    e.preventDefault();
    performSearch(document.getElementById('input-home').value);
});

navForm.addEventListener('submit', (e) => {
    e.preventDefault();
    performSearch(document.getElementById('input-nav').value);
});

async function triggerSync() {
    if (!folderId || folderId === PUBLIC_FOLDER_ID) {
        alert("O Acervo Público é apenas para leitura. Selecione seu Acervo Privado para sincronizar.");
        return;
    }
    if (!googleToken) {
        alert("Sessão do Drive expirada. Faça login novamente.");
        return;
    }
    if (isSyncing) return;

    isSyncing = true;
    const syncBtn = document.getElementById('btn-sync');
    const syncLogs = document.getElementById('sync-logs');

    if (syncBtn) {
        syncBtn.disabled = true;
        syncBtn.style.opacity = '0.5';
    }
    if (syncLogs) syncLogs.textContent = "Conectando ao servidor...";

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (userToken) {
            headers['Authorization'] = `Bearer ${userToken}`;
        }

        const response = await fetch('/api/sync', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ folder_id: folderId, google_token: googleToken })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let done = false;
        let buffer = "";

        while (!done) {
            const { value, done: readerDone } = await reader.read();
            done = readerDone;

            if (value) {
                buffer += decoder.decode(value, { stream: true });
                const messages = buffer.split('\n\n');
                buffer = messages.pop();

                for (const msg of messages) {
                    if (msg.startsWith('data: ')) {
                        const jsonStr = msg.replace('data: ', '');
                        if (!jsonStr.trim()) continue;

                        try {
                            const payload = JSON.parse(jsonStr);
                            if (payload.type === 'log') {
                                if (syncLogs) syncLogs.textContent = payload.message;
                            } else if (payload.type === 'result') {
                                if (syncLogs) syncLogs.textContent = "Sincronização Finalizada!";
                            } else if (payload.type === 'error') {
                                throw new Error(payload.message);
                            }
                        } catch (e) {
                            console.error("Erro no stream de sync:", e);
                        }
                    }
                }
            }
        }
    } catch (error) {
        console.error("Falha no Sync:", error);
        if (syncLogs) syncLogs.textContent = "Erro: " + error.message;
    } finally {
        isSyncing = false;
        if (syncBtn) {
            syncBtn.disabled = false;
            syncBtn.style.opacity = '1';
        }
        setTimeout(() => { if (syncLogs) syncLogs.textContent = ""; }, 5000);
    }
}

const btnSync = document.getElementById('btn-sync');
if (btnSync) {
    btnSync.addEventListener('click', triggerSync);
}

async function disconnectFolder() {
    if (!folderId || folderId === PUBLIC_FOLDER_ID) return;
    
    const confirmDisconnect = confirm("Deseja desconectar este acervo? Ele não aparecerá mais nas suas buscas, mas os dados processados continuarão salvos na nuvem.");
    if (!confirmDisconnect) return;

    try {
        const { error } = await supabaseClient
            .from('folders')
            .update({ is_active: false })
            .eq('id', folderId);

        if (error) throw error;

        console.log("Acervo desconectado com sucesso (Soft Delete).");
        window.location.reload(); 
    } catch (error) {
        console.error("Erro ao desconectar acervo:", error);
        alert("Erro ao desconectar o acervo.");
    }
}

if (btnSync) {
    btnSync.addEventListener('click', triggerSync);
    
    const btnRemove = document.createElement('button');
    btnRemove.id = 'btn-remove-folder';
    btnRemove.className = 'btn-outline';
    btnRemove.style.color = '#dc3545';  
    btnRemove.style.borderColor = '#dc3545';
    btnRemove.style.padding = '0 10px';
    btnRemove.title = "Desconectar Acervo";
    btnRemove.textContent = "✖";
    btnRemove.onclick = disconnectFolder;
    
    btnSync.parentNode.insertBefore(btnRemove, btnSync.nextSibling);
}

async function renderHistory() {
    const historyList = document.getElementById('history-list');
    
    if (!userToken) {
        historyList.innerHTML = '<p class="history-empty">Faça login para ver seu histórico.</p>';
        return;
    }

    try {
        const { data: { user } } = await supabaseClient.auth.getUser();
        
        const { data: history, error } = await supabaseClient
            .from('search_history')
            .select('query')
            .eq('user_id', user.id)
            .order('created_at', { ascending: false })
            .limit(15);

        if (error) throw error;

        if (!history || history.length === 0) {
            historyList.innerHTML = '<p class="history-empty">Nenhuma pesquisa recente.</p>';
            return;
        }
        
        const uniqueQueries = [...new Set(history.map(item => item.query))];

        historyList.innerHTML = uniqueQueries.map(q => `
            <div class="history-item" onclick="performSearch('${q.replace(/'/g, "\\'")}')">
                <span class="history-icon">◷</span> ${q}
            </div>
        `).join('');

    } catch (error) {
        console.error("Erro ao carregar histórico da nuvem:", error);
        historyList.innerHTML = '<p class="history-empty">Erro ao carregar histórico.</p>';
    }
}

async function saveHistory(query) {
    if (!userToken) return; 
    try {
        const { data: { user } } = await supabaseClient.auth.getUser();
        
        const { error } = await supabaseClient
            .from('search_history')
            .insert([{
                user_id: user.id,
                query: query
            }]);
        if (error) throw error;
        
        renderHistory();

    } catch (error) {
        console.error("Erro ao salvar histórico na nuvem:", error);
    }
}

initAuth();