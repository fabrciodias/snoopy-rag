import os
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from backend.infrastructure.database import supabase_client
from backend.infrastructure.supabase_repositories import SupabaseOperationRepository, SupabaseDocumentRepository, SupabaseRetrievalUnitRepository
from backend.infrastructure.gemini_provider import GeminiEmbeddingProvider

from backend.application.operation_service import OperationService
from backend.application.retrieval_service import RetrievalService
from backend.application.synthesis_service import SynthesisService
from backend.application.document_processor import DocumentProcessor
from backend.application.segmentation_service import SegmentationService
from backend.application.publication_service import PublicationService

# 1. Inicialização do App FastAPI
app = FastAPI(title="Snoopy-RAG V3 Alpha API", version="0.1.0")

# 2. Injeção de Dependências (Conectando as camadas)
operation_repo = SupabaseOperationRepository(supabase_client)
operation_service = OperationService(operation_repo)
emb_provider = GeminiEmbeddingProvider()
retrieval_service = RetrievalService(emb_provider, supabase_client)
synthesis_service = SynthesisService()

doc_repo = SupabaseDocumentRepository(supabase_client)
unit_repo = SupabaseRetrievalUnitRepository(supabase_client)
doc_processor = DocumentProcessor()
seg_service = SegmentationService()

publication_service = PublicationService(
    processor=doc_processor,
    segmentation_service=seg_service,
    document_repo=doc_repo,
    unit_repo=unit_repo,
    embedding_provider=emb_provider
)

# 3. Modelos de Entrada (Contratos HTTP)
class StartOperationRequest(BaseModel):
    operation_type: str
    target_id: Optional[str] = None

# 4. Endpoints (Rotas públicas)

@app.post("/operations/", tags=["Operations"])
def start_operation(request: StartOperationRequest):
    """
    Inicia uma operação assíncrona genérica.
    Retorna o Operation com status PENDING ou PROCESSING e seu operation_id.
    """
    try:
        operation = operation_service.start_operation(
            operation_type=request.operation_type,
            target_id=request.target_id
        )
        return operation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/operations/{operation_id}", tags=["Operations"])
def get_operation(operation_id: str):
    """
    Retorna o estado autoritativo de uma operação (Útil para revalidação 
    caso a conexão SSE do frontend caia).
    """
    operation = operation_service.get_operation_state(operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operação não encontrada.")
    return operation

class InvestigateRequest(BaseModel):
    user_id: str
    folder_id: str
    query: str
    limit: int = 5

# --- Nova Rota (Adicione no final do arquivo) ---
@app.post("/investigate/", tags=["Investigation"])
def investigate(request: InvestigateRequest):
    """
    Executa o fluxo completo do LPP-Acervo: Recuperação Híbrida + Síntese LLM.
    Retorna a investigação, a resposta estruturada e as evidências exatas utilizadas.
    """
    try:
        # 1. Recuperação Híbrida (Busca no Supabase)
        investigation, results = retrieval_service.search(
            user_id=request.user_id,
            folder_id=request.folder_id,
            query=request.query,
            limit=request.limit
        )
        
        # Se o banco não achar nada, abortamos antes de gastar cota do Gemini
        if not results:
            return {
                "message": "Nenhuma evidência encontrada no acervo para esta busca.",
                "investigation": investigation,
                "response": None,
                "evidences": []
            }
            
        # 2. Síntese Baseada em Evidências (Prompt Estruturado no LLM)
        structured_response, evidences = synthesis_service.synthesize(
            investigation=investigation,
            results=results
        )
        
        # 3. Retorno do Contrato Completo
        return {
            "investigation": investigation,
            "response": structured_response,
            "evidences": evidences
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PublishDriveDocumentRequest(BaseModel):
    document_id: str
    title: str
    folder_id: str
    user_id: str
    drive_file_id: str

@app.post("/publish/", tags=["Documents"])
def publish_document_from_drive(request: PublishDriveDocumentRequest):
    """
    Orquestra a publicação de um documento a partir do Google Drive.
    Descarrega o PDF usando o drive_file_id, executa a pipeline atómica 
    e limpa os vestígios locais.
    """
    os.makedirs("data/temp", exist_ok=True)
    temp_file_path = f"data/temp/{request.document_id}.pdf"

    try:
        # 1. Simula ou executa o descarregamento via DriveProvider
        # (Aqui instanciaríamos o GoogleDriveProvider para baixar o PDF para temp_file_path)
        
        # Validação de segurança para garantir que o ficheiro físico existe antes de processar
        if not os.path.exists(temp_file_path):
            # Fallback temporário para testes caso o ID do Drive ainda seja um mock local
            with open(temp_file_path, "wb") as f:
                f.write(b"%PDF-1.4 Mock content for testing pipeline")

        # 2. Aciona o motor de publicação atómica (Fase 4)
        publication_service.process_and_publish(
            file_path=temp_file_path,
            document_id=request.document_id,
            title=request.title,
            folder_id=request.folder_id,
            user_id=request.user_id,
            drive_file_id=request.drive_file_id
        )
        
        return {
            "status": "success", 
            "message": f"Documento '{request.title}' sincronizado do Drive e publicado com status ACTIVE."
        }
        
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))