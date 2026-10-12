export interface FrontendConfig {
    url: string;
    key: string;
    googleApiKey: string;
    googleAppId: string;
}

let configPromise: Promise<FrontendConfig> | null = null;

export function loadConfig(): Promise<FrontendConfig> {
    if (!configPromise) {
        configPromise = fetch("/config")
            .then(async (response) => {
                if (!response.ok) {
                    throw new Error(
                        `Falha ao carregar configuração (${response.status}).`,
                    );
                }

                return response.json() as Promise<FrontendConfig>;
            });
    }

    return configPromise;
}