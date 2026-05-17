/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

export const dom = {
    homeView: document.getElementById('home-view'),
    resultView: document.getElementById('result-view'),
    homeForm: document.getElementById('search-home'),
    navForm: document.getElementById('search-nav'),
    inputHome: document.getElementById('input-home'),
    inputNav: document.getElementById('input-nav'),
    queryDisplay: document.getElementById('query-title'),
    loadingState: document.getElementById('loading-state'),
    answerBox: document.getElementById('answer-box'),
    answerText: document.getElementById('answer-text'),
    sourcesContainer: document.getElementById('sources-container'),
    liveLogs: document.getElementById('live-logs'),
    btnLogin: document.getElementById('btn-login'),
    btnLogout: document.getElementById('btn-logout'),
    userInfo: document.getElementById('user-info'),
    userAvatar: document.getElementById('user-avatar'),
    folderContainer: document.getElementById('folder-container'),
    folderSelector: document.getElementById('folder-selector'),
    btnSync: document.getElementById('btn-sync'),
    syncLogs: document.getElementById('sync-logs'),
    btnDrive: document.getElementById('btn-drive'),
    historyList: document.getElementById('history-list')
};

export function resetToHome() {
    dom.resultView.classList.remove('active');
    dom.homeView.classList.add('active');
    dom.inputHome.value = '';
    dom.inputNav.value = '';
    dom.queryDisplay.textContent = '';
    dom.answerBox.classList.add('hidden');
    dom.sourcesContainer.innerHTML = '';
    dom.loadingState.classList.add('hidden');
    dom.liveLogs.textContent = '';
}

export function showSearchState(query) {
    dom.homeView.classList.remove('active');
    dom.resultView.classList.add('active');
    dom.inputNav.value = query;
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

    let formattedAnswer = data.answer.replace(/\[(TRECHOS?[^\]]+)\]/gi, '<span class="trecho-highlight">[$1]</span>');
    dom.answerText.innerHTML = formattedAnswer.replace(/\n\n/g, '<br><br>');
    dom.sourcesContainer.innerHTML = '';

    if (data.sources && data.sources.length > 0) {
        data.sources.forEach(source => {
            const card = document.createElement('div');
            card.className = 'source-card';
            
            const badge = document.createElement('div');
            badge.className = 'badge-secao';
            badge.textContent = `Trechos Referenciados: ${source.trechos ? source.trechos.join(', ') : 'N/A'}`;
            
            const title = document.createElement('h4');
            title.textContent = source.titulo;
            
            const meta = document.createElement('p');
            meta.className = 'source-meta';
            meta.textContent = `Arq: ${source.arquivo}`;
            
            card.append(badge, title, meta);

            if (source.link !== 'Link indisponível') {
                const link = document.createElement('a');
                link.href = source.link;
                link.target = '_blank';
                link.className = 'drive-link';
                link.textContent = 'Abrir no Drive ↗';
                card.appendChild(link);
            } else {
                const noLink = document.createElement('span');
                noLink.className = 'drive-link link-disabled';
                noLink.textContent = 'Link indisponível';
                card.appendChild(noLink);
            }
            dom.sourcesContainer.appendChild(card);
        });
    } else {
        dom.sourcesContainer.innerHTML = '<p class="no-sources-msg">Nenhuma fonte direta indexada para esta resposta.</p>';
    }
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