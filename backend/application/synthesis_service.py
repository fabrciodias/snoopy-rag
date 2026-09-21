import os
import json
import uuid
from typing import List
from google import genai
from google.genai import types
from backend.domain.entities import Investigation, RetrievalResult, Evidence, StructuredResponse

class SynthesisService:
    """
    Serviço responsável por transformar Resultados Híbridos em Evidências formais
    e orquestrar a geração da Resposta Estruturada via LLM (Gemini).
    Garante que a IA obedeça à rastreabilidade acadêmica do LPP-Acervo.
    """

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        self.model = os.environ.get("GEMINI_LLM_MODEL", "gemini-3.5-flash")
        self.client = genai.Client(api_key=api_key)

    def synthesize(self, investigation: Investigation, results: List[RetrievalResult]) -> tuple[StructuredResponse, List[Evidence]]:
        # 1. Transformação Matemática -> Metodológica
        # Convertendo o que o banco achou (RetrievalResult) em Evidências formais
        evidences = []
        for res in results:
            ev = Evidence(
                evidence_id=str(uuid.uuid4()),
                investigation_id=res.investigation_id,
                unit_id=res.unit_id,
                document_id=res.metadata.get("document_id", ""),
                location=res.metadata.get("location", {}),
                content=res.metadata.get("content", ""),
                context=f"Documento ID: {res.metadata.get('document_id')}",
                provenance=res.metadata
            )
            evidences.append(ev)

        # 2. Montagem do Contexto Blindado para o LLM
        # Injetamos a tag [ID da Evidência] para que o Gemini possa referenciá-la na resposta
        context_blocks = []
        for ev in evidences:
            block = f"--- INÍCIO DA EVIDÊNCIA [{ev.evidence_id}] ---\n{ev.content}\n--- FIM DA EVIDÊNCIA ---"
            context_blocks.append(block)
            
        context_text = "\n\n".join(context_blocks)

        prompt = f"""Você é um assistente acadêmico avançado do sistema LPP-Acervo.
Sua missão é responder à investigação do usuário baseando-se ESTRITAMENTE nas evidências fornecidas.

Investigação: {investigation.original_query}

EVIDÊNCIAS DISPONÍVEIS:
{context_text}

DIRETRIZES TÉCNICAS:
1. Responda apenas com base nas evidências acima. Se a resposta não estiver lá, declare a limitação.
2. Identifique quais evidências você utilizou e retorne os IDs exatos delas no array 'evidence_refs'.
3. Retorne EXCLUSIVAMENTE um objeto JSON válido, sem formatação markdown (```json).

ESTRUTURA DO JSON ESPERADA:
{{
    "content": "Sua resposta narrativa geral, conectando os pontos principais de forma analítica.",
    "sections": [
        {{
            "title": "Nome da Subseção (ex: Base Teórica)", 
            "content": "Conteúdo detalhado da subseção..."
        }}
    ],
    "evidence_refs": ["id-da-evidencia-1", "id-da-evidencia-2"]
}}
"""

        # 3. Execução Forçada (Structured Output)
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0 
                )
            )
            
            # 4. Deserialização e Validação do Contrato
            llm_output = json.loads(response.text)
            
            structured_response = StructuredResponse(
                response_id=str(uuid.uuid4()),
                content=llm_output.get("content", ""),
                sections=llm_output.get("sections", []),
                evidence_refs=llm_output.get("evidence_refs", []),
                references=[] 
            )
            
            return structured_response, evidences

        except json.JSONDecodeError:
            raise RuntimeError("O modelo falhou em retornar um JSON válido estruturado.")
        except Exception as e:
            raise RuntimeError(f"Falha na síntese do LLM: {str(e)}")