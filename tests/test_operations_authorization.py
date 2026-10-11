import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.api.routers import operations
from backend.domain.entities import (
    Operation,
    OperationStatus,
    OperationTargetType,
)


def create_test_operation() -> Operation:
    return Operation(
        operation_id="operation-test-001",
        operation_type="DRIVE_SYNC",
        target_type=OperationTargetType.FOLDER,
        target_id="private-folder-a",
        status=OperationStatus.COMPLETED,
    )


class OperationAuthorizationTests(unittest.TestCase):

    def test_owner_can_retrieve_operation(self):
        """
        A rota deve devolver a operação quando o acesso
        ao acervo é autorizado.
        """
        operation = create_test_operation()

        with (
            patch.object(
                operations.operation_service,
                "get_operation_state",
                return_value=operation,
            ),
            patch.object(
                operations,
                "get_authenticated_user_id",
                return_value="user-a",
            ),
            patch.object(
                operations,
                "ensure_folder_access",
            ) as ensure_access,
        ):
            result = operations.get_operation(
                operation_id="operation-test-001",
                authorization="Bearer test-token-a",
            )

        self.assertEqual(
            result.operation_id,
            "operation-test-001",
        )

        ensure_access.assert_called_once_with(
            "private-folder-a",
            "user-a",
        )

    def test_denied_folder_access_blocks_operation(self):
        """
        A rota deve respeitar a negativa de acesso ao acervo
        e não devolver os dados da operação.
        """
        operation = create_test_operation()

        with (
            patch.object(
                operations.operation_service,
                "get_operation_state",
                return_value=operation,
            ),
            patch.object(
                operations,
                "get_authenticated_user_id",
                return_value="user-b",
            ),
            patch.object(
                operations,
                "ensure_folder_access",
                side_effect=HTTPException(
                    status_code=404,
                    detail="Acervo não encontrado.",
                ),
            ) as ensure_access,
        ):
            with self.assertRaises(HTTPException) as context:
                operations.get_operation(
                    operation_id="operation-test-001",
                    authorization="Bearer test-token-b",
                )

        self.assertEqual(
            context.exception.status_code,
            404,
        )

        ensure_access.assert_called_once_with(
            "private-folder-a",
            "user-b",
        )

    def test_missing_operation_returns_404(self):
        """
        Uma operação inexistente deve resultar em HTTP 404.
        """
        with (
            patch.object(
                operations.operation_service,
                "get_operation_state",
                return_value=None,
            ),
            patch.object(
                operations,
                "get_authenticated_user_id",
                return_value="user-a",
            ),
            patch.object(
                operations,
                "ensure_folder_access",
            ) as ensure_access,
        ):
            with self.assertRaises(HTTPException) as context:
                operations.get_operation(
                    operation_id="operation-does-not-exist",
                    authorization="Bearer test-token-a",
                )

        self.assertEqual(
            context.exception.status_code,
            404,
        )

        ensure_access.assert_not_called()


if __name__ == "__main__":
    unittest.main()