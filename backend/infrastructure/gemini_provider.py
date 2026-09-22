import time
from typing import List

from google import genai
from google.genai import types

from backend.config import settings
from backend.domain.repositories import EmbeddingProvider


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Integração com a API do Google Gemini para geração de vetores semânticos.
    Inclui mecanismo de contenção (backoff) para respeitar os limites de taxa.
    """

    def __init__(self):
        self.model = settings.gemini_embedding_model
        self.batch_size = settings.gemini_embedding_batch_size

        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )

    def generate_embeddings(
        self,
        texts: List[str],
    ) -> List[List[float]]:

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
                    "Quantidade de embeddings não corresponde "
                    "à quantidade de textos do lote."
                )

            all_embeddings.extend(embeddings)

        return all_embeddings

    def _embed_batch(
        self,
        texts: List[str],
    ) -> List[List[float]]:

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

        max_retries = 5

        for attempt in range(max_retries):
            try:
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

            except Exception as api_err:

                error_text = str(api_err).lower()

                rate_limited = (
                    "429" in error_text
                    or "too many requests" in error_text
                    or "quota" in error_text
                )

                if not rate_limited:
                    raise

                if attempt == max_retries - 1:
                    raise RuntimeError(
                        "Falha crítica: limite de taxa "
                        "excedido repetidamente."
                    ) from api_err

                sleep_time = 2 * (2 ** attempt)

                time.sleep(sleep_time)

        raise RuntimeError(
            "Falha inesperada ao gerar embeddings."
        )