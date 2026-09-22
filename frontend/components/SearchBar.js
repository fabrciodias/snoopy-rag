
export function SearchBar({
    container,
    state,
    onInvestigate,
    onSync,
}) {
    container.innerHTML = `
        <section class="search-panel">
            <div class="field">
                <label for="folder-id">Acervo</label>
                <input
                    id="folder-id"
                    type="text"
                    placeholder="ID do acervo"
                    value="${state.folderId}"
                />
            </div>

            <div class="field">
                <label for="query">Investigação</label>
                <textarea
                    id="query"
                    rows="3"
                    placeholder="Digite a pergunta da investigação..."
                ></textarea>
            </div>

            <div class="actions">
                <button id="investigate-button">
                    Investigar
                </button>

                <button id="sync-button" type="button">
                    Sincronizar Drive
                </button>
            </div>

            <p id="search-status" class="status"></p>
        </section>
    `;

    const folderInput = container.querySelector("#folder-id");
    const queryInput = container.querySelector("#query");
    const status = container.querySelector("#search-status");

    folderInput.addEventListener("change", () => {
        state.folderId = folderInput.value.trim();
    });

    queryInput.addEventListener("input", () => {
        state.query = queryInput.value;
    });

    queryInput.addEventListener("keydown", async (event) => {
        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {
            event.preventDefault();
            await onInvestigate();
        }
    });

    container
        .querySelector("#investigate-button")
        .addEventListener("click", onInvestigate);

    container
        .querySelector("#sync-button")
        .addEventListener("click", onSync);

    return {
        setStatus(message) {
            status.textContent = message || "";
        },

        setBusy(busy) {
            container
                .querySelector("#investigate-button")
                .disabled = busy;

            container
                .querySelector("#sync-button")
                .disabled = busy;
        },
    };
} 
