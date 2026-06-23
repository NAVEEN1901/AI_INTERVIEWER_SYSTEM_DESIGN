"""LLM Service - abstraction layer for LLM providers (OpenAI, Azure OpenAI, local)."""

import json
from typing import Optional

from openai import OpenAI, AzureOpenAI

from app.core.config import settings


class LLMService:
    """
    Unified LLM interface supporting OpenAI, Azure OpenAI, and compatible APIs.
    Falls back to rule-based generation when no API key is configured.
    """

    def __init__(self):
        self._client: Optional[OpenAI] = None
        self.model = getattr(settings, "LLM_MODEL", "gpt-4o-mini")
        self.api_key = getattr(settings, "OPENAI_API_KEY", "")
        self.azure_endpoint = getattr(settings, "AZURE_OPENAI_ENDPOINT", "")

    @property
    def client(self) -> Optional[OpenAI]:
        """Lazy-initialize LLM client."""
        if self._client is None and self.api_key:
            if self.azure_endpoint:
                self._client = AzureOpenAI(
                    api_key=self.api_key,
                    azure_endpoint=self.azure_endpoint,
                    api_version="2024-06-01",
                )
            else:
                self._client = OpenAI(api_key=self.api_key)
        return self._client

    @property
    def is_available(self) -> bool:
        """Check if LLM API is configured."""
        return bool(self.api_key)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[dict] = None,
    ) -> str:
        """Generate a completion from the LLM."""
        if not self.is_available:
            return ""

        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> dict:
        """Generate a JSON response from the LLM."""
        if not self.is_available:
            return {}

        response_text = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"raw_response": response_text}


# Singleton
llm_service = LLMService()
