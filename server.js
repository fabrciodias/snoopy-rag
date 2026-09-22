require('dotenv').config({ override: true });

const express = require('express');
const path = require('path');

const app = express();

const PORT = Number(process.env.PORT || 3001);
const V3_API_URL = (
    process.env.V3_API_URL ||
    'http://127.0.0.1:3000'
).replace(/\/$/, '');


// ============================================================
// 1. Express
// ============================================================

app.use(express.json({ limit: '2mb' }));
app.use(express.static(path.join(__dirname, 'ui')));

app.get('/favicon.ico', (req, res) => {
    res.status(204).end();
});


// ============================================================
// 2. Configuração pública do frontend
// ============================================================

app.get('/api/config', (req, res) => {
    res.json({
        url: process.env.SUPABASE_URL,
        key: process.env.SUPABASE_KEY,
        googleApiKey: process.env.GOOGLE_API_KEY,
        googleAppId: process.env.GOOGLE_APP_ID
    });
});


// ============================================================
// 3. Ponte para a V3 Alpha
// ============================================================

async function proxyToV3(req, res, targetPath) {
    try {
        const headers = {
            'Content-Type': 'application/json'
        };

        // A identidade do usuário é sempre transportada
        // pelo JWT do Supabase.
        if (req.headers.authorization) {
            headers.Authorization = req.headers.authorization;
        }

        const response = await fetch(
            `${V3_API_URL}${targetPath}`,
            {
                method: req.method,
                headers,
                body: req.method === 'GET'
                    ? undefined
                    : JSON.stringify(req.body)
            }
        );

        const contentType =
            response.headers.get('content-type') ||
            'application/json';

        const body = await response.text();

        res.status(response.status);
        res.setHeader('Content-Type', contentType);
        res.send(body);

    } catch (error) {
        console.error(
            '[V3 PROXY] Falha na comunicação com a API:',
            error
        );

        res.status(502).json({
            error: 'Não foi possível comunicar com a API V3 Alpha.'
        });
    }
}


// ============================================================
// 4. Investigation
// ============================================================

app.post('/api/v3/investigate', async (req, res) => {
    await proxyToV3(
        req,
        res,
        '/investigate/'
    );
});


// ============================================================
// 5. Google Drive Sync
// ============================================================

app.post('/api/v3/sync-drive', async (req, res) => {
    await proxyToV3(
        req,
        res,
        '/sync-drive/'
    );
});


// ============================================================
// 6. Estado de operação
// ============================================================

app.get('/api/v3/operations/:operationId', async (req, res) => {
    await proxyToV3(
        req,
        res,
        `/operations/${encodeURIComponent(req.params.operationId)}`
    );
});


// ============================================================
// 7. Inicialização
// ============================================================

app.listen(PORT, '0.0.0.0', () => {
    console.log('');
    console.log('=========================================');
    console.log('SNOOPY-RAG — FRONTEND BRIDGE');
    console.log(`Frontend: http://localhost:${PORT}`);
    console.log(`V3 API:   ${V3_API_URL}`);
    console.log('=========================================');
    console.log('');
});