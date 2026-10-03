import {
    listFolders,
} from "./api";

import {
    folderState,
    setFolderError,
} from "../../state/folders";

export async function loadFolders(): Promise<void> {
    folderState.isLoading = true;
    folderState.error = null;

    try {
        const folders =
            await listFolders();

        folderState.folders = folders;

        if (
            !folderState.selectedFolderId &&
            folders.length > 0
        ) {
            folderState.selectedFolderId =
                folders[0].id;
        }
    } catch (error) {
        setFolderError(error);
        throw error;
    } finally {
        folderState.isLoading = false;
    }
}

export function selectFolder(
    folderId: string,
): void {
    folderState.selectedFolderId =
        folderId;
}