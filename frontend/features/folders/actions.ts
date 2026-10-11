import {
    createFolder,
    deleteFolder,
    listFolders,
} from "./api";

import {
    folderState,
    setFolderError,
} from "../../state/folders";

import {
    invalidateActiveWork,
} from "../../state/workContext";

import type {
    CreateFolderRequest,
} from "./contracts";

let folderRequestVersion = 0;

export async function loadFolders(): Promise<void> {
    const requestVersion = ++folderRequestVersion;

    folderState.isLoading = true;
    folderState.error = null;

    try {
        const folders = await listFolders();

        if (requestVersion !== folderRequestVersion) {
            return;
        }

        const previousSelectedId =
            folderState.selectedFolderId;

        const selectedStillExists = folders.some(
            (folder) => folder.id === previousSelectedId,
        );

        folderState.folders = folders;

        if (
            previousSelectedId &&
            selectedStillExists
        ) {
            return;
        }

        if (previousSelectedId) {
            invalidateActiveWork();
        }

        folderState.selectedFolderId =
            folders[0]?.id ?? null;
    } catch (error) {
        if (requestVersion !== folderRequestVersion) {
            return;
        }

        setFolderError(error);
        throw error;
    } finally {
        if (requestVersion === folderRequestVersion) {
            folderState.isLoading = false;
        }
    }
}

export function selectFolder(
    folderId: string,
): void {
    if (folderState.selectedFolderId === folderId) {
        return;
    }

    invalidateActiveWork();

    folderState.selectedFolderId = folderId;
}

export async function addFolder(
    request: CreateFolderRequest,
): Promise<void> {
    folderState.isCreating = true;
    folderState.error = null;

    try {
        const folder = await createFolder(request);

        await loadFolders();

        selectFolder(folder.id);
    } catch (error) {
        setFolderError(error);
        throw error;
    } finally {
        folderState.isCreating = false;
    }
}

export async function removeFolder(
    folderId: string,
): Promise<void> {
    folderState.error = null;

    const isSelectedFolder =
        folderState.selectedFolderId === folderId;

    try {
        await deleteFolder(folderId);

        if (isSelectedFolder) {
            invalidateActiveWork();
            folderState.selectedFolderId = null;
        }

        await loadFolders();
    } catch (error) {
        setFolderError(error);
        throw error;
    }
}