from backend.infrastructure.database import (
    supabase_client,
)

from backend.infrastructure.supabase_repositories import (
    SupabaseOperationRepository,
    SupabaseDocumentRepository,
    SupabaseRetrievalUnitRepository,
    SupabaseInvestigationRepository,
    SupabaseRetrievalResultRepository,
    SupabaseEvidenceRepository,
)

from backend.infrastructure.gemini_provider import (
    GeminiEmbeddingProvider,
)

from backend.infrastructure.drive_provider import (
    GoogleDriveProvider,
)

from backend.application.drive_sync_service import (
    DriveSyncService,
)

from backend.application.operation_service import (
    OperationService,
)

from backend.application.retrieval_service import (
    RetrievalService,
)

from backend.application.synthesis_service import (
    SynthesisService,
)

from backend.application.document_processor import (
    DocumentProcessor,
)

from backend.application.segmentation_service import (
    SegmentationService,
)

from backend.application.publication_service import (
    PublicationService,
)

from backend.application.bibliographic_metadata_extractor import (
    BibliographicMetadataExtractor,
)


# ============================================================
# Infrastructure
# ============================================================

operation_repo = SupabaseOperationRepository(
    supabase_client
)

emb_provider = GeminiEmbeddingProvider()

investigation_repo = SupabaseInvestigationRepository(
    supabase_client
)

retrieval_result_repo = (
    SupabaseRetrievalResultRepository(
        supabase_client
    )
)

evidence_repo = SupabaseEvidenceRepository(
    supabase_client
)

doc_repo = SupabaseDocumentRepository(
    supabase_client
)

unit_repo = SupabaseRetrievalUnitRepository(
    supabase_client
)

drive_provider = GoogleDriveProvider()


# ============================================================
# Application Services
# ============================================================

operation_service = OperationService(
    operation_repo
)

retrieval_service = RetrievalService(
    emb_provider,
    supabase_client,
    investigation_repo,
    retrieval_result_repo,
)

synthesis_service = SynthesisService(
    evidence_repo,
    investigation_repo,
    unit_repo,
)

doc_processor = DocumentProcessor()

seg_service = SegmentationService()

metadata_extractor = BibliographicMetadataExtractor()

publication_service = PublicationService(
    processor=doc_processor,
    segmentation_service=seg_service,
    document_repo=doc_repo,
    unit_repo=unit_repo,
    embedding_provider=emb_provider,
    metadata_extractor=metadata_extractor,
)

drive_sync_service = DriveSyncService(
    client=supabase_client,
    drive_provider=drive_provider,
    operation_service=operation_service,
    publication_service=publication_service,
    document_repo=doc_repo,
    )