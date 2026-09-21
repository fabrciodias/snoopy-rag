from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# ESTADOS OPERACIONAIS E DOCUMENTAIS 

class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    REMOVED = "REMOVED"

class OperationStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

# REPRESENTAÇÃO DOCUMENTAL 
class DocumentBlock(BaseModel):
    block_index: int
    text: str
    block_type: str = "paragraph"  

class DocumentPage(BaseModel):
    page_number: int
    blocks: List[DocumentBlock] = []

class DocumentRepresentation(BaseModel):
    representation_id: str
    document_id: str
    pages: List[DocumentPage] = []
    metadata: Dict[str, Any] = {}

# UNIDADE DE RECUPERAÇÃO (RetrievalUnit) 

class RetrievalUnit(BaseModel):
    unit_id: Optional[int] = None
    document_id: str
    representation_id: str
    unit_index: int
    content: str
    location: Dict[str, Any] = {}  
    section: str = "Geral"
    metadata: Dict[str, Any] = {}

# INVESTIGAÇÃO E EVIDÊNCIA

class Investigation(BaseModel):
    investigation_id: Optional[str] = None
    user_id: str
    original_query: str
    filters: Dict[str, Any] = {}
    status: str = "PROCESSING"
    structured_response: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

class RetrievalResult(BaseModel):
    result_id: str
    investigation_id: str
    unit_id: int
    rank: int
    retrieval_score: float
    metadata: Dict[str, Any] = {}

class Evidence(BaseModel):
    evidence_id: Optional[str] = None
    investigation_id: str
    unit_id: int
    document_id: str
    location: Dict[str, Any] = {}
    content: str
    context: str
    provenance: Dict[str, Any] = {}

# RESPOSTA ESTRUTURADA (StructuredResponse) 

class StructuredResponse(BaseModel):
    response_id: Optional[str] = None
    content: str
    sections: List[Dict[str, Any]] = []
    evidence_refs: List[str] = []  
    references: List[Dict[str, Any]] = []

# OPERAÇÃO ASSÍNCRONA (Operation) 

class Operation(BaseModel):
    operation_id: Optional[str] = None
    operation_type: str  
    target_id: Optional[str] = None
    status: OperationStatus = OperationStatus.PENDING
    error_log: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None