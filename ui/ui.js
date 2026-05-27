// 1. MAPEAMENTO DO DOM 
export const dom = {
    layoutGrid: document.querySelector('.layout-grid'),
    mobileOverlay: document.getElementById('mobile-overlay'),

    btnSettings: document.getElementById('btn-settings'),
    settingsModal: document.getElementById('settings-modal'),
    btnCloseModal: document.getElementById('btn-close-modal'),
    btnRemoveFolder: document.getElementById('btn-remove-folder'),
    btnLogout: document.getElementById('btn-logout'),

    sidebar: document.querySelector('.sidebar'),
    sidebarToggle: document.getElementById('btn-sidebar-toggle'),
    logoBtn: document.getElementById('logo-btn'),
    btnSidebarNew: document.getElementById('btn-sidebar-new'),
    btnMobileMenu: document.getElementById('btn-mobile-menu'),

    btnLogin: document.getElementById('btn-login'),
    userInfo: document.getElementById('user-info'),
    userName: document.querySelector('.user-name'),
    userAvatar: document.getElementById('user-avatar'),

    folderContainer: document.getElementById('folder-container'),
    folderSelector: document.getElementById('folder-selector'),
    btnDrive: document.getElementById('btn-drive'),
    btnSync: document.getElementById('btn-sync'), 
    syncLogs: document.getElementById('sync-logs'), 
    historyList: document.getElementById('history-list'),

    homeView: document.getElementById('home-view'),
    homeForm: document.getElementById('search-home'),
    inputHome: document.getElementById('input-home'),

    resultView: document.getElementById('result-view'),
    queryDisplay: document.getElementById('query-title'),
    btnNewSearch: document.getElementById('btn-new-search'),
    loadingState: document.getElementById('loading-state'),
    liveLogs: document.getElementById('live-logs'),

    answerBox: document.getElementById('answer-box'),
    answerText: document.getElementById('answer-text'),
    sourcesContainer: document.getElementById('sources-container'),

    btnCloseEvidence: document.getElementById('btn-close-evidence'),
    chunksContainer: document.getElementById('chunks-container'),

    readingView: document.getElementById('reading-view'),
    btnCloseReading: document.getElementById('btn-close-reading'),
    readingTitle: document.getElementById('reading-title'),
    readingOriginalLink: document.getElementById('reading-original-link'),
    readingContent: document.getElementById('reading-content')
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

// Função Core: Constrói a Síntese, Evidências e injeta os Gatilhos de Ação
export function renderResults(data) {
    dom.loadingState.classList.add('hidden');
    dom.answerBox.classList.remove('hidden');
    dom.sourcesContainer.innerHTML = '';
    dom.chunksContainer.innerHTML = '';

    let formattedAnswer = data.answer.replace(/\[TRECHOS?\s*(\d+)\]/gi, (match, numero) => {
        return `<span class="trecho-highlight" data-trecho="${numero}">${match}</span>`;
    });

    formattedAnswer = formattedAnswer
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/(^|\n)\*\s/g, '$1• ');
        
    dom.answerText.innerHTML = formattedAnswer.replace(/\n\n/g, '<br><br>');

    // Passo 3: Renderiza os Chunks Ocultos na Gaveta
    if (data.chunks && data.chunks.length > 0) {
        data.chunks.forEach(chunk => {
            const card = document.createElement('div');
            card.className = 'chunk-card';
            card.dataset.num = chunk.num;

            const header = document.createElement('div');
            header.style.display = 'flex';
            header.style.justifyContent = 'space-between';
            header.style.alignItems = 'center';
            header.style.marginBottom = '10px';

            const title = document.createElement('h4');
            title.style.margin = '0';
            title.textContent = `Trecho ${chunk.num}`;
        
            const btnLeitura = document.createElement('button');
            btnLeitura.className = 'btn-outline';
            btnLeitura.style.width = 'fit-content'; 
            btnLeitura.style.padding = '4px 10px';
            btnLeitura.style.fontSize = '0.75rem';
            btnLeitura.style.minHeight = 'unset'; 
            btnLeitura.innerHTML = `Ler no Contexto <i data-lucide="book-open" class="icon-sm" style="margin-left: 6px;"></i>`;
        
            header.appendChild(title);
            header.appendChild(btnLeitura);

            // Formata a Gaveta
            const text = document.createElement('p');
            let cleanGaveta = chunk.text.replace(/\[SEÇÃO:.*?\]\s*/gi, '').trim();
            cleanGaveta = cleanGaveta.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            text.innerHTML = cleanGaveta;
            text.style.whiteSpace = 'pre-wrap'; 
            text.style.lineHeight = '1.6';
        
            card.appendChild(header);
            card.appendChild(text);
            dom.chunksContainer.appendChild(card);

            btnLeitura.addEventListener('click', async (e) => {
                e.stopPropagation();

                const fonteOriginal = data.sources.find(s => s.trechos && s.trechos.includes(chunk.num));
                if (!fonteOriginal) return alert('Impossível rastrear o documento original de origem deste trecho.');
                
                dom.resultView.classList.remove('active');
                dom.readingView.classList.add('active');
                
                dom.readingTitle.textContent = fonteOriginal.titulo;
                const link = fonteOriginal.link || fonteOriginal.url || fonteOriginal.drive_link || '#';
                dom.readingOriginalLink.href = link;

                dom.readingContent.innerHTML = `
                    <div style="text-align: center; margin-top: 60px; color: var(--text-muted);">
                        <i data-lucide="loader" class="icon-sm" style="animation: spin 1s linear infinite; margin-bottom: 10px;"></i> 
                        <p style="font-size: 0.9rem;">Recuperando páginas do acervo e alinhando ao Trecho ${chunk.num}...</p>
                    </div>
                `;
                lucide.createIcons();

                try {
                    const folderId = dom.folderSelector.value;
                    const res = await fetch(`/api/document-chunks?title=${encodeURIComponent(fonteOriginal.titulo)}&folder_id=${folderId}`);
                    
                    if (!res.ok) {
                        const errData = await res.json().catch(() => ({}));
                        throw new Error(errData.error || `Servidor retornou código ${res.status}`);
                    }
                    
                    const docData = await res.json();
                    dom.readingContent.innerHTML = ''; 
                    let targetElement = null;
                    
                    docData.chunks.forEach((c) => {
                        const chunkDiv = document.createElement('div');
                        chunkDiv.className = 'reading-chunk';
                        
                        if (c.section && c.section !== 'Geral') {
                            const secSpan = document.createElement('span');
                            secSpan.className = 'reading-chunk-section';
                            secSpan.textContent = c.section;
                            chunkDiv.appendChild(secSpan);
                        }

                        // CORREÇÃO VISUAL
                        let cleanText = c.content.replace(/\[SEÇÃO:.*?\]\s*/gi, '').trim();
                        cleanText = cleanText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                        
                        const textSpan = document.createElement('span');
                        textSpan.className = 'chunk-text-content';
                        textSpan.innerHTML = cleanText;
                        textSpan.style.whiteSpace = 'pre-wrap'; 
                        chunkDiv.appendChild(textSpan);
                        
                        const btnTranslate = document.createElement('button');
                        btnTranslate.className = 'btn-translate-chunk';
                        btnTranslate.title = 'Traduzir este parágrafo';
                        btnTranslate.innerHTML = `<i data-lucide="languages" style="width: 15px; height: 15px;"></i>`;
                        chunkDiv.appendChild(btnTranslate);
                        
                        const cleanBankText = c.content.replace(/\s+/g, '').toLowerCase();
                        const cleanTargetText = chunk.text.replace(/\s+/g, '').toLowerCase();
                        
                        if (cleanBankText.includes(cleanTargetText) || cleanTargetText.includes(cleanBankText)) {
                            chunkDiv.style.borderLeft = '4px solid var(--primary)';
                            chunkDiv.style.paddingLeft = '16px';
                            targetElement = chunkDiv; 
                        }
                        
                        dom.readingContent.appendChild(chunkDiv);
                        
                        btnTranslate.addEventListener('click', async (evt) => {
                            evt.stopPropagation();
                            if (chunkDiv.classList.contains('translating-pulse')) return;
                            
                            chunkDiv.classList.add('translating-pulse');
                            btnTranslate.style.opacity = '0'; 
                            
                            try {
                                const tRes = await fetch('/api/translate', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ text: c.content })
                                });
                                
                                if (!tRes.ok) throw new Error();
                                const tData = await tRes.json();

                                let translatedClean = tData.translation.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                                
                                // INJEÇÃO DA TRADUÇÃO
                                textSpan.innerHTML = `<strong style="color: var(--primary);">[Tradução Original]:</strong>\n\n${translatedClean}`;
                                textSpan.style.color = 'var(--text-main)';
                            } catch (err) {
                                alert('Incapaz de obter tradução da inteligência central. Tente novamente.');
                                btnTranslate.style.opacity = '1';
                            } finally {
                                chunkDiv.classList.remove('translating-pulse');
                            }
                        });
                    });
                    
                    lucide.createIcons();
                    
                    if (targetElement) {
                        setTimeout(() => {
                            targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }, 150); 
                    }
                    
                } catch (err) {
                    console.error("Erro no Fetch do Modo Leitura:", err);
                    dom.readingContent.innerHTML = `
                        <p style="color: var(--primary); text-align: center; margin-top: 40px; font-size: 0.9rem;">
                           <i data-lucide="alert-triangle" class="icon-sm"></i> Falha no acervo completo: ${err.message}
                        </p>
                    `;
                    lucide.createIcons();
                }
            });
        }); 
    }

    // Passo 4: Renderiza as Referências
    if (data.sources && data.sources.length > 0) {
        data.sources.forEach(source => {
            const card = document.createElement('div');
            card.className = 'source-card';
     
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
                
                const link = source.link || source.url || source.drive_link;
                if (link) window.open(link, '_blank');
            });
        });
    } else {
        dom.sourcesContainer.innerHTML = '<p class="no-sources-msg">Nenhuma fonte direta indexada.</p>';
    }

    // Passo 5: Eventos de clique nas tags [TRECHO X]
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
            dom.mobileOverlay.classList.add('active');

            document.querySelectorAll('.chunk-card').forEach(c => {
                if (c.dataset.num === numeroTrecho) {
                    c.classList.add('active-chunk');
                } else {
                    c.classList.remove('active-chunk');
                }           
            });
        });
    });

    // CORREÇÃO FINAL: Garante que todos os ícones desenhados nas linhas acima vão aparecer de primeira!
    lucide.createIcons();
}