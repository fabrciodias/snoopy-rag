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

    os.makedirs(download_dir, exist_ok=True)
    try:
        with open(cred_path, 'r', encoding='utf-8') as f:
            creds_data = json.load(f)
            FOLDER_ID = creds_data.get('folder_id')
    except Exception as e:
        print(f"[ERROR] Falha ao ler o credentials.json: {e}")
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
    print(f"Buscando PDFs na pasta: {FOLDER_ID}...")
    try:
        query = f"'{FOLDER_ID}' in parents and trashed = false and mimeType = 'application/pdf'"
        results = service.files().list(
            q=query,
            fields="files(id, name, webViewLink)"
        ).execute()

        items = results.get('files', [])
        if not items:
            print("Nenhum PDF encontrado na pasta.")
            return
        print(f"Encontrados {len(items)} arquivos. Iniciando sincronização...")

        links_map = {}
        for item in items:
            file_id = item['id']
            file_name = item['name']
            file_link = item['webViewLink']
            file_path = os .path.join(download_dir, file_name)
            links_map[file_name] = file_link

            if os.path.exists(file_path):
                print(f"Pulando: {file_name} (já baixado)")
                continue
            print(f"Baixando: {file_name}...")

            request = service.files().get_media(fileId=file_id)
            fh = io.FileIO(file_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            print(f"Download concluído: {file_name}")
        
        map_path = os.path.join(base_dir, 'data', 'drive_links.json')
        with open(map_path, 'w', encoding='utf-8') as f:
            json.dump(links_map, f, ensure_ascii=False, indent=4)
        print("Mapa de links do Drive atualizado.")

    except Exception as e:
        print(f"Erro ao comunicar com a API do Drive: {e}")

if __name__ == '__main__':
    sync_drive()