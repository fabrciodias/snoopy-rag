export interface Folder {
    id: string;
    user_id: string;
    name: string;
    drive_id: string;
    is_active: boolean;
    created_at: string;
}

export interface CreateFolderRequest {
    drive_id: string;
    name: string;
}