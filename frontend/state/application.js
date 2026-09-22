export const PUBLIC_FOLDER_ID =
    "f7faf7d9-ec80-46c6-9572-174865bf1e62";

export const appState = {
    supabaseClient: null,

    session: null,
    user: null,
    userToken: null,

    googleToken: null,
    googleApiKey: null,
    googleAppId: null,
    pickerApiLoaded: false,

    folders: [],
    folderId: PUBLIC_FOLDER_ID,
    folderName: "Acervo Público",

    isAuthLoaded: false,
};