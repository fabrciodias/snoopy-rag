/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */
 
require('dotenv').config();
const express = require('express');
const { createClient } = require('@supabase/supabase-js');
const { spawn } = require('child_process');
const path = require('path');
const crypto = require('crypto');
const fs = require('fs');

const WebSocket = require('ws');
global.WebSocket = WebSocket;

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
    auth: {
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false
    }
});

const app = express();
app.use(express.json());
app.use(express.static('ui'));

const cache = {};

app.get('/api/config', (req, res) => {
    res.json({
        url: SUPABASE_URL,
        key: SUPABASE_KEY,
        googleApiKey: process.env.GOOGLE_API_KEY,
        googleAppId: process.env.GOOGLE_APP_ID
    });
});

app.post('/api/search', async (req, res) => {
    const { query, folder_id } = req.body;
    
    if (!query) return res.status(400).json({error: "Pergunta vazia" });
    if (!folder_id) return res.status(400).json({error: "ID da pasta não fornecido" });

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    let userId = '00000000-0000-0000-0000-000000000000';
    const token = req.headers.authorization?.split(' ')[1];

    if (token) {
        const { data: { user }, error } = await supabase.auth.getUser(token);
        if (!error && user) userId = user.id;
    }

    const hash = crypto.createHash('md5').update(`${userId}_${folder_id}_${query}`).digest('hex');
    
    if (cache[hash]) {
        console.log(`[CACHE HIT] Poupando API. Resposta da memória para: "${query}" (User: ${userId}, Acervo: ${folder_id})`);
        res.write(`data: ${JSON.stringify({ type: 'log', message: 'Recuperando resposta da memória local...' })}\n\n`);
        res.write(`data: ${JSON.stringify({ type: 'result', data: cache[hash] })}\n\n`);
        return res.end();
    }

    console.log(`[MOTOR V2] Usuário ${userId} pesquisando: "${query}" no Acervo: ${folder_id}`);

    const pythonProcess = spawn('./.venv/bin/python3', ['src/search.py', query, userId, folder_id, GEMINI_API_KEY]);
    let rawOutput = '';

    pythonProcess.stdout.on('data', (data) => {
        rawOutput += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        const output = data.toString().split('\n');
        for (const line of output) {
            const msg = line.trim();
            if (msg.startsWith('UI_LOG::')) {
                const cleanMsg = msg.replace('UI_LOG::', '');
                res.write(`data: ${JSON.stringify({ type: 'log', message: cleanMsg })}\n\n`);
            } else if (msg) {
                console.log(`[PYTHON SYSTEM]: ${msg}`)
            }
        }
    });

    pythonProcess.on('close', (code) => {
        try {
            const jsonMatch = rawOutput.match(/\{[\s\S]*\}/);
            if (!jsonMatch) throw new Error("JSON não encontrado na saída do Python.");
            const jsonResponse = JSON.parse(jsonMatch[0]);

            if (!jsonResponse.error) {
                cache[hash] = jsonResponse;
            }
            res.write(`data: ${JSON.stringify({ type: 'result', data: jsonResponse })}\n\n`);
            res.end();
        } catch (e) {
            console.log("[ERRO FATAL] Falha no parser:", rawOutput);
            res.write(`data: ${JSON.stringify({ type: 'error', message: 'Falha na comunicação com o motor semântico.' })}\n\n`);
            res.end();
        }
    });
});

app.post('/api/sync', async (req, res) => {
    const { folder_id, google_token } = req.body;
    
    if (!folder_id || !google_token) {
        return res.status(400).json({ error: "Parâmetros folder_id ou google_token ausentes." });
    }

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const sendLog = (message) => {
        res.write(`data: ${JSON.stringify({ type: 'log', message })}\n\n`);
    };

    try {
        let userId = '00000000-0000-0000-0000-000000000000';
        const token = req.headers.authorization?.split(' ')[1];

        if (token) {
            const { data: { user }, error } = await supabase.auth.getUser(token);
            if (!error && user) userId = user.id;
        }

        sendLog("Buscando metadados do acervo no banco...");
        const { data: folderData, error: folderError } = await supabase
            .from('folders')
            .select('drive_id')
            .eq('id', folder_id)
            .single();

        if (folderError || !folderData?.drive_id) {
            throw new Error("Acervo não encontrado ou sem pasta no Drive vinculada.");
        }

        const driveId = folderData.drive_id;
        sendLog("Conectando à API do Google Drive...");

        const driveUrl = `https://www.googleapis.com/drive/v3/files?q='${driveId}' in parents and mimeType='application/pdf' and trashed=false&fields=files(id, name, webViewLink)`;
        
        const driveRes = await fetch(driveUrl, {
            headers: { 'Authorization': `Bearer ${google_token}` } 
        });
        const driveData = await driveRes.json();
        const googleFiles = driveData.files || [];

        if (googleFiles.length === 0) {
            sendLog("Sincronização concluída. Nenhum PDF encontrado no Drive.");
            res.write(`data: ${JSON.stringify({ type: 'result', status: 'empty' })}\n\n`);
            return res.end();
        }

        const { data: dbDocs } = await supabase
            .from('documents')
            .select('drive_file_id')
            .eq('folder_id', folder_id);

        const processedFileId = new Set(dbDocs?.map(d => d.drive_file_id || []));
        const newFiles = googleFiles.filter(f => !processedFileId.has(f.id));

        if (newFiles.length === 0) {
            sendLog("Sincronização concluída. O acervo está atualizado.");
            res.write(`data: ${JSON.stringify({ type: 'result', status: 'up-to-date' })}\n\n`);
            return res.end();
        }

        sendLog(`Encontrado ${newFiles.length} novo(s) arquivo(s). Iniciando esteira sequencial...`);
        for (let i = 0; i < newFiles.length; i++) {
            const file = newFiles[i];
            const currentIdx = i+1;

            sendLog(`[${currentIdx}/${newFiles.length}] Baixando binário de: "${file.name}"...`);
            const downloadUrl = `https://www.googleapis.com/drive/v3/files/${file.id}?alt=media`;
            
            const downloadRes = await fetch(downloadUrl, {
                headers: { 'Authorization': `Bearer ${google_token}` }
            });

            if (!downloadRes.ok) {
                console.error(`Falha ao baixar ${file.name}`);
                continue; 
            }

            const arrayBuffer = await downloadRes.arrayBuffer();
            const buffer = Buffer.from(arrayBuffer);

            const tempDir = path.join(__dirname, 'data', 'raw_pdfs');
            if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });

            const tempPath = path.join(tempDir, `${file.id}.pdf`);
            fs.writeFileSync(tempPath, buffer);

            sendLog(`[${currentIdx}/${newFiles.length}] Triturando e vetorizando: "${file.name}"...`);

            await new Promise((resolve) => {
                const pythonProcess = spawn('./.venv/bin/python3', [
                    'src/pipeline.py', 
                    tempPath, 
                    file.id, 
                    userId, 
                    folder_id, 
                    file.webViewLink
                ]);

                pythonProcess.stdout.on('data', (data) => {
                    const lines = data.toString().split('\n');
                    for (const line of lines) {
                        if (line.trim()) console.log(`[PYTHON PIPELINE]: ${line.trim()}`);
                    }
                });

                pythonProcess.stderr.on('data', (data) => {
                    const lines = data.toString().split('\n');
                    for (const line of lines) {
                        const msg = line.trim();
                        if (msg && !msg.includes("DEBUG") && !msg.includes("INFO")) {
                            console.log(`[PIPELINE SYS LOG]: ${msg}`);
                        }
                    }
                });

                pythonProcess.on('close', (code) => {
                    try { if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath); } catch(e) {}
                    resolve();
                });
            });
        }

        sendLog("Sincronização concluída com sucesso! Atualizando acervo...");
        res.write(`data: ${JSON.stringify({ type: 'result', status: 'success' })}\n\n`);
        res.end();

    } catch (error) {
        console.error("[ERRO CRÍTICO NO SYNC]:", error);
        res.write(`data: ${JSON.stringify({ type: 'error', message: error.message })}\n\n`);
        res.end();
    }
});

const PORT = 3333;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`\n=========================================`);
    console.log(`SNOOPY-RAG V2 (SaaS) ATIVADO`);
    console.log(`Acesse: http://localhost:${PORT}`);
    console.log(`=========================================\n`);
});