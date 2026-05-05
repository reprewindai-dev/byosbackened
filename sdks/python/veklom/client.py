"""Veklom Python SDK — governed inference client."""
from __future__ import annotations

import httpx
from typing import Optional
from .models import CompleteResponse, CompletionRequest


DEFAULT_BASE_URL = "https://api.veklom.com/api/v1"


class VeklomClient:
    """
    Official Python client for the Veklom governed inference API.

    Usage::

        from veklom import VeklomClient

        client = VeklomClient(api_key="your-api-key")
        response = client.complete(prompt="Hello", model="qwen2.5:1.5b")
        print(response.text)
        print(response.audit_log_id)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ):
        if not api_key and not access_token:
            raise ValueError("Provide either api_key or access_token")

        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._token = api_key or access_token
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "X-Veklom-SDK": "python/0.1.0",
        }

    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        workspace_id: Optional[str] = None,
    ) -> CompleteResponse:
        """
        Send a governed inference request.

        Returns a CompleteResponse with:
        - text: the model output
        - audit_log_id: tamper-evident audit chain entry
        - provider: which provider executed (ollama | groq)
        - model: which model was used
        - tokens_used: total tokens consumed
        """
        payload = CompletionRequest(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            workspace_id=workspace_id,
        ).model_dump(exclude_none=True)

        with httpx.Client(timeout=self._timeout) as http:
            r = http.post(
                f"{self._base_url}/ai/complete",
                json=payload,
                headers=self._headers,
            )
            r.raise_for_status()
            return CompleteResponse(**r.json())

    async def complete_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        workspace_id: Optional[str] = None,
    ) -> CompleteResponse:
        """Async version of complete()."""
        payload = CompletionRequest(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            workspace_id=workspace_id,
        ).model_dump(exclude_none=True)

        async with httpx.AsyncClient(timeout=self._timeout) as http:
            r = await http.post(
                f"{self._base_url}/ai/complete",
                json=payload,
                headers=self._headers,
            )
            r.raise_for_status()
            return CompleteResponse(**r.json())
