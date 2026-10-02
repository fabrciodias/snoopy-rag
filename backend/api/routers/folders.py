from fastapi import (
    APIRouter,
    Header,
    HTTPException,
)

from backend.api.dependencies import (
    get_authenticated_user_id,
    ensure_folder_access,
    PUBLIC_FOLDER_ID,
)
from backend.infrastructure.database import supabase_client
from pydantic import BaseModel


router = APIRouter(
    prefix="/folders",
    tags=["Folders"],
)


class FolderCreateRequest(BaseModel):
    drive_id: str
    name: str


@router.get("/")
def list_folders(
    authorization: str | None = Header(default=None),
):
    user_id = get_authenticated_user_id(
        authorization
    )

    response = (
        supabase_client
        .table("folders")
        .select(
            "id, user_id, name, drive_id, is_active, created_at"
        )
        .eq("is_active", True)
        .or_(
            f"user_id.eq.{user_id},"
            f"id.eq.{PUBLIC_FOLDER_ID}"
        )
        .order("created_at")
        .execute()
    )

    return response.data


@router.post("/")
def create_folder(
    request: FolderCreateRequest,
    authorization: str | None = Header(default=None),
):
    user_id = get_authenticated_user_id(
        authorization
    )

    drive_id = request.drive_id.strip()
    name = request.name.strip()

    if not drive_id:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail="drive_id não pode ser vazio.",
        )

    if not name:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail="name não pode ser vazio.",
        )

    try:
        response = (
            supabase_client
            .table("folders")
            .upsert(
                {
                    "user_id": user_id,
                    "drive_id": drive_id,
                    "name": name,
                    "is_active": True,
                },
                on_conflict="user_id,drive_id",
            )
            .execute()
        )

        if not response.data:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=500,
                detail="Falha ao registrar o acervo.",
            )

        return response.data[0]

    except Exception as error:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@router.delete("/{folder_id}")
def delete_folder(
    folder_id: str,
    authorization: str | None = Header(default=None),
):
    from fastapi import HTTPException

    user_id = get_authenticated_user_id(
        authorization
    )

    if folder_id == PUBLIC_FOLDER_ID:
        raise HTTPException(
            status_code=403,
            detail="O acervo público não pode ser removido.",
        )

    folder = (
        supabase_client
        .table("folders")
        .select(
            "id, user_id, is_active"
        )
        .eq("id", folder_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if not folder.data:
        raise HTTPException(
            status_code=404,
            detail="Acervo não encontrado.",
        )

    record = folder.data[0]

    if record.get("user_id") != user_id:
        raise HTTPException(
            status_code=404,
            detail="Acervo não encontrado.",
        )

    response = (
        supabase_client
        .table("folders")
        .update({
            "is_active": False,
        })
        .eq("id", folder_id)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="Falha ao desativar o acervo.",
        )

    return {
        "id": folder_id,
        "is_active": False,
    }