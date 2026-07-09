from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .costing import normalize_token_usage


class LLMProviderError(RuntimeError):
    pass


class LLMProvider(Protocol):
    provider_name: str
    model: str | None

    def generate_plan(
        self,
        *,
        task: dict[str, Any],
        retrieved_knowledge: list[dict[str, Any]],
        baseline_plan: dict[str, Any],
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        ...


Transport = Callable[..., dict[str, Any]]
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-flash"


@dataclass
class OpenAICompatibleProvider:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 60
    max_tokens: int = 2400
    transport: Transport | None = None

    provider_name: str = "openai-compatible"
    last_usage: dict[str, int] = field(default_factory=lambda: normalize_token_usage(None), init=False)
    last_response_metadata: dict[str, Any] = field(default_factory=dict, init=False)
    _last_transport_name: str = field(default="urllib", init=False)

    def generate_plan(
        self,
        *,
        task: dict[str, Any],
        retrieved_knowledge: list[dict[str, Any]],
        baseline_plan: dict[str, Any],
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": _build_messages(
                task=task,
                retrieved_knowledge=retrieved_knowledge,
                baseline_plan=baseline_plan,
                output_schema=output_schema,
            ),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = self._send_json(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            headers=headers,
            payload=payload,
            timeout=self.timeout,
        )
        self.last_usage = normalize_token_usage(response.get("usage"))
        self.last_response_metadata = {
            "usage": self.last_usage,
            "model": response.get("model", self.model),
            "id": response.get("id"),
            "transport": self._last_transport_name,
        }
        content = _extract_message_content(response)
        return _parse_json_content(content)

    def _send_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: int,
    ) -> dict[str, Any]:
        if self.transport:
            self._last_transport_name = "custom"
            return self.transport(url=url, headers=headers, payload=payload, timeout=timeout)
        try:
            self._last_transport_name = "urllib"
            return _urllib_transport(url=url, headers=headers, payload=payload, timeout=timeout)
        except LLMProviderError as primary_error:
            try:
                self._last_transport_name = "curl"
                return _curl_transport(url=url, headers=headers, payload=payload, timeout=timeout)
            except LLMProviderError as fallback_error:
                self._last_transport_name = "urllib"
                raise LLMProviderError(
                    f"{primary_error}; curl fallback failed: {fallback_error}"
                ) from fallback_error


def build_llm_provider(
    provider_name: str | None,
    *,
    api_key: str | None = None,
    api_key_env: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> LLMProvider | None:
    normalized = (provider_name or "none").strip().lower()
    if normalized in {"none", "offline", "rule-based"}:
        return None
    if normalized in {"deepseek", "deepseek-chat"}:
        return _build_openai_compatible_provider(
            provider_name="deepseek",
            api_key=api_key,
            api_key_env=api_key_env or "DEEPSEEK_API_KEY",
            model=model or os.getenv("DEEPSEEK_MODEL") or DEEPSEEK_DEFAULT_MODEL,
            base_url=base_url or os.getenv("DEEPSEEK_BASE_URL") or DEEPSEEK_BASE_URL,
        )
    if normalized not in {"openai-compatible", "openai"}:
        raise LLMProviderError(f"unsupported LLM provider: {provider_name}")

    return _build_openai_compatible_provider(
        provider_name="openai-compatible",
        api_key=api_key,
        api_key_env=api_key_env or "OPENAI_API_KEY",
        model=model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
        base_url=base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1",
    )


def _build_openai_compatible_provider(
    *,
    provider_name: str,
    api_key: str | None,
    api_key_env: str,
    model: str,
    base_url: str,
) -> OpenAICompatibleProvider:
    resolved_api_key = api_key or os.getenv(api_key_env)
    if not resolved_api_key:
        raise LLMProviderError(f"missing API key: set {api_key_env} or pass api_key")

    return OpenAICompatibleProvider(
        api_key=resolved_api_key,
        model=model,
        base_url=base_url,
        provider_name=provider_name,
    )


def _build_messages(
    *,
    task: dict[str, Any],
    retrieved_knowledge: list[dict[str, Any]],
    baseline_plan: dict[str, Any],
    output_schema: dict[str, Any],
) -> list[dict[str, str]]:
    system_prompt = (
        "You are a UAV mission planning assistant. "
        "Return JSON only, using recommendations, risks, and mission_config fields. "
        "Preserve concrete mission constraints from the parsed task."
    )
    user_payload = {
        "task": task,
        "retrieved_knowledge": retrieved_knowledge,
        "baseline_plan": baseline_plan,
        "output_schema": output_schema,
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
    ]


def _urllib_transport(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except OSError as exc:
        raise LLMProviderError(f"LLM provider request failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise LLMProviderError("LLM provider returned invalid JSON response") from exc


def _curl_transport(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    curl_path = shutil.which("curl.exe") or shutil.which("curl")
    if not curl_path:
        raise LLMProviderError("curl executable is not available")

    command = [
        curl_path,
        "-sS",
        "--fail-with-body",
        "--max-time",
        str(timeout),
        "-X",
        "POST",
        url,
    ]
    for key, value in headers.items():
        command.extend(["-H", f"{key}: {value}"])
    command.extend(["--data-binary", "@-"])

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        completed = subprocess.run(
            command,
            input=body,
            capture_output=True,
            timeout=timeout + 5,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise LLMProviderError("curl request timed out") from exc
    except OSError as exc:
        raise LLMProviderError(f"curl request failed to start: {exc}") from exc

    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        details = _redact_header_values((stderr or stdout).strip(), headers)
        raise LLMProviderError(f"curl request failed with exit code {completed.returncode}: {details[:500]}")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        details = _redact_header_values(stdout.strip(), headers)
        raise LLMProviderError(f"curl returned invalid JSON response: {details[:500]}") from exc


def _redact_header_values(text: str, headers: dict[str, str]) -> str:
    redacted = text
    for value in headers.values():
        if value and len(value) > 8:
            redacted = redacted.replace(value, "[redacted]")
    return redacted


def _extract_message_content(response: dict[str, Any]) -> str:
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError("LLM provider response does not contain choices[0].message.content") from exc


def _parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMProviderError("LLM provider message content is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise LLMProviderError("LLM provider message content must be a JSON object")
    return parsed
