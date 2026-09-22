from typing import Dict, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


class GoogleDriveProvider:
    """
    Adaptador de infraestrutura para leitura do Google Drive.

    O access token é fornecido pela sessão autenticada do usuário
    e não é persistido pelo backend.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    def _service(self, access_token: str):

        if not access_token:
            raise ValueError(
                "Google access token não fornecido."
            )

        credentials = Credentials(
            token=access_token,
            scopes=self.SCOPES,
        )

        return build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    def list_pdf_files(
        self,
        folder_id: str,
        access_token: str,
    ) -> List[Dict]:

        service = self._service(access_token)

        files = []
        page_token = None

        while True:

            response = (
                service.files()
                .list(
                    q=(
                        f"'{folder_id}' in parents "
                        "and mimeType='application/pdf' "
                        "and trashed=false"
                    ),
                    spaces="drive",
                    pageSize=1000,
                    pageToken=page_token,
                    fields=(
                        "nextPageToken,"
                        "files("
                        "id,"
                        "name,"
                        "mimeType,"
                        "webViewLink,"
                        "modifiedTime,"
                        "size,"
                        "md5Checksum"
                        ")"
                    ),
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                )
                .execute()
            )

            files.extend(
                response.get("files", [])
            )

            page_token = response.get(
                "nextPageToken"
            )

            if not page_token:
                break

        return files

    def download_pdf(
        self,
        drive_file_id: str,
        access_token: str,
        output_path: str,
    ) -> str:

        service = self._service(access_token)

        request = (
            service.files()
            .get_media(
                fileId=drive_file_id,
                supportsAllDrives=True,
            )
        )

        with open(output_path, "wb") as file_handle:

            downloader = MediaIoBaseDownload(
                file_handle,
                request,
            )

            done = False

            while not done:
                _, done = downloader.next_chunk()

        return output_path