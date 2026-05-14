# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import io 
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

def sync_drive():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cred_path = os.path.join(base_dir, 'credentials.json')
    download_dir = os.path.join(base_dir, 'data', 'raw_pdfs')
    state_path = os.path.join(base_dir, 'data', 'drive_state.json')

    os.makedirs(download_dir, exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'data'), exist_ok=True)
    
    try:
        with open(cred_path, 'r', encoding='utf-8') as f:
            creds_data = json.load(f)
            FOLDER_ID = creds_data.get('folder_id')
    except Exception as e:
        print(f"[ERRO] Falha ao ler o credentials.json: {e}")
        return
        
    if not FOLDER_ID:
        print("[ERRO] 'folder_id' não encontrado no credentials.json.")
        return
        
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

    try:
        creds = service_account.Credentials.from_service_account_file(
            cred_path, scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)
        print("[DRIVE] Robô autenticado com sucesso.")
    except Exception as e:
        print(f"[ERRO] Falha ao autenticar o bot: {e}")
        return
        
    state = {}
    if os.path.exists(state_path):
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
            
    print(f"Buscando PDFs na pasta: {FOLDER_ID}...")

    try:
        query = f"'{FOLDER_ID}' in parents and trashed = false and mimeType = 'application/pdf'"
        results = service.files().list(
            q=query,
            fields="files(id, name, webViewLink, modifiedTime)"
        ).execute()

        items = results.get('files', [])
        if not items:
            print("Nenhum PDF encontrado na pasta.")
            return
            
        print(f"Encontrados {len(items)} arquivos. Iniciando sincronização...")

        for item in items:
            file_id = item['id']
            file_name = item['name']
            file_link = item['webViewLink']
            file_mod_time = item['modifiedTime']
            file_path = os.path.join(download_dir, file_name)
            
            file_state = state.get(file_id, {})
            is_processed = file_state.get('status') == 'processado'
            is_same_version = file_state.get('modifiedTime') == file_mod_time

            if is_processed and is_same_version:
                print(f"Pulando: {file_name} (já processado e sem alterações)")
                continue
                
            if is_processed and not is_same_version:
                print(f"Atualização detectada para: {file_name}. Re-baixando...")
            else:
                print(f"Baixando novo arquivo: {file_name}...")

            request = service.files().get_media(fileId=file_id)
            fh = io.FileIO(file_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False

            while done is False:
                status, done = downloader.next_chunk()
                
            state[file_id] = {
                "name": file_name,
                "webViewLink": file_link,
                "modifiedTime": file_mod_time,
                "status": "pendente_extracao"
            }            
        
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        print("Estado do Drive atualizado.")

    except Exception as e:
        print(f"Erro ao comunicar com a API do Drive: {e}")

if __name__ == '__main__':
    sync_drive()