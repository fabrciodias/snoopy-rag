import hashlib
import os
import uuid
from typing import Dict, List

from supabase import Client

from backend.application.operation_service import OperationService
from backend.application.publication_service import PublicationService
from backend.domain.entities import DocumentStatus
from backend.domain.repositories import (
    DocumentRepository,
    RetrievalUnitRepository,
)
from backend.infrastructure.drive_provider import (
    GoogleDriveProvider,
)


class DriveSyncService:

    def __init__(
        self,
        client: Client,
        drive_provider: GoogleDriveProvider,
        operation_service: OperationService,
        publication_service: PublicationService,
        document_repo: DocumentRepository,
        unit_repo: RetrievalUnitRepository,
    ):
        self.client = client
        self.drive_provider = drive_provider
        self.operation_service = operation_service
        self.publication_service = publication_service
        self.document_repo = document_repo
        self.unit_repo = unit_repo

    def sync_folder(
        self,
        operation_id: str,
        folder_id: str,
        user_id: str,
        google_access_token: str,
    ):

        temp_dir = "data/raw_pdfs"
        os.makedirs(
            temp_dir,
            exist_ok=True,
        )

        try:
            folder = (
                self.client
                .table("folders")
                .select("id, drive_id")
                .eq("id", folder_id)
                .eq("user_id", user_id)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )

            if not folder.data:
                raise ValueError(
                    "Acervo não encontrado ou não pertence ao usuário."
                )

            drive_folder_id = folder.data[0]["drive_id"]

            if not drive_folder_id:
                raise ValueError(
                    "Acervo não possui pasta do Google Drive vinculada."
                )

            drive_files = (
                self.drive_provider.list_pdf_files(
                    folder_id=drive_folder_id,
                    access_token=google_access_token,
                )
            )

            processed = 0
            skipped = 0
            failed = 0
            errors: List[Dict] = []

            for drive_file in drive_files:

                drive_file_id = drive_file["id"]
                title = drive_file["name"]
                drive_md5 = drive_file.get(
                    "md5Checksum"
                )

                try:
                    existing = (
                        self.client
                        .table("documents")
                        .select(
                            "id,status,document_hash,representation"
                        )
                        .eq(
                            "folder_id",
                            folder_id,
                        )
                        .eq(
                            "user_id",
                            user_id,
                        )
                        .eq(
                            "drive_file_id",
                            drive_file_id,
                        )
                        .limit(1)
                        .execute()
                    )

                    existing_document = (
                        existing.data[0]
                        if existing.data
                        else None
                    )

                    # Documento V3 já publicado e sem alteração.
                    if (
                        existing_document
                        and existing_document["status"]
                        == DocumentStatus.ACTIVE.value
                        and drive_md5
                        and existing_document["document_hash"]
                        == drive_md5
                        and existing_document.get(
                            "representation"
                        )
                    ):
                        skipped += 1
                        continue

                    if existing_document:
                        document_id = existing_document["id"]

                        # Remove derivados antigos, inclusive
                        # chunks legadas da V2.
                        self.unit_repo.delete_by_document(
                            document_id
                        )
                    else:
                        document_id = str(
                            uuid.uuid4()
                        )

                    temp_path = os.path.join(
                        temp_dir,
                        f"{drive_file_id}.pdf",
                    )

                    self.drive_provider.download_pdf(
                        drive_file_id=drive_file_id,
                        access_token=google_access_token,
                        output_path=temp_path,
                    )

                    document_hash = self._md5(
                        temp_path
                    )

                    self.document_repo.create_or_update(
                        document_id=document_id,
                        title=title,
                        folder_id=folder_id,
                        user_id=user_id,
                        drive_file_id=drive_file_id,
                        document_hash=document_hash,
                    )

                    self.publication_service.process_and_publish(
                        document_id=document_id,
                        title=title,
                        folder_id=folder_id,
                        user_id=user_id,
                        drive_file_id=drive_file_id,
                        file_path=temp_path,
                    )

                    processed += 1

                    if os.path.exists(temp_path):
                        os.remove(temp_path)

                except Exception as error:

                    failed += 1

                    errors.append(
                        {
                            "drive_file_id": drive_file_id,
                            "title": title,
                            "error": str(error),
                        }
                    )

                    temp_path = os.path.join(
                        temp_dir,
                        f"{drive_file_id}.pdf",
                    )

                    if os.path.exists(temp_path):
                        os.remove(temp_path)

            if failed:
                self.operation_service.fail_operation(
                    operation_id,
                    (
                        f"Sincronização parcial: "
                        f"{processed} processados, "
                        f"{skipped} ignorados, "
                        f"{failed} falharam. "
                        f"Erros: {errors}"
                    ),
                )

                return {
                    "status": "FAILED",
                    "processed": processed,
                    "skipped": skipped,
                    "failed": failed,
                    "errors": errors,
                }

            self.operation_service.complete_operation(
                operation_id
            )

            return {
                "status": "COMPLETED",
                "processed": processed,
                "skipped": skipped,
                "failed": 0,
                "errors": [],
            }

        except Exception as error:

            self.operation_service.fail_operation(
                operation_id,
                str(error),
            )

            raise

        finally:
            if os.path.isdir(temp_dir):
                for filename in os.listdir(temp_dir):
                    path = os.path.join(
                        temp_dir,
                        filename,
                    )

                    if os.path.isfile(path):
                        os.remove(path)

    @staticmethod
    def _md5(file_path: str) -> str:

        digest = hashlib.md5()

        with open(file_path, "rb") as file_handle:

            for chunk in iter(
                lambda: file_handle.read(1024 * 1024),
                b"",
            ):
                digest.update(chunk)

        return digest.hexdigest()