import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
import requests

class GeminiAPIError(RuntimeError):
    pass

@dataclass
class GeminiClient:
    api_key: Optional[str] = None
    model: Optional[str] = None
    timeout: int = 60
    max_retries: int = 2

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("GEMINI_API_KEY")
        self.model = self.model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        if not self.api_key:
            raise GeminiAPIError("GEMINI_API_KEY is missing.")

    @property
    def endpoint(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def generate(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
        temperature: float = 1.0,
        max_output_tokens: int = 4096,
    ) -> str:
        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_output_tokens},
        }

        if system_instruction:
            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

        headers = {
            "x-goog-api-key": self.api_key or "",
            "Content-Type": "application/json",
        }

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(self.endpoint, headers=headers, json=payload, timeout=self.timeout)
                if response.status_code == 429 and attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                if response.status_code >= 400:
                    raise GeminiAPIError(f"Gemini API error {response.status_code}: {response.text[:1000]}")
                
                return self._extract_text(response.json())
            except (requests.RequestException, ValueError, GeminiAPIError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                break

        raise GeminiAPIError(f"Gemini request failed: {last_error}")

    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> str:
        candidates = data.get("candidates", [])
        if not candidates:
            raise GeminiAPIError(f"No candidates returned by Gemini: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if part.get("text")]
        text = "\n".join(texts).strip()
        if not text:
            raise GeminiAPIError(f"Gemini returned empty text: {data}")
        return text
