from fastapi import (
    APIRouter,
    Header,
    HTTPException,
)

from pydantic import BaseModel

from google import genai
from google.genai import types

from backend.config import settings

from backend.api.dependencies import (
    get_authenticated_user_id,
)


router = APIRouter(
    tags=["Translation"],
)


client = genai.Client(
    api_key=settings.gemini_api_key
)


class TranslationRequest(BaseModel):
    text: str


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
