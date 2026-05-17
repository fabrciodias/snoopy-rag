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

async function initAuth() {
    try {
        const res = await fetch('/api/config');
        const config = await res.json();
        supabaseClient = window.supabase.createClient(config.url, config.key);

        const { data: { session }, error } = await supabaseClient.auth.getSession();
        await processSession(session);

        supabaseClient.auth.onAuthStateChange(async (event, newSession) => {
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
            try { await supabaseClient.auth.signOut(); } catch(err) { console.error(err); }
            window.location.reload(); 
        });
        
    } catch (error) {
        console.error("Erro Crítico na inicialização do app:", error);
    }
}

async function processSession(session) {
    const folderContainer = document.getElementById('folder-container');
    const folderNameEl = document.getElementById('folder-name');

    if (session) {
        userToken = session.access_token;
        document.getElementById('btn-login').classList.add('hidden');
        document.getElementById('user-info').classList.remove('hidden');
        document.getElementById('user-avatar').src = session.user.user_metadata.avatar_url;

        await fetchUserFolder(session.user.id, folderContainer, folderNameEl);
    } else {
        userToken = null;
        folderId = PUBLIC_FOLDER_ID;

        document.getElementById('btn-login').classList.remove('hidden');
        document.getElementById('user-info').classList.add('hidden');

        folderNameEl.textContent = "Acervo Público GEPAFOR";
        folderContainer.classList.remove('hidden');
        isAuthLoaded = true; 
        console.log("Modo Anônimo Ativado. Pasta:", folderId);
    }
}

async function fetchUserFolder(userId, folderContainer, folderNameEl) {
    try {
        const { data, error } = await supabaseClient
            .from('folders')
            .select('id, name')
            .eq('user_id', userId)
            .limit(1)
            .maybeSingle();

        if (data) {
            folderId = data.id;
            folderNameEl.textContent = data.name;
            folderContainer.classList.remove('hidden');
            console.log("Acervo do Usuário carregado:", folderId);
        } else {
            console.log("Usuário novo detectado. Criando acervo base...");
            const { data: newFolder, error: insertError } = await supabaseClient
                .from('folders')
                .insert([{ user_id: userId, name: 'Meu Acervo Pessoal' }])
                .select()
                .single();

            if (newFolder) {
                folderId = newFolder.id;
                folderNameEl.textContent = newFolder.name;
                folderContainer.classList.remove('hidden');
                console.log("Acervo criado com sucesso:", folderId);
            } else {
                console.error("Erro ao criar acervo:", insertError);
            }
        }
    } catch (err) {
        console.error("Erro na comunicação com o banco:", err);
    } finally {
        isAuthLoaded = true;  
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

            card.innerHTML = `
                <div class="badge-secao">Trecho ${index + 1} | ${source.secao.substring(0, 30)}...</div>
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

function renderHistory() {
    const historyList = document.getElementById('history-list');
    let history = JSON.parse(localStorage.getItem('snoopy_history')) || [];
    
    if (history.length === 0) {
        historyList.innerHTML = '<p class="history-empty">Nenhuma pesquisa recente.</p>';
        return;
    }
    
    historyList.innerHTML = history.map(q => `
        <div class="history-item" onclick="performSearch('${q.replace(/'/g, "\\'")}')">
            <span class="history-icon">◷</span> ${q}
        </div>
    `).join('');
}

function saveHistory(query) {
    let history = JSON.parse(localStorage.getItem('snoopy_history')) || [];
    history = history.filter(q => q !== query);
    history.unshift(query);
    if(history.length > 15) history.pop();
    localStorage.setItem('snoopy_history', JSON.stringify(history));
    renderHistory();
}

renderHistory();
initAuth();