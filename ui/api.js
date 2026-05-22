// 1. IMPORTAÇÕES
import { appState } from './auth.js';

// 2. OPERAÇÕES DE HISTÓRICO (Supabase)
export async function fetchHistory() {
    if (!appState.userToken || !appState.supabaseClient) return [];
    
    try {
        const { data: { user } } = await appState.supabaseClient.auth.getUser();
        const { data: history, error } = await appState.supabaseClient
            .from('search_history')
            .select('query')
            .eq('user_id', user.id)
            .order('created_at', { ascending: false })
            .limit(15);

        if (error) throw error;
        
        // Retorna apenas queries únicas (remove duplicados do array)
        return history ? [...new Set(history.map(item => item.query))] : [];
    } catch (error) {
        console.error("[API] Erro ao carregar histórico da nuvem:", error);
        return [];
    }
}

export async function saveHistory(query) {
    if (!appState.userToken || !appState.supabaseClient) return; 
    
    try {
        const { data: { user } } = await appState.supabaseClient.auth.getUser();
        await appState.supabaseClient
            .from('search_history')
            .insert([{ user_id: user.id, query: query }]);
    } catch (error) {
        console.error("[API] Erro ao salvar histórico na nuvem:", error);
    }
}


// 3. SERVIÇOS DE STREAMING (Node.js / Python)
export async function streamSearch(query, callbacks) {
    const { onLog, onResult, onError } = callbacks;
    
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (appState.userToken) headers['Authorization'] = `Bearer ${appState.userToken}`;

        const response = await fetch('/api/search', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ query, folder_id: appState.folderId })
        });

        await readStream(response, onLog, onResult, onError);
    } catch (error) {
        onError(error.message);
    }
}

export async function streamSync(callbacks) {
    const { onLog, onResult, onError } = callbacks;
    
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (appState.userToken) headers['Authorization'] = `Bearer ${appState.userToken}`;

        const response = await fetch('/api/sync', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ folder_id: appState.folderId, google_token: appState.googleToken })
        });

        await readStream(response, onLog, () => onResult("Sincronização Finalizada!"), onError);
    } catch (error) {
        onError(error.message);
    }
}


// 4. FUNÇÕES UTILITÁRIAS (Parser de SSE)
async function readStream(response, onLog, onResult, onError) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let done = false;
    let buffer = "";

    while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        
        if (value) {
            buffer += decoder.decode(value, { stream: true });
            
            // Separa as mensagens pelo padrão duplo \n\n do SSE
            const messages = buffer.split('\n\n');
            
            // O último elemento pode estar incompleto, volta pro buffer
            buffer = messages.pop();

            for (const msg of messages) {
                if (msg.startsWith('data: ')) {
                    const jsonStr = msg.replace('data: ', '');
                    if(!jsonStr.trim()) continue;
                    
                    try {
                        const payload = JSON.parse(jsonStr);
                        
                        if (payload.type === 'log') {
                            onLog(payload.message);
                        } else if (payload.type === 'result') {
                            onResult(payload.data || payload.status);
                        } else if (payload.type === 'error') {
                            throw new Error(payload.message);
                        }
                    } catch (e) {
                        console.error("[API] Erro no parser do stream:", e, jsonStr);
                    }
                }
            }
        }
    }
}