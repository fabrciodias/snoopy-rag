// 1. MAPEAMENTO DO DOM 
export const dom = {
    // 1.1. Globais & Layout
    layoutGrid: document.querySelector('.layout-grid'),
    mobileOverlay: document.getElementById('mobile-overlay'),

    // 1.2. Modais e Configurações
    btnSettings: document.getElementById('btn-settings'),
    settingsModal: document.getElementById('settings-modal'),
    btnCloseModal: document.getElementById('btn-close-modal'),
    btnRemoveFolder: document.getElementById('btn-remove-folder'),
    btnLogout: document.getElementById('btn-logout'),

    // 1.3. Sidebar & Navegação
    sidebar: document.querySelector('.sidebar'),
    sidebarToggle: document.getElementById('btn-sidebar-toggle'),
    logoBtn: document.getElementById('logo-btn'),
    btnSidebarNew: document.getElementById('btn-sidebar-new'),
    btnMobileMenu: document.getElementById('btn-mobile-menu'),

    // 1.4. Auth & Perfil do Usuário
    btnLogin: document.getElementById('btn-login'),
    userInfo: document.getElementById('user-info'),
    userName: document.querySelector('.user-name'),
    userAvatar: document.getElementById('user-avatar'),

    // 1.5. Seletor de Acervo & Sincronização
    folderContainer: document.getElementById('folder-container'),
    folderSelector: document.getElementById('folder-selector'),
    btnDrive: document.getElementById('btn-drive'),
    btnSync: document.getElementById('btn-sync'), 
    syncLogs: document.getElementById('sync-logs'), 
    historyList: document.getElementById('history-list'),

    // 1.6. Home View (Tela Inicial de Pesquisa)
    homeView: document.getElementById('home-view'),
    homeForm: document.getElementById('search-home'),
    inputHome: document.getElementById('input-home'),

    // 1.7. Result View (Cabeçalho e Status)
    resultView: document.getElementById('result-view'),
    queryDisplay: document.getElementById('query-title'),
    btnNewSearch: document.getElementById('btn-new-search'),
    loadingState: document.getElementById('loading-state'),
    liveLogs: document.getElementById('live-logs'),

    // 1.8. Área da Síntese e Referências
    answerBox: document.getElementById('answer-box'),
    answerText: document.getElementById('answer-text'),
    sourcesContainer: document.getElementById('sources-container'),

    // 1.9. Painel de Evidências (Gaveta Mobile / Split-Screen)
    btnCloseEvidence: document.getElementById('btn-close-evidence'),
    chunksContainer: document.getElementById('chunks-container')
};

// 2. TRANSIÇÕES DE TELA E ESTADOS DE UI
export function resetToHome() {
    dom.layoutGrid.classList.remove('evidence-active');
    dom.resultView.classList.remove('active');
    dom.homeView.classList.add('active');
    
    dom.inputHome.value = '';
    dom.queryDisplay.textContent = '';
    
    dom.answerBox.classList.add('hidden');
    dom.sourcesContainer.innerHTML = '';
    
    dom.loadingState.classList.add('hidden');
    dom.liveLogs.textContent = '';
}

export function showSearchState(query) {
    dom.layoutGrid.classList.remove('evidence-active');
    dom.homeView.classList.remove('active');
    dom.resultView.classList.add('active');
    
    dom.queryDisplay.textContent = query;
    dom.answerBox.classList.add('hidden');
    dom.sourcesContainer.innerHTML = '';
    
    dom.loadingState.classList.remove('hidden');
    dom.liveLogs.textContent = 'Iniciando motor semântico...';
}

export function updateLog(message) {
    dom.liveLogs.textContent = message;
}

export function showError(message) {
    dom.loadingState.classList.add('hidden');
    dom.answerBox.classList.remove('hidden');
    dom.answerText.innerHTML = `<span class="error-text">Erro: ${message}</span>`;
}


// 3. RENDERIZAÇÃO DE COMPONENTES COMPLEXOS
export function renderHistoryList(historyArray, onHistoryClick) {
    dom.historyList.innerHTML = '';
    
    if (historyArray.length === 0) {
        dom.historyList.innerHTML = '<p class="history-empty">Nenhuma pesquisa recente.</p>';
        return;
    }
    
    historyArray.forEach(q => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `<span class="history-icon">◷</span> ${q}`;
        item.onclick = () => onHistoryClick(q);
        dom.historyList.appendChild(item);
    });
}


 // Função Core: Constrói a Síntese, Evidências e injeta os Gatilhos de Ação (EventListeners)
export function renderResults(data) {
    // Passo 1: Prepara a tela limpando estados anteriores
    dom.loadingState.classList.add('hidden');
    dom.answerBox.classList.remove('hidden');
    dom.sourcesContainer.innerHTML = '';
    dom.chunksContainer.innerHTML = '';

    // Passo 2: Formata a Síntese (Transforma tags de trecho em botões clicáveis)
    let formattedAnswer = data.answer.replace(/\[TRECHOS?\s*(\d+)\]/gi, (match, numero) => {
        return `<span class="trecho-highlight" data-trecho="${numero}">${match}</span>`;
    });
    dom.answerText.innerHTML = formattedAnswer.replace(/\n\n/g, '<br><br>');

    // Passo 3: Renderiza os Chunks Ocultos na Gaveta
    if (data.chunks && data.chunks.length > 0) {
        data.chunks.forEach(chunk => {
            const chunkCard = document.createElement('div');
            chunkCard.className = 'chunk-card';
            chunkCard.dataset.num = chunk.num;

            const badge = document.createElement('span');
            badge.className = 'chunk-badge';
            badge.textContent = `TRECHO ${chunk.num}`;

            const textContent = document.createElement('q');
            textContent.textContent = chunk.text;

            chunkCard.append(badge, textContent);
            dom.chunksContainer.appendChild(chunkCard);
        }); 
    }

    // Passo 4: Renderiza as Referências do Acervo
    if (data.sources && data.sources.length > 0) {
        data.sources.forEach(source => {
            const card = document.createElement('div');
            card.className = 'source-card';
            card.style.cursor = 'pointer';
     
            const title = document.createElement('h4');
            title.style.fontSize = '0.85rem';
            const autores = source.autores && source.autores.length > 0
                ? source.autores.join('; ').toUpperCase()
                : 'AUTOR DESCONHECIDO';
            const ano = source.ano || 's.d.';
            
            title.textContent = `${autores}. ${source.titulo}. ${ano}.`;
            
            const meta = document.createElement('p');
            meta.className = 'source-meta';
            meta.style.fontSize = '0.75rem';
            meta.textContent = `Cita os trechos: [${source.trechos ? source.trechos.join(', ') : ''}]`;
            
            card.append(title, meta);
            dom.sourcesContainer.appendChild(card);

            // Ação ao clicar no card de referência
            card.addEventListener('click', () => {
                dom.sidebar.classList.add('collapsed');
                
                const trechosAlvo = source.trechos || [];
                document.querySelectorAll('.chunk-card').forEach(c => {
                    if (trechosAlvo.includes(c.dataset.num)) {
                        c.classList.add('highlight-active');
                        c.style.opacity = '1';
                        c.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    } else {
                        c.classList.remove('highlight-active');
                        c.style.opacity = '0.2';
                    }
                });
                
                // Tenta puxar o link direto
                const link = source.link || source.url || source.drive_link;
                if (link) {
                    window.open(link, '_blank');
                } else {
                    console.warn("Nenhum link do Drive foi retornado para este documento:", source);
                }
            })
        });
    } else {
        dom.sourcesContainer.innerHTML = '<p class="no-sources-msg">Nenhuma fonte direta indexada.</p>';
    }

    // Passo 5: Eventos de clique nas tags [TRECHO X] geradas no Passo 2
    document.querySelectorAll('.trecho-highlight').forEach(tag => {
        tag.addEventListener('click', (e) => {
            const numeroTrecho = e.target.getAttribute('data-trecho');
            const fonte = data.sources.find(s => s.trechos && s.trechos.includes(numeroTrecho));

            // Gera o ABNT na gaveta se achar a fonte
            if (fonte) {
                const autores = fonte.autores && fonte.autores.length > 0
                    ? fonte.autores.join('; ').toUpperCase()
                    : 'AUTOR DESCONHECIDO';
                const ano = fonte.ano || 's.d.';

                document.getElementById('chunk-abnt').textContent = `${autores}. ${fonte.titulo}. ${ano}.`;
            } else {
                document.getElementById('chunk-abnt').textContent = `Metadados indisponíveis para este trecho.`;
            }

            // Ativa o Layout de Evidências (Split-Screen / Gaveta Mobile)
            dom.sidebar.classList.add('collapsed');
            dom.layoutGrid.classList.add('evidence-active');
            dom.mobileOverlay.classList.add('active');

            // Isola apenas o chunk clicado na visão
            document.querySelectorAll('.chunk-card').forEach(c => {
                if (c.dataset.num === numeroTrecho) {
                    c.classList.add('active-chunk');
                } else {
                    c.classList.remove('active-chunk');
                }           
            });
        });
    });
}