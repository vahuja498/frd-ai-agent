"""
app/services/llm_service.py
Supports OpenAI, Grok, and Ollama (local, free).
"""
import requests
from app.config import settings


class LLMService:

    def __init__(self) -> None:
        self._provider = settings.model_provider
        self._model = settings.active_model

        if self._provider == "ollama":
            self._base_url = "http://localhost:11434/api/generate"
            print(f"[LLMService] Provider: OLLAMA | Model: {self._model}")
        else:
            from openai import OpenAI
            kwargs = {"api_key": settings.active_api_key}
            if settings.active_base_url:
                kwargs["base_url"] = settings.active_base_url
            self._client = OpenAI(**kwargs)
            print(f"[LLMService] Provider: {self._provider.upper()} | Model: {self._model}")

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        if self._provider == "ollama":
            return self._ollama_complete(system_prompt, user_prompt)
        else:
            return self._openai_complete(system_prompt, user_prompt, temperature, max_tokens)

    def _ollama_complete(self, system_prompt: str, user_prompt: str) -> str:
        full_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"
        response = requests.post(
            self._base_url,
            json={
                "model": self._model,
                "prompt": full_prompt,
                "stream": False,
            },
            timeout=600,
        )
        response.raise_for_status()
        return response.json().get("response", "")

    def _openai_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    @property
    def model_name(self) -> str:
        return f"{self._provider}/{self._model}"