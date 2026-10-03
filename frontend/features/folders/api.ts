import {
    apiRequest,
} from "../../infrastructure/api";

import type {
    CreateFolderRequest,
    Folder,
} from "./contracts";

export function listFolders(): Promise<Folder[]> {
    return apiRequest<Folder[]>(
        "/folders/",
    );
}

export function createFolder(
    request: CreateFolderRequest,
): Promise<Folder> {
    return apiRequest<Folder>(
        "/folders/",
        {
            method: "POST",
            body: JSON.stringify(request),
        },
    );
}

export function deleteFolder(
    folderId: string,
): Promise<{
    id: string;
    is_active: boolean;
}> {
    return apiRequest(
        `/folders/${folderId}`,
        {
            method: "DELETE",
        },
    );
}