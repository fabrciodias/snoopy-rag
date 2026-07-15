// 1. DEPENDÊNCIAS E IMPORTAÇÕES
require('dotenv').config({ override: true });
const express = require('express');
const { createClient } = require('@supabase/supabase-js');
const { spawn } = require('child_process');
const path = require('path');
const crypto = require('crypto');
const fs = require('fs');

const WebSocket = require('ws');
global.WebSocket = WebSocket;


// 2. VARIÁVEIS DE AMBIENTE E INSTÂNCIAS GLOBAIS
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


// 3. CONFIGURAÇÕES DO EXPRESS E ESTADOS EM MEMÓRIA
const app = express();
app.use(express.json());
app.use(express.static('ui')); // Serve o frontend nativamente
app.get('/favicon.ico', (req, res) => res.status(204).end());

// Cache de Respostas (Evita refazer a mesma pergunta na API do Gemini)
const cache = {};


// 4. ROTAS DA API
// [ROTA]: Configurações do Front-end (Injeção de chaves públicas)
app.get('/api/config', (req, res) => {
    res.json({
        url: SUPABASE_URL,
        key: SUPABASE_KEY,
        googleApiKey: process.env.GOOGLE_API_KEY,
        googleAppId: process.env.GOOGLE_APP_ID
    });
});


// [ROTA]: Motor Semântico (Busca e Síntese)
app.post('/api/search', async (req, res) => {
    const { query, folder_id } = req.body;
    
    if (!query) return res.status(400).json({error: "Pergunta vazia" });
    if (!folder_id) return res.status(400).json({error: "ID da pasta não fornecido" });

    // Configura a conexão como Server-Sent Events (SSE) para streaming ao vivo
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Validação de Autenticação
    let userId = '00000000-0000-0000-0000-000000000000';
    const token = req.headers.authorization?.split(' ')[1];

    if (token) {
        const { data: { user }, error } = await supabase.auth.getUser(token);
        if (!error && user) userId = user.id;
    }

    // Checagem de Cache (Hash MD5 da Pergunta + Pasta + Usuário)
    const hash = crypto.createHash('md5').update(`${userId}_${folder_id}_${query}`).digest('hex');
    
    if (cache[hash]) {
        console.log(`[CACHE HIT] Poupando API. Resposta da memória para: "${query}" (User: ${userId}, Acervo: ${folder_id})`);
        res.write(`data: ${JSON.stringify({ type: 'log', message: 'Recuperando resposta da memória local...' })}\n\n`);
        res.write(`data: ${JSON.stringify({ type: 'result', data: cache[hash] })}\n\n`);
        return res.end();
    }

    // Acionamento do Motor Python In-Memory
    console.log(`[MOTOR V2] Usuário ${userId} pesquisando: "${query}" no Acervo: ${folder_id}`);
    const pythonProcess = spawn('./.venv/bin/python3', ['src/search.py', query, userId, folder_id, GEMINI_API_KEY]);
    let rawOutput = '';

    // Captura da Saída Padrão 
    pythonProcess.stdout.on('data', (data) => {
        rawOutput += data.toString();
    });

    // Captura dos Erros e Logs de Telemetria (Streaming para o Front)
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

    // Finalização e Parser da Resposta
    pythonProcess.on('close', (code) => {
        try {
            const jsonMatch = rawOutput.match(/\{[\s\S]*\}/);
            if (!jsonMatch) throw new Error("JSON não encontrado na saída do Python.");
            
            const jsonResponse = JSON.parse(jsonMatch[0]);

            if (!jsonResponse.error) {
                cache[hash] = jsonResponse; // Salva no cache se for sucesso
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


// [ROTA]: Sincronização do Acervo
app.post('/api/sync', async (req, res) => {
    console.log("\n[INÍCIO SYNC] Requisitado pelo front-end");
    const { folder_id, google_token } = req.body;
    
    if (!folder_id || !google_token) {
        console.log("[SYNC ERRO] Parâmetros ausentes.");
        return res.status(400).json({ error: "Parâmetros folder_id ou google_token ausentes." });
    }

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();

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
        console.log(`[SYNC] Usuário autenticado: ${userId}`);

        sendLog("Buscando metadados do acervo no banco...");
        const { data: folderData, error: folderError } = await supabase
            .from('folders')
            .select('drive_id')
            .eq('id', folder_id)
            .single();

        if (folderError || !folderData?.drive_id) throw new Error("Acervo não encontrado ou sem pasta no Drive vinculada.");
        const driveId = folderData.drive_id;

        console.log(`[SYNC] Conectando ao Google Drive para a pasta: ${driveId}`);
        sendLog("Conectando à API do Google Drive...");
        const driveUrl = `https://www.googleapis.com/drive/v3/files?q='${driveId}' in parents and mimeType='application/pdf' and trashed=false&fields=files(id, name, webViewLink)`;
        
        const driveRes = await fetch(driveUrl, { headers: { 'Authorization': `Bearer ${google_token}` } });
        const driveData = await driveRes.json();

        // TRAVA CONTRA TOKEN EXPIRADO
        if (!driveRes.ok) {
            console.error("[ERRO GOOGLE API]:", driveData);
            throw new Error(`Acesso negado pelo Google. O seu token expirou. Atualize a página e faça login novamente. (${driveData.error?.message})`);
        }

        const googleFiles = driveData.files || [];
        console.log(`[SYNC] O Drive retornou ${googleFiles.length} PDF(s).`);

        if (googleFiles.length === 0) {
            sendLog("Sincronização concluída. Nenhum PDF encontrado no Drive.");
            res.write(`data: ${JSON.stringify({ type: 'result', status: 'empty' })}\n\n`);
            return res.end();
        }

        const { data: dbDocs } = await supabase.from('documents').select('drive_file_id').eq('folder_id', folder_id);
        const { data: dbJobs } = await supabase.from('jobs').select('drive_file_id').eq('folder_id', folder_id);

        const processedFileId = new Set(dbDocs?.map(d => d.drive_file_id) || []);
        const queuedFileId = new Set(dbJobs?.map(j => j.drive_file_id) || []);

        const newFiles = googleFiles.filter(f => !processedFileId.has(f.id) && !queuedFileId.has(f.id));
        console.log(`[SYNC] Filtro aplicado. Arquivos novos: ${newFiles.length}`);

        if (newFiles.length === 0) {
            sendLog("Sincronização concluída. O acervo já está atualizado.");
            res.write(`data: ${JSON.stringify({ type: 'result', status: 'up-to-date' })}\n\n`);
            return res.end();
        }

        sendLog(`Encontrado ${newFiles.length} novo(s) arquivo(s). Preparando fila...`);
        
        for (let i = 0; i < newFiles.length; i++) {
            const file = newFiles[i];
            const currentIdx = i + 1;

            try { 
                console.log(`[SYNC] Baixando ${currentIdx}/${newFiles.length}: ${file.name}`);
                sendLog(`[${currentIdx}/${newFiles.length}] Baixando e registrando: "${file.name}"...`);
                
                const downloadUrl = `https://www.googleapis.com/drive/v3/files/${file.id}?alt=media`;
                const downloadRes = await fetch(downloadUrl, {
                    headers: { 'Authorization': `Bearer ${google_token}` }
                });

                if (!downloadRes.ok) throw new Error(`Falha na rede (HTTP ${downloadRes.status})`);

                const arrayBuffer = await downloadRes.arrayBuffer();
                const buffer = Buffer.from(arrayBuffer);

                const tempDir = path.join(__dirname, 'data', 'raw_pdfs');
                if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });

                const tempPath = path.join(tempDir, `${file.id}.pdf`);
                fs.writeFileSync(tempPath, buffer);

                const { error: jobError } = await supabase.from('jobs').insert([{
                    user_id: userId,
                    folder_id: folder_id,
                    file_name: file.name,
                    drive_file_id: file.id,
                    status: 'pending'
                }]);

                if (jobError) throw jobError;
                console.log(`[SYNC] Arquivo ${file.name} inserido na tabela jobs com sucesso.`);

            } catch (err) { 
                sendLog(`[AVISO] Falha ao capturar "${file.name}". Pulando para o próximo.`);
                console.error(`[SYNC ERRO] Falha no arquivo ${file.name}:`, err);
            }
        }
        
        console.log("[FIM SYNC] Todos os arquivos enfileirados");
        sendLog("Arquivos adicionados à fila do Motor Semântico com sucesso!");
        res.write(`data: ${JSON.stringify({ type: 'result', status: 'success' })}\n\n`);
        res.end();

    } catch (error) {
        console.error("[ERRO CRÍTICO NO SYNC]:", error);
        res.write(`data: ${JSON.stringify({ type: 'error', message: error.message })}\n\n`);
        res.end();
    }
});

// 6. Modo Leitura
app.get('/api/document-chunks', async (req, res) => {
    const { title, folder_id } = req.query;

    console.log(`[MODO LEITURA] Buscando documento: "${title}" na pasta: ${folder_id}`);

    if (!title || !folder_id) {
        return res.status(400).json({ error: 'Título e folder_id são obrigatórios.' });
    }

    try {
        // Busca o ID do documento usando o título exato
        const { data: docData, error: docError } = await supabase
            .from('documents')
            .select('id')
            .eq('folder_id', folder_id)
            .eq('title', title)
            .limit(1);

        if (docError) {
            console.error("[MODO LEITURA] Erro no banco de dados:", docError);
            return res.status(500).json({ error: 'Erro ao consultar o banco de dados: ' + docError.message });
        }

        let documentId;

        // Se falhar a busca exata (problema de codificação ou espaços), tenta a busca aproximada (ilike)
        if (!docData || docData.length === 0) {
            console.log("[MODO LEITURA] Documento não encontrado com nome exato. Tentando busca tolerante (ilike)...");
            
            const { data: fallbackData } = await supabase
                .from('documents')
                .select('id')
                .eq('folder_id', folder_id)
                .ilike('title', `%${title.trim()}%`)
                .limit(1);
                
            if (!fallbackData || fallbackData.length === 0) {
                 return res.status(404).json({ error: `O documento original "${title}" não foi encontrado neste acervo.` });
            }
            documentId = fallbackData[0].id;
        } else {
            documentId = docData[0].id;
        }

        // Puxa todos os chunks pertencentes àquele documento
        const { data: chunksData, error: chunksError } = await supabase
            .from('chunks')
            .select('id, content, section')
            .eq('document_id', documentId)
            .order('id', { ascending: true });

        if (chunksError) throw chunksError;

        console.log(`[MODO LEITURA] Sucesso! ${chunksData.length} chunks enviados para a interface.`);
        res.json({ chunks: chunksData });
    } catch (error) {
        console.error('Anomalia ao recuperar chunks do acervo:', error);
        res.status(500).json({ error: error.message });
    }
});

// [ROTA]: Tradução Sob Demanda (Modo Leitura)
app.post('/api/translate', async (req, res) => {
    const { text } = req.body;
    if (!text) return res.status(400).json({ error: 'Texto ausente.' });

    try {
        const prompt = `Você é um tradutor acadêmico especializado de alta precisão. 
Traduza o seguinte trecho de um documento científico/acadêmico para o Português.
Mantenha o rigor técnico, preserve integralmente jargões conceituais, e respeite fielmente o tom do autor original.
Retorne APENAS o texto traduzido limpo, sem comentários ou aspas extras.

TEXTO ORIGINAL:
${text}`;

        const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`;
        
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{ parts: [{ text: prompt }] }],
                generationConfig: { temperature: 0.1 }
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error?.message || 'Falha na API do Gemini');
        }

        const data = await response.json();
        const translatedText = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
        
        res.json({ translation: translatedText.trim() });
    } catch (error) {
        console.error('Falha na rota de tradução:', error);
        res.status(500).json({ error: error.message });
    }
});

// 7. INICIALIZAÇÃO DO SERVIDOR
const PORT = 3000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`\n=========================================`);
    console.log(`SNOOPY-RAG V2 (SaaS) ATIVADO`);
    console.log(`Servidor de Orquestração: http://localhost:${PORT}`);
    console.log(`=========================================\n`);
});