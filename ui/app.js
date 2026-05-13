const homeView = document.getElementById('home-view');
const resultView = document.getElementById('result-view');
const homeForm = document.getElementById('search-home');
const navForm = document.getElementById('search-nav');
const queryDisplay = document.getElementById('query-title');
const loadingState = document.getElementById('loading-state');
const answerBox = document.getElementById('answer-box');
const answerText = document.getElementById('answer-text');
const sourcesContainer = document.getElementById('sources-container');

async function performSearch(query) {
    if (!query.trim()) return;

    homeView.classList.remove('active');
    resultView.classList.add('active');
    
    document.getElementById('input-nav').value = query;
    queryDisplay.textContent = query;
    answerBox.classList.add('hidden');
    sourcesContainer.innerHTML = '';
    loadingState.classList.remove('hidden');

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });

        const data = await response.json();
        if (data.error) throw new Error(data.error);

        renderResults(data);
        
    } catch (error) {
        loadingState.classList.add('hidden');
        answerBox.classList.remove('hidden');
        answerText.innerHTML = `<span style="color: red;"><strong>Erro:</strong> ${error.message}</span>`;
    }
}

function renderResults(data) {
    loadingState.classList.add('hidden');
    answerBox.classList.remove('hidden');

    let formattedAnswer = data.answer.replace(/\[TRECHO (\d+)\]/g, '<span class="trecho-highlight">[Trecho $1]</span>');
    formattedAnswer = formattedAnswer.replace(/\n\n/g, '<br><br>');
    
    answerText.innerHTML = formattedAnswer;

    if (data.sources && data.sources.length > 0) {
        data.sources.forEach((source, index) => {
            const card = document.createElement('div');
            card.className = 'source-card';
            
            const driveBtn = source.link !== 'Link indisponível' 
                ? `<a href="${source.link}" target="_blank" class="drive-link">Abrir no Drive ↗</a>` 
                : `<span class="drive-link" style="opacity: 0.5; cursor: not-allowed;">Link indisponível</span>`;

            card.innerHTML = `
                <div class="badge-secao">Trecho ${index + 1} | ${source.secao.substring(0, 30)}...</div>
                <h4>${source.titulo}</h4>
                <p style="font-size: 0.8rem; color: #6b7280; margin-bottom: 10px;">Arq: ${source.arquivo}</p>
                ${driveBtn}
            `;
            sourcesContainer.appendChild(card);
        });
    } else {
        sourcesContainer.innerHTML = '<p style="color: #6b7280; font-size: 0.9rem;">Nenhuma fonte direta indexada para esta resposta.</p>';
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