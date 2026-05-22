// 1. ESTADO GLOBAL DE AUTENTICAÇÃO
export const appState = {
    supabaseClient: null,
    userToken: null,
    folderId: "f7faf7d9-ec80-46c6-9572-174865bf1e62", // Default: Acervo Público
    isAuthLoaded: false,
    googleToken: null,
    googleApiKey: null,
    googleAppId: null,
    pickerApiLoaded: false
};

export const PUBLIC_FOLDER_ID = "f7faf7d9-ec80-46c6-9572-174865bf1e62";

// 2. INJEÇÃO DE DEPENDÊNCIAS EXTERNAS (Google Picker)
const gScript = document.createElement('script');
gScript.src = 'https://apis.google.com/js/api.js';
gScript.onload = () => gapi.load('picker', () => { appState.pickerApiLoaded = true; });
document.body.appendChild(gScript);

// 3. INICIALIZAÇÃO E ESCUTA DE SESSÃO
export async function initAuth(onSessionUpdate) {
    try {
        // 3.1. Busca as chaves públicas no servidor
        const res = await fetch('/api/config');
        const config = await res.json();

        // 3.2. Inicializa o cliente do Supabase
        appState.supabaseClient = window.supabase.createClient(config.url, config.key, {
            auth: {
                storage: window.localStorage,
                autoRefreshToken: true,
                persistSession: true,
                detectSessionInUrl: true
            }
        });
        
        appState.googleApiKey = config.googleApiKey;
        appState.googleAppId = config.googleAppId;

        // 3.3. Restaura a sessão existente (se houver)
        const { data: { session } } = await appState.supabaseClient.auth.getSession();
        
        if (session?.provider_token) {
            localStorage.setItem('snoopy_g_token', session.provider_token);
        }
        appState.googleToken = localStorage.getItem('snoopy_g_token');
        
        await onSessionUpdate(session);

        // 3.4. Fica escutando mudanças na conta (Login/Logout)
        appState.supabaseClient.auth.onAuthStateChange(async (event, newSession) => {
            if (event === 'SIGNED_IN') {
                if (newSession?.provider_token) {
                    localStorage.setItem('snoopy_g_token', newSession.provider_token);
                }
                appState.googleToken = localStorage.getItem('snoopy_g_token');
            }
            if (event === 'SIGNED_IN' || event === 'SIGNED_OUT') {
                await onSessionUpdate(newSession);
            }
        });
    } catch (error) {
        console.error("[AUTH] Erro Crítico na inicialização:", error);
    }
}

// 4. AÇÕES DE CONTA (Login / Logout)
export async function login() {
    await appState.supabaseClient.auth.signInWithOAuth({
        provider: 'google',
        options: { scopes: 'https://www.googleapis.com/auth/drive.readonly' }
    });
}

export async function logout() {
    console.log("[AUTH] Sinal de Logout enviado ao Supabase...");
    localStorage.removeItem('snoopy_g_token');
    
    try { 
        await appState.supabaseClient.auth.signOut(); 
    } catch(err) { 
        console.error(err); 
    }
    
    window.location.reload(); 
}

// 5. OPERAÇÕES DE ACERVO (Banco de Dados)
export async function fetchUserFolder(userId) {
    try {
        const { data, error } = await appState.supabaseClient
            .from('folders')
            .select('id, name')
            .eq('user_id', userId)
            .eq('is_active', true)
            .limit(1)
            .maybeSingle();
        return data;
    } catch (err) {
        console.error("[AUTH] Erro ao verificar acervo:", err);
        return null;
    }
}

export async function linkDriveFolder(folderName, driveFolderId) {
    try {
        const { data: { user } } = await appState.supabaseClient.auth.getUser();
        
        // Verifica se a pasta já existe no banco (mesmo desativada)
        const { data: existingFolder } = await appState.supabaseClient
            .from('folders')
            .select('id')
            .eq('user_id', user.id)
            .eq('drive_id', driveFolderId)
            .maybeSingle();

        if (existingFolder) {
            // Reativa e atualiza o nome (Soft Undelete)
            await appState.supabaseClient
                .from('folders')
                .update({ is_active: true, name: folderName }) 
                .eq('id', existingFolder.id);
        } else {
            // Cria um novo registro de pasta
            await appState.supabaseClient
                .from('folders')
                .insert([{
                    user_id: user.id,
                    name: folderName,
                    drive_id: driveFolderId,
                    is_active: true
                }]);
        }
        
        window.location.reload();
    } catch (error) {
        console.error("[AUTH] Erro ao vincular pasta no banco:", error);
        alert("Erro ao vincular a pasta no Drive");
    }
}

export async function disconnectFolder() {
    if (!appState.folderId || appState.folderId === PUBLIC_FOLDER_ID) return;
    
    const confirmDisconnect = confirm("Deseja desconectar este acervo? Ele não aparecerá mais nas suas buscas, mas os dados processados continuarão salvos na nuvem.");
    if (!confirmDisconnect) return;

    try {
        // Soft Delete: Apenas marca como is_active = false
        await appState.supabaseClient
            .from('folders')
            .update({ is_active: false })
            .eq('id', appState.folderId);
            
        console.log("[AUTH] Acervo desconectado com sucesso (Soft Delete).");
        window.location.reload(); 
    } catch (error) {
        console.error("[AUTH] Erro ao desconectar acervo:", error);
        alert("Erro ao desconectar o acervo.");
    }
}