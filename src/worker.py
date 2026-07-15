import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client
from pipeline import memory_process

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("\n=========================================")
print("SNOOPY WORKER INICIADO E VIGIANDO A FILA")
print("=========================================\n")

while True:
    # Declaramos as variáveis fora do try para o except saber quem são
    job_id = None
    file_name = "Desconhecido"
    
    try:
        # 1. Inicia a partir do mais antigo
        res = supabase.table("jobs").select("*").eq("status", "pending").order("created_at").limit(1).execute()
        
        if not res.data:
            time.sleep(2)
            continue
            
        job = res.data[0]
        job_id = job["id"]
        file_name = job["file_name"]
        
        print(f"\n[WORKER] Iniciando arquivo: {file_name}")
        
        # 2. Processing
        supabase.table("jobs").update({"status": "processing"}).eq("id", job_id).execute()
        
        # 3. Caminho do arquivo
        file_path = os.path.join(os.getcwd(), "data", "raw_pdfs", f"{job['drive_file_id']}.pdf")
        
        # 4. Limpeza e Processamento
        memory_process(
            file_path=file_path, 
            file_id=job["drive_file_id"], 
            user_id=job["user_id"], 
            folder_id=job["folder_id"], 
            drive_link=""
        )
        
        # 5. Concluído
        supabase.table("jobs").update({"status": "completed"}).eq("id", job_id).execute()
        print(f"[WORKER] Sucesso total no arquivo: {file_name}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"[WORKER ERRO] Falha no arquivo {file_name}: {error_msg}")
        # Só tenta salvar o erro no banco se o job_id chegou a ser gerado
        if job_id:
            supabase.table("jobs").update({"status": "failed", "error_log": error_msg}).eq("id", job_id).execute()
            
    time.sleep(1)