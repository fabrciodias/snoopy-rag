from fastapi import Header, HTTPException

from backend.infrastructure.database import supabase_client


PUBLIC_FOLDER_ID = (
    "f7faf7d9-ec80-46c6-9572-174865bf1e62"
)


def get_authenticated_user_id(
    authorization: str | None = Header(default=None),
) -> str:
    """
    Valida o JWT do Supabase e retorna o ID do usuário
    autenticado.

    O identificador do usuário nunca deve ser confiado
    quando fornecido pelo cliente no corpo da requisição.
    """

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação não fornecido.",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Formato de autenticação inválido.",
        )

    supabase_token = authorization.split(
        " ",
        1,
    )[1].strip()

    if not supabase_token:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação inválido.",
        )

    try:
        user_response = (
            supabase_client.auth.get_user(
                supabase_token
            )
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Sessão Supabase inválida.",
        )

    if not user_response.user:
        raise HTTPException(
            status_code=401,
            detail="Sessão Supabase inválida.",
        )

    return user_response.user.id


def ensure_folder_access(
    folder_id: str,
    user_id: str,
):
    """
    Verifica se o acervo existe, está ativo e pode ser
    acessado pelo usuário autenticado.

    Acesso permitido quando:

    1. o acervo pertence ao usuário autenticado; ou
    2. o acervo é o acervo público GEPAFOR.

    O acervo continua sendo a fronteira de autorização
    da V3 Alpha.
    """

    folder = (
        supabase_client
        .table("folders")
        .select(
            "id, user_id, name, drive_id, is_active"
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

    if (
        record["id"] != PUBLIC_FOLDER_ID
        and record.get("user_id") != user_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Acervo não encontrado.",
        )

    return record