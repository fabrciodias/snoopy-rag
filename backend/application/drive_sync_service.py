import hashlib
import os
import uuid
import shutil
from typing import Dict, List

from supabase import Client

from backend.application.operation_service import (
    OperationService,
)
from backend.application.publication_service import (
    PublicationService,
)
from backend.domain.entities import (
    Document,
    DocumentStatus,
    OperationProgress,
)
from backend.domain.repositories import (
    DocumentRepository,
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
    ):
        self.client = client
        self.drive_provider = drive_provider
        self.operation_service = operation_service
        self.publication_service = publication_service
        self.document_repo = document_repo

    def _write_progress(
            self,
            operation_id: str,
            phase: str,
            message: str,
            current: int | None = None,
            total: int | None = None,
            processed: int = 0,
            skipped: int = 0,
            failed: int = 0,
    ) -> None:

        self.operation_service.update_progress(
            operation_id,
            OperationProgress(
                phase=phase,
                message=message,
                current=current,
                total=total,
                unit="files",
                processed=processed,
                skipped=skipped,
                failed=failed,
            ),
        )

    def _reconcile_removed_documents(
            self,
            folder_id: str,
            user_id: str,
            drive_file_ids: set[str],
    ) -> int:
        """
        Marca como REMOVED os documentos associados a arquivos
        que deixaram de existir na pasta monitorada do Drive.

        a consulta é restrita ao acervo e ao propritetário atuais.

        Documentos já removidos permanecem inalterados. Registros
        sem drive_file_id também são preservados.

        A remoção é lógica: não elimina representações históricas,
        RetrievalUnits ou evidências persistidas.
        """

        response = (
            self.client
            .table("documents")
            .select(
                "id, drive_file_id, status"
            )
            .eq(
                "folder_id",
                folder_id,
            )
            .eq(
                "user_id",
                user_id,
            )
            .execute()
        )

        records = response.data or []

        removed_count = 0

        for record in records:
            document_id = record.get('id')
            drive_file_id = record.get("drive_file_id")
            status = record.get("status")

            # Não presumimos que documentos sem identificador
            # do Drive devam se removidos
            if not drive_file_id:
                continue

            # O arquivo continua na pasta monitorada
            if drive_file_id in drive_file_ids:
                continue

            # Evita atualizações desnecessárias
            if status == DocumentStatus.REMOVED.value:
                continue

            if not document_id:
                raise RuntimeError(
                    "Não foi possível identificar um documento " \
                    "durante a reconciliação do acervo."
                )

            self.document_repo.update_status(
                document_id,
                DocumentStatus.REMOVED,
            )

            removed_count += 1

            print(
                "[SYNC] Documento removido do corpus ativo: " 
                f"document_id={document_id}, "
                f"drive_file_id={drive_file_id}"
            )

            return removed_count

    def sync_folder(
        self,
        operation_id: str,
        folder_id: str,
        user_id: str,
        google_access_token: str,
    ):

        temp_dir = os.path.join(
            "data",
            "raw_pdfs",
            operation_id,
        )

        processed = 0
        skipped = 0
        failed = 0

        errors: List[Dict] = []

        total: int | None = None

        try:
            os.makedirs(
                temp_dir,
                exist_ok=True,
            )

            self._write_progress(
                operation_id=operation_id,
                phase="discovering",
                message="Localizando arquivos PDF no Google Drive...",
                current=0,
                total=None,
            )

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

            # A reconciliação só pode ocorrer depois de uma 
            # listagem válida e com identificadores verificáveis.
            if not isinstance(drive_files, list):
                raise RuntimeError(
                    "A listagem do Google Drive não retornou " \
                    "uma lista válida de arquivos."
                )

            drive_file_ids: set[str] = set()

            for drive_file_id in drive_files:
                drive_file_id = (
                    drive_file.get("id")
                    if isinstance(drive_file, dict)
                    else None
                )

                if (
                    not isinstance(drive_file_id, str)
                    or not drive_file_id.strip()
                ):
                    raise RuntimeError(
                        "A listagem do Google Drive contém " 
                        "um arquivo sem identificador válido. " 
                        "A reconciliação foi interrompida " \
                        "para evitar remoções indevidas."
                    )

                drive_file_ids.add(drive_file_id)

            removed_count = (
                self._reconcile_removed_documents(
                    folder_id=folder_id,
                    user_id=user_id,
                    drive_file_ids=drive_file_ids,
                )
            )

            print(
                "[SYNC] Reconciliação concluída: " \
                f"{removed_count} documento(s) removido(s) "
                "do corpus ativo."
            )

            total = len(drive_files)

            self._write_progress(
                operation_id=operation_id,
                phase="processing",
                message=(
                    "Sincronizando arquivos do acervo..."
                    if total > 0
                    else "Nenhum arquivo encontrado"
                ),
                current=0,
                total=total,
                processed=processed,
                skipped=skipped,
                failed=failed,
            )

            print(
                f"[SYNC DEBUG] folder_id={folder_id} "
                f"drive_folder_id={drive_folder_id}"
            )

            print(
                f"[SYNC DEBUG] PDFs encontrados: {len(drive_files)}"
            )

            for drive_file in drive_files:
                print(
                    "[SYNC DEBUG] PDF: "
                    f"id={drive_file.get('id')} "
                    f"name={drive_file.get('name')} "
                    f"mimeType={drive_file.get('mimeType')}"
                )

            for file_index, drive_file in enumerate(
                drive_files,
                start=1,
            ):

                self._write_progress(
                    operation_id=operation_id,
                    phase="processing",
                    message=(
                        f"Processando arquivo "
                        f"{file_index} de {total}..."
                    ),
                    current=processed + skipped + failed,
                    total=total,
                    processed=processed,
                    skipped=skipped,
                    failed=failed,
                )

                drive_file_id = drive_file["id"]

                drive_file_name = drive_file["name"]

                drive_link = drive_file.get("webViewLink")

                mime_type = drive_file.get("mimeType")

                drive_md5 = drive_file.get("md5Checksum")

                temp_path = os.path.join(
                    temp_dir,
                    f"{drive_file_id}.pdf",
                )

                try:
                    # ====================================================
                    # 1. Descobre se o documento já existe
                    # ====================================================

                    existing = (
                        self.client
                        .table("documents")
                        .select(
                            "id,status,document_hash"
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

                    # ====================================================
                    # 2. Documento já publicado e sem alteração
                    # ====================================================

                    if (
                        existing_document
                        and existing_document["status"]
                        == DocumentStatus.ACTIVE.value
                        and drive_md5
                        and existing_document["document_hash"]
                        == drive_md5
                    ):
                        skipped += 1

                        self._write_progress(
                            operation_id=operation_id,
                            phase="processing",
                            message="Sincronizando arquivos do acervo...",
                            current=processed + skipped + failed,
                            total=total,
                            processed=processed,
                            skipped=skipped,
                            failed=failed,
                        )

                        continue

                    # ====================================================
                    # 3. Baixa primeiro.
                    # ====================================================
                    #
                    # Nenhum estado persistente do documento é alterado
                    # antes de sabermos que o arquivo físico existe.
                    #

                    self.drive_provider.download_pdf(
                        drive_file_id=drive_file_id,
                        access_token=google_access_token,
                        output_path=temp_path,
                    )

                    # ====================================================
                    # 4. Calcula o hash físico real
                    # ====================================================

                    document_hash = self._md5(
                        temp_path
                    )

                    # ====================================================
                    # 5. Monta o documento candidato
                    # ====================================================

                    if existing_document:

                        document_id = (
                            existing_document["id"]
                        )

                        current_document = (
                            self.document_repo.get_by_id(
                                document_id
                            )
                        )

                        if current_document is None:
                            raise RuntimeError(
                                f"Documento '{document_id}' "
                                "não pôde ser recuperado."
                            )

                        if (
                            current_document.status
                            == DocumentStatus.REMOVED
                        ):
                            current_document = (
                                self.document_repo.update_status(
                                    document_id,
                                    DocumentStatus.PENDING,
                                )
                            )

                        document = current_document.model_copy(
                            update={
                                "drive_file_name": drive_file_name,
                                "drive_file_id": drive_file_id,
                                "drive_link": drive_link,
                                "mime_type": mime_type,
                                "document_hash": document_hash,
                            }
                        )

                    else:

                        document = Document(
                            document_id=str(uuid.uuid4()),
                            folder_id=folder_id,
                            user_id=user_id,
                            title="Título não identificado",
                            drive_file_name=drive_file_name,
                            drive_file_id=drive_file_id,
                            drive_link=drive_link,
                            mime_type=mime_type,
                            document_hash=document_hash,
                            status=DocumentStatus.PENDING,
                        )

                        # O documento novo precisa existir antes
                        # que a publicação possa armazenar sua
                        # representação histórica.
                        document = (
                            self.document_repo
                            .create_or_update(document)
                        )

                    # ====================================================
                    # 6. Processa e publica
                    # ====================================================

                    self.publication_service.process_and_publish(
                        document=document,
                        file_path=temp_path,
                    )

                    processed += 1

                    self._write_progress(
                        operation_id=operation_id,
                        phase="processing",
                        message="Sincronizando arquivos do acervo...",
                        current=processed + skipped + failed,
                        total=total,
                        processed=processed,
                        skipped=skipped, 
                        failed=failed,
                    )

                except Exception as error:

                    failed += 1

                    errors.append({
                        "drive_file_id": drive_file_id,
                        "drive_file_name": drive_file_name,
                        "error": str(error),
                    })

                    self._write_progress(
                        operation_id=operation_id,
                        phase="processing",
                        message="Sincronizando arquivos do acervo...",
                        current=processed + skipped + failed,
                        total=total,
                        processed=processed,
                        skipped=skipped,
                        failed=failed,
                    )

                finally:

                    if os.path.exists(temp_path):
                        os.remove(temp_path)

            completed_files = (
                processed + skipped + failed
            )

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

                    progress=OperationProgress(
                        phase="failed",
                        message="Sincronização concluída com falhas.",
                        current=completed_files,
                        total=total,
                        unit="files",
                        processed=processed,
                        skipped=skipped,
                        failed=failed,
                    ),
                )

                return {
                    "status": "FAILED",
                    "processed": processed,
                    "skipped": skipped,
                    "failed": failed,
                    "errors": errors,
                }

            self._write_progress(
                operation_id=operation_id,
                phase="finalizing",
                message="Finalizando sincronização...",
                current=completed_files,
                total=total,
                processed=processed,
                skipped=skipped,
                failed=failed,
            )

            self.operation_service.complete_operation(
                operation_id,
                progress=OperationProgress(
                    phase="completed",
                    message=(
                        "Nenhum arquivo PDF encontrado."
                        if total == 0
                        else "Sincronização concluída."
                    ),
                    current=completed_files,
                    total=total,
                    unit="files",
                    processed=processed,
                    skipped=skipped,
                    failed=failed,
                ),
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
                progress=OperationProgress(
                    phase="failed",
                    message="A sincronização não pôde ser concluída.",
                    current=processed + skipped + failed,
                    total=total,
                    unit="files",
                    processed=processed,
                    skipped=skipped,
                    failed=failed,
                ),
            )

            raise

        finally:

            if os.path.isdir(temp_dir):
                shutil.rmtree(
                    temp_dir,
                    ignore_errors=True,
                )

    @staticmethod
    def _md5(
        file_path: str,
    ) -> str:

        digest = hashlib.md5()

        with open(
            file_path,
            "rb",
        ) as file_handle:

            for chunk in iter(
                lambda: file_handle.read(1024 * 1024),
                b"",
            ):
                digest.update(chunk)

        return digest.hexdigest()