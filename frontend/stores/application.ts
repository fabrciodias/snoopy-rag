import type {
    User,
    Session,
} from "@supabase/supabase-js";

export const PUBLIC_FOLDER_ID =
    "f7faf7d9-ec80-46c6-9572-174865bf1e62";

export interface Folder {
    id: string;
    user_id?: string | null;
    name: string;
    drive_id?: string | null;
    is_active?: boolean;
    created_at?: string;
}

export interface ApplicationState {
    session: Session | null;
    user: User | null;
    userToken: string | null;

    googleToken: string | null;

    folders: Folder[];

    folderId: string;
    folderName: string;

    isAuthLoaded: boolean;

    theme: "dark" | "light";
}

export const applicationState: ApplicationState = {
    session: null,
    user: null,
    userToken: null,

    googleToken: null,

    folders: [],

    folderId: PUBLIC_FOLDER_ID,
    folderName: "Acervo Público",

    isAuthLoaded: false,

    theme: "dark",
};