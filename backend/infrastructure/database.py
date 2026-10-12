from httpx import (
    Client as HttpxClient,
    Timeout,
)

from supabase import (
    create_client,
    Client,
    ClientOptions,
)

from backend.config import settings


# ============================================================
# Cliente HTTP compartilhado pelo SDK do Supabase
# ============================================================
#
# O PostgREST 2.31.0 habilita HTTP/2 por padrão.
#
# Para evitar a utilização desse transporte durante a
# investigação da falha RemoteProtocolError, configuramos
# explicitamente HTTP/2 como desabilitado.
#
# O cliente continua utilizando HTTPS normalmente.
# Apenas o protocolo HTTP negociado é alterado.
#
# O timeout de leitura e de operação permanece em 120 s,
# equivalente ao timeout padrão do PostgREST 2.31.0.
# O estabelecimento da conexão possui limite de 10 s.
# ============================================================

supabase_http_client = HttpxClient(
    http2=False,
    timeout=Timeout(
        120.0,
        connect=10.0,
    ),
    follow_redirects=True,
)


# ============================================================
# Configuração do Supabase
# ============================================================

supabase_options = ClientOptions(
    httpx_client=supabase_http_client,
)


# ============================================================
# Cliente principal
# ============================================================

supabase_client: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key,
    options=supabase_options,
)