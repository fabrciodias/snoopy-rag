from fastapi import (
    APIRouter,
    Header,
    HTTPException,
)

from pydantic import BaseModel

from google import genai
from google.genai import types

from backend.config import settings


router = APIRouter(
    tags=["Translation"],
)


client = genai.Client(
    api_key=settings.gemini_api_key
)


class TranslationRequest(BaseModel):
    text: str


def get_authenticated_user_id(
    authorization: str | None,
) -> str:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação não fornecido.",
        )

    if not authorization.startswith(
        "Bearer "
    ):
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
        from backend.infrastructure.database import (
            supabase_client,
        )

        user_response = (
            supabase_client
            .auth
            .get_user(
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


@router.post(
    "/translate/",
)
def translate(
    request: TranslationRequest,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    Traduz sob demanda um trecho do documento
    para português.

    A rota exige autenticação porque utiliza o
    recurso LLM do backend em nome do usuário.
    """

    get_authenticated_user_id(
        authorization
    )

    text = request.text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Texto ausente.",
        )

    prompt = f"""
Você é um tradutor acadêmico especializado
de alta precisão.

Traduza o seguinte trecho de um documento
científico ou acadêmico para o português
brasileiro.

Mantenha:

- o rigor técnico;
- os termos conceituais;
- os jargões da área;
- o sentido original;
- o tom acadêmico do autor;
- a estrutura dos parágrafos quando aplicável.

Não resuma.
Não explique.
Não acrescente informações.
Não interprete o argumento.

Retorne APENAS o texto traduzido,
sem comentários, aspas ou introduções.

TEXTO ORIGINAL:

{text}
"""

    try:
        response = (
            client
            .models
            .generate_content(
                model=settings.gemini_llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                ),
            )
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Falha na execução da tradução: "
                f"{error}"
            ),
        )

    translation = (
        response.text or ""
    ).strip()

    if not translation:
        raise HTTPException(
            status_code=500,
            detail=(
                "O modelo não retornou "
                "uma tradução."
            ),
        )

    return {
        "translation":
            translation,
    }