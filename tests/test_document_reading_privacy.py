import unittest

from backend.api.routers.documents import (
    _sanitize_representation_for_copy_access,
)
from backend.domain.entities import (
    DocumentRepresentation,
)


class DocumentReadingPrivacyTests(unittest.TestCase):

    def test_sanitization_removes_private_source_metadata(self):
        """
        O acesso por uma cópia não deve expor os identificadores
        da fonte original na representação devolvida pela API.
        """

        original_metadata = {
            "drive_link": "https://drive.example/original",
            "drive_file_id": "original-drive-id",
            "drive_file_name": "documento-original.pdf",
            "document_hash": "original-document-hash",
            "mime_type": "application/pdf",
            "author": "Autor bibliográfico",
            "bibliographic": {
                "title": "Título do trabalho",
            },
        }

        representation = DocumentRepresentation(
            representation_id="representation-test",
            document_id="document-test",
            pages=[],
            metadata=original_metadata,
        )

        sanitized = (
            _sanitize_representation_for_copy_access(
                representation
            )
        )

        private_keys = (
            "drive_link",
            "drive_file_id",
            "drive_file_name",
            "document_hash",
        )

        for key in private_keys:
            with self.subTest(key=key):
                self.assertNotIn(
                    key,
                    sanitized.metadata,
                )

        # Os metadados necessários à leitura permanecem disponíveis.
        self.assertEqual(
            sanitized.metadata["mime_type"],
            "application/pdf",
        )

        self.assertEqual(
            sanitized.metadata["bibliographic"]["title"],
            "Título do trabalho",
        )

        # A representação original continua intacta.
        # A sanitização não pode modificar os dados persistidos.
        self.assertEqual(
            representation.metadata["drive_link"],
            "https://drive.example/original",
        )

        self.assertEqual(
            representation.metadata["drive_file_id"],
            "original-drive-id",
        )

        self.assertEqual(
            representation.metadata["document_hash"],
            "original-document-hash",
        )

        # A sanitização produz uma nova instância.
        self.assertIsNot(
            sanitized,
            representation,
        )


if __name__ == "__main__":
    unittest.main()