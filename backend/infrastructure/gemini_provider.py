import os
import time
from typing import List
from google import genai
from google.genai import types
from backend.domain.repositories import EmbeddingProvider

class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Integração com a API do Google Gemini para geração de vetores semânticos.
    Inclui mecanismo de contenção (backoff) para respeitar os limites de taxa (Rate Limits).
    """
    
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        self.model = os.environ.get("GEMINI_EMBEDDING_MODEL", "text-multilingual-embedding-002")
        self.client = genai.Client(api_key=api_key)

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
            
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self.client.models.embed_content(
                    model=self.model,
                    contents=texts,
                    config=types.EmbedContentConfig(output_dimensionality=768)
                )
                return [emb.values for emb in response.embeddings]
                
            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "too many requests" in error_msg or "quota" in error_msg:
                    if attempt == max_retries - 1:
                        raise RuntimeError("Falha crítica: Limite de taxa da API Gemini excedido repetidamente.")
                    sleep_time = 2 * (2 ** attempt)
                    print(f"[API LIMIT] Cota da IA quase excedida. Em pausa por {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    raise e