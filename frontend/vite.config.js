import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig({
    plugins: [vue()],
    server: {
        proxy: {
            "/config": {
                target: "http://localhost:3000",
            },
            "/folders": {
                target: "http://localhost:3000",
            },
            "/investigate": {
                target: "http://localhost:3000",
            },
            "/history": {
                target: "http://localhost:3000",
            },
            "/documents": {
                target: "http://localhost:3000",
            },
            "/operations": {
                target: "http://localhost:3000",
            },
            "/sync-drive": {
                target: "http://localhost:3000",
            },
            "/translate": {
                target: "http://localhost:3000",
            },
        },
    },
});
