import {
    apiRequest,
} from "./client";

import type {
    Folder,
} from "../../stores/application";

export async function getFolders(): Promise<Folder[]> {
    return apiRequest<Folder[]>(
        "/folders/",
    );
}