export const dom = {
    btnSidebarNew: document.getElementById('btn-sidebar-new'),
    logoBtn: document.getElementById('logo-btn'),
    userName: document.querySelector('.user-name'),
    layoutGrid: document.querySelector('.layout-grid'),
    btnCloseEvidence: document.getElementById('btn-close-evidence'),
    homeView: document.getElementById('home-view'),
    resultView: document.getElementById('result-view'),
    homeForm: document.getElementById('search-home'),
    inputHome: document.getElementById('input-home'),
    queryDisplay: document.getElementById('query-title'),
    loadingState: document.getElementById('loading-state'),
    answerBox: document.getElementById('answer-box'),
    answerText: document.getElementById('answer-text'),
    sourcesContainer: document.getElementById('sources-container'),
    chunksContainer: document.getElementById('chunks-container'),
    sidebar: document.querySelector('.sidebar'),
    sidebarToggle: document.getElementById('btn-sidebar-toggle'),
    btnSettings: document.getElementById('btn-settings'),
    liveLogs: document.getElementById('live-logs'),
    btnLogin: document.getElementById('btn-login'),
    userInfo: document.getElementById('user-info'),
    userAvatar: document.getElementById('user-avatar'),
    folderContainer: document.getElementById('folder-container'),
    folderSelector: document.getElementById('folder-selector'),
    btnDrive: document.getElementById('btn-drive'),
    historyList: document.getElementById('history-list'),
    btnNewSearch: document.getElementById('btn-new-search')
};

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

export function renderResults(data) {
    dom.loadingState.classList.add('hidden');
    dom.answerBox.classList.remove('hidden');

    let formattedAnswer = data.answer.replace(/\[TRECHOS?\s*(\d+)\]/gi, (match, numero) => {
        return `<span class="trecho-highlight" data-trecho="${numero}">${match}</span>`;
    });
    dom.answerText.innerHTML = formattedAnswer.replace(/\n\n/g, '<br><br>');
    dom.sourcesContainer.innerHTML = '';
    dom.chunksContainer.innerHTML = '';

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

    if (data.sources && data.sources.length > 0) {
        data.sources.forEach(source => {
            const card = document.createElement('div');
            card.className = 'source-card';
            card.style.cursor = 'pointer';
     
            const title = document.createElement('h4');
            title.style.fontSize = '0.85rem';
            title.textContent = source.titulo;
            
            const meta = document.createElement('p');
            meta.className = 'source-meta';
            meta.style.fontSize = '0.75rem';
            meta.textContent = `Cita os trechos: [${source.trechos ? source.trechos.join(', ') : ''}]`;
            
            card.append(title, meta);
            dom.sourcesContainer.appendChild(card);

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
            });
        });
    } else {
            dom.sourcesContainer.innerHTML = '<p class="no-sources-msg">Nenhuma fonte direta indexada.</p>';
    }
    document.querySelectorAll('.trecho-highlight').forEach(tag => {
        tag.addEventListener('click', (e) => {
            const numeroTrecho = e.target.getAttribute('data-trecho');
            const fonte = data.sources.find(s => s.trechos && s.trechos.includes(numeroTrecho));

            if (fonte) {
                const autores = fonte.autores && fonte.autores.length > 0
                    ? fonte.autores.join('; ').toUpperCase()
                    : 'AUTOR DESCONHECIDO';
                const ano = fonte.ano || 's.d.';

                document.getElementById('chunk-abnt').textContent = `${autores}. ${fonte.titulo}. ${ano}.`;
            } else {
                document.getElementById('chunk-abnt').textContent = `Metadados indisponíveis para este trecho.`;
            }

            dom.sidebar.classList.add('collapsed');
            dom.layoutGrid.classList.add('evidence-active');

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