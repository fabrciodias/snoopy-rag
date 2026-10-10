from typing import List

from google import genai
from google.genai import types 

from backend.config import settings
from backend.domain.repositories import EmbeddingProvider

class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Integração com a API do Google Gemini para a geração de vetores
    semânticos.

    Utiliza retentativas HTTP nativas do SDK para tratar as falhas
    transitórias durnte as chamadas à API.
    """

    def __init__(self):
        self.model = settings.gemini_embedding_model
        self.batch_size = settings.gemini_embedding_batch_size

        self.client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpOptions(
                    attempts=5,
                    initial_delay=1.0,
                    max_delay=60.0,
                    exp_base=2.0,
                    jitter=1.0,
                    http_status_codes=[
                        408,
                        429,
                        500,
                        502,
                        503,
                        504,
                    ],
                ),
            ),
        )

    def generate_embeddings(
            self,
            texts: List[str],
    ) -> List[List[float]]:
        """
        Gera embeddings para os textos recebidos, respeitando
        o tamanho de lote configurado.

        A quantidade de vetores retornados deve corresponder
        à quantidade de textos enviados em cada lote.
        """

        if not texts:
            return []

        all_embeddings: List[List[float]] = []

        for start in range(
            0,
            len(texts),
            self.batch_size,
        ):
            batch = texts[
                start:start + self.batch_size
            ]

            embeddings = self._embed_batch(batch)

            if len(embeddings) != len(batch):
                raise RuntimeError(
                    "Quantidade de embeddings não corresponde " \
                    "à quantidade de textos do lote."
                )

            all_embeddings.extend(embeddings)

        return all_embeddings

    def _embed_batch(
            self,
            texts: List[str],
    ) -> List[List[float]]:
        """
        Gera embeddings para um lote.

        Falhas HTTP transitórias são tratadas pela política de retry
        configurada no cliente Gemini. Falhas definitivas são
        propagadas para o fluxo de publicação.
        """

        contents = [
            types.Content(
                parts=[
                    types.Part.from_text(
                        text=text
                    )
                ]
            )
            for text in texts
        ]

        response = self.client.models.embed_content(
            model=self.model,
            contents=contents,
            config=types.EmbedContentConfig(
                output_dimensionality=768,
            ),
        )

        return [
            embedding.values
            for embedding in response.embeddings
        ]