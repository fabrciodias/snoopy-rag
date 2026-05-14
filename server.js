/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */
 
const express = require('express')
const { spawn } = require('child_process')
const crypto = require('crypto')
const path = require('path');
const { Server } = require('http');

const app = express();
app.use(express.json());
app.use(express.static('ui'));

const cache = {};

app.post('/api/search', (req, res) => {
    const { query } = req.body;
    if (!query) return res.status(400).json({error: "Pergunta vazia" });
    const hash = crypto.createHash('md5').update(query.toLowerCase().trim()).digest('hex');

    if (cache[hash]) {
        console.log(`[CACHE HIT] Poupando API. Resposta carregada da memória para: "${query}"`);
        return res.json(cache[hash]);
    }
    console.log(`[MOTOR] Iniciando busca para: "${query}"`);

    const pythonProcess = spawn('./.venv/bin/python3', ['src/search.py', query]);
    let rawOutput = '';

    pythonProcess.stdout.on('data', (data) => {
        rawOutput += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        console.log(`[SNOOPY LOG]: ${data.toString().trim()}`);
    });

    pythonProcess.on('close', (code) => {
        try {
            const jsonMatch = rawOutput.match(/\{[\s\S]*\}/);
            if (!jsonMatch) throw new Error("JSON não encontrado na saída do Python.");
            const jsonResponse = JSON.parse(jsonMatch[0]);

            if (!jsonResponse.error) {
                cache[hash] = jsonResponse
            }
            res.json(jsonResponse);
        } catch (e) {
            console.log("[ERRO FATAL] Falha no parser:", rawOutput);
            res.status(500).json({ error: "Falha na comunicação com o motor semântico." });
        }
    });
});

const PORT = 3333;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`\n=========================================`);
    console.log(`SNOOPY-RAG SERVIDOR ATIVADO`);
    console.log(`Acesse: http://localhost:${PORT}`);
    console.log(`=========================================\n`);
});
