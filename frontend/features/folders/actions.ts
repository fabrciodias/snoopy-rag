import {
    createFolder,
    deleteFolder,
    listFolders,
} from "./api";

import {
    folderState,
    setFolderError,
} from "../../state/folders";

import type {
    CreateFolderRequest,
} from "./contracts";

export async function loadFolders(): Promise<void> {
    folderState.isLoading = true;
    folderState.error = null;

    try {
        const folders =
            await listFolders();

        folderState.folders =
            folders;

        if (
            !folderState.selectedFolderId &&
            folders.length > 0
        ) {
            folderState.selectedFolderId =
                folders[0].id;
        }

        const selectedExists =
            folderState.folders.some(
                (folder) =>
                    folder.id ===
                    folderState.selectedFolderId,
            );

        if (
            folderState.selectedFolderId &&
            !selectedExists
        ) {
            folderState.selectedFolderId =
                folders[0]?.id ??
                null;
        }
    } catch (error) {
        setFolderError(error);
        throw error;
    } finally {
        folderState.isLoading =
            false;
    }
}

export function selectFolder(
    folderId: string,
): void {
    folderState.selectedFolderId =
        folderId;
}

export async function addFolder(
    request: CreateFolderRequest,
): Promise<void> {
    folderState.isCreating = true;
    folderState.error = null;

    try {
        const folder =
            await createFolder(
                request,
            );

        await loadFolders();

        folderState.selectedFolderId =
            folder.id;
    } catch (error) {
        setFolderError(error);
        throw error;
    } finally {
        folderState.isCreating =
            false;
    }
}

export async function removeFolder(
    folderId: string,
): Promise<void> {
    folderState.error = null;

    try {
        await deleteFolder(folderId);

        await loadFolders();
    } catch (error) {
        setFolderError(error);
        throw error;
    }
}