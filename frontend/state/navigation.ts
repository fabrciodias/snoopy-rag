import {
    reactive,
} from "vue";

export type ViewName =
    | "home"
    | "investigation"
    | "reading";

export interface NavigationState {
    currentView: ViewName;
}

export const navigationState =
    reactive<NavigationState>({
        currentView: "home",
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

export function goToReading(): void {
    navigateTo("reading");
}