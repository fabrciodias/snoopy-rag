import unittest

from pydantic import ValidationError

from backend.domain.entities import (
    Operation,
    OperationProgress,
    OperationStatus,
    OperationTargetType,
)


class OperationProgressContractTests(unittest.TestCase):

    def test_operation_contains_structured_progress(self):
        progress = OperationProgress(
            phase="processing",
            message="Sincronizando arquivos do acervo...",
            current=2,
            total=4,
            unit="files",
            processed=1,
            skipped=1,
            failed=0,
        )

        operation = Operation(
            operation_id="operation-test-001",
            operation_type="DRIVE_SYNC",
            target_type=OperationTargetType.FOLDER,
            target_id="folder-test-001",
            status=OperationStatus.PROCESSING,
            progress=progress,
        )

        payload = operation.model_dump(
            mode="json",
        )

        self.assertEqual(
            payload["progress"]["current"],
            2,
        )

        self.assertEqual(
            payload["progress"]["total"],
            4,
        )

        self.assertEqual(
            payload["progress"]["processed"],
            1,
        )

        self.assertEqual(
            payload["progress"]["skipped"],
            1,
        )

        self.assertEqual(
            payload["progress"]["failed"],
            0,
        )

    def test_progress_cannot_contain_negative_counts(self):
        with self.assertRaises(ValidationError):
            OperationProgress(
                phase="processing",
                message="Processando...",
                current=-1,
                total=4,
                unit="files",
            )

        with self.assertRaises(ValidationError):
            OperationProgress(
                phase="processing",
                message="Processando...",
                processed=-1,
            )


if __name__ == "__main__":
    unittest.main()