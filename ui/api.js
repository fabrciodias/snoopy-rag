import { appState } from './auth.js';


// ============================================================
// 1. Histórico
// ============================================================

export async function fetchHistory() {
    if (!appState.userToken || !appState.supabaseClient) {
        return [];
    }

    try {
        const {
            data: { user },
            error: userError
        } = await appState.supabaseClient.auth.getUser();

        if (userError || !user) {
            return [];
        }

        const { data: history, error } =
            await appState.supabaseClient
                .from('search_history')
                .select('query')
                .eq('user_id', user.id)
                .order('created_at', { ascending: false })
                .limit(15);

        if (error) {
            throw error;
        }

        return history
            ? [...new Set(history.map(item => item.query))]
            : [];

    } catch (error) {
        console.error(
            '[API] Erro ao carregar histórico:',
            error
        );

        return [];
    }
}


export async function saveHistory(query) {
    if (
        !appState.userToken ||
        !appState.supabaseClient ||
        !query
    ) {
        return;
    }

    try {
        const {
            data: { user },
            error: userError
        } = await appState.supabaseClient.auth.getUser();

        if (userError || !user) {
            return;
        }

        const { error } = await appState.supabaseClient
            .from('search_history')
            .insert([
                {
                    user_id: user.id,
                    query
                }
            ]);

        if (error) {
            throw error;
        }

    } catch (error) {
        console.error(
            '[API] Erro ao salvar histórico:',
            error
        );
    }
}


// ============================================================
// 2. Headers da API
// ============================================================

function getAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json'
    };

    if (appState.userToken) {
        headers.Authorization =
            `Bearer ${appState.userToken}`;
    }

    return headers;
}


// ============================================================
// 3. Investigação V3
// ============================================================

export async function streamSearch(query, callbacks) {
    const {
        onLog = () => {},
        onResult = () => {},
        onError = () => {}
    } = callbacks;

    if (!query?.trim()) {
        onError('A pergunta não pode estar vazia.');
        return;
    }

    if (!appState.userToken) {
        onError('Sessão não autenticada.');
        return;
    }

    try {
        onLog('Consultando o acervo...');

        const response = await fetch(
            '/api/v3/investigate',
            {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    folder_id: appState.folderId,
                    query: query.trim(),
                    limit: 5
                })
            }
        );

        const payload = await parseJsonResponse(response);

        if (!response.ok) {
            throw new Error(
                payload?.detail ||
                payload?.error ||
                'Falha na investigação.'
            );
        }

        onLog('Investigação concluída.');

        onResult(payload);

    } catch (error) {
        console.error(
            '[API V3] Falha na investigação:',
            error
        );

        onError(error.message);
    }
}


// ============================================================
// 4. Sincronização V3
// ============================================================

export async function streamSync(callbacks) {
    const {
        onLog = () => {},
        onResult = () => {},
        onError = () => {}
    } = callbacks;

    if (!appState.userToken) {
        onError('Sessão não autenticada.');
        return;
    }

    if (!appState.googleToken) {
        onError(
            'Token do Google indisponível. Faça login novamente.'
        );
        return;
    }

    try {
        onLog('Iniciando sincronização do acervo...');

        const response = await fetch(
            '/api/v3/sync-drive',
            {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    folder_id: appState.folderId,
                    google_token: appState.googleToken
                })
            }
        );

        const payload = await parseJsonResponse(response);

        if (!response.ok) {
            throw new Error(
                payload?.detail ||
                payload?.error ||
                'Falha ao iniciar sincronização.'
            );
        }

        const operationId = payload.operation_id;

        if (!operationId) {
            throw new Error(
                'A API não retornou o identificador da operação.'
            );
        }

        onLog(
            `Sincronização iniciada (${operationId}).`
        );

        const finalOperation =
            await waitForOperation(
                operationId,
                {
                    onUpdate: (operation) => {
                        onLog(
                            formatOperationStatus(operation)
                        );
                    }
                }
            );

        onResult(finalOperation);

    } catch (error) {
        console.error(
            '[API V3] Falha na sincronização:',
            error
        );

        onError(error.message);
    }
}


// ============================================================
// 5. Consulta do estado da operação
// ============================================================

export async function fetchOperation(operationId) {
    if (!operationId) {
        throw new Error(
            'Identificador da operação não fornecido.'
        );
    }

    const response = await fetch(
        `/api/v3/operations/${encodeURIComponent(operationId)}`,
        {
            method: 'GET',
            headers: getAuthHeaders()
        }
    );

    const payload = await parseJsonResponse(response);

    if (!response.ok) {
        throw new Error(
            payload?.detail ||
            payload?.error ||
            'Falha ao consultar operação.'
        );
    }

    return payload;
}


// ============================================================
// 6. Polling de operação
// ============================================================

async function waitForOperation(
    operationId,
    {
        onUpdate = () => {},
        intervalMs = 1500,
        timeoutMs = 15 * 60 * 1000
    } = {}
) {
    const startedAt = Date.now();

    while (true) {
        if (
            Date.now() - startedAt >
            timeoutMs
        ) {
            throw new Error(
                'Tempo limite excedido ao acompanhar a operação.'
            );
        }

        const operation =
            await fetchOperation(operationId);

        onUpdate(operation);

        const status =
            String(operation.status || '').toUpperCase();

        if (status === 'COMPLETED') {
            return operation;
        }

        if (
            status === 'FAILED' ||
            status === 'CANCELLED'
        ) {
            throw new Error(
                operation.error ||
                `A operação terminou com estado: ${status}.`
            );
        }

        await sleep(intervalMs);
    }
}


// ============================================================
// 7. Formatação de estado
// ============================================================

function formatOperationStatus(operation) {
    const status =
        String(operation?.status || '')
            .toUpperCase();

    switch (status) {
        case 'PENDING':
            return 'Sincronização aguardando processamento...';

        case 'PROCESSING':
            return 'Processando documentos do acervo...';

        case 'COMPLETED':
            return 'Sincronização concluída.';

        case 'FAILED':
            return 'Sincronização falhou.';

        case 'CANCELLED':
            return 'Sincronização cancelada.';

        default:
            return `Estado da operação: ${
                operation?.status || 'desconhecido'
            }`;
    }
}


// ============================================================
// 8. Parser HTTP
// ============================================================

async function parseJsonResponse(response) {
    const text = await response.text();

    if (!text) {
        return {};
    }

    try {
        return JSON.parse(text);
    } catch {
        return {
            error: text
        };
    }
}


// ============================================================
// 9. Utilidades
// ============================================================

function sleep(ms) {
    return new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}