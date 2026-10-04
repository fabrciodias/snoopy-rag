import {
    reactive,
} from "vue";

import type {
    DocumentLocation,
} from "../features/investigation/contracts";

export type ViewName =
    | "home"
    | "investigation"
    | "reading";

export interface ReadingNavigationState {
    documentId: string | null;
    location: DocumentLocation | null;
}

export interface NavigationState {
    currentView: ViewName;
    reading: ReadingNavigationState;
}

export const navigationState =
    reactive<NavigationState>({
        currentView: "home",
        reading: {
            documentId: null,
            location: null,
        },
    });

export function navigateTo(
    view: ViewName,
): void {
    navigationState.currentView =
        view;
}

export function goHome(): void {
    navigateTo("home");
}

export function goToInvestigation(): void {
    navigateTo("investigation");
}

export function goToReading(
    documentId: string,
    location: DocumentLocation,
): void {
    navigationState.reading.documentId =
        documentId;

    navigationState.reading.location =
        location;

    navigateTo("reading");
}