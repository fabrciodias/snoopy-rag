/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */
 
require('dotenv').config();
const express = require('express');
const { createClient } = require('@supabase/supabase-js');
const { spawn } = require('child_process');
const path = require('path');
const crypto = require('crypto')

const WebSocket = require('ws');
const { json } = require('stream/consumers');
global.WebSocket = WebSocket;

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;
const API_KEY = process.env.API_KEY;

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY, {
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
    res.json({ url: SUPABASE_URL, key: SUPABASE_KEY});
});

app.post('/api/search', async (req, res) => {
    const { query, folder_id } = req.body;
    if (!query) return res.status(400).json({error: "Pergunta vazia" });
    if (!folder_id) return res.status(400).json({ error: "Acervo (folder_id) não selecionado" });

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    let userId = '00000000-0000-0000-0000-000000000000';
    const token = req.headers.authorization?.split(' ')[1];

    if (token) {
        const { data: { user }, error } = await supabase.auth.getUser(token);
        if (!error && user) {
            userId = user.id;
        }
    }
    
    const hash = crypto.createHash('md5').update(query.toLowerCase().trim() + userId + folder_id).digest('hex');
    if (cache[hash]) {
        console.log(`[CACHE HIT] Poupando API. Resposta da memória para: "${query}" (User: ${userId}, Acervo: ${folder_id})`);
        res.write(`data: ${JSON.stringify({ type: 'log', message: '[CACHE HIT] Recuperando resposta da memória local...' })}\n\n`);
        res.write(`data: ${JSON.stringify({ type: 'result', data: cache[hash] })}\n\n`);
        return res.end();
    }
    console.log(`[MOTOR V2] Usuário ${userId} pesquisando: "${query}" no Acervo: ${folder_id}`);

    const pythonProcess = spawn('./.venv/bin/python3', ['src/search.py', query, userId, folder_id, API_KEY]);
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

const PORT = 3333;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`\n=========================================`);
    console.log(`SNOOPY-RAG V2 (SaaS) ATIVADO`);
    console.log(`Acesse: http://localhost:${PORT}`);
    console.log(`=========================================\n`);
});
