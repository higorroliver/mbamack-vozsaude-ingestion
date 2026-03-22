"""
Cliente HTTP reutilizável com retry automático e timeout configurável.

Utiliza a biblioteca *tenacity* para política de retentativas e
*requests* para chamadas HTTP.
"""

from typing import Any

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)

from app.config.settings import HTTP_TIMEOUT, HTTP_RETRIES, HTTP_RETRY_WAIT
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HttpClient:
    """Wrapper para requisições HTTP com retry e tratamento de erro."""

    def __init__(
        self,
        timeout: int = HTTP_TIMEOUT,
        retries: int = HTTP_RETRIES,
        retry_wait: int = HTTP_RETRY_WAIT,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.retry_wait = retry_wait
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "VozesDaSaude-Ingestion/1.0",
            "Accept": "application/json",
        })

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        stream: bool = False,
    ) -> requests.Response:
        """Executa GET com retry automático."""
        return self._request("GET", url, params=params, headers=headers, stream=stream)

    def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        stream: bool = False,
    ) -> requests.Response:
        """Executa uma requisição HTTP com política de retry."""

        def _is_retryable(exc: BaseException) -> bool:
            """Retorna True se o erro é retentável (5xx, conexão, timeout)."""
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                return True
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                return exc.response.status_code >= 500
            return False

        @retry(
            stop=stop_after_attempt(self.retries),
            wait=wait_exponential(multiplier=self.retry_wait, min=2, max=60),
            retry=retry_if_exception(_is_retryable),
            before_sleep=before_sleep_log(logger, log_level=20),
            reraise=True,
        )
        def _do_request() -> requests.Response:
            logger.debug("Requisição %s → %s | params=%s", method, url, params)
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                timeout=self.timeout,
                stream=stream,
            )
            response.raise_for_status()
            return response

        return _do_request()

    def download_file(self, url: str, dest_path: str) -> str:
        """Baixa um arquivo em modo streaming e salva em *dest_path*."""
        logger.info("Download: %s → %s", url, dest_path)
        response = self.get(url, stream=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("Download concluído: %s", dest_path)
        return dest_path
