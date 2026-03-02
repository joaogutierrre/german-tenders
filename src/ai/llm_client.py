"""Unified Ollama LLM wrapper."""

import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the LLM call fails."""


class OllamaClient:
    """Client for the Ollama /api/generate endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout

    async def is_available(self) -> bool:
        """Check whether Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def generate(self, prompt: str, system: str = "") -> str:
        """Call Ollama generate endpoint and return the response text.

        Raises:
            LLMError: On timeout, connection, or unexpected API errors.
        """
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()["response"]
        except httpx.TimeoutException as exc:
            raise LLMError(f"Ollama timeout after {self.timeout}s") from exc
        except httpx.ConnectError as exc:
            raise LLMError(f"Cannot connect to Ollama at {self.base_url}") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"Ollama HTTP {exc.response.status_code}") from exc
        except KeyError as exc:
            raise LLMError("Unexpected Ollama response format") from exc
