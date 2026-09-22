import json
import uuid
from typing import List

from google import genai
from google.genai import types

from backend.config import settings
from backend.domain.entities import (
    Investigation,
    RetrievalResult,
    Evidence,
    StructuredResponse,
)
from backend.domain.repositories import (
    EvidenceRepository,
    InvestigationRepository,
)


class SynthesisService:
    """
    Transforma RetrievalResults em Evidence e produz uma
    StructuredResponse baseada exclusivamente nas evidências.

    Responsabilidades:
        1. Materializar Evidence a partir dos resultados recuperados.
        2. Persistir as Evidence.
        3. Construir o contexto enviado ao LLM.
        4. Validar/deserializar a resposta estruturada.
        5. Persistir a StructuredResponse na Investigation.

    O serviço não trata RetrievalResult como evidência metodológica
    automaticamente. A Evidence é uma entidade derivada do resultado
    recuperado, com sua própria identidade e proveniência.
    """

    def __init__(
        self,
        evidence_repo: EvidenceRepository,
        investigation_repo: InvestigationRepository,
    ):
        self.evidence_repo = evidence_repo
        self.investigation_repo = investigation_repo

        self.model = settings.gemini_llm_model

        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )
        
    def synthesize(
        self,
        investigation: Investigation,
        results: List[RetrievalResult],
    ) -> tuple[StructuredResponse, List[Evidence]]:

        # ========================================================
        # 1. MATERIALIZAÇÃO DAS EVIDÊNCIAS
        # ========================================================

        evidences: List[Evidence] = []

        for result in results:

            document_id = result.metadata.get(
                "document_id",
                "",
            )

            location = result.metadata.get(
                "location",
                {},
            )

            content = result.metadata.get(
                "content",
                "",
            )

            evidence = Evidence(
                evidence_id=str(uuid.uuid4()),
                investigation_id=result.investigation_id,
                unit_id=result.unit_id,
                document_id=document_id,
                location=location,
                content=content,
                context=(
                    f"Documento ID: {document_id}"
                ),
                provenance={
                    "investigation_id": (
                        result.investigation_id
                    ),
                    "result_id": result.result_id,
                    "unit_id": result.unit_id,
                    "document_id": document_id,
                    "location": location,
                },
            )

            evidences.append(evidence)

        # A Evidence passa a existir independentemente
        # da resposta do LLM.
        self.evidence_repo.save_batch(evidences)

        # ========================================================
        # 2. CONSTRUÇÃO DO CONTEXTO PARA O LLM
        # ========================================================

        context_blocks = []

        for evidence in evidences:

            block = (
                f"--- INÍCIO DA EVIDÊNCIA "
                f"[{evidence.evidence_id}] ---\n"
                f"{evidence.content}\n"
                f"--- FIM DA EVIDÊNCIA ---"
            )

            context_blocks.append(block)

        context_text = "\n\n".join(context_blocks)

        # ========================================================
        # 3. PROMPT DE SÍNTESE
        # ========================================================

        prompt = f"""
Você é um assistente acadêmico do sistema Snoopy-RAG.

Sua função é sintetizar uma resposta para a investigação
do usuário utilizando exclusivamente as evidências fornecidas.

INVESTIGAÇÃO:
{investigation.original_query}

EVIDÊNCIAS DISPONÍVEIS:
{context_text}

REGRAS:

1. Responda somente com base nas evidências fornecidas.

2. Não invente informações ausentes nas evidências.

3. Quando as evidências forem insuficientes para responder
   determinada parte da investigação, declare explicitamente
   essa limitação.

4. Identifique as evidências utilizadas na resposta por meio
   de seus IDs exatos.

5. Não trate similaridade de recuperação como prova de
   relevância metodológica.

6. Retorne exclusivamente um objeto JSON válido.

7. Não utilize Markdown ou blocos de código na resposta.

ESTRUTURA OBRIGATÓRIA:

{{
    "content": "Resposta narrativa geral.",
    "sections": [
        {{
            "title": "Título da seção",
            "content": "Conteúdo da seção."
        }}
    ],
    "evidence_refs": [
        "id-da-evidencia-utilizada"
    ]
}}
"""

        # ========================================================
        # 4. EXECUÇÃO DO LLM
        # ========================================================

        try:

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )

        except Exception as exc:

            self.investigation_repo.update_status(
                investigation.investigation_id,
                "FAILED",
            )

            raise RuntimeError(
                f"Falha na execução do modelo de síntese: {exc}"
            ) from exc

        # ========================================================
        # 5. VALIDAÇÃO DA RESPOSTA ESTRUTURADA
        # ========================================================

        try:

            llm_output = json.loads(response.text)

        except (json.JSONDecodeError, TypeError) as exc:

            self.investigation_repo.update_status(
                investigation.investigation_id,
                "FAILED",
            )

            raise RuntimeError(
                "O modelo não retornou um JSON válido."
            ) from exc

        if not isinstance(llm_output, dict):
            self.investigation_repo.update_status(
                investigation.investigation_id,
                "FAILED",
            )

            raise RuntimeError(
                "A resposta do modelo não possui estrutura JSON de objeto."
            )

        # ========================================================
        # 6. MATERIALIZAÇÃO DA STRUCTURED RESPONSE
        # ========================================================

        structured_response = StructuredResponse(
            response_id=str(uuid.uuid4()),
            content=llm_output.get(
                "content",
                "",
            ),
            sections=llm_output.get(
                "sections",
                [],
            ),
            evidence_refs=llm_output.get(
                "evidence_refs",
                [],
            ),
            references=llm_output.get(
                "references",
                [],
            ),
        )

        # ========================================================
        # 7. VALIDAÇÃO BÁSICA DAS REFERÊNCIAS
        # ========================================================

        valid_evidence_ids = {
            evidence.evidence_id
            for evidence in evidences
        }

        invalid_refs = [
            ref
            for ref in structured_response.evidence_refs
            if ref not in valid_evidence_ids
        ]

        if invalid_refs:
            self.investigation_repo.update_status(
                investigation.investigation_id,
                "FAILED",
            )

            raise RuntimeError(
                "A StructuredResponse contém referências "
                "para evidências inexistentes: "
                f"{invalid_refs}"
            )

        # ========================================================
        # 8. PERSISTÊNCIA DA STRUCTURED RESPONSE
        # ========================================================

        self.investigation_repo.save_structured_response(
            investigation.investigation_id,
            structured_response.model_dump(
                mode="json",
            ),
        )

        return structured_response, evidences