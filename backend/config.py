import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """
    Configuração central da aplicação.

    O backend não deve acessar variáveis de ambiente diretamente.
    Os demais módulos devem consumir esta configuração através de
    `settings`.
    """

    def __init__(self):
        self.environment = os.getenv(
            "ENVIRONMENT",
            "development",
        )

        self.api_port = int(
            os.getenv(
                "API_PORT",
                "3000",
            )
        )

        # Google / Drive
        self.google_api_key = self._required(
            "GOOGLE_API_KEY"
        )

        self.google_app_id = self._required(
            "GOOGLE_APP_ID"
        )

        # Supabase
        self.supabase_url = self._required(
            "SUPABASE_URL"
        )

        self.supabase_key = self._required(
            "SUPABASE_KEY"
        )

        self.supabase_service_key = self._required(
            "SUPABASE_SERVICE_KEY"
        )

        # Gemini
        self.gemini_api_key = self._required(
            "GEMINI_API_KEY"
        )

        self.gemini_llm_model = self._required(
            "GEMINI_LLM_MODEL"
        )

        self.gemini_embedding_model = self._required(
            "GEMINI_EMBEDDING_MODEL"
        )

        # Retrieval
        self.retrieval_default_limit = int(
            os.getenv(
                "RETRIEVAL_DEFAULT_LIMIT",
                "10",
            )
        )

        self.retrieval_max_limit = int(
            os.getenv(
                "RETRIEVAL_MAX_LIMIT",
                "50",
            )
        )

        self.gemini_embedding_batch_size = int(
            os.getenv(
                "GEMINI_EMBEDDING_BATCH_SIZE",
                "5",
            )
        )

    @staticmethod
    def _required(name: str) -> str:
        value = os.getenv(name)

        if not value:
            raise RuntimeError(
                f"{name} não configurada no ambiente."
            )

        return value

settings = Settings()