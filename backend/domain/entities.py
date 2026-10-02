from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Document
# ============================================================

class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    REMOVED = "REMOVED"


class Document(BaseModel):
    """
    Entidade documental principal do Snoopy.

    Representa o documento lógico pertencente a um acervo.
    A representação extraída do arquivo físico é mantida
    separadamente em DocumentRepresentation.
    """

    document_id: str
    folder_id: str
    user_id: str

    title: str
    authors: Optional[str] = None
    publication_year: Optional[int] = None

    drive_file_id: Optional[str] = None
    drive_link: Optional[str] = None
    document_hash: Optional[str] = None

    status: DocumentStatus = DocumentStatus.PENDING

    current_representation_id: Optional[str] = None
    representation: Optional["DocumentRepresentation"] = None


# ============================================================
# Document Representation
# ============================================================

class DocumentBlock(BaseModel):
    """
    Unidade elementar da representação documental.

    Mantém o conteúdo textual e a posição espacial do bloco
    dentro da página original.
    """

    block_index: int
    text: str
    block_type: str = "text"

    x0: Optional[float] = None
    y0: Optional[float] = None
    x1: Optional[float] = None
    y1: Optional[float] = None


class DocumentPage(BaseModel):
    """
    Página da representação canônica do documento.

    As dimensões permitem interpretar as coordenadas dos blocos
    no sistema espacial original da página.
    """

    page_number: int

    width: Optional[float] = None
    height: Optional[float] = None

    blocks: List[DocumentBlock] = Field(
        default_factory=list
    )


class DocumentRepresentation(BaseModel):
    """
    Representação canônica derivada da fonte documental.

    Preserva a estrutura necessária para reconstruir a localização
    de uma unidade de recuperação dentro da fonte original.
    """

    representation_id: str
    document_id: str

    pages: List[DocumentPage] = Field(
        default_factory=list
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# Retrieval Location
# ============================================================

class DocumentLocation(BaseModel):
    """
    Localização de uma unidade dentro da representação documental.

    Página e bloco identificam a posição estrutural.
    Bounding boxes identificam a região espacial correspondente
    na página quando essa informação estiver disponível.
    """

    start_page: Optional[int] = None
    end_page: Optional[int] = None

    start_block: Optional[int] = None
    end_block: Optional[int] = None

    start_x0: Optional[float] = None
    start_y0: Optional[float] = None
    start_x1: Optional[float] = None
    start_y1: Optional[float] = None

    end_x0: Optional[float] = None
    end_y0: Optional[float] = None
    end_x1: Optional[float] = None
    end_y1: Optional[float] = None


# ============================================================
# Retrieval Unit
# ============================================================

class RetrievalUnit(BaseModel):
    """
    Unidade de recuperação derivada de uma representação documental.

    É o objeto efetivamente indexado para recuperação híbrida.
    """

    unit_id: Optional[int] = None

    document_id: str
    representation_id: str

    unit_index: int
    content: str

    location: DocumentLocation = Field(
        default_factory=DocumentLocation
    )

    section: str = "Geral"

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# Investigation
# ============================================================

class InvestigationStatus(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Investigation(BaseModel):
    """
    Contexto persistente de uma investigação.

    O acervo pesquisado é parte explícita da investigação:
    não fica escondido dentro de um dicionário genérico de filtros.
    """

    investigation_id: Optional[str] = None

    user_id: str
    folder_id: str

    original_query: str

    status: InvestigationStatus = (
        InvestigationStatus.PROCESSING
    )

    structured_response: Optional[
        Dict[str, Any]
    ] = None

    created_at: Optional[datetime] = None


# ============================================================
# Retrieval Result
# ============================================================

class RetrievalResult(BaseModel):
    """
    Resultado persistente de uma etapa de recuperação.

    RetrievalResult representa o resultado da recuperação,
    não uma evidência documental validada.

    Os dados essenciais para interpretar o resultado ficam
    explicitamente declarados no contrato.
    """

    result_id: str
    investigation_id: str

    unit_id: int
    document_id: str
    representation_id: str
    unit_index: int

    rank: int
    retrieval_score: float

    semantic_score: Optional[float] = None
    lexical_score: Optional[float] = None

    content: str
    location: DocumentLocation = Field(
        default_factory=DocumentLocation
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# Evidence Provenance
# ============================================================

class EvidenceProvenance(BaseModel):
    """
    Relação de proveniência que permite reconstruir a origem
    imediata de uma Evidence dentro da investigação.

    A resolução histórica completa da representação documental
    será consolidada na Passada 4.
    """

    investigation_id: str
    result_id: str
    unit_id: int
    document_id: str
    representation_id: str

    location: DocumentLocation = Field(
        default_factory=DocumentLocation
    )


# ============================================================
# Evidence
# ============================================================

class Evidence(BaseModel):
    """
    Materialização documental utilizada na síntese.

    Uma Evidence possui identidade própria e mantém a ligação
    com o resultado de recuperação e com a fonte documental.
    """

    evidence_id: Optional[str] = None

    investigation_id: str
    unit_id: int
    document_id: str

    location: DocumentLocation = Field(
        default_factory=DocumentLocation
    )

    content: str
    context: str

    provenance: EvidenceProvenance


# ============================================================
# Structured Response
# ============================================================

class StructuredResponse(BaseModel):
    """
    Resposta estruturada produzida a partir das evidências
    de uma investigação.
    """

    response_id: Optional[str] = None

    content: str

    sections: List[Dict[str, Any]] = Field(
        default_factory=list
    )

    evidence_refs: List[str] = Field(
        default_factory=list
    )

    references: List[Dict[str, Any]] = Field(
        default_factory=list
    )


# ============================================================
# Operations
# ============================================================

class OperationStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OperationTargetType(str, Enum):
    FOLDER = "FOLDER"
    DOCUMENT = "DOCUMENT"
    INVESTIGATION = "INVESTIGATION"


class Operation(BaseModel):
    """
    Execução assíncrona de uma ação do sistema.

    target_type + target_id identificam explicitamente
    a entidade sobre a qual a operação atua.
    """

    operation_id: Optional[str] = None

    operation_type: str

    target_type: Optional[OperationTargetType] = None
    target_id: Optional[str] = None

    status: OperationStatus = OperationStatus.PENDING

    error_log: Optional[str] = None

    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
