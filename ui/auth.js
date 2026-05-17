/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

export const appState = {
    supabaseClient: null,
    userToken: null,
    folderId: "f7faf7d9-ec80-46c6-9572-174865bf1e62", 
    isAuthLoaded: false,
    googleToken: null,
    googleApiKey: null,
    googleAppId: null,
    pickerApiLoaded: false
};

export const PUBLIC_FOLDER_ID = "f7faf7d9-ec80-46c6-9572-174865bf1e62";

const gScript = document.createElement('script');
gScript.src = 'https://apis.google.com/js/api.js';
gScript.onload = () => gapi.load('picker', () => { appState.pickerApiLoaded = true; });
document.body.appendChild(gScript);

export async function initAuth(onSessionUpdate) {
    try {
        const res = await fetch('/api/config');
        const config = await res.json();

        appState.supabaseClient = window.supabase.createClient(config.url, config.key);
        appState.googleApiKey = config.googleApiKey;
        appState.googleAppId = config.googleAppId;

        const { data: { session } } = await appState.supabaseClient.auth.getSession();
        if (session?.provider_token) localStorage.setItem('snoopy_g_token', session.provider_token);
        appState.googleToken = localStorage.getItem('snoopy_g_token');
        
        await onSessionUpdate(session);

        appState.supabaseClient.auth.onAuthStateChange(async (event, newSession) => {
            if (event === 'SIGNED_IN') {
                if (newSession?.provider_token) localStorage.setItem('snoopy_g_token', newSession.provider_token);
                appState.googleToken = localStorage.getItem('snoopy_g_token');
            }
            if (event === 'SIGNED_IN' || event === 'SIGNED_OUT') {
                await onSessionUpdate(newSession);
            }
        });
    } catch (error) {
        console.error("Erro Crítico na inicialização do auth:", error);
    }
}

export async function login() {
    await appState.supabaseClient.auth.signInWithOAuth({
        provider: 'google',
        options: { scopes: 'https://www.googleapis.com/auth/drive.readonly' }
    });
}

export async function logout() {
    console.log("Sinal de Logout enviado ao Supabase...");
    localStorage.removeItem('snoopy_g_token');
    try { await appState.supabaseClient.auth.signOut(); } catch(err) { console.error(err); }
    window.location.reload(); 
}

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
        console.error("Erro ao verificar acervo:", err);
        return null;
    }
}

export async function linkDriveFolder(folderName, driveFolderId) {
    try {
        const { data: { user } } = await appState.supabaseClient.auth.getUser();
        const { data: existingFolder } = await appState.supabaseClient
            .from('folders')
            .select('id')
            .eq('user_id', user.id)
            .eq('drive_id', driveFolderId)
            .maybeSingle();

        if (existingFolder) {
            await appState.supabaseClient
                .from('folders')
                .update({ is_active: true, name: folderName }) 
                .eq('id', existingFolder.id);
        } else {
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
        console.error("Erro ao vincular pasta no banco:", error);
        alert("Erro ao vincular a pasta no Drive");
    }
}

export async function disconnectFolder() {
    if (!appState.folderId || appState.folderId === PUBLIC_FOLDER_ID) return;
    
    const confirmDisconnect = confirm("Deseja desconectar este acervo? Ele não aparecerá mais nas suas buscas, mas os dados processados continuarão salvos na nuvem.");
    if (!confirmDisconnect) return;

    try {
        await appState.supabaseClient
            .from('folders')
            .update({ is_active: false })
            .eq('id', appState.folderId);
        console.log("Acervo desconectado com sucesso (Soft Delete).");
        window.location.reload(); 
    } catch (error) {
        console.error("Erro ao desconectar acervo:", error);
        alert("Erro ao desconectar o acervo.");
    }
}