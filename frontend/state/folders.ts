import {
    reactive,
} from "vue";

import type {
    Folder,
} from "../features/folders/contracts";

export interface FolderState {
    folders: Folder[];
    selectedFolderId: string | null;

    isLoading: boolean;
    isCreating: boolean;
    error: string | null;
}

export const folderState =
    reactive<FolderState>({
        folders: [],
        selectedFolderId: null,

        isLoading: false,
        isCreating: false,
        error: null,
    });

export function setFolderError(
    error: unknown,
): void {
    folderState.error =
        error instanceof Error
            ? error.message
            : String(error);
}